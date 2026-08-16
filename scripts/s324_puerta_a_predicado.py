# -*- coding: utf-8 -*-
"""s324 — PUERTA A rehecha: predicado de RECONSTRUIBILIDAD, validado contra el DOBLE CONTROL
antes de mirar una sola fila nueva. NO aplica nada.

Por qué se rehace (DEC-220 / evals/s323_criterio_limpieza_candidates_v1.md): el predicado de s323
(«aparece una medida/norma a ±90 chars») pasó 3 filas y las 3 eran productos reales (VSN 2Plus, PL4-E,
34110400) — correlacionaba, no probaba. El predicado correcto: **los caracteres del término tienen que
ser RECONSTRUIBLES desde el texto vecino** («82 mm» → MM-82; «up to 3200 m» → TO-3200M; «of 48V» →
OF-48V; «local 360°» → LOCAL-360; «EN 54-25» → EN-54-25).

Predicado ARTEFACTO(term, texto_del_documento_fuente) — TODAS:
  1. SEGMENTOS: el término se parte en tramos alfabéticos/numéricos (MM-82 → mm|82; TO-3200M → to|3200|m).
     Todos los tramos ALFABÉTICOS pertenecen al LÉXICO de palabras/unidades/preposiciones comunes
     (mm, m, v, of, to, en, local, up, max…) y hay al menos uno. Un tramo que NO es palabra (vsn, pl,
     zx…) desactiva el predicado: eso es un código, no una frase colapsada.
  2. RECONSTRUCCIÓN: en el texto extraído del documento fuente existe una VENTANA corta (≤ 48 chars)
     donde TODOS los tramos aparecen como tokens completos (en cualquier orden: «82 mm» ↔ MM-82).
     Se guarda ese fragmento verbatim como prueba.
  3. NO ES SUJETO: el término no aparece como titular markdown, fila de tabla de modelos ni referencia
     comercial («Ref./Mod./Modelo:») en el texto extraído del documento fuente.
  Clase aparte NORMA/CERT: el término casa con ^(EN|UNE|ISO|IEC|NFPA|UL|VdS|LPCB|CPD|CPR|ATEX|IP|IK)[- ]?\\d
  y aparece literal en el texto → ARTEFACTO (código de norma/certificación, no producto).
  Términos SOLO numéricos: NUNCA artefacto por este predicado (pueden ser referencias/part-numbers).

Salida: evals/s324_puerta_a_predicado_v1.json — validación (positivos deben PASAR, negativos deben
FALLAR) y, solo si valida, el resultado sobre las filas RETIRAR de E1b (§0.D 4 + las de veredicto
RETIRAR en §1). Si NO valida → se declara y esas clases se quedan en cuarentena.
"""
from __future__ import annotations
import json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)
from src.http_pool import abierto
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}

# léxico de palabras/unidades/preposiciones que un extractor puede colapsar en un «modelo»
LEXICO = set("""
mm cm m km in ft v vdc vac vcc vca kv w kw ma a ah mah hz khz db dba ohm ohms k kohm mohm bar psi lpm lux lm
c f k s ms min h hrs hr sec seg dia dias day days
to of the and or for with from up down at on in by per max min mín máx
en de del la el los las con para por sin sobre entre hasta desde según segun y o u e a al
et le la les des du de pour avec dans par sur
und der die das mit für von zu bis
local remote global standard estandar estándar general normal
""".split())
RX_NORMA = re.compile(r"^(EN|UNE|ISO|IEC|NFPA|UL|VdS|LPCB|CPD|CPR|ATEX|IP|IK|CE)[- ]?\d", re.I)
RX_SUJETO = [
    (r"^#{1,4}[^\n]*\b{t}\b", "titular"),
    (r"\|\s*{t}\s*\|", "fila de tabla"),
    (r"\b(ref|mod|modelo|model|art|référence|referencia)\.?\s*:?\s*{t}\b", "referencia comercial"),
    (r"^\s*\*\*{t}\*\*", "negrita de encabezado"),
]


def segmentos(term: str) -> list[str]:
    return [s.lower() for s in re.findall(r"[A-Za-zÀ-ÿ]+|\d+", term)]


def _tok(seg: str) -> str:
    """Token completo POR CLASE: un tramo numérico no puede ir pegado a otro dígito, y uno
    alfabético no puede ir pegado a otra letra — pero «48V» sí cuenta como «48»+«v» (así es
    como el extractor colapsó «of 48V» en OF-48V)."""
    if seg.isdigit():
        return r"(?<!\d)" + re.escape(seg) + r"(?!\d)"
    return r"(?<![A-Za-zÀ-ÿ])" + re.escape(seg) + r"(?![A-Za-zÀ-ÿ])"


