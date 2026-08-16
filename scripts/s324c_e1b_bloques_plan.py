# -*- coding: utf-8 -*-
"""s324c — PLANES por bloque del packet E1b (`evals/s320_e1b_packet_adjudicacion_v2.md`) para que
Alberto dé su «sí» bloque a bloque CON el resultado del gate delante. NADA SE APLICA: este script
solo LEE (catálogo + Supabase) y escribe planes + censo; el writer se invoca SIEMPRE en dry-run.

Bloques (uno por plan, `evals/s324c_e1b_bloque_<nombre>_plan_v1.json`):
  §0.A «confirmar» determinista (s322f detalle.bloque, ruta=determinista) — UN plan por marca:
        notifier · unresolved · kidde · morley · systemsensor · xtralis · fidegas · spectrex
        (detnov YA aplicado hoy por la puerta → se salta).
  §0.B «confirmar» juez alta+cita (s322f detalle.bloque, ruta=llm, 129).
  §0.C «revisar»→CONFIRMAR (s322 secciones.0_bloque_confirmar, 144).
  §0.D «revisar»→RETIRAR (s322 secciones.0_bloque_retirar, 4) → products_retirar.

Cada fila `products_confirmar`: id existente + candidate + activo; `document_id` de la evidencia;
`n_token = n_token(texto, canonical) ≥ 1` (token literal, s324_lib) y `cita = ventana(texto, canonical)`
verificada full-text. Si no verifica → `no_aplicar` con motivo (no se inventa nada).
ALIAS DESCRIPTIVOS (precedente detnov, gate r30): para cada id del plan se clasifican sus alias y los
descriptivos/peligrosos van a `aliases_quitar` (regla en `avisos`); los model-shaped se conservan.
Colisiones que el validador de la puerta rechazaría (canonical duplicado entre consumibles, alias↔canonical)
o que pisarían un paraguas (exact gana al paraguas) → `no_aplicar` + aviso (decide Alberto).

Uso:  python -X utf8 scripts/s324c_e1b_bloques_plan.py [--solo 0a_notifier,0b] [--sin-writer] [--sin-censo]
      (el writer se lanza en dry-run por bloque; si STOP por un alias descriptivo que se escapó, se añade a
       aliases_quitar y se re-corre; si el culpable es un CANONICAL, el bloque queda en STOP y se explica).
Salida: planes + evals/s324c_e1b_bloque_<nombre>_v1_radio_explosion.json (writer) + evals/s324c_e1b_bloques_censo_v1.md
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys, unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)
from src.http_pool import abierto
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl, norm_token
from src.rag import catalog as C
from src.rag.catalog_resolver import DETECT_ALIAS_TIPOS, DETECT_STOPWORDS
from scripts.s324_lib import SB, HS, doc, texto, n_token, ventana, cita_ok, norm

PY = sys.executable
UTC = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
S322F = ROOT / "evals" / "s322f_e1b_confirmar_encoger_v1.json"
S322Q = ROOT / "evals" / "s322_e1b_revisar_qa_v1.json"
K5 = ROOT / "evals" / "s324c_rejuicio_k5_v1.json"
PACKET = "evals/s320_e1b_packet_adjudicacion_v2.md"
ADDED_BY = "s324c-e1b-bloques"
WRITER = ROOT / "scripts" / "s324_lote_firmado_writer.py"
CENSO_MD = ROOT / "evals" / "s324c_e1b_bloques_censo_v1.md"

# ───────────────────────── catálogo (solo lectura) ─────────────────────────
P = {r["id"]: r for r in _read_jsonl(CATALOG_DIR / "products.jsonl")}
ALIASES = _read_jsonl(CATALOG_DIR / "aliases.jsonl")
UMBRELLAS = _read_jsonl(CATALOG_DIR / "umbrellas.jsonl")
HOMONYMS = _read_jsonl(CATALOG_DIR / "homonyms.jsonl")
DOC_MAP = _read_jsonl(CATALOG_DIR / "doc_map.jsonl")
ALIAS_BY_ID: dict[str, list[dict]] = defaultdict(list)
for a in ALIASES:
    ALIAS_BY_ID[a["id"]].append(a)
ALIAS_BY_NORM: dict[str, list[dict]] = defaultdict(list)
for a in ALIASES:
    ALIAS_BY_NORM[norm_token(a["alias"])].append(a)
CANON_CONSUMIBLE = {norm_token(p["canonical_model"]): pid for pid, p in P.items()
                    if p.get("estado") == "activo" and not p.get("candidate")}
UMB_BY_NORM = {norm_token(u["termino"]): u for u in UMBRELLAS}
HOM_BY_NORM = {norm_token(h["termino"]): h for h in HOMONYMS}


def consumible(pid: str) -> bool:
    p = P.get(pid)
    seen = set()
    while p and p.get("estado") == "redirect" and p.get("redirect_to") and pid not in seen:
        seen.add(pid); pid = p["redirect_to"]; p = P.get(pid)
    return bool(p) and p.get("estado") == "activo" and not p.get("candidate")


# ───────────────────────── léxico: model-shaped / descriptivo ─────────────────────────
UNIT_RX = re.compile(r"^\d+(?:[.,]\d+)?(v|vdc|vac|vcc|ah|ma|mah|mm|cm|m|km|hz|khz|mhz|db|dba|kg|g|l|ml|ft|in|"
                     r"ohm|ohms|s|ms|h|min|bar|psi|w|kw|va|x|u|ud|uds|mm2|pulgadas)$")
GENERICAS_RX = re.compile(r"\b(panel|panels|paneles|central|centrales|detector|detectores|detectors|module|modules|"
                          r"modulo|modulos|software)\b")
NZ_RX = re.compile(r"^\d+ (zonas|zones|lazos|loops|entradas|salidas)$")
OCR_RX = re.compile(r"(?<=\d)[oO]|[oO](?=\d)")
COMUNES_CANON = {"serie", "series", "sistema", "system", "vision", "plus", "mini", "vista", "model", "modelo",
                 "transponder", "honeywell", "app", "software", "smart", "notifier", "kit", "caja", "panel",
                 "central", "tipo", "type", "unit", "unidad", "cable", "board", "display", "remote", "solo",
                 "point", "exit", "max", "base", "zona", "lazo", "sensor", "detector", "nas", "net", "plus"}


def fold(s: str) -> str:
    n = unicodedata.normalize("NFKD", s or "")
    return "".join(ch for ch in n if not unicodedata.combining(ch)).lower()


def model_shaped(word: str) -> bool:
    """Token con pinta de modelo: letras+dígitos (con o sin guión/punto/+), o P/N numérico con guión
    (9-30441, 020-590, 380114-2) o ≥4 dígitos seguidos (3466, 777650). NO: números sueltos («2», «250»),
    unidades («24V», «12Ah», «5.5m»), versiones sin letra («3.2»), palabras."""
    t = word.strip("()[]{}«»\"'.,;:*#|™")
    if not t or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+/_-]*", t):
        return False
    hd, hl = any(c.isdigit() for c in t), any(c.isalpha() for c in t)
    if hd and hl:
        return not UNIT_RX.match(t.lower())
    if hd:
        digs = sum(c.isdigit() for c in t)
        return ("-" in t and digs >= 4) or (t.isdigit() and len(t) >= 4)
    return False


def entra_en_detector(a: dict) -> bool:
    """Réplica de `catalog_resolver._resolvable_terms._add` para un alias de un id consumible."""
    nk = C.normkey(a["alias"])
    segs = "".join(re.findall(r"[a-z]+|\d+", C._fold(a["alias"])))
    if not nk or not segs or segs.isdigit() or nk in DETECT_STOPWORDS:
        return False
    return a.get("tipo") in DETECT_ALIAS_TIPOS or any(ch.isdigit() for ch in a["alias"])


def clasificar_alias(a: dict, canonical: str, canon_otros: dict[str, str] | None = None) -> list[str]:
    """Reglas del encargo (precedente detnov): devuelve las reglas que marcan el alias como
    descriptivo/peligroso ([] = se conserva). «Token de modelo» = palabra model-shaped O el propio
    canonical del producto contenido en el alias (anclado: «Sensor analógico MI-LZR», «Cargador Solo 725»).
    R6 (nace del gate de este mismo lote: «VSN12»→VSN-12 Plus2 disparó el negativo «vsn 12»): alias que
    ENTRA en el detector y cuyo normkey es prefijo del canonical de OTRO producto consumible/del plan
    seguido de letras (VSN12 → «VSN 12 PLUS»/«VSN12-2Plus»): truncación de familia AMBIGUA, no un modelo."""
    raw = a["alias"]; f = fold(raw).strip(); words = f.split()
    ck, ak = norm_token(canonical), norm_token(raw)
    anclado = bool(ck) and ck in ak
    ms = [w for w in words if model_shaped(w)]
    tiene_modelo = bool(ms) or anclado
    reglas = []
    if canon_otros and ak and ak != ck and entra_en_detector(a):
        core = C._core(raw)
        rx = re.compile(r"^" + core + r"[-\s/.+]+[a-z]") if core else None
        amb = sorted({pid for cnk, pid in canon_otros.items()
                      if rx and pid != a["id"] and cnk not in (ck, ak) and cnk.startswith(ak)
                      and rx.match(C._fold(P.get(pid, {}).get("canonical_model") or ""))})
        if amb:
            reglas.append(f"R6 truncación ambigua de familia (prefijo de {', '.join(amb[:3])})")
    if len(words) >= 2 and not tiene_modelo:
        reglas.append("R1 multipalabra sin token de modelo")
    if NZ_RX.match(f):
        reglas.append("R2 «N zonas/lazos/…»")
    if GENERICAS_RX.search(f) and not tiene_modelo:
        reglas.append("R3 palabra genérica (panel/central/detector/módulo/software) sin token de modelo")
    if len(words) == 1 and 5 <= len(f) <= 6 and OCR_RX.search(raw) and not anclado:
        reglas.append("R4 OCR (O/0 pegada a dígitos)")
    if ck and ak != ck and ak.replace("o", "0") == ck.replace("o", "0"):
        reglas.append("R4 OCR (variante O/0 del canonical)")
    return reglas


def riesgo_canonical(cm: str) -> list[str]:
    t = cm.strip(); nk = C.normkey(t); flags = []
    if len(nk) <= 3:
        flags.append("muy_corto")
    if not any(ch.isdigit() for ch in t):
        flags.append("sin_digitos")
    if re.fullmatch(r"[a-z]{1,5}", nk):
        flags.append("acronimo_corto")
    words = fold(t).split()
    if len(words) >= 2:
        flags.append("multipalabra")
    com = [w for w in words if w in COMUNES_CANON]
    if com:
        flags.append("palabra_comun:" + "/".join(com))
    segs = "".join(re.findall(r"[a-z]+|\d+", C._fold(t)))
    if segs.isdigit():
        flags.append("solo_digitos(no entra en el detector)")
    return flags


def score_riesgo(flags: list[str], n_alias_det: int, extra: int = 0) -> float:
    s = 0.0
    for f in flags:
        s += {"muy_corto": 2, "sin_digitos": 2, "acronimo_corto": 1, "multipalabra": 1}.get(f, 0)
        if f.startswith("palabra_comun"):
            s += 3
    return s + 0.5 * n_alias_det + extra


# ───────────────────────── evidencia (Supabase, solo lectura) ─────────────────────────
_docs_nombre: dict[str, list[dict]] = {}
_texto_sf: dict[str, tuple[str | None, str]] = {}


def limpia_nombre(nombre: str) -> str:
    n = (nombre or "").strip()
    for corte in (" (", " |", "|"):
        if corte in n:
            n = n.split(corte)[0].strip()
    return n


def docs_por_nombre(c, nombre: str) -> list[dict]:
    """documents por nombre (s324_lib.doc → único; si no, ilike prefijo / contiene, cualquier status)."""
    if nombre in _docs_nombre:
        return _docs_nombre[nombre]
    out = []
    d = doc(c, nombre)
    if d:
        out = [d]
    else:
        seguro = nombre.replace("%", r"\%").replace("_", r"\_").replace("*", "").replace(",", " ")
        for patron in (f"ilike.{seguro}*", f"ilike.*{seguro}*"):
            r = c.get(f"{SB}/rest/v1/documents", headers=HS,
                      params={"select": "id,source_pdf_filename,status,product_model,manufacturer",
                              "source_pdf_filename": patron, "limit": "20"})
            if r.status_code in (200, 206) and r.json():
                rows = r.json()
                out = sorted(rows, key=lambda x: (x.get("status") != "active", x.get("source_pdf_filename") or ""))
                break
    _docs_nombre[nombre] = out
    return out


def texto_por_source_file(c, nombre: str) -> tuple[str | None, str]:
    """(document_id o None, texto) de los chunks cuyo `source_file` casa (huérfanos sin fila en documents)."""
    if nombre in _texto_sf:
        return _texto_sf[nombre]
    seguro = nombre.replace("%", r"\%").replace("_", r"\_").replace("*", "")
    r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
              params={"select": "document_id,content,chunk_index", "source_file": f"ilike.{seguro}*",
                      "order": "chunk_index.asc", "limit": "1000"})
    rows = r.json() if r.status_code in (200, 206) else []
    did = next((x["document_id"] for x in rows if x.get("document_id")), None)
    _texto_sf[nombre] = (did, norm(" ".join((x.get("content") or "") for x in rows)))
    return _texto_sf[nombre]


_nombre_por_id: dict[str, str | None] = {}


def nombre_doc(c, document_id: str | None) -> str | None:
    """source_pdf_filename de `documents` por id (fallback: chunks_v2.source_file del documento)."""
    if not document_id:
        return None
    if document_id in _nombre_por_id:
        return _nombre_por_id[document_id]
    nombre = None
    r = c.get(f"{SB}/rest/v1/documents", headers=HS, params={"select": "source_pdf_filename", "id": f"eq.{document_id}"})
    if r.status_code in (200, 206) and r.json():
        nombre = r.json()[0].get("source_pdf_filename")
    if not nombre:
        r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS, params={"select": "source_file", "document_id": f"eq.{document_id}", "limit": "1"})
        if r.status_code in (200, 206) and r.json():
            nombre = r.json()[0].get("source_file")
    _nombre_por_id[document_id] = nombre
    return nombre


def n_token_flexible(txt: str, cm: str) -> int:
    core = C._core(cm)
    if not core:
        return 0
    return len(re.findall(r"(?<![a-z0-9])" + core + r"(?![a-z0-9])", C._fold(txt)))


def verifica_en_doc(c, document_id: str | None, cm: str, cita_ref: str | None, nombre: str | None = None,
                    txt: str | None = None) -> dict:
    """n_token literal + ventana + (si hay) verificación de la cita del juez/QA en ESTE documento."""
    if txt is None:
        txt = texto(c, document_id) if document_id else ""
    if not nombre and document_id:
        nombre = nombre_doc(c, document_id)
    n = n_token(txt, cm) if txt else 0
    cita = ventana(txt, cm) if n else ""
    ref_ok = None
    if cita_ref and txt:      # estricta (s324_lib.cita_ok) o, si falla, insensible a mayúsculas (el juez a veces cambia «The»→«the»)
        ref_ok = cita_ok(txt, cita_ref) or (norm(cita_ref).strip("«»\" ").casefold()[:200] in txt.casefold())
    return {"document_id": document_id, "doc": nombre, "n_token": n, "cita": cita,
            "cita_verifica": bool(cita) and cita_ok(txt, cita),
            "cita_ref_verifica": ref_ok,
            "n_token_flexible": n_token_flexible(txt, cm) if txt else 0}


# ───────────────────────── bloques ─────────────────────────
def cargar_bloques() -> dict[str, dict]:
    f = json.loads(S322F.read_text(encoding="utf-8"))
    q = json.loads(S322Q.read_text(encoding="utf-8"))
    bloque = f["detalle"]["bloque"]
    det = [x for x in bloque if x["ruta"] == "determinista"]
    llm = [x for x in bloque if x["ruta"] == "llm"]
    por_marca: dict[str, list] = defaultdict(list)
    for x in det:
        por_marca[x["id"].split(":")[0]].append(x)
    bloques: dict[str, dict] = {}
    for marca, filas in sorted(por_marca.items(), key=lambda kv: -len(kv[1])):
        if marca == "detnov":
            continue      # aplicado hoy por la puerta (evals/s324c_e1b_detnov_plan_v1.json)
        bloques[f"0a_{marca}"] = {"seccion": "§0.A", "titulo": f"§0.A «confirmar» determinista — {marca} ({len(filas)})",
                                  "fuente": "evals/s322f_e1b_confirmar_encoger_v1.json → detalle.bloque (ruta=determinista)",
                                  "filas": filas, "tipo": "confirmar_s322f"}
    bloques["0b"] = {"seccion": "§0.B", "titulo": f"§0.B «confirmar» juez alta + cita verificada ({len(llm)})",
                     "fuente": "evals/s322f_e1b_confirmar_encoger_v1.json → detalle.bloque (ruta=llm)",
                     "filas": llm, "tipo": "confirmar_s322f"}
    conf = q["secciones"]["0_bloque_confirmar"]; ret = q["secciones"]["0_bloque_retirar"]
    bloques["0c"] = {"seccion": "§0.C", "titulo": f"§0.C «revisar» → CONFIRMAR ({len(conf)})",
                     "fuente": "evals/s322_e1b_revisar_qa_v1.json → secciones.0_bloque_confirmar",
                     "filas": conf, "tipo": "confirmar_qa"}
    bloques["0d"] = {"seccion": "§0.D", "titulo": f"§0.D «revisar» → RETIRAR ({len(ret)})",
                     "fuente": "evals/s322_e1b_revisar_qa_v1.json → secciones.0_bloque_retirar",
                     "filas": ret, "tipo": "retirar_qa"}
    # (s324c noche) §1 «una a una» re-juzgadas K=5 cross-model (3× sonnet-5 + 2× gpt-5.5, rúbrica original,
    # texto completo, cita verificada): las CONVERGENTES (≥4/5) suben a bloque propuesto — mismo tratamiento
    # que §0.C/§0.D (verificación full-text + gate). Fuente: evals/s324c_rejuicio_k5_v1.json (NADA aplicado).
    if K5.exists():
        k5 = json.loads(K5.read_text(encoding="utf-8"))
        conv = {x["id"]: x for x in k5["filas"] if x.get("packet") == "E1b" and x.get("convergente") and x.get("en_bloque")}
        ind = {r["id"]: r for r in q["secciones"].get("1_individual", [])}
        k5c = [dict(ind[i], k5=conv[i]) for i in conv if i in ind and conv[i]["veredicto_mayoria"] == "CONFIRMAR"]
        k5r = [dict(ind[i], k5=conv[i]) for i in conv if i in ind and conv[i]["veredicto_mayoria"] == "RETIRAR"]
        if k5c:
            bloques["k5_confirmar"] = {"seccion": "§1·K5", "titulo": f"§1 «una a una» re-juzgadas K=5 cross-model → CONFIRMAR convergente ≥4/5 ({len(k5c)})",
                                      "fuente": "evals/s324c_rejuicio_k5_v1.json (E1b convergentes) × evals/s322_e1b_revisar_qa_v1.json → secciones.1_individual",
                                      "filas": k5c, "tipo": "confirmar_qa"}
        if k5r:
            bloques["k5_retirar"] = {"seccion": "§1·K5", "titulo": f"§1 «una a una» re-juzgadas K=5 cross-model → RETIRAR convergente ≥4/5 ({len(k5r)})",
                                     "fuente": "evals/s324c_rejuicio_k5_v1.json (E1b convergentes) × evals/s322_e1b_revisar_qa_v1.json → secciones.1_individual",
                                     "filas": k5r, "tipo": "retirar_qa"}
    return bloques


def plan_vacio(nombre: str, b: dict) -> dict:
    return {"que_es": f"s324c — E1b {b['titulo']} — plan por bloque para el sí de Alberto (NADA APLICADO; dry-run del writer)",
            "bloque": nombre, "titulo": b["titulo"], "seccion": b["seccion"], "tipo": b["tipo"], "packet": PACKET, "fuente_evidencia": b["fuente"], "utc": UTC,
            "pendiente_si_alberto": True,
            "doc_map_altas": [], "doc_map_modificaciones": [], "products_altas": [], "products_confirmar": [],
            "products_retirar": [], "products_redirect": [], "aliases_quitar": [], "aliases_altas": [], "umbrellas_altas": [],
            "retags_db": [], "no_aplicar": [], "avisos": [], "clasificacion_confirmados": {},
            "adjudicados_por_alberto_para_el_gate": {}, "colisiones_intra_bloque": [], "colisiones_cross_bloque": [],
            "alias_conservados": [], "alias_palabra_suelta": [], "riesgo_lexico": []}


def estado_producto(pid: str) -> str | None:
    p = P.get(pid)
    if not p:
        return "no existe en products.jsonl"
    if p.get("estado") == "redirect":
        return f"ya redirigido → {p.get('redirect_to')} (aplicado antes)"
    if p.get("estado") == "retirado":
        return "retirado (etiqueta retirada antes; queda como está)"
    if not p.get("candidate"):
        return "ya confirmado (candidate=false) — aplicado antes"
    return None


def evidencia_s322f(c, x: dict, cm: str) -> tuple[dict | None, list[str]]:
    """§0.A/§0.B: documento de la evidencia (evidencia.document_id) y, si allí no hay token literal, las extra."""
    intentos, motivos = [], []
    ev = x.get("evidencia") or {}
    if ev.get("document_id"):
        intentos.append((ev["document_id"], (ev.get("documento") or {}).get("fichero")))
    for e in x.get("evidencias_extra") or []:
        if e.get("document_id") and e["document_id"] not in [i[0] for i in intentos]:
            intentos.append((e["document_id"], None))
    cita_ref = x.get("cita") if x.get("ruta") == "llm" else (ev.get("fragmento") or "").strip("…")
    mejor = None
    for did, nombre in intentos:
        v = verifica_en_doc(c, did, cm, cita_ref, nombre)
        if v["n_token"] >= 1 and v["cita_verifica"]:
            if v["cita_ref_verifica"] or not cita_ref:      # preferir el doc donde TAMBIÉN verifica la cita del juez/fragmento
                return v, motivos
            mejor = mejor or v
        else:
            motivos.append(f"{nombre or did}: n_token={v['n_token']} (flexible {v['n_token_flexible']})")
    return mejor, motivos


def evidencia_qa(c, x: dict, cm: str) -> tuple[dict | None, list[str]]:
    """§0.C/§0.D: doc por nombre (provenance_doc / atribución corregida s322j); fallback chunks huérfanos."""
    motivos = []
    corr = x.get("atribucion_corregida_s322j") or {}
    cita_ref = (x.get("llm") or {}).get("cita")
    if corr.get("ahora_document_id"):
        v = verifica_en_doc(c, corr["ahora_document_id"], cm, cita_ref, corr.get("ahora_source_file"))
        if v["n_token"] >= 1 and v["cita_verifica"]:
            return v, motivos
        motivos.append(f"{corr.get('ahora_source_file')}: n_token={v['n_token']} (flexible {v['n_token_flexible']})")
    nombre = limpia_nombre(x.get("provenance_doc") or "")
    cands = docs_por_nombre(c, nombre) if nombre else []
    mejor = None
    for d in cands:
        v = verifica_en_doc(c, d["id"], cm, cita_ref, d.get("source_pdf_filename"))
        if v["n_token"] >= 1 and v["cita_verifica"]:
            if v["cita_ref_verifica"]:
                return v, motivos
            mejor = mejor or v
        else:
            motivos.append(f"{d.get('source_pdf_filename')}: n_token={v['n_token']} (flexible {v['n_token_flexible']})")
    if mejor:
        return mejor, motivos
    if nombre:
        did, txt = texto_por_source_file(c, nombre)
        if txt:
            v = verifica_en_doc(c, did, cm, cita_ref, nombre, txt=txt)
            v["huerfano_sin_fila_en_documents"] = did is None
            if v["n_token"] >= 1 and v["cita_verifica"]:
                return v, motivos
            motivos.append(f"chunks source_file≈{nombre}: n_token={v['n_token']} (flexible {v['n_token_flexible']})")
        elif not cands:
            motivos.append(f"documento «{nombre}» no resoluble ni en documents ni en chunks_v2.source_file")
    return None, motivos


def construir_plan(c, nombre: str, b: dict) -> dict:
    plan = plan_vacio(nombre, b)
    tipo = b["tipo"]
    canon_en_plan: dict[str, list[str]] = defaultdict(list)
    filas_ok: list[dict] = []
    for x in b["filas"]:
        pid = x["id"]; p = P.get(pid)
        cm = p["canonical_model"] if p else x.get("modelo")
        base = {"id": pid, "canonical_model": cm, "bloque": nombre}
        est = estado_producto(pid)
        if est:
            plan["no_aplicar"].append({**base, "motivo": est}); continue
        if tipo == "retirar_qa":
            v, motivos = evidencia_qa(c, x, cm)
            llm = x.get("llm") or {}
            if not v:
                plan["no_aplicar"].append({**base, "motivo": "la evidencia del juez no verifica full-text: " + "; ".join(motivos)}); continue
            plan["products_retirar"].append({
                "id": pid, "canonical_model": cm, "estado": "retirado",
                "motivo": f"E1b {b['seccion']} (revisar→retirar; sí de Alberto al bloque) — juez {'claude-fable-5'} RETIRAR alta: {llm.get('razon')} | qué es: {llm.get('que_es')} | cita en {v['doc']}: «{v['cita']}»" + (f" | K=5 cross-model {x['k5']['n_votos_mayoria']}/{x['k5']['n_votos_validos']} RETIRAR ({x['k5']['votos_por_juez']})" if x.get('k5') else ""),
                "doc": v["doc"], "document_id": v["document_id"], "n_token": v["n_token"], "cita": v["cita"],
                "cita_juez": llm.get("cita"), "cita_juez_verifica": v["cita_ref_verifica"], "razon_juez": llm.get("razon"),
                "que_es_juez": llm.get("que_es"), "n_frontera_hoy": x.get("n_frontera_hoy")})
            continue
        # ── confirmar ──
        nk = norm_token(cm)
        # colisiones que la puerta rechaza o que pisan un paraguas
        if nk in CANON_CONSUMIBLE and CANON_CONSUMIBLE[nk] != pid:
            plan["no_aplicar"].append({**base, "motivo": f"colisión: canonical «{cm}» ya es consumible en {CANON_CONSUMIBLE[nk]} (el validador rechaza canonical duplicado) — adjudicar (¿redirect {pid} → {CANON_CONSUMIBLE[nk]}?)"}); continue
        al_col = [a for a in ALIAS_BY_NORM.get(nk, []) if a["id"] != pid]
        if al_col:
            a0 = al_col[0]
            plan["no_aplicar"].append({**base, "motivo": f"colisión alias↔canonical: el alias «{a0['alias']}» ({a0['tipo']}) apunta a {a0['id']} — el validador rechaza un canonical consumible igual a un alias ajeno; adjudicar (¿duplicado de {a0['id']}: redirect {pid} → {a0['id']}?)",
                                       "alias_colision": al_col}); continue
        if nk in UMB_BY_NORM:
            u = UMB_BY_NORM[nk]
            plan["no_aplicar"].append({**base, "motivo": f"colisión con PARAGUAS «{u['termino']}» ({u['tipo']}, ids {u['ids']}): exact pisaría la expansión del paraguas en resolve() — adjudicar (¿{pid} ES la familia? retirar/redirigir el candidate)"}); continue
        # evidencia + verificación
        if tipo == "confirmar_s322f":
            v, motivos = evidencia_s322f(c, x, cm)
        else:
            v, motivos = evidencia_qa(c, x, cm)
        if not v:
            plan["no_aplicar"].append({**base, "motivo": "token literal del canonical NO verifica en la evidencia (n_token=0): " + "; ".join(motivos) + " — no se inventa; si el corpus lo escribe con otra grafía, adjudicar canonical/alias",
                                       "medida_e1b": {k: x.get(k) for k in ("n_chunks_token_exacto", "docs_distintos_con_exacta", "n_frontera_hoy") if k in x}})
            continue
        canon_en_plan[nk].append(pid)
        fila = {"id": pid, "canonical_model": cm, "doc": v["doc"], "document_id": v["document_id"], "n_token": v["n_token"], "cita": v["cita"]}
        if v.get("huerfano_sin_fila_en_documents"):
            fila["huerfano_sin_fila_en_documents"] = True
        if tipo == "confirmar_s322f":
            n_ch, n_docs = x.get("n_chunks_token_exacto"), x.get("docs_distintos_con_exacta")
            fila["medida_e1b"] = {"n_chunks_token_exacto": n_ch, "docs_distintos_con_exacta": n_docs, "n_ilike_hoy": x.get("n_ilike_hoy"),
                                  "banderas": x.get("banderas"), "coherencia_fabricante": x.get("coherencia_fabricante"),
                                  "fabricante_del_manual": ((x.get("evidencia") or {}).get("documento") or {}).get("fabricante")}
            if x["ruta"] == "llm":
                fila["juez"] = {"modelo": "claude-fable-5 (s322f)", "veredicto": x.get("veredicto"), "confianza": x.get("confianza"),
                                "por_que": x.get("por_que"), "cita_juez": x.get("cita"), "cita_juez_verifica_en_doc": v["cita_ref_verifica"]}
                fila["provenance_add"] = (f"s324c E1b {b['seccion']} (sí de Alberto al bloque, packet E1b v2) — juez claude-fable-5 s322f: confirmar/alta «{(x.get('por_que') or '')[:160]}»; "
                                          f"token exacto {n_ch} chunks / {n_docs} docs; cita verificada full-text en {v['doc']}: «{v['cita']}»")
            else:
                fila["provenance_add"] = (f"s324c E1b {b['seccion']} bloque {nombre.split('_',1)[-1]} (sí de Alberto al bloque, packet E1b v2) — medida determinista E1b s322f "
                                          f"(token exacto {n_ch} chunks / {n_docs} docs); cita verificada full-text en {v['doc']}: «{v['cita']}»")
        else:
            llm = x.get("llm") or {}
            fila["medida_e1b"] = {"n_frontera_hoy": x.get("n_frontera_hoy"), "n_substring_hoy": x.get("n_substring_hoy"), "marca_fila": x.get("marca"),
                                  "provenance_doc": x.get("provenance_doc"), "provenance_chunks_hoy": x.get("provenance_chunks_hoy"), "clase": x.get("clase")}
            fila["juez"] = {"modelo": "claude-fable-5 (s322 QA)", "veredicto": llm.get("veredicto"), "confianza": llm.get("confianza"),
                            "razon": llm.get("razon"), "cita_juez": llm.get("cita"), "cita_juez_verifica_en_doc": v["cita_ref_verifica"]}
            fila["provenance_add"] = (f"s324c E1b {b['seccion']} revisar→confirmar (sí de Alberto al bloque, packet E1b v2) — atestado con frontera de palabra (n_frontera_hoy={x.get('n_frontera_hoy')}); "
                                      f"juez claude-fable-5 s322 {llm.get('veredicto') or 'CONFIRMAR'} ({llm.get('confianza')}): «{(llm.get('razon') or '')[:160]}»; cita verificada full-text en {v['doc']}: «{v['cita']}»")
            if x.get("k5"):
                k = x["k5"]
                fila["juez_k5"] = {"veredicto_mayoria": k["veredicto_mayoria"], "n_votos_mayoria": k["n_votos_mayoria"], "n_votos_validos": k["n_votos_validos"],
                                   "votos_por_juez": k["votos_por_juez"], "cita_representativa": k.get("cita_representativa"), "recibo": "evals/s324c_rejuicio_k5_v1.json"}
                fila["provenance_add"] += (f"; re-juicio K=5 cross-model s324c (3× claude-sonnet-5 + 2× gpt-5.5, cita verificada full-text): "
                                           f"{k['veredicto_mayoria']} {k['n_votos_mayoria']}/{k['n_votos_validos']}")
        fila["n_token_flexible"] = v["n_token_flexible"]
        filas_ok.append(fila)
    # ── colisiones intra-bloque (mismo canonical normalizado en ≥2 ids del plan) ──
    dup = {k: v for k, v in canon_en_plan.items() if len(v) > 1}
    for k, ids in dup.items():
        branded = [i for i in ids if not i.startswith("unresolved:")]
        unres = [i for i in ids if i.startswith("unresolved:")]
        hom = HOM_BY_NORM.get(k)
        if hom:
            prop = f"homónimo «{hom['termino']}» ya registrado (política {hom.get('politica')}, candidate={hom.get('candidate')}): {hom.get('provenance','')[:140]} — confirmar los dos rompe el validador; adjudicar el homónimo (¿uno solo? ¿prefer?)"
        elif len(branded) == 1 and unres:
            prop = f"propuesta: confirmar {branded[0]} y redirect {', '.join(unres)} → {branded[0]} (como CCD-103 en el precedente detnov); decide Alberto"
        else:
            prop = "propuesta: adjudicar cuál es la marca real (¿rebrand/OEM? merge/redirect); decide Alberto"
        plan["colisiones_intra_bloque"].append({"canonical_norm": k, "ids": ids, "propuesta": prop})
        for f in [f for f in filas_ok if f["id"] in ids]:
            plan["no_aplicar"].append({"id": f["id"], "canonical_model": f["canonical_model"], "bloque": nombre,
                                       "motivo": f"colisión intra-bloque: canonical «{f['canonical_model']}» también en {[i for i in ids if i != f['id']]} — el validador rechaza dos consumibles con el mismo canonical; {prop}",
                                       "evidencia_verificada": {k2: f[k2] for k2 in ("doc", "document_id", "n_token", "cita")}})
    filas_ok = [f for f in filas_ok if norm_token(f["canonical_model"]) not in dup]
    plan["products_confirmar"] = filas_ok
    # ── alias de los ids que se confirman: descriptivos → quitar; model-shaped → conservar ──
    n_det_por_id: Counter = Counter()
    canon_otros = dict(CANON_CONSUMIBLE)                       # consumibles de hoy + los que confirma este plan
    canon_otros.update({norm_token(f["canonical_model"]): f["id"] for f in filas_ok})
    for f in filas_ok:
        for a in ALIAS_BY_ID.get(f["id"], []):
            reglas = clasificar_alias(a, f["canonical_model"], canon_otros)
            det = entra_en_detector(a)
            if reglas:
                plan["aliases_quitar"].append({**a, "regla": "; ".join(reglas), "entra_en_detector": det})
            else:
                plan["alias_conservados"].append({"alias": a["alias"], "id": a["id"], "tipo": a["tipo"], "entra_en_detector": det})
                if det:
                    n_det_por_id[f["id"]] += 1
                w = fold(a["alias"]).split()
                if len(w) == 1 and not model_shaped(w[0]) and norm_token(a["alias"]) != norm_token(f["canonical_model"]):
                    plan["alias_palabra_suelta"].append({"alias": a["alias"], "id": a["id"], "tipo": a["tipo"], "entra_en_detector": det})
    # ── avisos ──
    n_q = len(plan["aliases_quitar"]); n_q_det = sum(1 for a in plan["aliases_quitar"] if a["entra_en_detector"])
    plan["avisos"].append({"que": "alias descriptivos retirados ANTES de confirmar (precedente detnov, gate r30)",
                           "aviso": (f"{n_q} alias de los ids confirmados marcados descriptivo/peligroso ({n_q_det} entrarían en el detector al confirmar; los {n_q - n_q_det} restantes son nombre-largo sin dígito: hoy NO entran en el detector, se retiran por la misma regla — higiene, no seguridad; si prefieres conservarlos, filtra entra_en_detector=false). "
                                     "Reglas: R1 forma normalizada con ≥2 palabras y NINGUNA model-shaped (letras+dígitos con/sin guión, p. ej. CAD-250, SGD-151, TG-IP-1; P/N numérico con guión o ≥4 dígitos) ni el propio canonical dentro del alias; "
                                     "R2 «^\\d+ (zonas|zones|lazos|loops|entradas|salidas)$»; R3 contiene panel(s)/central(es)/detector(es)/module/módulo/software sin token de modelo; R4 OCR (O/0 pegada a dígitos, 5-6 chars; o variante O/0 del canonical); "
                                     "R6 (nace del gate de este lote: «VSN12» disparó el negativo «vsn 12») alias que entra en el detector y es prefijo del canonical de OTRO producto seguido de letras (truncación ambigua de familia). "
                                     f"Se conservan {len(plan['alias_conservados'])} alias model-shaped/anclados al canonical.")})
    if plan["alias_palabra_suelta"]:
        plan["avisos"].append({"que": "alias de UNA palabra sin dígito (no cubiertos por R1-R4)",
                               "aviso": f"{len(plan['alias_palabra_suelta'])} alias de una sola palabra sin pinta de modelo ({', '.join(sorted({a['alias'] for a in plan['alias_palabra_suelta']})[:12])}…): los nombre-largo NO entran en el detector; los de tipo numero-de-parte/variante-tipografica SÍ (el gate mide palabra_comun/negativos). Se conservan salvo que el gate los señale."})
    if nombre.startswith("0a_unresolved") or any(f["id"].startswith("unresolved:") for f in filas_ok):
        n_u = sum(1 for f in filas_ok if f["id"].startswith("unresolved:"))
        plan["avisos"].append({"que": "namespace unresolved: la marca NO se fabrica",
                               "aviso": f"{n_u} ids quedan en `unresolved:` (vendido_bajo tal cual está en el catálogo): confirmar solo levanta candidate=false; el fabricante del manual de la evidencia se anota por fila (medida_e1b.fabricante_del_manual) como pista para resolver la marca DESPUÉS, con adjudicación explícita (nunca automática)."})
    homs = [f for f in filas_ok if norm_token(f["canonical_model"]) in HOM_BY_NORM]
    for f in homs:
        h = HOM_BY_NORM[norm_token(f["canonical_model"])]
        plan["avisos"].append({"que": f"homónimo {h['termino']} ({f['id']})",
                               "aviso": f"el término ya es homónimo (ids {h['ids']}, política {h.get('politica')}, candidate={h.get('candidate')}): resolve() consulta el homónimo ANTES que exact ⇒ confirmar {f['id']} NO cambia la resolución {'(fail-open mientras el homónimo sea candidate)' if h.get('candidate') else ''}; el término YA está en el detector vía homónimo. Confirmar el OTRO id del homónimo en otro bloque romperá el validador (canonical duplicado)."})
    solo_dig = [f["canonical_model"] for f in filas_ok if "solo_digitos(no entra en el detector)" in riesgo_canonical(f["canonical_model"])]
    if solo_dig:
        plan["avisos"].append({"que": "canonical solo dígitos", "aviso": f"{solo_dig}: el detector excluye términos solo-dígitos ⇒ confirmar no añade término; efecto solo en resolver exact/alias y doc_map."})
    huer = [f["id"] for f in filas_ok if f.get("huerfano_sin_fila_en_documents")]
    if huer:
        plan["avisos"].append({"que": "evidencia en chunks huérfanos", "aviso": f"{huer}: la cita verifica en chunks_v2 cuyo source_file casa con el doc de procedencia pero SIN fila en documents (document_id=null); decide si eso basta."})
    # ── riesgo léxico por fila (para el censo) ──
    for f in filas_ok:
        flags = riesgo_canonical(f["canonical_model"])
        plan["riesgo_lexico"].append({"id": f["id"], "canonical_model": f["canonical_model"], "flags": flags,
                                      "alias_activados_en_detector": n_det_por_id.get(f["id"], 0),
                                      "score": score_riesgo(flags, n_det_por_id.get(f["id"], 0))})
    plan["riesgo_lexico"].sort(key=lambda r: -r["score"])
    plan["resumen"] = {k: len(v) for k, v in plan.items() if isinstance(v, list)}
    return plan


def colisiones_cross(planes: dict[str, dict]) -> None:
    por_nk: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for nombre, plan in planes.items():
        plan["colisiones_cross_bloque"] = []
        plan["avisos"] = [a for a in plan["avisos"] if a.get("que") != "colisiones con otros bloques"]
        for f in plan["products_confirmar"]:
            por_nk[norm_token(f["canonical_model"])].append((nombre, f["id"]))
    for nk, lst in por_nk.items():
        if len({b for b, _ in lst}) > 1:
            for nombre, pid in lst:
                otros = [f"{b}:{i}" for b, i in lst if b != nombre]
                planes[nombre]["colisiones_cross_bloque"].append({"id": pid, "canonical_norm": nk, "tambien_en": otros,
                                                                  "aviso": "cada bloque pasa solo; si se aplican AMBOS, el segundo dry-run fallará (canonical duplicado entre consumibles) → adjudicar antes (redirect unresolved→marca / homónimo)"})
    for nombre, plan in planes.items():
        if plan["colisiones_cross_bloque"]:
            plan["avisos"].append({"que": "colisiones con otros bloques",
                                   "aviso": f"{len(plan['colisiones_cross_bloque'])} canonicals de este bloque también se confirman en otro bloque (ver colisiones_cross_bloque): aplicar uno solo o adjudicar antes."})
        plan["resumen"] = {k: len(v) for k, v in plan.items() if isinstance(v, list)}


# ───────────────────────── writer (dry-run) ─────────────────────────
def ruta_plan(nombre: str) -> Path:
    return ROOT / "evals" / f"s324c_e1b_bloque_{nombre}_plan_v1.json"


def ruta_censo(nombre: str) -> Path:
    return ROOT / "evals" / f"s324c_e1b_bloque_{nombre}_v1_radio_explosion.json"


def escribir_plan(nombre: str, plan: dict) -> None:
    plan["resumen"] = {k: len(v) for k, v in plan.items() if isinstance(v, list)}
    ruta_plan(nombre).write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")


def dry_run(nombre: str) -> tuple[int, str, dict | None]:
    r = subprocess.run([PY, "-X", "utf8", str(WRITER), "--plan", str(ruta_plan(nombre).relative_to(ROOT))],
                       cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    out = (r.stdout or "") + ("\n[stderr]\n" + r.stderr[-3000:] if r.returncode not in (0, 1) or "Traceback" in (r.stderr or "") else "")
    cz = json.loads(ruta_censo(nombre).read_text(encoding="utf-8")) if ruta_censo(nombre).exists() else None
    return r.returncode, out, cz


def culpables_stop(cz: dict, plan: dict) -> tuple[list[dict], list[str]]:
    """Términos que causan el STOP: alias descriptivo activado (→ quitar y re-correr) o canonical (→ queda STOP)."""
    c = cz["censo"]
    terminos = set(c.get("terminos_que_disparan_negativos") or [])
    for r in c.get("por_termino") or []:
        if "palabra_comun" in r.get("riesgo", []):
            terminos.add(r["termino"])
    for q, v in (c.get("gold_perdidas") or {}).items():   # el culpable es el término NUEVO que absorbe la detección
        terminos.update(set(v.get("despues") or []) - set(v.get("antes") or []))
    canon_nk = {C.normkey(f["canonical_model"]): f["id"] for f in plan["products_confirmar"]}
    quitar, canonicos = [], []
    for t in sorted(terminos):
        nk = C.normkey(t)
        if nk in canon_nk:
            canonicos.append(f"{t} (canonical de {canon_nk[nk]})"); continue
        act = [a for a in c.get("alias_activados") or [] if C.normkey(a["alias"]) == nk]
        if act:
            for a in act:
                fila = next((r for r in ALIASES if r["alias"] == a["alias"] and r["id"] == a["id"]), None)
                if fila:
                    quitar.append({**fila, "regla": "R5 disparó en negativo sintético/gold del gate (dry-run)", "entra_en_detector": True})
        else:
            canonicos.append(f"{t} (no es alias activado ni canonical del plan: ¿resolver_gold_perdidas/paraguas?)")
    return quitar, canonicos


# ───────────────────────── censo MD ─────────────────────────
def tp_heuristico(q: str, terms: list[str]) -> str:
    fq = C._normkey(q)
    out = []
    for t in terms:
        nk = C.normkey(t)
        if nk in fq and (any(ch.isdigit() for ch in t) or len(nk) >= 5):
            out.append(f"{t}: probable TP")
        elif nk in fq:
            out.append(f"{t}: REVISAR (corto)")
        else:
            out.append(f"{t}: REVISAR")
    return "; ".join(out)


def escribir_censo(planes: dict[str, dict], resultados: dict[str, dict]) -> None:
    """Censo COMPACTO (≤900 palabras): tabla por bloque + 3-5 filas más arriesgadas por bloque + señales del gate."""
    L = [f"# s324c — E1b: censo del radio de explosión POR BLOQUE (dry-run) · {UTC}\n",
         "> ## NADA APLICADO — para el «sí» de Alberto, bloque a bloque\n"
         "> **Ojo con la nomenclatura:** las «R1…R6» de ESTE fichero son las reglas del CLASIFICADOR DE ALIAS DESCRIPTIVOS (qué alias se retiran antes de confirmar), NO las reglas de adjudicación R1–R7 del residuo (`evals/s324_reglas_residuo_adjudicacion_v1.json`).\n"
         "> Un plan por bloque (`evals/s324c_e1b_bloque_<nombre>_plan_v1.json`) + su gate (`…_v1_radio_explosion.json`, dry-run del writer, nunca `--aplicar`); sin LLM ($0). "
         "El bloque detnov (§0.A) ya se aplicó y no está aquí. Los bloques `k5_*` son las filas de §1 «una a una» cuyo re-juicio K=5 cross-model (s324c, `evals/s324c_rejuicio_k5_v1.md`) convergió ≥4/5 — propuesta, con el mismo gate. Fila confirmable = token literal ≥1 + cita verbatim verificada full-text en su documento; lo que no verifica, ya estaba aplicado o "
         "colisiona (canonical duplicado / alias ajeno / paraguas: la puerta lo rechaza) va a `no_aplicar` con motivo. Alias descriptivos de los ids confirmados → `aliases_quitar` "
         "(R1 multipalabra sin token de modelo · R2 «N zonas» · R3 panel/central/detector/módulo/software sin modelo · R4 OCR O/0 · R6 truncación ambigua de familia — nace del gate: «VSN12» disparó «vsn 12»); "
         "los model-shaped se conservan; los sin dígito no entran hoy en el detector (se retiran por higiene: filtra `entra_en_detector=false` para conservarlos).\n",
         "| bloque | filas | confirmables | no_aplicar | alias a retirar (entran en detector) | +términos | gold perdidas | negativos | tráfico real | VEREDICTO |", "|---|---|---|---|---|---|---|---|---|---|"]
    for nombre, plan in planes.items():
        r = resultados.get(nombre) or {}; cz = (r.get("censo") or {}).get("censo") or {}
        filas = len(plan.get("_filas_origen") or [])
        es_ret = plan["seccion"] == "§0.D" or plan.get("tipo") == "retirar_qa"
        conf = plan["resumen"]["products_retirar"] if es_ret else plan["resumen"]["products_confirmar"]
        n_q = plan["resumen"]["aliases_quitar"]; n_qd = sum(1 for a in plan["aliases_quitar"] if a.get("entra_en_detector"))
        L.append(f"| {nombre} | {filas} | {conf}{' (retirar)' if es_ret else ''} | {plan['resumen']['no_aplicar']} | {n_q} ({n_qd}) | {cz.get('entran','–')} | "
                 f"{len(cz.get('gold_perdidas') or {})}/{len(cz.get('resolver_gold_perdidas') or {})} | {len(cz.get('disparos_en_negativos') or {})}/{cz.get('negativos_probados','–')} | "
                 f"{len(cz.get('trafico_real_detecciones_nuevas') or {})}/{cz.get('trafico_real_consultas','–')} | **{r.get('veredicto','no medido')}** |")
    L.append("\ngold perdidas = patrón/resolver (51 gold) · negativos = frases sintéticas del writer · tráfico real = consultas de `query_logs` con detección nueva.\n")
    L.append("## Por bloque: filas más arriesgadas léxicamente y señales del gate\n")
    for nombre, plan in planes.items():
        r = resultados.get(nombre) or {}; cz = (r.get("censo") or {}).get("censo") or {}
        partes = []
        na = plan["no_aplicar"]
        if na:
            cats = Counter(("ya aplicado" if any(s in x["motivo"] for s in ("aplicado antes", "ya redirigido", "retirado (")) else
                            "colisión" if "colisi" in x["motivo"] else "sin token literal") for x in na)
            col = [x["id"] for x in na if "colisi" in x["motivo"] or "NO verifica" in x["motivo"]]
            partes.append("no_aplicar " + ", ".join(f"{v} {k}" for k, v in cats.items()) + (f" ({', '.join(col[:8])}{'…' if len(col) > 8 else ''})" if col else ""))
        top = [t for t in plan["riesgo_lexico"] if t["score"] > 0][:5]
        if top:
            partes.append("más arriesgadas: " + "; ".join(f"`{t['id']}` [{', '.join(t['flags']) or 'sin banderas'}{'; +' + str(t['alias_activados_en_detector']) + ' alias' if t['alias_activados_en_detector'] else ''}]" for t in top))
        elif plan["riesgo_lexico"]:
            partes.append("sin banderas léxicas")
        if r.get("stop_canonicos"):
            partes.append("**STOP no resuelto**: " + ", ".join(r["stop_canonicos"]))
        if cz.get("disparos_en_negativos"):
            partes.append("negativos: " + "; ".join(f"«{q}»→{v['nuevos']}" for q, v in list(cz["disparos_en_negativos"].items())[:4]))
        if cz.get("gold_perdidas") or cz.get("resolver_gold_perdidas"):
            partes.append("GOLD PIERDE: " + "; ".join(f"«{q[:50]}»" for q in list({**cz.get('gold_perdidas', {}), **cz.get('resolver_gold_perdidas', {})})[:4]))
        tr = cz.get("trafico_real_detecciones_nuevas") or {}
        if tr:
            partes.append("tráfico real: " + "; ".join(f"«{q[:55]}»→{tp_heuristico(q, v)}" for q, v in list(tr.items())[:4]))
        gn = cz.get("gold_nuevas_detecciones") or {}
        if gn:
            partes.append(f"gold con detección nueva: {len(gn)} ({'; '.join(str(v['despues']) for v in list(gn.values())[:3])})")
        if cz.get("avisos_muy_corto"):
            partes.append(f"muy cortos: {', '.join(cz['avisos_muy_corto'][:8])}")
        if plan["colisiones_cross_bloque"]:
            partes.append(f"cross-bloque: {len(plan['colisiones_cross_bloque'])} (aplicar uno o adjudicar)")
        homs = [a["que"].split(" ")[1] for a in plan["avisos"] if a["que"].startswith("homónimo")]
        if homs:
            partes.append(f"homónimos (sin efecto en resolución): {', '.join(homs)}")
        if r.get("iteraciones", 1) > 1:
            partes.append(f"re-corrido {r['iteraciones']-1}× tras quitar alias que dispararon")
        L.append(f"- **{nombre}** ({plan['seccion']}) — **{r.get('veredicto','no medido')}**" + (" · " + " · ".join(partes) if partes else ""))
    L.append("\n## No medido\n")
    L.append("- Retrieval/generación end-to-end (instrumento: FULL v3.2). El «TP» del tráfico real es heurístico (modelo literal en la consulta), no juzgado. "
             "El efecto sobre `must_preserve` (alias de una palabra como token distintivo D2) no se mide. Cada bloque se midió contra el catálogo de HOY: aplicar varios cambia el punto de partida (colisiones cross-bloque en cada plan).")
    CENSO_MD.write_text("\n".join(L), encoding="utf-8")


# ───────────────────────── main ─────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", default=None, help="lista de bloques separados por coma (p. ej. 0a_notifier,0b)")
    ap.add_argument("--sin-writer", action="store_true", help="solo planes, sin dry-run del writer")
    ap.add_argument("--sin-censo", action="store_true", help="no reescribir el .md del censo")
    ap.add_argument("--max-iter", type=int, default=3)
    args = ap.parse_args()
    bloques = cargar_bloques()
    solo = set(args.solo.split(",")) if args.solo else None
    planes: dict[str, dict] = {}
    with abierto(timeout=90.0) as c:
        for nombre, b in bloques.items():
            if solo and nombre not in solo:
                if ruta_plan(nombre).exists():
                    planes[nombre] = json.loads(ruta_plan(nombre).read_text(encoding="utf-8"))
                continue
            print(f"── construyendo {nombre}: {b['titulo']} ({len(b['filas'])} filas)", flush=True)
            plan = construir_plan(c, nombre, b)
            plan["_filas_origen"] = [x["id"] for x in b["filas"]]
            planes[nombre] = plan
            print(f"   confirmar {plan['resumen']['products_confirmar']} · retirar {plan['resumen']['products_retirar']} · no_aplicar {plan['resumen']['no_aplicar']} · aliases_quitar {plan['resumen']['aliases_quitar']} · conservados {plan['resumen']['alias_conservados']}", flush=True)
    colisiones_cross(planes)
    for nombre, plan in planes.items():
        if not solo or nombre in solo:
            escribir_plan(nombre, plan)
    resultados: dict[str, dict] = {}
    for nombre, plan in planes.items():
        if args.sin_writer or (solo and nombre not in solo):
            if ruta_censo(nombre).exists():
                cz = json.loads(ruta_censo(nombre).read_text(encoding="utf-8"))
                resultados[nombre] = {"veredicto": cz.get("veredicto"), "censo": cz, "iteraciones": 1, "stop_canonicos": []}
            continue
        it, stop_canonicos = 0, []
        while True:
            it += 1
            print(f"── dry-run {nombre} (iteración {it})", flush=True)
            rc, out, cz = dry_run(nombre)
            print(out.strip()[-1800:], flush=True)
            if cz is None:
                resultados[nombre] = {"veredicto": "ERROR (sin censo)", "censo": None, "iteraciones": it, "stop_canonicos": ["el writer no produjo censo: " + out[-400:]]}
                break
            ver = cz.get("veredicto")
            if ver == "PASS" or it >= args.max_iter:
                resultados[nombre] = {"veredicto": ver, "censo": cz, "iteraciones": it, "stop_canonicos": stop_canonicos}
                break
            quitar, canonicos = culpables_stop(cz, plan)
            nuevos = [q for q in quitar if (q["alias"], q["id"]) not in {(a["alias"], a["id"]) for a in plan["aliases_quitar"]}]
            stop_canonicos = canonicos
            if not nuevos:
                resultados[nombre] = {"veredicto": ver, "censo": cz, "iteraciones": it, "stop_canonicos": canonicos or ["STOP sin término atribuible (ver censo: resolver_gold_perdidas / findability)"]}
                break
            plan["aliases_quitar"] += nuevos
            plan["avisos"].append({"que": "alias quitados por el gate (dry-run)", "aviso": f"iteración {it}: el gate dio STOP por {[q['alias'] for q in nuevos]} (alias activados que disparan negativo/gold) → se añaden a aliases_quitar y se re-corre."})
            escribir_plan(nombre, plan)
        # NO se reescribe el plan tras el dry-run: el recibo del writer lleva `plan_sha` del fichero EXACTO que
        # midió (y `--aplicar` exige ese mismo sha) — el veredicto queda en el censo .json/.md, no en el plan.
    if not args.sin_censo:
        escribir_censo(planes, resultados)
        print("censo:", CENSO_MD.relative_to(ROOT))
    print("\nRESUMEN")
    for nombre, plan in planes.items():
        r = resultados.get(nombre) or {}
        cz = (r.get("censo") or {}).get("censo") or {}
        print(f"  {nombre:16} confirmar {plan['resumen']['products_confirmar']:3} retirar {plan['resumen']['products_retirar']} no_aplicar {plan['resumen']['no_aplicar']:3} alias_quitar {plan['resumen']['aliases_quitar']:3} "
              f"+términos {cz.get('entran','–')} gold_perdidas {len(cz.get('gold_perdidas') or {})}/{len(cz.get('resolver_gold_perdidas') or {})} neg {len(cz.get('disparos_en_negativos') or {})} "
              f"real {len(cz.get('trafico_real_detecciones_nuevas') or {})} → {r.get('veredicto','no medido')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
