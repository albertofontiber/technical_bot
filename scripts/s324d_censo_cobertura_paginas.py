# -*- coding: utf-8 -*-
"""s324d — CENSO DE COBERTURA DE PÁGINAS del corpus activo (solo LECTURA; cero escrituras en la DB).

POR QUÉ (lo que el censo de DENSIDAD no ve): el censo previo midió chars/página **sobre las páginas
que SÍ entraron** (`chars / pmax`). Un manual de 100 páginas del que solo se ingestaron 30 tiene
densidad normal y es INVISIBLE ahí: `pmax`=30 y chars/página sanos. Este censo compara contra la
VERDAD del PDF — `page_count` real de PyMuPDF — y usa el texto NATIVO del PDF para separar
«el PDF es un escaneo sin capa de texto» (nada que perder) de «el PDF traía texto y lo perdimos»
(el defecto real: p. ej. LlamaParse devolviendo `md` degenerado mientras `text` traía el contenido,
que `src/reingest/chunk.py:270` consume como `p.get("md") or p.get("text")`).

CONFOUND MEDIDO Y NEUTRALIZADO (por qué NO basta contar `page_number` distintos): el chunker escribe
`page_number = página del PRIMER bloque del chunk` (`src/reingest/chunk.py:335`), así que un chunk que
abarca varias páginas deja huecos en la secuencia de páginas SIN haber perdido nada. Verificado en el
smoke: `55360004 … DGD-600` tiene 2 páginas y solo `page_number=1`, pero 9.292 chars en corpus contra
15.068 nativos — el contenido de la página 2 SÍ está. Por eso `cobertura_page_number` se declara como
**COTA INFERIOR** y la clase se decide con una VERIFICACIÓN DE TEXTO por página:

  para cada página del PDF ausente de la secuencia de `page_number`, se toman sus palabras nativas
  distintas de ≥6 letras y se busca cada una en el texto normalizado de TODOS los chunks del documento;
  `presente` si aparece ≥70 %, `ausente` si <35 %, `parcial` en medio, `inconcluyente` si la página
  tiene <8 palabras útiles (portadas, planos, páginas en blanco).

MÉTRICAS por documento: `page_count` · `paginas_presentes`/`cobertura_page_number` (cota inferior) ·
`paginas_ausentes_verificadas` (rangos) + `chars_nativos_ausentes` · `cola_no_ingerida`
(`page_count − pmax`: el corte de cola clásico) · `chars_corpus` vs `chars_nativos` →
`ratio_texto` y `texto_nativo_perdido` = max(0, nativos − corpus).

CLASE (excluyente, en este orden): `error_descarga` · `sin_url` · `pdf_ilegible` ·
`sin_chunks` · `escaneado_sin_texto` (nativo <100 chars/pág y corpus <250 chars/pág: no había texto
que perder) · `escaneado_ocr_ok` (nativo <100 chars/pág pero el corpus SÍ tiene contenido — OCR de
LlamaParse) · `paginas_perdidas` (≥1 página verificada ausente con ≥500 chars nativos; sub-flag
`cola_truncada` si son un sufijo) · `texto_perdido` (ninguna página verificada ausente, pero
`ratio_texto` <0,5 con nativo ≥200 chars/pág — patología tipo `md` degenerado) · `sano`.

ORDEN DE MEDICIÓN (importa si se corta con `--limit`): 1) documentos que sustentan un gold
(`pdfs_used` de `evals/gold_answers_v1.yaml`), 2) sospechosos por densidad (<250 chars/pág),
3) el resto por tamaño ASCENDENTE (más documentos medidos por minuto). Cada PDF se descarga a un
temporal, se lee y se BORRA (no se acumula nada en disco).

Uso:
    python scripts/s324d_censo_cobertura_paginas.py                 # censo completo (~1,34 GB de descarga)
    python scripts/s324d_censo_cobertura_paginas.py --limit 20      # smoke
    python scripts/s324d_censo_cobertura_paginas.py --solo-sospechosos
    python scripts/s324d_censo_cobertura_paginas.py --solo-informe  # re-genera JSON+MD desde el parcial

Reanudable: cada documento medido se apendiza a `--parcial` (JSONL) y NO se vuelve a descargar.
Coste LLM: $0 (esto es REST + descarga + PyMuPDF).
"""
from __future__ import annotations

import argparse
import json
import os
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
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)
from src.http_pool import abierto  # noqa: E402

import fitz  # PyMuPDF  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
CHUNKS = os.getenv("CHUNKS_TABLE", "chunks_v2")
PAGINA_REST = 1000          # PostgREST corta a 1000 filas por petición: paginar SIEMPRE
OUT_JSON = ROOT / "evals" / "s324d_censo_cobertura_paginas_v1.json"
OUT_MD = ROOT / "evals" / "s324d_censo_cobertura_paginas_v1.md"
DOC_MAP = ROOT / "data" / "catalog" / "doc_map.jsonl"
GOLD = ROOT / "evals" / "gold_answers_v1.yaml"