def es_sujeto(term: str, txt_md: str) -> str | None:
    t = re.escape(term)
    for rx, que in RX_SUJETO:
        if re.search(rx.replace("{t}", t), txt_md, re.I | re.M):
            return que
    return None


def reconstruible(term: str, texto: str, ventana: int = 48) -> dict:
    segs = segmentos(term)
    alfa = [s for s in segs if not s.isdigit()]
    out = {"term": term, "segmentos": segs, "clase": None, "artefacto": False, "prueba": None, "motivo": None}
    if not segs:
        out["motivo"] = "sin segmentos"; return out
    if not alfa:
        out["motivo"] = "solo numérico: nunca artefacto por predicado (puede ser part-number)"; return out
    if RX_NORMA.match(term) and re.search(_tok_seq(segs), texto, re.I):
        out.update(clase="norma/certificación", artefacto=True,
                   prueba=_fragmento(texto, _tok_seq(segs)), motivo="código de norma/certificación literal en el texto")
        return out
    fuera = [s for s in alfa if s not in LEXICO]
    if fuera:
        out["motivo"] = f"tramo(s) que NO son palabra/unidad común: {fuera} → es un código, no una frase colapsada"; return out
    # ventana con TODOS los tramos como tokens completos, en cualquier orden
    posiciones = [[m.start() for m in re.finditer(_tok(s), texto, re.I)] for s in segs]
    if any(not p for p in posiciones):
        out["motivo"] = "algún tramo no aparece como token completo en el documento fuente"; return out
    mejor = None
    for p0 in posiciones[0]:
        lo, hi = p0, p0 + len(segs[0])
        ok = True
        for k in range(1, len(segs)):
            cerca = [p for p in posiciones[k] if abs(p - p0) <= ventana]
            if not cerca:
                ok = False; break
            q = min(cerca, key=lambda p: abs(p - p0)); lo, hi = min(lo, q), max(hi, q + len(segs[k]))
        if ok and (hi - lo) <= ventana + max(len(s) for s in segs):
            frag = texto[max(0, lo - 30): min(len(texto), hi + 30)]
            if mejor is None or (hi - lo) < mejor[0]:
                mejor = (hi - lo, frag)
    if not mejor:
        out["motivo"] = "los tramos no co-ocurren en una ventana corta"; return out
    out.update(clase="frase/medida colapsada", artefacto=True, prueba=mejor[1],
               motivo=f"todos los tramos {segs} son palabras/unidades comunes y co-ocurren en {mejor[0]} chars")
    return out


def _tok_seq(segs: list[str]) -> str:
    return r"(?<![A-Za-z0-9])" + r"[-\s/.]*".join(re.escape(s) for s in segs) + r"(?![A-Za-z0-9])"


def _fragmento(texto: str, rx: str) -> str | None:
    m = re.search(rx, texto, re.I)
    return texto[max(0, m.start() - 40): m.end() + 40] if m else None


_cache: dict[str, str] = {}


def texto_doc(c, source_file: str) -> str:
    if source_file in _cache:
        return _cache[source_file]
    r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
              params={"select": "chunk_index,content", "source_file": f"eq.{source_file}",
                      "order": "chunk_index.asc", "limit": "1000"})
    rows = r.json() if r.status_code == 200 else []
    _cache[source_file] = "\n".join(x.get("content") or "" for x in rows)
    return _cache[source_file]


def evaluar(c, term: str, source_file: str) -> dict:
    txt = texto_doc(c, source_file)
    res = reconstruible(term, re.sub(r"[ \t]+", " ", txt))
    suj = es_sujeto(term, txt)
    res["source_file"] = source_file
    res["es_sujeto"] = suj
    res["n_chars_texto"] = len(txt)
    res["puerta_a"] = bool(res["artefacto"] and not suj)
    return res


