# -*- coding: utf-8 -*-
"""s324d — VERIFICACIÓN DEL IDIOMA DEL TEXTO AUSENTE (cierra el cabo suelto del censo de cobertura).

POR QUÉ: el censo (`s324d_censo_cobertura_paginas.py`) dejó 4 documentos en la clase `texto_perdido`
(ratio corpus/nativo 0,33-0,41 con TODAS las páginas presentes) sin verificar EN QUÉ IDIOMA está lo
que falta, y 3 en `paginas_perdidas_sin_idioma` sin adjudicar. Un `texto_perdido` en una ficha
multilingüe cuyo texto ausente es EN/FR/DE/NL NO es un defecto (la política de idiomas lo descarta a
propósito); uno cuyo texto ausente es CASTELLANO sí lo es (habría que re-ingestar). La hipótesis a
REFUTAR es la primera.

MÉTODO (mismo que el censo, pero por FRAGMENTO en vez de por página — es la única granularidad que
sirve aquí: en estos documentos NO falta ninguna página entera, falta texto DENTRO de páginas que sí
están):
  1. texto nativo por página con PyMuPDF → fragmentos de ~35 palabras respetando saltos de línea
     (una hoja multilingüe alterna idioma por párrafo/columna: el fragmento los separa);
  2. cada fragmento se busca en el texto normalizado de TODOS los chunks del documento por palabras
     de ≥6 letras — `ausente` si aparece <35 %, `presente` si ≥70 %, `parcial` en medio;
  3. el texto ausente se concatena POR PÁGINA y en GLOBAL, y se le adjudica idioma con el detector
     offline de 19 idiomas del censo (más texto = adjudicación más fiable que por fragmento suelto).

VEREDICTO por documento: `otro_idioma_por_politica` (ausente ≥500 chars, bucket español <500 y el
dominante es un idioma conocido ≠ es → NO accionable) · `castellano_perdido` (bucket español ≥500
chars → accionable: re-ingestar) · `indeterminado` (dominante '?' o poco texto ausente — se dice, no
se fuerza).

SALIDAS (actualiza los entregables del censo, sin commit):
  · `evals/s324d_censo_cobertura_paginas_v1.json` — añade `veredicto_idioma`, `idiomas_texto_ausente`,
    `cita_texto_ausente` y `accionable` a los documentos verificados; deja `clase_censo_original` y
    un bloque `meta.verificacion_idioma` con TODA reclasificación aplicada (nunca silenciosa);
  · `evals/s324d_censo_cobertura_paginas_v1.md` — sección «Verificación del idioma del texto ausente»
    al final (idempotente: se reemplaza si ya existe).

OJO: `--solo-informe` del censo REGENERA el .md y el .json desde el parcial y borraría esta capa.
Si vuelves a generar el censo, re-ejecuta ESTE script después.

Uso:  python scripts/s324d_verificacion_idioma_ausente.py [--dry-run]
Coste LLM: $0 (descarga + PyMuPDF + REST). Cero escrituras en la DB.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)
from src.http_pool import abierto  # noqa: E402

import fitz  # noqa: E402
from s324d_censo_cobertura_paginas import (  # noqa: E402  (reutiliza el método del censo, no lo altera)
    MIN_CHARS_PERDIDA, TOK_AUSENTE, TOK_PRESENTE, idioma, normalizar,
)

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
CENSO_JSON = ROOT / "evals" / "s324d_censo_cobertura_paginas_v1.json"
CENSO_MD = ROOT / "evals" / "s324d_censo_cobertura_paginas_v1.md"
MARCA = "## Verificación del idioma del texto ausente"
PALABRAS_FRAGMENTO = 35
MIN_TOKENS_FRAGMENTO = 5
# Guarda anti-MOJIBAKE (medida, no supuesta): `15088SP` extrae con la fuente rota — «7DEOD GH
# &RQWHQLGRV» por «Tabla de Contenidos» — y esos fragmentos parecen «ausentes» aunque el corpus
# (899k chars, OCR de LlamaParse) sea MAYOR que el texto nativo (528k). Un texto ilegible no puede
# sostener NINGUNA reclamación de pérdida. Separación medida en los 9 casos: legítimos 0,36-0,46 ·
# mojibake 0,17-0,23 (el cifrado manda las vocales a consonantes).
MIN_VOCALES = 0.30

# Lectura HUMANA de los casos que el detector no puede cerrar solo (portadas, tablas): se declara
# como lo que es —ojo humano, no inferencia del script— y se cita verbatim.
NOTA_HUMANA = {
    "TMP2_QRefnotiES": ("castellano_perdido (ojo humano)",
                        "La pág. 1 ausente es la portada ESPAÑOLA: «OGGIONI S.A.S. DETECTORES "
                        "TÉRMICOS TMP2 … DETECTORES TÉRMICOS TERMOVELOCIMÉTRICOS TMP2 Manual de "
                        "Usuario». El detector la deja en '?' porque una portada casi no lleva "
                        "palabras vacías; leída, es castellano."),
    "15088SP": ("fuente_ilegible",
                "El texto nativo sale cifrado por una fuente rota («1RWD /RV 6LVWHPDV GH $ODUPD» "
                "= «Nota: Los Sistemas de Alarma»); el corpus (899.952 chars) SUPERA al nativo "
                "(528.328) porque LlamaParse lo OCRizó bien. No hay pérdida: hay fuente ilegible."),
    "HLSI-TI-007_VSN-4REL": ("sano_reverificado",
                             "RE-INGESTADO después del censo (47 → 3.601 chars, 2 chunks, con el "
                             "procedimiento PROG/Z1/40 cm dentro). Re-medido hoy: 0 chars de texto "
                             "nativo ausentes. Su fila del censo refleja el estado ANTERIOR."),
    "D1056-1_NFXI-BS-BSF": ("castellano_perdido",
                            "Falta la tabla DIP entera, con su columna española: «Configuración», "
                            "«Desactivado», «Activado», «Descripción», «tono», «conmutador» y "
                            "«reserva» NO aparecen en ninguno de sus 2 chunks (verificado token a "
                            "token contra el corpus)."),
}

# Universo EXPLÍCITO (4 `texto_perdido` sin verificar + 3 `paginas_perdidas_sin_idioma` + 2 confirmaciones).
OBJETIVO = [
    "D 1149-1 BGL Notifier", "D1056-1_NFXI-BS-BSF", "HLSI-MA-103 _Korte handleiding RP1r_Supra_NL",
    "I56-1653-022 ECO1003",                                    # texto_perdido sin verificar
    "TMP2_QRefnotiES", "085501987j_PY X-M", "15088SP",         # paginas_perdidas_sin_idioma
    "Installation manual_conduct detector",                     # paginas_perdidas_es (confirmar)
    "HLSI-TI-007_VSN-4REL",                                     # calibración (RE-INGESTADO tras el censo)
]


def texto_corpus(c, doc_id: str) -> tuple[str, int, int]:
    """(texto normalizado de todos los chunks, n_chunks, chars) — paginado (PostgREST corta a 1000)."""
    partes, off = [], 0
    while True:
        r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                  params={"select": "content", "document_id": f"eq.{doc_id}",
                          "order": "chunk_index.asc", "limit": "1000", "offset": str(off)})
        r.raise_for_status()
        lote = r.json()
        partes += [x["content"] or "" for x in lote]
        off += len(lote)
        if len(lote) < 1000:
            break
    crudo = " ".join(partes)
    return normalizar(crudo), len(partes), len(crudo)


def fragmentos(texto: str) -> list[str]:
    """Trocea el texto de una página en fragmentos de ~35 palabras SIN cruzar saltos de línea de más:
    en una hoja multilingüe el idioma cambia por párrafo, y el fragmento tiene que respetarlo."""
    out, buf, n = [], [], 0
    for linea in (texto or "").splitlines():
        pal = linea.split()
        if not pal:
            continue
        buf.append(linea.strip())
        n += len(pal)
        if n >= PALABRAS_FRAGMENTO:
            out.append(" ".join(buf))
            buf, n = [], 0
    if buf:
        out.append(" ".join(buf))
    return out


def ratio_vocales(txt: str) -> float:
    """Vocales / letras. El texto real ronda 0,36-0,46; el mojibake de fuente rota, 0,17-0,23."""
    letras = [ch for ch in (txt or "").lower() if ch.isalpha()]
    return round(sum(ch in "aeiouáéíóúü" for ch in letras) / max(1, len(letras)), 3)


def veredicto_fragmento(frag: str, corpus: str) -> tuple[str, float, int]:
    toks = [t for t in dict.fromkeys(normalizar(frag).split()) if len(t) >= 6]
    if len(toks) < MIN_TOKENS_FRAGMENTO:
        return "inconcluyente", -1.0, len(toks)
    hits = sum(1 for t in toks if f" {t} " in corpus)
    frac = hits / len(toks)
    return ("presente" if frac >= TOK_PRESENTE else
            "ausente" if frac < TOK_AUSENTE else "parcial"), round(frac, 3), len(toks)


def analizar(doc: dict, corpus: str, tmpdir: Path, c) -> dict:
    """Descarga el PDF, localiza el texto AUSENTE por fragmentos y le adjudica idioma."""
    res = {"error": None, "chars_ausentes": 0, "chars_por_idioma": {}, "paginas": {},
           "cita": "", "cita_pagina": None, "cita_por_idioma": {},
           "fragmentos": {"ausente": 0, "parcial": 0, "presente": 0, "inconcluyente": 0}}
    if not doc.get("source_url"):
        res["error"] = "sin source_url"
        return res
    tmp = tmpdir / f"{doc['document_id']}.pdf"
    try:
        r = c.get(doc["source_url"])
        if r.status_code != 200:
            res["error"] = f"HTTP {r.status_code}"
            return res
        tmp.write_bytes(r.content)
        por_idioma: dict[str, int] = defaultdict(int)
        todo_ausente, mejor = [], ("", None)
        with fitz.open(tmp) as pdf:
            for i, pg in enumerate(pdf, start=1):
                ausentes_pag = []
                for frag in fragmentos(pg.get_text() or ""):
                    v, frac, _ = veredicto_fragmento(frag, corpus)
                    res["fragmentos"][v] = res["fragmentos"].get(v, 0) + 1
                    if v == "ausente":
                        ausentes_pag.append(frag)
                        if len(frag) > len(mejor[0]):
                            mejor = (frag, i)
                        # cita POR IDIOMA: una reclamación de «castellano perdido» tiene que citar
                        # castellano, no el fragmento más largo (que suele ser el alemán).
                        lg_f = idioma(frag)
                        if len(frag) > len(res["cita_por_idioma"].get(lg_f, ("",))[0]):
                            res["cita_por_idioma"][lg_f] = (re.sub(r"\s+", " ", frag)[:240], i)
                if ausentes_pag:
                    txt = " ".join(ausentes_pag)
                    lg = idioma(txt)
                    res["paginas"][i] = {"chars": len(txt), "idioma": lg,
                                         "muestra": re.sub(r"\s+", " ", txt)[:220]}
                    por_idioma[lg] += len(txt)
                    todo_ausente.append(txt)
        res["chars_ausentes"] = sum(por_idioma.values())
        res["chars_por_idioma"] = dict(sorted(por_idioma.items(), key=lambda kv: -kv[1]))
        res["idioma_global"] = idioma(" ".join(todo_ausente)) if todo_ausente else "?"
        res["ratio_vocales"] = ratio_vocales(" ".join(todo_ausente))
        res["cita"] = re.sub(r"\s+", " ", mejor[0])[:240]
        res["cita_pagina"] = mejor[1]
    except Exception as e:  # noqa: BLE001
        res["error"] = f"{type(e).__name__}: {e}"
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
    return res


def veredicto(res: dict) -> str:
    if res.get("error"):
        return "no_medible"
    porid = res.get("chars_por_idioma") or {}
    es = porid.get("es", 0)
    if res["chars_ausentes"] >= MIN_CHARS_PERDIDA and res.get("ratio_vocales", 1.0) < MIN_VOCALES:
        # PRIMERO que cualquier reclamación: un texto nativo ilegible (fuente rota) no prueba nada.
        return "fuente_ilegible"
    if es >= MIN_CHARS_PERDIDA:
        return "castellano_perdido"
    if res["chars_ausentes"] < MIN_CHARS_PERDIDA:
        return "sin_perdida_relevante"
    dom = max(porid, key=lambda k: porid[k]) if porid else "?"
    return "indeterminado" if dom in ("?", "otro") and res.get("idioma_global") in ("?", "otro") \
        else ("otro_idioma_por_politica" if dom != "es" else "castellano_perdido")


# --------------------------------------------------------------------------- reclasificación
def reclasificar(clase: str, ver: str) -> str | None:
    """Clase NUEVA a la luz del veredicto, o None si no procede tocarla. La traza queda en meta."""
    if ver == "fuente_ilegible":
        return "fuente_ilegible"          # ni sano ni pérdida: el nativo no sirve de verdad
    if ver in ("sin_perdida_relevante", "sano_reverificado") and clase != "sano":
        return "sano_reverificado"        # hoy no falta nada (p. ej. tras una re-ingesta)
    if ver == "castellano_perdido" and clase in ("paginas_perdidas_sin_idioma", "texto_perdido"):
        return "paginas_perdidas_es" if clase.startswith("paginas") else "texto_perdido_es"
    if ver == "otro_idioma_por_politica":
        if clase == "texto_perdido":
            return "texto_perdido_otro_idioma"
        if clase == "paginas_perdidas_sin_idioma":
            return "paginas_perdidas_otro_idioma"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="no escribe los entregables")
    args = ap.parse_args()
    censo = json.loads(CENSO_JSON.read_text(encoding="utf-8"))
    docs = censo["documentos"]
    tmpdir = Path(tempfile.gettempdir()) / "s324d_pdfs"
    tmpdir.mkdir(parents=True, exist_ok=True)

    elegidos = []
    for pat in OBJETIVO:
        hit = [d for d in docs if pat.lower() in (d["source_file"] or "").lower()]
        if len(hit) != 1:
            print(f"AVISO: {pat!r} casa con {len(hit)} documentos — se salta")
            continue
        elegidos.append(hit[0])

    filas, reclas = [], []
    with abierto(timeout=300.0, reintentos=1) as c:
        for d in elegidos:
            corpus, n_chunks, chars = texto_corpus(c, d["document_id"])
            res = analizar(d, corpus, tmpdir, c)
            ver = veredicto(res)
            nota = next((v for k, v in NOTA_HUMANA.items() if k.lower() in d["source_file"].lower()), None)
            if nota:
                # El ojo humano MANDA sobre el detector en los casos que este no puede cerrar
                # (portadas sin palabras vacías, fuente rota) — y se declara como tal.
                ver = nota[0].split(" (")[0]
                d["nota_humana"] = nota[1]
                d["veredicto_humano"] = nota[0]
            nueva = reclasificar(d["clase"], ver)
            print(f"{d['source_file'][:44]:<44} {d['clase'][:26]:<26} → {ver:<24} "
                  f"aus={res['chars_ausentes']:>6} {res['chars_por_idioma']}")
            d["clase_censo_original"] = d["clase"]
            d["veredicto_idioma"] = ver
            d["idiomas_texto_ausente"] = res["chars_por_idioma"]
            d["chars_texto_ausente"] = res["chars_ausentes"]
            d["idioma_global_ausente"] = res.get("idioma_global")
            d["ratio_vocales_ausente"] = res.get("ratio_vocales")
            d["cita_texto_ausente"] = res["cita"]
            d["cita_pagina"] = res["cita_pagina"]
            d["fragmentos_verificados"] = res["fragmentos"]
            d["paginas_texto_ausente"] = res["paginas"]
            d["accionable"] = ver == "castellano_perdido"
            d["chunks_ahora"] = n_chunks
            d["chars_corpus_ahora"] = chars
            if nueva:
                reclas.append({"source_file": d["source_file"], "de": d["clase"], "a": nueva,
                               "motivo": ver})
                d["clase"] = nueva
            filas.append((d, res, ver))

    clases = Counter(x["clase"] for x in docs)
    censo["meta"]["verificacion_idioma"] = {
        "que_es": "veredicto de idioma del TEXTO AUSENTE por fragmentos (~35 palabras) — s324d",
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "documentos_verificados": [d["source_file"] for d, _, _ in filas],
        "metodo": "fragmentos de ~35 palabras respetando líneas; ausente si <35 % de sus palabras "
                  "de ≥6 letras están en los chunks; idioma por palabras vacías (19 idiomas)",
        "reclasificaciones": reclas,
        "clases_tras_reclasificar": dict(clases.most_common()),
    }
    if args.dry_run:
        print("\n--dry-run: no se escribe nada\n", json.dumps(censo["meta"]["verificacion_idioma"],
                                                             ensure_ascii=False, indent=1))
        return 0
    CENSO_JSON.write_text(json.dumps(censo, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- sección del informe (idempotente: se reemplaza si ya existía) ----
    def celda(s, n):
        return (s or "—")[:n]

    L = [MARCA, "",
         "Cierra el cabo suelto declarado: los 4 `texto_perdido` sin verificar y los 3 "
         "`paginas_perdidas_sin_idioma`, más las 2 confirmaciones. Método: fragmentos de ~35 palabras "
         "(en estos documentos NO falta ninguna página entera — falta texto DENTRO de páginas "
         "presentes), buscados en los chunks por palabras de ≥6 letras; idioma por palabras vacías.", "",
         "|documento|clase censo|ausente (chars)|idiomas|veredicto|",
         "|---|---|---:|---|---|"]
    for d, res, ver in filas:
        L.append("|" + "|".join([
            celda(d["source_file"], 36), d.get("clase_censo_original", d["clase"]),
            f"{res['chars_ausentes']:,}".replace(",", "."),
            celda(", ".join(f"{k} {v//1000}k" if v >= 1000 else f"{k} {v}"
                            for k, v in list(res["chars_por_idioma"].items())[:3]), 34),
            ver,
        ]) + "|")
    L += ["", "**Citas de lo que falta** (verbatim del PDF; en los `castellano_perdido`, el fragmento "
              "ausente más largo adjudicado al ESPAÑOL):"]
    for d, res, ver in filas:
        if ver != "castellano_perdido":
            continue
        cita, pag = res.get("cita_por_idioma", {}).get("es") or (res.get("cita"), res.get("cita_pagina"))
        if cita:
            L.append(f"- `{d['source_file'][:38]}` p{pag}: «{cita[:170]}»")
    notas = [(d, d.get("nota_humana")) for d, _, _ in filas if d.get("nota_humana")]
    if notas:
        L += ["", "**Lectura humana** (donde el detector no puede cerrar solo; amplía y corrige la "
                  "sección «Verificado a ojo» de arriba):"]
        L += [f"- `{d['source_file'][:38]}` → **{d['veredicto_humano']}**: {n}" for d, n in notas]
    if reclas:
        L += ["", "**Reclasificaciones aplicadas** (el recuento por clase de arriba es el del censo "
                  "ORIGINAL; estas filas lo corrigen):"]
        L += [f"- `{r['source_file'][:38]}`: `{r['de']}` → `{r['a']}` ({r['motivo']})" for r in reclas]
        L += ["", "Clases tras reclasificar: " +
              " · ".join(f"{k} {v}" for k, v in clases.most_common()) + "."]
    else:
        L += ["", "Ninguna reclasificación procede: los veredictos confirman las clases del censo."]
    L += ["", "> **Dato posterior al censo**: `HLSI-TI-007_VSN-4REL` ya está **RE-INGESTADO** "
              "(47 → 3.601 chars, 2 chunks, con el procedimiento PROG/Z1/40 cm dentro). Su fila del "
              "censo refleja el estado ANTERIOR: no está pendiente.", ""]

    md = CENSO_MD.read_text(encoding="utf-8")
    md = md.split(MARCA)[0].rstrip() + "\n\n" + "\n".join(L)
    CENSO_MD.write_text(md, encoding="utf-8")
    print(f"\nactualizados: {CENSO_JSON.relative_to(ROOT)} · {CENSO_MD.relative_to(ROOT)} "
          f"({len(md.split())} palabras totales)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