UMBRAL_DENSIDAD = 250        # chars/página en corpus por debajo → sospechoso (censo de densidad)
UMBRAL_NATIVO_ESCANEO = 100  # chars/página nativos por debajo → PDF sin capa de texto útil
UMBRAL_RATIO = 0.5           # corpus/nativos por debajo (con nativo alto) → texto perdido
MIN_CHARS_PAGINA = 200       # menos que esto en una página ausente → no se reclama pérdida
MIN_CHARS_PERDIDA = 500      # chars nativos verificados ausentes para clasificar `paginas_perdidas`
TOK_PRESENTE, TOK_AUSENTE = 0.70, 0.35
MAX_TOKENS_SONDA = 60

_print_lock = threading.Lock()
_NOALNUM = re.compile(r"[^0-9a-záéíóúüñç]+", re.I)

# Detector de idioma por palabras vacías (offline, determinista, $0). Existe porque el smoke
# demostró que la MAYORÍA de las páginas realmente ausentes son la mitad FR/IT/DE/EN/NL/PL/SV de una
# hoja multilingüe (verificado a mano: `55360004 … DGD-600` pág. 2 = FR+IT; `0044-055-02 … addendum`
# pág. 3 = DE) — perder eso NO es el mismo defecto que perder una página ES en un bot español.
# Los 9 idiomas de las hojas «-ML» de Kidde están TODOS: sin `nl`, la pág. 14 NEERLANDESA de
# `3102984-ml…` se adjudicaba a `es` y producía un falso `paginas_perdidas_es` (verificado a mano).
_STOP = {
    "es": "de la que el en los del las por para con una como pero sus más este esta cuando sobre "
          "también hasta donde desde todo durante todos entre debe puede ser está son sin",
    "en": "the of and to in is that it was for on are as with they at be this have from or by but "
          "not what all were when your can there use each which their if will should must",
    "fr": "le la les des et en un une du que qui dans pour pas sur au avec ce il sont par plus ne "
          "se son est ou aux comme mais nous vous leur être doit peut lors cette",
    "it": "il lo la gli le di che un una per non con del della sono più come si da nel alla anche "
          "essere questo deve può viene dei delle nella agli sulla",
    "de": "der die das und ist den dem des ein eine nicht mit von zu für auf sie im werden bei auch "
          "aus oder wird nach kann muss sind eines einer dieser diese",
    "pt": "de que em um uma para com não os as dos das por mais como mas ao seu sua ou quando muito "
          "pode deve são está pelo pela nos nas",
    "nl": "de het een en van in is dat op te voor met zijn niet aan door worden bij deze als om "
          "naar uit kan moet wordt of ook tot",
    "pl": "nie się na do jest że oraz lub przez które przy dla może być jako tego tym który sposób "
          "urządzenia należy jeśli można",
    "sv": "och att det som är för på med av till den inte har kan ska vid eller från detta när ett "
          "de om",
    # Hojas «-ML» de Kidde/Aritech: hasta 21 idiomas (en cs da de el es fi fr hu it lt nl no pl pt
    # ro ru sk sr sv tr). Sin estos, sus páginas caían en '?' y ensuciaban la clase que pide ojo.
    "da": "og at det som er for på med af til den ikke har kan skal ved eller fra dette når et de om",
    "no": "og at det som er for på med av til den ikke har kan skal ved eller fra dette når et de om",
    "fi": "ja on ei tai että sekä kun myös vain jos niin ovat sen tämä ole voi kuin mutta",
    "cs": "a je na se v že nebo pro do po při této tento které jsou být není podle jako",
    "sk": "a je na sa v že alebo pre do po pri tejto tento ktoré sú byť nie podľa ako",
    "hu": "és az egy nem hogy meg van ezt vagy csak ha még már kell lehet amely",
    "ro": "și de la în pe cu care este nu sau pentru din ale acest această trebuie poate",
    "tr": "ve bir bu için ile olarak veya daha çok gibi olan sonra kadar değil",
    "el": "και το του της των στο στην είναι για από με που θα να τα οι",
    "ru": "и в не на что с по для или это как быть при от же его",
}
_STOP = {k: set(v.split()) for k, v in _STOP.items()}
UMBRAL_IDIOMA = 0.04         # fracción mínima de palabras vacías para adjudicar idioma
MARGEN_IDIOMA = 1.25         # el mejor debe superar al segundo por este factor; si no → '?'
_NOLETRA = re.compile(r"[^0-9a-zÀ-ſ]+")


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def normalizar(s: str) -> str:
    """Texto comparable: minúsculas, todo lo no alfanumérico → espacio, colapsado y con centinelas."""
    return " " + _NOALNUM.sub(" ", (s or "").lower()).strip() + " "