def main() -> int:
    positivos = [("MM-82", "I56-4407-001 MI-DCMOE"), ("TO-3200M", "MIW-INT-Cuantos-expansores-puedo-conectar-al-Interface-pasarela"),
                 ("OF-48V", "I56-4422-000 M701E-240"), ("LOCAL-360", "I56-1320-001 SDX-751TEM"),
                 ("EN-54-25", "I56-4205-001 NRX-SMT3 Web")]
    negativos = [("VSN 2Plus", "MF_HSF_280_rv004"), ("PL4-E", "MNDT515"), ("34110400", "55310600 Manual TCD-106 kit_ES")]
    salida = {"que_es": __doc__.strip().splitlines()[0], "utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
              "validacion": {"positivos": [], "negativos": []}, "valida": None, "filas_retirar": [], "resumen": None}
    with abierto(timeout=60.0) as c:
        for t, sf in positivos:
            salida["validacion"]["positivos"].append(evaluar(c, t, sf))
        for t, sf in negativos:
            salida["validacion"]["negativos"].append(evaluar(c, t, sf))
        pos_ok = all(r["puerta_a"] for r in salida["validacion"]["positivos"])
        neg_ok = all(not r["puerta_a"] for r in salida["validacion"]["negativos"])
        salida["valida"] = bool(pos_ok and neg_ok)
        print("VALIDACIÓN doble control:")
        for r in salida["validacion"]["positivos"] + salida["validacion"]["negativos"]:
            print(f"  {r['term']!r:12} puerta_a={r['puerta_a']!s:5} clase={r['clase']} sujeto={r['es_sujeto']} — {r['motivo'][:90]}")
            if r["prueba"]:
                print(f"      prueba: «{re.sub(chr(10), ' ', r['prueba'])[:120]}»")
        print("VALIDA:", salida["valida"], "(positivos", pos_ok, "· negativos", neg_ok, ")")
        if salida["valida"]:
            qa = json.loads((ROOT / "evals" / "s322_e1b_revisar_qa_v1.json").read_text(encoding="utf-8"))
            filas = list(qa["secciones"]["0_bloque_retirar"]) + [f for f in qa["secciones"]["1_individual"]
                                                                if (f.get("llm") or {}).get("veredicto") == "RETIRAR"]
            P = {p["id"]: p for p in _read_jsonl(CATALOG_DIR / "products.jsonl")}
            for f in filas:
                p = P.get(f["id"])
                # documento fuente = provenance del id (s83:<source_file>) o el doc con más menciones hoy
                prov = (p or {}).get("provenance") or f.get("provenance") or ""
                m = re.match(r"s83:(.+?)(?: \(|$)", prov)
                sf = m.group(1).strip() if m else None
                docs = f.get("provenance_chunks_hoy") or []
                if not sf and docs:
                    sf = docs[0] if isinstance(docs[0], str) else (docs[0].get("source_file") or docs[0].get("doc"))
                res = evaluar(c, f["modelo"], sf) if sf else {"term": f["modelo"], "puerta_a": False, "motivo": "sin documento fuente"}
                res.update(id=f["id"], en_catalogo=bool(p), candidate=(p or {}).get("candidate"), veredicto_llm=(f.get("llm") or {}).get("veredicto"))
                salida["filas_retirar"].append(res)
            # generalización: los 17 «RETIRAR en bloque» del draft E1 (§0.D: la clase MM-82/«82 mm») —
            # NO son filas del catálogo (son altas del draft que no se hacen), pero miden si el
            # predicado cubre esa clase más allá de los 5 controles.
            tri = json.loads((ROOT / "evals" / "s322g_e1_candidatos_triage_v1.json").read_text(encoding="utf-8"))
            salida["generalizacion_e1_0D"] = []
            for f in tri["seccion_0b_retirar_en_bloque"]:
                sf = f["documento"]["source_pdf_filename"]
                sf = re.sub(r"\.pdf$", "", sf) if not texto_doc(c, sf) else sf
                res = evaluar(c, f["canonical_model"], sf)
                res.update(id=f["id"], veredicto_llm=f["llm"].get("veredicto"), termino_real_llm=f["llm"].get("termino_real"))
                salida["generalizacion_e1_0D"].append(res)
            g = salida["generalizacion_e1_0D"]
            print(f"generalización E1 §0.D (17 artefactos del draft): pasan Puerta A {sum(1 for r in g if r['puerta_a'])}/{len(g)}")
            for r in g:
                print(f"   {'PASA ' if r['puerta_a'] else 'no   '} {r['term']!r:22} — {r['motivo'][:80]}")
            n = len(salida["filas_retirar"]); k = sum(1 for r in salida["filas_retirar"] if r["puerta_a"])
            salida["resumen"] = {"filas_retirar_evaluadas": n, "pasan_puerta_a": k,
                                 "generalizacion_e1_0D": f"{sum(1 for r in g if r['puerta_a'])}/{len(g)}"}
            print(f"filas RETIRAR de E1b evaluadas: {n} · pasan Puerta A: {k}")
            for r in salida["filas_retirar"]:
                if r["puerta_a"]:
                    print(f"  PASA {r['id']} «{r['term']}» — {r['motivo'][:80]} · prueba «{re.sub(chr(10),' ',r['prueba'] or '')[:90]}»")
    (ROOT / "evals" / "s324_puerta_a_predicado_v1.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if salida["valida"] else 1


if __name__ == "__main__":
    sys.exit(main())
