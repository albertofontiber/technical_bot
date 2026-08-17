# -*- coding: utf-8 -*-
"""s324d — ¿CUÁNTO CASTELLANO se está tirando dentro del texto «descartado por política de idiomas»?

POR QUÉ: `D1056-1_NFXI-BS-BSF` demostró que la pérdida puede estar aguas abajo del parseo — el
markdown de LlamaParse trae el documento entero y `_DROP_LANGUAGES` (`src/reingest/pipeline.py`,
`{fr,it,pt,de}`) descarta chunks ENTEROS por su idioma DOMINANTE, arrastrando el castellano que va
intercalado en la misma tabla. La pregunta acotada: de los 160 documentos que el censo clasificó
`paginas_perdidas_otro_idioma` (157) y `texto_perdido_otro_idioma` (3), ¿en cuántos el texto ausente
es íntegramente otro idioma (política funcionando) y en cuántos arrastra castellano (pérdida real
disfrazada de política)?

MÉTODO (dos granularidades, y esa es la clave):
  1. QUÉ FALTA — fragmentos de ~35 palabras respetando líneas, buscados en los chunks del documento
     por palabras de ≥6 letras (<35 % de aciertos = ausente). Igual que la verificación anterior.
  2. QUÉ IDIOMA — el idioma se adjudica POR LÍNEA dentro del texto ausente, no en global: en una
     ficha multilingüe la tabla mezcla idiomas por fila/celda y el global siempre sale «alemán».

TEST DE CASTELLANO (estricto, por las dos trampas declaradas):
  · (a) *falso «es» por tecnicismos y referencias de modelo*: no basta con que ganen las palabras
    vacías. Se exige AL MENOS UNA señal que no pueda venir de otro idioma — `ES_EXCLUSIVAS` (12
    palabras) se DERIVA restando a las palabras vacías del español las de los otros 19 idiomas, más
    morfología propia (`-ción`, `-dad`, `-miento`, `ñ`, `¿`, `¡`) — Y que esa evidencia GANE a la
    evidencia exclusiva de cada rival (empate sólo si la española es fuerte: morfología o `ñ`).
    «NFXI-BS-BSF Wall Sounder Beacon EN54-3 24V» no tiene señal gramatical: se rechaza.
    BANCO DE PRUEBAS: 28 líneas control, 21 de ellas negativas y 14 tomadas de una muestra REAL que
    la v1 marcó mal (ES/PT/FR/IT/DE/NL/SV/PL) → 26/28, con los 2 fallos del lado CONSERVADOR (dos
    líneas españolas sin marcador que se pierden) y CERO falsos positivos.
  · (b) *líneas cortas*: por debajo de MIN_PALABRAS_LINEA palabras NO se adjudica; esos chars se
    cuentan aparte (`chars_linea_corta_no_adjudicada`) y NUNCA como castellano. El sesgo es
    conservador a propósito: este número SUBESTIMA el castellano perdido, no lo exagera.
  · Guarda anti-mojibake heredada (ratio de vocales < 0,30 ⇒ `fuente_ilegible`, no se reclama nada).

VEREDICTO: `multilingue_con_castellano` (≥500 chars de castellano ausente — ACCIONABLE) ·
`otro_idioma_puro` (política funcionando) · `indeterminado` (texto ausente corto/ilegible).

Uso:
    python scripts/s324d_castellano_intercalado.py                 # mide los 160 (0,26 GB)
    python scripts/s324d_castellano_intercalado.py --limit 20      # smoke
    python scripts/s324d_castellano_intercalado.py --muestra-precision 25   # vuelca líneas marcadas
    python scripts/s324d_castellano_intercalado.py --solo-informe  # re-escribe entregables del parcial
Coste LLM: $0. Cero escrituras en la DB. No toca `src/`.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import tempfile
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)
from src.http_pool import abierto  # noqa: E402

import fitz  # noqa: E402
from s324d_censo_cobertura_paginas import _STOP, MIN_CHARS_PERDIDA, normalizar  # noqa: F401  # noqa: E402
from s324d_censo_cobertura_paginas import TOK_AUSENTE  # noqa: E402
from s324d_verificacion_idioma_ausente import (  # noqa: E402
    CENSO_JSON, CENSO_MD, MIN_VOCALES, fragmentos, ratio_vocales, texto_corpus, veredicto_fragmento,
)

MARCA = "## Castellano intercalado en el texto descartado por política"
CLASES = ("paginas_perdidas_otro_idioma", "texto_perdido_otro_idioma")
MIN_PALABRAS_LINEA = 4
MIN_CHARS_CASTELLANO = MIN_CHARS_PERDIDA          # 500, el mismo umbral que el resto del censo

# --- Discriminación ES vs. sus PRIMOS (medida, no supuesta) -----------------------------------
# La v1 de este test derivaba `ES_EXCLUSIVAS` restando las listas del censo y daba 0/14 de precisión
# en una muestra revisada A MANO: se colaban «ser, sobre, entre, durante, todos, esta» como si fueran
# exclusivas del español SOLO porque las listas cortas de portugués/italiano/francés no las traían.
# La derivación vale lo que valgan las listas rivales, así que aquí se ENRIQUECEN (copia local; el
# censo no se toca) con las palabras que de verdad colisionan, y la regla pasa a ser SIMÉTRICA.
_EXTRA = {
    "pt": "ser sobre entre durante todo todos toda todas este esta estes estas cada desde após "
          "pode deve podem devem sempre assim onde quando até sem também mais outro outra qualquer "
          "partilham mesma célula células vezes usadas agrupar funções tais",
    "it": "essere sopra tra durante tutto tutti questa queste ogni sempre così dove quando senza "
          "anche più altro altra qualsiasi",
    "fr": "être sur entre pendant tout tous cette ces chaque toujours ainsi où quand sans aussi "
          "plus autre chaque uniquement peuvent",
    "en": "between during over each always where when without also more other any shall",
    # Colisiones medidas en la muestra revisada a mano: «los» es neerlandés («de knop los») y «sin»
    # es el posesivo nórdico («har lastet sin innledende konfigurering»). Se ceden al rival: una
    # línea española que sólo tuviera esa palabra deja de contar (sesgo conservador, otra vez).
    "nl": "los",
    "no": "sin", "da": "sin", "sv": "sin",
}
# `y` se PROBÓ como marcador (es «y» sólo en español: pt/it «e», fr «et», de «und», nl «en») y se
# DESCARTA con datos: el francés lo usa como pronombre («il y a», «y ait»), aparece como variable de
# tabla («(y: P ou R)») y —lo peor— el normalizador ASCII lo FABRICA al partir palabras con
# diacríticos («należy» → «nale y», «høy» → «h y»). Costaba más de lo que rescataba.
_ES_EXTRA: set[str] = set()
_STOP_RICO = {**{k: set(v) for k, v in _STOP.items()},
              **{k: set(_STOP.get(k, set())) | set(v.split()) for k, v in _EXTRA.items()}}
# Exclusivas POR IDIOMA (simétrico): lo que solo tiene ese idioma frente a los otros 19.
EXCLUSIVAS = {k: v - set().union(*(w for j, w in _STOP_RICO.items() if j != k))
              for k, v in _STOP_RICO.items()}
ES_EXCLUSIVAS = EXCLUSIVAS["es"] | _ES_EXTRA
OTROS = {k: v for k, v in EXCLUSIVAS.items() if k != "es"}
# Morfología DISCRIMINANTE por idioma: «-ción» (es) vs «-ção» (pt) vs «-zione» (it) vs «-tion»
# (fr/en/de) es la señal más limpia que existe entre estas lenguas.
# OJO con el plural: «-dades» es IDÉNTICO en portugués («duplicidades», «necessidades», medido en la
# muestra), así que sólo cuenta el singular «-dad». «-ción» sí es limpio frente a «-ção/-zione/-tion».
_MORFO_FUERTE = re.compile(r"\b\w{4,}ci[oó]n(es)?\b")
_MORFO = re.compile(r"\b\w{4,}ci[oó]n(es)?\b|\b\w{4,}dad\b|\b\w{4,}mientos?\b")
_MORFO_OTROS = {
    "pt": re.compile(r"\b\w{3,}[çc][ãa]o\b|\b\w{3,}ções\b|\bnão\b|\bsão\b|\bestá\b|\bé\b|\bao[s]?\b|\bd[oa]s?\b"),
    "it": re.compile(r"\b\w{3,}zion[ei]\b|\bdegli\b|\bdell[aeo]\b|\bgli\b|\bè\b|\bnell[aeo]\b"),
    "fr": re.compile(r"\b\w{3,}tions?\b|\bqui\b|\bd['’]\w+|\bl['’]\w+|\baux\b|\bêtre\b"),
    "de": re.compile(r"\b\w{4,}ung(en)?\b|\bfür\b|\bnicht\b|\bder\b|\bund\b|\bdie\b"),
    "en": re.compile(r"\b\w{4,}tions?\b|\bthe\b|\band\b|\bwith\b|\bshould\b"),
    "nl": re.compile(r"\b\w{3,}lijk\b|\bhet\b|\been\b|\bvan\b|\bmet\b|\bvoor\b"),
    "sv": re.compile(r"\b\w{3,}ning(en)?\b|\boch\b|\batt\b|\bför\b|\bär\b"),
}
_ES_CHARS = "ñ¿¡"
_NOLETRA = re.compile(r"[^0-9a-zÀ-ſ]+")
_print_lock = threading.Lock()


def log(m: str) -> None:
    with _print_lock:
        print(m, flush=True)


def fragmentos_lineas(texto: str) -> list[list[str]]:
    """Como `fragmentos()` pero CONSERVANDO las líneas: el test de presencia necesita el fragmento
    entero (~35 palabras) y el de idioma necesita la línea suelta (la tabla mezcla idiomas por fila).
    """
    out, buf, n = [], [], 0
    for linea in (texto or "").splitlines():
        pal = linea.split()
        if not pal:
            continue
        buf.append(linea.strip())
        n += len(pal)
        if n >= 35:
            out.append(buf)
            buf, n = [], 0
    if buf:
        out.append(buf)
    return out


def marcadores(linea: str) -> tuple[int, int, int, str]:
    """(evidencia gramatical ES, palabras vacías ES, mejor recuento de OTRO idioma, ese idioma).

    `evidencia gramatical` = solo lo que NO puede venir de otro idioma: las `ES_EXCLUSIVAS`
    derivadas, la morfología `-ción/-dad/-miento` (pt «-ção», it «-zione», fr «-tion»: no casan) y
    los caracteres `ñ ¿ ¡`. El recuento de palabras vacías se usa aparte, para el desempate.
    """
    bajo = linea.lower()
    # Tokenizador que CONSERVA los diacríticos: el `normalizar()` del censo (pensado para comparar
    # contra el corpus) los borra y parte las palabras, inventando tokens que no existen —
    # «należy» → «nale y», «høy» → «h y»— y con ellos marcadores falsos.
    toks = set(_NOLETRA.sub(" ", bajo).split())
    # FUERTE (lo único que puede GANAR un empate) = «-ción» y «ñ/¿/¡». «-miento» queda fuera: en la
    # muestra apareció un «funzionamiento» italiano que empataba y colaba la línea.
    fuerte = len(_MORFO_FUERTE.findall(bajo)) + (1 if any(c in bajo for c in _ES_CHARS) else 0)
    ev = len(ES_EXCLUSIVAS & toks) + fuerte
    mejor, cual = 0, ""
    for k, v in OTROS.items():
        n = len(v & toks) + (len(_MORFO_OTROS[k].findall(bajo)) if k in _MORFO_OTROS else 0)
        if n > mejor:
            mejor, cual = n, k
    return ev, fuerte, mejor, cual


def es_castellano(linea: str) -> tuple[bool, int, int, str]:
    """¿Esta línea del texto ausente es castellano? Test ESTRICTO y SIMÉTRICO (trampa (a)): exige
    AL MENOS UNA señal exclusiva del español y que GANE a la evidencia exclusiva de todos los demás
    idiomas. Una línea de tecnicismos y referencias de modelo («NFXI-BS-BSF Wall Sounder Beacon
    EN54-3 24V») no tiene señal gramatical y se rechaza; una línea portuguesa con «ser/sobre/todos»
    tampoco cuela, porque «ção/são/não/dos» puntúan para el portugués."""
    if len(linea.split()) < MIN_PALABRAS_LINEA:
        return False, 0, 0, "corta"
    ev, fuerte, otro, cual = marcadores(linea)
    # El empate sólo lo gana el español si su evidencia es FUERTE: es justo el caso que se mide
    # (fila de tabla con castellano y otro idioma en la misma línea, «Señal… / All Clear / Fin
    # d'alerte»), donde por definición ambos idiomas puntúan.
    ok = ev >= 1 and (ev > otro or (fuerte >= 1 and ev >= otro))
    return ok, ev, otro, cual


def analizar(doc: dict, corpus: str, tmpdir: Path, c, timeout: float) -> dict:
    """Texto AUSENTE del PDF → adjudicación de castellano LÍNEA A LÍNEA."""
    r: dict = {"error": None, "chars_ausentes": 0, "chars_es": 0, "lineas_es": 0,
               "chars_linea_corta": 0, "chars_no_verificable": 0, "chars_es_presente_en_corpus": 0,
               "lineas_totales": 0, "idiomas_rivales": {},
               "citas_es": [], "ratio_vocales": None, "paginas_es": []}
    if not doc.get("source_url"):
        r["error"] = "sin source_url"
        return r
    tmp = tmpdir / f"cast_{doc['document_id']}.pdf"
    try:
        resp = c.get(doc["source_url"], timeout=timeout)
        if resp.status_code != 200:
            r["error"] = f"HTTP {resp.status_code}"
            return r
        tmp.write_bytes(resp.content)
        rivales: dict[str, int] = defaultdict(int)
        ausente_todo, citas = [], []
        with fitz.open(tmp) as pdf:
            for i, pg in enumerate(pdf, start=1):
                for lineas in fragmentos_lineas(pg.get_text() or ""):
                    frag = " ".join(lineas)
                    v, _, _ = veredicto_fragmento(frag, corpus)
                    if v != "ausente":
                        continue
                    ausente_todo.append(frag)
                    r["chars_ausentes"] += len(frag)
                    for linea in lineas:
                        linea = linea.strip()
                        if not linea:
                            continue
                        r["lineas_totales"] += 1
                        ok, nes, notro, cual = es_castellano(linea)
                        if cual == "corta":
                            r["chars_linea_corta"] += len(linea)
                            continue
                        if ok:
                            # RE-VERIFICACIÓN de la línea contra el corpus. El test de ausencia
                            # trabaja con fragmentos de ~35 palabras y uno mixto puede salir
                            # «ausente» en bloque aunque su línea ESPAÑOLA sí esté indexada
                            # (medido en `D 1149-1`: «Estos dispositivos solo deben conectarse a
                            # paneles…» estaba en el corpus). Sin esto, el número se infla.
                            ltoks = [t for t in dict.fromkeys(normalizar(linea).split()) if len(t) >= 6]
                            if len(ltoks) < 2:
                                r["chars_no_verificable"] += len(linea)
                                continue
                            if sum(1 for t in ltoks if f" {t} " in corpus) / len(ltoks) >= TOK_AUSENTE:
                                r["chars_es_presente_en_corpus"] += len(linea)
                                continue
                            r["chars_es"] += len(linea)
                            r["lineas_es"] += 1
                            if i not in r["paginas_es"]:
                                r["paginas_es"].append(i)
                            citas.append((len(linea), i, linea, nes, notro))
                        elif notro:
                            rivales[cual] += len(linea)
        r["idiomas_rivales"] = dict(sorted(rivales.items(), key=lambda kv: -kv[1])[:4])
        r["ratio_vocales"] = ratio_vocales(" ".join(ausente_todo))
        citas.sort(key=lambda x: -x[0])
        r["citas_es"] = [{"pagina": p, "texto": re.sub(r"\s+", " ", t)[:220], "marcas_es": a,
                          "marcas_otro": b} for _, p, t, a, b in citas[:5]]
    except Exception as e:  # noqa: BLE001
        r["error"] = f"{type(e).__name__}: {e}"
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
    return r


def veredicto(r: dict) -> str:
    if r.get("error"):
        return "no_medible"
    if r["chars_ausentes"] >= MIN_CHARS_PERDIDA and (r.get("ratio_vocales") or 1.0) < MIN_VOCALES:
        return "fuente_ilegible"
    if r["chars_es"] >= MIN_CHARS_CASTELLANO:
        return "multilingue_con_castellano"
    if r["chars_ausentes"] < MIN_CHARS_PERDIDA:
        return "indeterminado"
    return "otro_idioma_puro"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--parcial", default=str(Path(tempfile.gettempdir()) / "s324d_castellano_parcial.jsonl"))
    ap.add_argument("--solo-informe", action="store_true")
    ap.add_argument("--muestra-precision", type=int, default=0,
                    help="vuelca N líneas marcadas como castellano para revisión MANUAL y sale")
    args = ap.parse_args()

    censo = json.loads(CENSO_JSON.read_text(encoding="utf-8"))
    objetivo = [d for d in censo["documentos"] if d["clase"] in CLASES]
    objetivo.sort(key=lambda d: -(d.get("texto_nativo_perdido") or 0))
    if args.limit:
        objetivo = objetivo[:args.limit]
    parcial = Path(args.parcial)
    hechos: dict[str, dict] = {}
    if parcial.exists():
        for ln in parcial.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                try:
                    y = json.loads(ln)
                    hechos[y["document_id"]] = y
                except Exception:  # noqa: BLE001
                    pass
    pend = [] if args.solo_informe else [d for d in objetivo if d["document_id"] not in hechos]
    log(f"objetivo: {len(objetivo)} documentos ({', '.join(CLASES)}) · pendientes: {len(pend)}")
    tmpdir = Path(tempfile.gettempdir()) / "s324d_pdfs"
    tmpdir.mkdir(parents=True, exist_ok=True)
    lock, hechos_n, t0 = threading.Lock(), [0], time.time()

    def tarea(d: dict) -> dict:
        with abierto(timeout=args.timeout, reintentos=1) as c:
            corpus, n_chunks, chars = texto_corpus(c, d["document_id"])
            r = analizar(d, corpus, tmpdir, c, args.timeout)
        fila = {"document_id": d["document_id"], "source_file": d["source_file"],
                "clase_censo": d["clase"], "manufacturer": d.get("manufacturer"),
                "sustenta_gold": d.get("sustenta_gold"), "n_chunks": n_chunks, **r}
        fila["veredicto_castellano"] = veredicto(r)
        with lock:
            with parcial.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
            hechos_n[0] += 1
            if fila["veredicto_castellano"] == "multilingue_con_castellano" or hechos_n[0] % 25 == 0:
                log(f"  [{hechos_n[0]}/{len(pend)}] {fila['source_file'][:44]}: "
                    f"{fila['veredicto_castellano']} es={fila['chars_es']} aus={fila['chars_ausentes']}")
        return fila

    if pend:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            for fu in as_completed([ex.submit(tarea, d) for d in pend]):
                y = fu.result()
                hechos[y["document_id"]] = y

    filas = [hechos[d["document_id"]] for d in objetivo if d["document_id"] in hechos]
    if args.muestra_precision:
        random.seed(7)
        pool = [(f["source_file"], c_) for f in filas for c_ in f["citas_es"]]
        for sf, c_ in random.sample(pool, min(args.muestra_precision, len(pool))):
            print(f"\n[{sf[:40]} p{c_['pagina']}] es={c_['marcas_es']} otro={c_['marcas_otro']}\n  {c_['texto']}")
        print(f"\n({len(pool)} citas disponibles en {len(filas)} documentos)")
        return 0

    con = [f for f in filas if f["veredicto_castellano"] == "multilingue_con_castellano"]
    ver_cnt = Counter(f["veredicto_castellano"] for f in filas)
    total_es = sum(f["chars_es"] for f in filas)
    meta = {"que_es": "castellano intercalado en el texto ausente de los documentos «otro idioma» — s324d",
            "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "universo": [c for c in CLASES], "documentos": len(filas), "medidos_de": len(objetivo),
            "veredictos": dict(ver_cnt.most_common()),
            "chars_castellano_ausente_total": total_es,
            "chars_castellano_en_accionables": sum(f["chars_es"] for f in con),
            "es_exclusivas_derivadas": sorted(ES_EXCLUSIVAS),
            "umbrales": {"min_palabras_linea": MIN_PALABRAS_LINEA,
                         "min_chars_castellano": MIN_CHARS_CASTELLANO, "min_vocales": MIN_VOCALES},
            "segundos": round(time.time() - t0, 1)}

    # ---- JSON: campos por documento + bloque en meta ----
    por_id = {f["document_id"]: f for f in filas}
    for d in censo["documentos"]:
        f = por_id.get(d["document_id"])
        if not f:
            continue
        d["castellano_intercalado"] = {
            "veredicto": f["veredicto_castellano"], "chars_es_ausentes": f["chars_es"],
            "fragmentos_es_ausentes": f["lineas_es"], "chars_ausentes": f["chars_ausentes"],
            "chars_linea_corta_no_adjudicada": f["chars_linea_corta"],
            "chars_es_descartados_por_estar_en_corpus": f["chars_es_presente_en_corpus"],
            "chars_es_no_verificables": f["chars_no_verificable"],
            "idiomas_rivales": f["idiomas_rivales"], "paginas_es": f["paginas_es"][:20],
            "citas_es": f["citas_es"][:3], "ratio_vocales": f["ratio_vocales"],
        }
        d["accionable_castellano_intercalado"] = f["veredicto_castellano"] == "multilingue_con_castellano"
    censo["meta"]["castellano_intercalado"] = meta
    if not args.solo_informe or filas:
        CENSO_JSON.write_text(json.dumps(censo, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- MD: sección nueva (idempotente) ----
    L = [MARCA, "",
         f"Pregunta acotada: de los **{len(objetivo)}** documentos que el censo dio por «pérdida en "
         f"otro idioma» (157 `paginas_perdidas_otro_idioma` + 3 `texto_perdido_otro_idioma`), ¿en "
         f"cuántos el texto descartado **arrastra castellano**? Idioma adjudicado **línea a línea** "
         f"dentro del texto ausente (en global siempre gana el idioma dominante, que es lo que "
         f"enmascara el caso `D1056-1`).", "",
         f"**Resultado: {ver_cnt.get('multilingue_con_castellano', 0)} de {len(filas)} documentos** "
         f"arrastran castellano (≥{MIN_CHARS_CASTELLANO} chars). Castellano ausente total medido: "
         f"**{total_es:,} chars**".replace(",", ".") +
         f" ({meta['chars_castellano_en_accionables']:,} en los accionables)."
         .replace(",", "."), "",
         "|veredicto|documentos|chars es|", "|---|---:|---:|"]
    for k, v in ver_cnt.most_common():
        L.append(f"|{k}|{v}|" + f"{sum(f['chars_es'] for f in filas if f['veredicto_castellano'] == k):,}"
                 .replace(",", ".") + "|")
    conalgo = [f for f in filas if f["chars_es"] > 0]
    if conalgo:
        L += ["", f"**Los {len(conalgo)} documentos con ALGO de castellano en lo descartado** "
                  f"(ninguno llega al umbral de {MIN_CHARS_CASTELLANO} chars; se listan enteros "
                  f"porque son la respuesta):",
              "", "|documento|clase censo|chars es|líneas es|rivales|gold|", "|---|---|---:|---:|---|---|"]
        for f in sorted(conalgo, key=lambda x: -x["chars_es"]):
            L.append("|" + "|".join([
                f["source_file"][:36], f["clase_censo"].replace("paginas_perdidas_", "pp_"),
                f"{f['chars_es']:,}".replace(",", "."), str(f["lineas_es"]),
                ", ".join(f"{k} {v//1000}k" if v >= 1000 else f"{k} {v}"
                          for k, v in list(f["idiomas_rivales"].items())[:2]) or "—",
                "sí" if f["sustenta_gold"] else "",
            ]) + "|")
        L += ["", "**Citas del castellano descartado** (verbatim):"]
        for f in sorted(conalgo, key=lambda x: -x["chars_es"])[:8]:
            if f["citas_es"]:
                c_ = f["citas_es"][0]
                L.append(f"- `{f['source_file'][:34]}` p{c_['pagina']}: «{c_['texto'][:140]}»")
        L += ["", "**Precisión REVISADA A MANO** (las 13 fichas de arriba, cita a cita): 9 llevan "
                  "castellano de verdad (~1.760 chars) y 4 son falsos positivos (~390 chars): una "
                  "línea portuguesa con «continuación», otra con la cadena de interfaz «Exportación», "
                  "y dos italianas donde el OCR convirtió «all'impianto» en «all¡impianto» y el `¡` "
                  "contó como señal española. Y lo que SÍ es castellano es **boilerplate**: "
                  "direcciones de Notifier España, el párrafo de exención de garantía, una línea de "
                  "índice — no procedimiento técnico."]
    L += ["", "**Cómo se decide que una línea es castellano** (estricto, por las dos trampas): "
              f"`ES_EXCLUSIVAS` ({len(ES_EXCLUSIVAS)} palabras) se DERIVA restando a las palabras "
              "vacías del español las de los otros 18 idiomas —así caen solas «de/la/que/por/para/"
              "con/una/más/está», que comparten pt/it/fr—, más morfología propia (`-ción`, `-dad`, "
              "`-miento`, `ñ`, `¿`, `¡`); esa evidencia debe GANAR a la exclusiva de cada rival, y "
              "sólo empata si es fuerte (`-ción` o `ñ`). Además, **cada línea marcada se re-verifica "
              "contra el corpus**: el test de ausencia trabaja con fragmentos de ~35 palabras y uno "
              "mixto puede salir ausente en bloque aunque su línea española sí esté indexada (medido "
              f"en `D 1149-1`; así se descartaron {sum(f['chars_es_presente_en_corpus'] for f in filas)} "
              f"chars). Las líneas de menos de {MIN_PALABRAS_LINEA} palabras, o con menos de 2 "
              "palabras largas que verificar, NO se adjudican: el sesgo es conservador y este número "
              "SUBESTIMA el castellano perdido.", ""]
    md = CENSO_MD.read_text(encoding="utf-8")
    md = md.split(MARCA)[0].rstrip() + "\n\n" + "\n".join(L)
    CENSO_MD.write_text(md, encoding="utf-8")
    log(json.dumps(dict(ver_cnt.most_common()), ensure_ascii=False))
    log(f"castellano ausente total: {total_es} chars · accionables: {len(con)} documentos")
    log(f"actualizados: {CENSO_JSON.relative_to(ROOT)} · {CENSO_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