def idioma(txt: str) -> str:
    """'es'/'en'/'fr'/'it'/'de'/'pt'/'nl'/'pl'/'sv' o '?' (tablas, planos, texto insuficiente).
    Normalizador PROPIO que conserva los diacríticos latinos (el de comparación los borra y
    rompería «się», «är», «für»)."""
    pal = _NOLETRA.sub(" ", (txt or "").lower()).split()
    if len(pal) < 25:
        return "?"                                   # texto insuficiente: no se afirma nada
    marc = {k: sum(1 for p in pal if p in v) / len(pal) for k, v in _STOP.items()}
    orden = sorted(((v, k) for k, v in marc.items()), reverse=True)
    (m1, k1), (m2, k2) = orden[0], orden[1]
    if m1 < UMBRAL_IDIOMA:
        return "?"                                   # texto SIN idioma (tabla de códigos, plano)
    if m1 >= MARGEN_IDIOMA * m2:
        return k1
    # Empate entre dos idiomas (página frontera de una hoja multilingüe, o dos columnas FR+IT en la
    # misma página): la afirmación DÉBIL «no es español» se sostiene si el español no está entre los
    # dos primeros. PROPIEDAD QUE IMPORTA: una página realmente española siempre es el argmax (`es`
    # ∈ top-2), así que JAMÁS puede acabar en «otro» — como mucho cae en '?' (revisión a ojo).
    # (No sirve exigir `marc['es'] < UMBRAL`: las lenguas romances comparten «de/la/en/que» y una
    # página FR+IT puntúa alto en español — verificado con `55360004 … DGD-600` pág. 2.)
    return "otro" if "es" not in (k1, k2) else "?"


# ---------------------------------------------------------------- Supabase (solo lectura)
def paginar(c, tabla: str, select: str, orden: str, filtro: dict | None = None) -> list[dict]:
    """GET paginado con limit=1000 + offset (PostgREST corta a 1000: pedir 'limit=2000' devuelve 1000)."""
    filas, off = [], 0
    while True:
        params = {"select": select, "order": orden, "limit": str(PAGINA_REST), "offset": str(off)}
        params.update(filtro or {})
        r = c.get(f"{SB}/rest/v1/{tabla}", headers=HS, params=params)
        r.raise_for_status()
        lote = r.json()
        if not lote:
            break
        filas += lote
        off += len(lote)
        if len(lote) < PAGINA_REST:
            break
    return filas


def documentos_activos(c) -> list[dict]:
    return paginar(c, "documents", "id,source_pdf_filename,manufacturer,product_model,source_url,status",
                   "id.asc", {"status": "eq.active"})


def corpus_por_documento(c) -> dict[str, dict]:
    """{document_id: {paginas:set, chars, n_chunks, sin_pagina, texto_norm}} leyendo TODA la tabla."""
    agg: dict[str, dict] = defaultdict(
        lambda: {"paginas": set(), "chars": 0, "n_chunks": 0, "sin_pagina": 0, "_partes": []})
    off = 0
    while True:
        r = c.get(f"{SB}/rest/v1/{CHUNKS}", headers=HS,
                  params={"select": "document_id,page_number,content", "order": "id.asc",
                          "limit": str(PAGINA_REST), "offset": str(off)})
        r.raise_for_status()
        lote = r.json()
        if not lote:
            break
        for x in lote:
            a = agg[x["document_id"]]
            cont = x.get("content") or ""
            a["n_chunks"] += 1
            a["chars"] += len(cont)
            a["_partes"].append(cont)
            p = x.get("page_number")
            if p is None:
                a["sin_pagina"] += 1
            else:
                a["paginas"].add(int(p))
        off += len(lote)
        if off % 5000 == 0:
            log(f"  chunks leídos: {off}")
        if len(lote) < PAGINA_REST:
            break
    log(f"  chunks leídos: {off}")
    for a in agg.values():
        a["texto_norm"] = normalizar(" ".join(a.pop("_partes")))
    return agg


# ---------------------------------------------------------------- golds
def basen(s: str) -> str:
    s = (s or "").replace("\\", "/").rsplit("/", 1)[-1].strip().lower()
    return s[:-4] if s.endswith(".pdf") else s


def pdfs_de_golds() -> tuple[set[str], set[str]]:
    """(basenames de `pdfs_used` de los golds, document_ids presentes en doc_map.jsonl)."""
    usados: set[str] = set()
    try:
        import yaml
        for g in yaml.safe_load(GOLD.read_text(encoding="utf-8")) or []:
            for p in (g.get("pdfs_used") or []):
                if isinstance(p, str):
                    usados.add(basen(p))
    except Exception as e:  # noqa: BLE001 — no reventar el censo por el gold
        log(f"AVISO: no se pudieron leer los golds ({e})")
    en_mapa: set[str] = set()
    if DOC_MAP.exists():
        for ln in DOC_MAP.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                try:
                    en_mapa.add(json.loads(ln)["document_id"])
                except Exception:  # noqa: BLE001
                    pass
    return usados, en_mapa


# ---------------------------------------------------------------- medición de un PDF
def rangos(nums: list[int]) -> str:
    """[31,32,33,40] → '31-33,40' (compacto)."""
    if not nums:
        return ""
    nums = sorted(nums)
    out, a, prev = [], nums[0], nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        out.append(f"{a}-{prev}" if prev > a else f"{a}")
        a = prev = n
    out.append(f"{a}-{prev}" if prev > a else f"{a}")
    return ",".join(out)


def veredicto_pagina(txt: str, corpus_norm: str) -> tuple[str, float, int]:
    """¿El texto de esta página está en el corpus del documento? (robusto a re-flujo: por palabras)."""
    if len(txt.strip()) < MIN_CHARS_PAGINA:
        return "corta_o_vacia", -1.0, 0
    toks = [t for t in dict.fromkeys(normalizar(txt).split()) if len(t) >= 6]
    if len(toks) < 8:
        return "inconcluyente", -1.0, len(toks)
    if len(toks) > MAX_TOKENS_SONDA:                    # muestra uniforme (no solo el encabezado)
        paso = len(toks) / MAX_TOKENS_SONDA
        toks = [toks[int(i * paso)] for i in range(MAX_TOKENS_SONDA)]
    hits = sum(1 for t in toks if f" {t} " in corpus_norm)
    frac = hits / len(toks)
    v = "presente" if frac >= TOK_PRESENTE else ("ausente" if frac < TOK_AUSENTE else "parcial")
    return v, round(frac, 3), len(toks)


def medir_pdf(x: dict, corpus_norm: str, destino: Path, timeout: float) -> dict:
    """Descarga → page_count + texto nativo + verificación por página → BORRA el fichero.
    Nunca lanza: devuelve el error en la clave `error`."""
    res: dict = {"pdf_bytes": 0, "page_count": None, "chars_nativos": None,
                 "paginas_con_texto_nativo": None, "encriptado": None, "error": None,
                 "verificacion": {}, "chars_por_pagina_ausente": {}, "idioma_por_pagina_ausente": {}}
    url = x.get("source_url")
    if not url:
        res["error"] = "sin source_url"
        return res
    tmp = destino / f"{x['document_id']}.pdf"
    try:
        ultimo = None
        bajado = False
        for intento in range(3):
            try:
                with abierto(timeout=timeout, reintentos=1) as c:
                    r = c.get(url)
                if r.status_code == 200:
                    tmp.write_bytes(r.content)
                    res["pdf_bytes"] = len(r.content)
                    bajado = True
                    break
                ultimo = f"HTTP {r.status_code}"
                if r.status_code in (400, 403, 404):
                    res["error"] = ultimo
                    return res
            except Exception as e:  # noqa: BLE001
                ultimo = f"{type(e).__name__}: {e}"
            time.sleep(1.0 + intento)
        if not bajado:
            res["error"] = f"descarga fallida ({ultimo})"
            return res
        try:
            doc = fitz.open(tmp)
        except Exception as e:  # noqa: BLE001
            res["error"] = f"pdf ilegible: {type(e).__name__}: {e}"
            return res
        with doc:
            res["encriptado"] = bool(doc.is_encrypted and doc.needs_pass)
            res["page_count"] = doc.page_count
            if res["encriptado"]:
                res["chars_nativos"], res["paginas_con_texto_nativo"] = 0, 0
                return res
            presentes = set(x["_pags"])
            tot, con = 0, 0
            for i, pg in enumerate(doc, start=1):     # `page_number` del corpus es 1-based (verificado)
                try:
                    t = pg.get_text() or ""
                except Exception:  # noqa: BLE001
                    t = ""
                tot += len(t)
                con += 1 if len(t.strip()) >= 20 else 0
                if i not in presentes:                # solo las candidatas se verifican contra el corpus
                    v, frac, ntok = veredicto_pagina(t, corpus_norm)
                    lg = idioma(t) if v in ("ausente", "parcial") else ""
                    res["verificacion"][i] = {"v": v, "frac": frac, "toks": ntok,
                                              "chars": len(t), "idioma": lg}
                    if v in ("ausente", "parcial"):
                        # muestra AUDITABLE: deja re-adjudicar el idioma (y que un humano juzgue la
                        # pérdida) sin volver a descargar 1,34 GB.
                        res["verificacion"][i]["muestra"] = re.sub(r"\s+", " ", t)[:300]
                    if v == "ausente":
                        res["chars_por_pagina_ausente"][i] = len(t)
                        res["idioma_por_pagina_ausente"][i] = lg
            res["chars_nativos"], res["paginas_con_texto_nativo"] = tot, con
    finally:
        try:
            tmp.unlink(missing_ok=True)               # BORRAR siempre: no acumular GB
        except Exception:  # noqa: BLE001
            pass
    return res


def clasificar(f: dict) -> str:
    e = f.get("error")
    if e:
        if e == "sin source_url":
            return "sin_url"
        return "pdf_ilegible" if e.startswith("pdf ilegible") else "error_descarga"
    if f.get("encriptado"):
        return "pdf_ilegible"
    pc = f.get("page_count") or 0
    if pc <= 0:
        return "pdf_ilegible"
    if not f.get("n_chunks"):
        return "sin_chunks"
    nat_pp = (f["chars_nativos"] or 0) / pc
    cor_pp = (f["chars_corpus"] or 0) / pc
    if nat_pp < UMBRAL_NATIVO_ESCANEO:
        return "escaneado_ocr_ok" if cor_pp >= UMBRAL_DENSIDAD else "escaneado_sin_texto"
    aus = f.get("chars_ausentes_por_idioma") or {}
    if (aus.get("es") or 0) >= MIN_CHARS_PERDIDA:
        return "paginas_perdidas_es"
    if (f.get("chars_nativos_ausentes") or 0) >= MIN_CHARS_PERDIDA:
        # manda el bucket DOMINANTE, no la mera presencia de '?': un manual portugués entero tiene
        # también páginas de tabla sin idioma adjudicable, y sigue siendo pérdida en otro idioma.
        dom = max(aus, key=lambda k: aus[k]) if aus else "?"
        return "paginas_perdidas_sin_idioma" if dom == "?" else "paginas_perdidas_otro_idioma"
    if (f.get("ratio_texto") or 0) < UMBRAL_RATIO and nat_pp >= 200:
        return "texto_perdido"
    return "sano"


# ---------------------------------------------------------------- informe
def escribir_salidas(filas: list[dict], meta: dict) -> None:
    OUT_JSON.write_text(json.dumps({"meta": meta, "documentos": filas}, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    clases = Counter(f["clase"] for f in filas)
    GRAVES = ("paginas_perdidas_es", "paginas_perdidas_sin_idioma", "texto_perdido",
              "escaneado_sin_texto", "sin_chunks", "pdf_ilegible", "error_descarga", "sin_url")
    afectados = [f for f in filas if f["clase"] in GRAVES]
    peores = sorted(filas, key=lambda f: -(f.get("texto_nativo_perdido") or 0))[:25]

    def mil(n) -> str:
        return f"{n:,}".replace(",", ".") if isinstance(n, int) else "—"

    def fila_md(f: dict) -> str:
        # sin espacios alrededor de los `|`: el informe tiene presupuesto de palabras y el relleno
        # de la tabla se lo comía (25 filas × 10 pipes ≈ 250 «palabras» de pura sintaxis).
        return "|" + "|".join([
            f['source_file'][:36],
            str(f.get('page_count') if f.get('page_count') is not None else '—'),
            (f.get('paginas_ausentes_verificadas') or '—')[:16],
            (f.get('idiomas_ausentes') or '—')[:12],
            mil(f.get('chars_nativos')), mil(f.get('chars_corpus')), mil(f.get('texto_nativo_perdido')),
            f['clase'].replace("paginas_perdidas_", "pp_") + ("+cola" if f.get('cola_truncada') else ""),
            ('sí' if f.get('sustenta_gold') else ''),
        ]) + "|"

    QUE = {"sano": "texto verificado en corpus; ratio normal",
           "paginas_perdidas_es": "**defecto real**: páginas ESPAÑOLAS ausentes",
           "paginas_perdidas_otro_idioma": "solo faltan páginas EN/FR/IT/DE/NL/PL/SV… (hojas multilingües)",
           "paginas_perdidas_sin_idioma": "ausentes sin idioma adjudicable — exige ojo",
           "texto_perdido": "todas las páginas, pero <50 % del texto nativo",
           "escaneado_ocr_ok": "sin capa de texto; el OCR de LlamaParse sí entró",
           "escaneado_sin_texto": "sin capa de texto y corpus pobre: nada que recuperar",
           "sin_chunks": "activo y sin chunks", "pdf_ilegible": "PDF corrupto o cifrado",
           "error_descarga": "no se pudo bajar", "sin_url": "`source_url` vacío: NO medible"}

    L = ["# s324d — Censo de COBERTURA DE PÁGINAS del corpus activo", "",
         f"{meta['utc']} · `{meta['tabla_chunks']}` · **solo lectura, cero escrituras, $0 de LLM** · "
         f"**{meta['medidos']}/{meta['documentos_activos']}** documentos activos medidos "
         f"(censo {'COMPLETO' if meta['completo'] else 'PARCIAL'}) · {meta['gb_descargados']} GB de PDF "
         f"descargados, leídos con PyMuPDF y borrados.", "",
         "Mide lo que el censo de densidad no ve: páginas ENTERAS que no entraron. Contra la verdad "
         "del PDF (`page_count` de PyMuPDF), no contra `pmax`.", "",
         "## Los 25 peores por texto nativo perdido (nativos − corpus)", "",
         "|documento|pág|ausentes†|idioma|nativos|corpus|perdido|clase|gold|",
         "|---|---:|---|---|---:|---:|---:|---|---|"]
    L += [fila_md(f) for f in peores]
    L += ["", "† páginas cuyo texto nativo NO aparece en NINGÚN chunk del documento (por palabras de "
          "≥6 letras; <35 % de aciertos). `pp_` = `paginas_perdidas_`.", "",
          "## Recuento por clase", "", "|clase|n|gold|significado|", "|---|---:|---:|---|"]
    for k, v in clases.most_common():
        L.append(f"|{k}|{v}|{sum(1 for f in filas if f['clase'] == k and f.get('sustenta_gold'))}"
                 f"|{QUE.get(k, '')}|")
    L += ["", f"**Afectados** por defecto accionable o no medible: **{len(afectados)}** de "
              f"{meta['medidos']}. De ellos **{sum(1 for f in afectados if f.get('sustenta_gold'))}** "
              f"sustentan un gold (`pdfs_used` de `gold_answers_v1.yaml`) y "
              f"**{sum(1 for f in afectados if f.get('en_doc_map'))}** están en `doc_map.jsonl`. "
              f"Los {sum(1 for f in filas if f.get('sustenta_gold') and f['clase'] == 'paginas_perdidas_otro_idioma')} "
              f"documentos-gold tocados lo son solo por páginas en OTRO idioma.", "",
          "## Verificado a ojo (no inferido)", "",
          "- `Installation manual_conduct detector` (Uniguard, Detnov): manual DE/ES intercalado; las "
          "págs. 5 y 8 ausentes SÍ llevan castellano («Fije el soporte al conducto», «Taladre un "
          "orificio de Ø 51 mm»). **Pérdida real.**",
          "- `TMP2_QRefnotiES` (OGGIONI): la pág. 1 ausente es la portada ESPAÑOLA («DETECTORES "
          "TÉRMICOS TERMOVELOCIMÉTRICOS TMP2 Manual de Usuario»). **Pérdida real**, clasificada `?` "
          "por ser portada con pocas palabras vacías.",
          "- `085501987j PY X-M` (D-GB-F-RU-IT) y `15088SP`: las ausentes son alemanas/francesas la "
          "primera, y de una página con fuente rota la segunda (corpus 899k > nativo 528k). Benignas.",
          "- Calibración: `HLSI-TI-007_VSN-4REL` — el `md` degenerado ya conocido (47 chars en corpus "
          "vs 2.252 nativos) cae en `texto_perdido`, como debía.", "",
          "## Lo que este censo NO cubre (declarado)", "",
          "1. **No mide impacto en respuestas**: ni retrieval, ni eval, ni si un gold cambia.",
          "2. **`cobertura_page_number` no es pérdida**: es cota inferior (ver †); la clase se decide "
          "por TEXTO.",
          "3. **Falsos «presente»**: una página que repite contenido de otra (tablas idénticas en dos "
          "idiomas) se da por presente → la pérdida medida es cota INFERIOR, nunca exagerada.",
          "4. **Idioma**: 19 idiomas por palabras vacías; cs, hu, lt, sr… caen en `otro`/`?`. Una "
          "página española jamás cae en `otro` (sería el argmax), pero sí en `?`.",
          "5. **PDFs sin capa de texto o con fuente rota**: no hay verdad contra la que comparar; "
          "`ratio_texto` > 1 es normal (LlamaParse añade markdown de tablas y descripciones de imagen).",
          f"6. **No medidos**: los {sum(1 for f in filas if f['clase'] == 'sin_url')} sin `source_url` "
          f"y los 26 `document_id` con chunks que NO están activos (fuera de alcance).",
          "7. **No mide calidad del chunk** (orden, tablas rotas, secciones), solo presencia de texto.",
          ""]
    if not meta["completo"]:
        L.insert(3, f"> **AVISO**: censo PARCIAL — {meta['medidos']} de {meta['documentos_activos']} "
                    f"documentos activos. NO es el censo completo.\n")
    OUT_MD.write_text("\n".join(L), encoding="utf-8")
    log(f"informe: {len(' '.join(L).split())} palabras")


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="mide solo los N primeros (orden de prioridad)")
    ap.add_argument("--solo-sospechosos", action="store_true",
                    help=f"solo densidad < {UMBRAL_DENSIDAD} chars/pág (o que sustenten un gold)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--parcial", default=str(Path(tempfile.gettempdir()) / "s324d_cobertura_parcial.jsonl"))
    ap.add_argument("--solo-informe", action="store_true", help="no descarga: re-genera JSON+MD del parcial")
    args = ap.parse_args()

    parcial = Path(args.parcial)
    parcial.parent.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.gettempdir()) / "s324d_pdfs"
    tmpdir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    with abierto(timeout=120.0, reintentos=1) as c:
        docs = documentos_activos(c)
        log(f"documentos activos: {len(docs)}")
        log("leyendo chunks (paginado 1000)…")
        agg = corpus_por_documento(c)
    huerfanos = [k for k in agg if k not in {d["id"] for d in docs}]
    log(f"documentos con chunks: {len(agg)} (de ellos {len(huerfanos)} NO activos) · "
        f"chunks: {sum(a['n_chunks'] for a in agg.values())} ({time.time()-t0:.0f}s)")

    usados_gold, en_doc_map = pdfs_de_golds()
    vacio = {"paginas": set(), "chars": 0, "n_chunks": 0, "sin_pagina": 0, "texto_norm": " "}
    base_docs = {}
    for d in docs:
        a = agg.get(d["id"], vacio)
        pags = a["paginas"]
        dens = (a["chars"] / max(pags)) if pags and max(pags) > 0 else 0.0
        base_docs[d["id"]] = {
            "document_id": d["id"], "source_file": d["source_pdf_filename"] or "",
            "manufacturer": d.get("manufacturer"), "product_model": d.get("product_model"),
            "source_url": d.get("source_url"), "n_chunks": a["n_chunks"],
            "chars_corpus": a["chars"], "chunks_sin_pagina": a["sin_pagina"],
            "pmax": max(pags) if pags else 0, "pmin": min(pags) if pags else None,
            "paginas_presentes": len(pags), "_pags": sorted(pags),
            "densidad_corpus": round(dens, 1),
            "sustenta_gold": basen(d["source_pdf_filename"] or "") in usados_gold,
            "en_doc_map": d["id"] in en_doc_map,
        }

    universo = list(base_docs.values())
    if args.solo_sospechosos:
        universo = [x for x in universo if x["densidad_corpus"] < UMBRAL_DENSIDAD or x["sustenta_gold"]]
    # prioridad: golds → sospechosos por densidad → resto por tamaño ASCENDENTE (proxy: chars_corpus)
    universo.sort(key=lambda x: (0 if x["sustenta_gold"] else (1 if x["densidad_corpus"] < UMBRAL_DENSIDAD else 2),
                                 x["chars_corpus"]))
    if args.limit:
        universo = universo[:args.limit]

    hechos: dict[str, dict] = {}
    if parcial.exists():
        for ln in parcial.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                try:
                    y = json.loads(ln)
                    hechos[y["document_id"]] = y
                except Exception:  # noqa: BLE001
                    pass
        log(f"parcial: {len(hechos)} documentos ya medidos ({parcial})")

    pendientes = [] if args.solo_informe else [x for x in universo if x["document_id"] not in hechos]
    log(f"universo: {len(universo)} · pendientes de descarga: {len(pendientes)}")

    escritura = threading.Lock()
    hecho_n = [0]

    def tarea(x: dict) -> dict:
        r = medir_pdf(x, agg.get(x["document_id"], vacio)["texto_norm"], tmpdir, args.timeout)
        fila = {k: v for k, v in x.items() if k != "_pags"}
        fila.update({k: r[k] for k in ("page_count", "chars_nativos", "paginas_con_texto_nativo",
                                       "pdf_bytes", "encriptado", "error")})
        pc = r["page_count"] or 0
        if pc > 0:
            pags = set(x["_pags"])
            esperadas = set(range(1, pc + 1))
            ausentes = sorted(r["chars_por_pagina_ausente"])
            ver = r["verificacion"]
            fila["cobertura_page_number"] = round(len(pags & esperadas) / pc, 4)
            fila["paginas_sin_page_number"] = rangos(sorted(esperadas - pags))[:300]
            fila["paginas_ausentes_verificadas"] = rangos(ausentes)[:300]
            fila["paginas_ausentes_n"] = len(ausentes)
            fila["chars_nativos_ausentes"] = sum(r["chars_por_pagina_ausente"].values())
            por_idioma: dict[str, int] = defaultdict(int)
            for p, ch in r["chars_por_pagina_ausente"].items():
                por_idioma[r["idioma_por_pagina_ausente"].get(p) or "?"] += ch
            fila["chars_ausentes_por_idioma"] = dict(sorted(por_idioma.items(), key=lambda kv: -kv[1]))
            fila["idiomas_ausentes"] = ",".join(fila["chars_ausentes_por_idioma"])
            fila["paginas_parciales"] = rangos([p for p, v in ver.items() if v["v"] == "parcial"])[:200]
            fila["paginas_recuperadas_por_texto"] = sum(1 for v in ver.values() if v["v"] == "presente")
            fila["paginas_inconcluyentes"] = sum(1 for v in ver.values()
                                                 if v["v"] in ("inconcluyente", "corta_o_vacia"))
            fila["cola_no_ingerida"] = max(0, pc - x["pmax"])
            fila["cola_truncada"] = bool(ausentes and min(ausentes) > x["pmax"] and x["pmax"] > 0)
            fila["paginas_fuera_de_rango"] = rangos(sorted(pags - esperadas))[:200]
            fila["ratio_texto"] = round(x["chars_corpus"] / r["chars_nativos"], 4) if r["chars_nativos"] else None
            fila["texto_nativo_perdido"] = max(0, (r["chars_nativos"] or 0) - x["chars_corpus"])
            fila["_ver"] = {str(k): v for k, v in ver.items() if v["v"] in ("ausente", "parcial")}
        else:
            fila.update({"cobertura_page_number": None, "paginas_sin_page_number": "",
                         "paginas_ausentes_verificadas": "", "paginas_ausentes_n": None,
                         "chars_nativos_ausentes": None, "chars_ausentes_por_idioma": {},
                         "idiomas_ausentes": "", "paginas_parciales": "",
                         "paginas_recuperadas_por_texto": None, "paginas_inconcluyentes": None,
                         "cola_no_ingerida": None, "cola_truncada": None, "paginas_fuera_de_rango": "",
                         "ratio_texto": None, "texto_nativo_perdido": 0, "_ver": {}})
        fila["clase"] = clasificar(fila)
        with escritura:
            with parcial.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
            hecho_n[0] += 1
            if hecho_n[0] % 50 == 0 or fila["clase"] not in ("sano", "escaneado_ocr_ok"):
                log(f"  [{hecho_n[0]}/{len(pendientes)}] {fila['source_file'][:46]}: {fila['clase']} "
                    f"pc={fila['page_count']} cob={fila['cobertura_page_number']} "
                    f"aus={fila['paginas_ausentes_verificadas'] or '-'} "
                    f"nat={fila['chars_nativos']} cor={fila['chars_corpus']}")
        return fila

    if pendientes:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(tarea, x) for x in pendientes]
            for fu in as_completed(futs):
                y = fu.result()
                hechos[y["document_id"]] = y

    filas = [hechos[x["document_id"]] for x in universo if x["document_id"] in hechos]
    # Re-adjudicación de CLASE desde los campos ya guardados (idempotente): permite afinar los
    # umbrales o el bucketing con `--solo-informe`, SIN volver a descargar 1,34 GB.
    for y in filas:
        y["clase"] = clasificar(y)
    meta = {"que_es": "censo de cobertura de páginas del corpus activo — s324d",
            "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tabla_chunks": CHUNKS, "documentos_activos": len(docs),
            "documentos_con_chunks": len(agg), "doc_ids_con_chunks_no_activos": len(huerfanos),
            "chunks_totales": sum(a["n_chunks"] for a in agg.values()),
            "universo_pedido": len(universo), "medidos": len(filas),
            "completo": len(filas) == len(base_docs),
            "filtros": {"solo_sospechosos": args.solo_sospechosos, "limit": args.limit},
            "umbrales": {"densidad_corpus": UMBRAL_DENSIDAD, "nativo_escaneo_por_pag": UMBRAL_NATIVO_ESCANEO,
                         "ratio_texto": UMBRAL_RATIO, "min_chars_pagina": MIN_CHARS_PAGINA,
                         "min_chars_perdida": MIN_CHARS_PERDIDA,
                         "tokens_presente": TOK_PRESENTE, "tokens_ausente": TOK_AUSENTE},
            "gb_descargados": round(sum((f.get("pdf_bytes") or 0) for f in filas) / 1e9, 3),
            "segundos": round(time.time() - t0, 1)}
    escribir_salidas(filas, meta)
    log(json.dumps(dict(Counter(f["clase"] for f in filas)), ensure_ascii=False))
    log(f"salidas: {OUT_JSON.relative_to(ROOT)} · {OUT_MD.relative_to(ROOT)} ({meta['segundos']}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
