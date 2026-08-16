# -*- coding: utf-8 -*-
"""s324c — RE-JUICIO K=5 CROSS-MODEL de las filas que cayeron del bloque SOLO por
«confianza media» del juez único (packets E1 y E1b). PROPUESTA para Alberto: NADA se
aplica al catálogo, ni a Supabase, ni al snapshot del detector. Solo lectura + dos
ficheros en evals/.

QUÉ FILAS
=========
· E1  (recibo evals/s322g_e1_candidatos_triage_v1.json → seccion_1_individual): filas cuyo
  primer motivo es «juez:confianza-media» — altas del draft donde el documento nombra al
  término pero el juez único (claude-fable-5) dudó. 14 filas.
· E1b (recibo evals/s322_e1b_revisar_qa_v1.json → secciones.1_individual): filas cuyo
  motivo_seccion contiene «confianza media» — candidates ya en el catálogo. 47 filas.

QUÉ HACE POR FILA (K=5, dos familias de modelo)
===============================================
· 3 votos con Anthropic `claude-sonnet-5` (temperatura por defecto — los modelos 2026 no
  aceptan `temperature`; tres llamadas independientes = tres muestras) + 2 votos con
  OpenAI `gpt-5.5` (el JUDGE_MODEL de scripts/bvg_kmajority.py). MISMO prompt para todos.
· La RÚBRICA es la ORIGINAL, importada literalmente de los dos scripts juez
  (`s322_e1b_revisar_qa.PROMPT` y `s322g_e1_candidatos_triage.PROMPT`): criterios,
  veredictos y formato JSON intactos. Lo ÚNICO que cambia es la EVIDENCIA: en vez de 6
  chunks / 8 pasajes, el TEXTO COMPLETO del documento (E1b: el documento de procedencia
  del candidate, por `source_file`; E1: el documento de origen del alta, por
  `documents.id`) — y por eso se retitula la cabecera del bloque de evidencia (dos
  `str.replace` con `assert count == 1`, para que una deriva del original no pase en
  silencio). Para E1 se conserva además la muestra dirigida de OTROS documentos (pasajes
  ±240 chars, ≤8, ≤2 por doc — misma función `_pasajes` del original), porque las
  SEÑALES DURAS de esa rúbrica hablan del resto del corpus. Para E1b, si el documento de
  procedencia NO contiene el término con frontera de palabra (o ya no está), se añaden
  hasta 6 chunks ÍNTEGROS de otros documentos que sí lo mencionan (lo que veía el juez
  original), etiquetados.
· CADA cita se verifica a TEXTO COMPLETO contra la evidencia mostrada (subcadena tras
  normalizar espacios, caja y comillas angulares «» en ambos lados; longitud mínima la de
  cada juez original: E1 ≥12 chars normalizados —s322g: «una cita de tres letras no
  fundamenta nada»—, E1b sin mínimo). Un voto con cita no verificada NO cuenta (tampoco un
  voto sin cita).
· Convergente ⇔ ≥4 de los 5 votos son VÁLIDOS y comparten veredicto. Todo lo demás sigue
  una a una. En E1 la unidad es el ID del catálogo: si el mismo id aparece en dos filas
  del draft y no son unánimes/convergentes las dos, ninguna va al bloque (regla del
  original).

SALIDA
======
· evals/s324c_rejuicio_k5_v1.json — por fila: votos (modelo_juez, veredicto, confianza,
  cita, cita_verificada, razón, uso), veredicto_mayoria, n_votos_validos, convergente,
  cita_representativa; y el coste (tokens reales × tarifa).
· evals/s324c_rejuicio_k5_v1.md — PROPUESTA DE BLOQUE agrupada por veredicto (una casilla
  por fila) + lista de las no convergentes. NADA APLICADO.

USO
===
    python scripts/s324c_rejuicio_k5.py                    # las 61 filas
    python scripts/s324c_rejuicio_k5.py --ids a:b,c:d      # smoke (escribe en el scratch)
    python scripts/s324c_rejuicio_k5.py --max-usd 12       # guardarraíl de gasto

Los votos se cachean por (packet, fila, juez, idx) en un JSON de trabajo fuera de evals/,
así una caída a mitad no vuelve a pagar lo ya juzgado (y el smoke se reutiliza en la
pasada completa).
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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import anthropic  # noqa: E402
import openai  # noqa: E402

import s322_e1b_revisar_qa as E1B  # noqa: E402  (rúbrica E1b + helpers de texto; SOLO lectura)
import s322g_e1_candidatos_triage as E1  # noqa: E402  (rúbrica E1 + recolectar(); SOLO lectura)
import s324_lib as L  # noqa: E402
from src.http_pool import abierto  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

# ───────────────────────────── configuración ─────────────────────────────

MODELO_SONNET = "claude-sonnet-5"
MODELO_GPT = "gpt-5.5"                 # = bvg_kmajority.JUDGE_MODEL
VOTOS_SONNET, VOTOS_GPT = 3, 2
K = VOTOS_SONNET + VOTOS_GPT
UMBRAL_CONVERGENCIA = 4                # ≥4/5 votos válidos con el mismo veredicto
MAX_CITA = 200
# Longitud mínima de la cita normalizada, POR PACKET, tal como la aplicaba cada juez original:
# E1 (s322g.verificar_cita) exige ≥12 chars («una cita de 3 palabras no fundamenta nada»);
# E1b (s322_e1b_revisar_qa) no impone mínimo. Se respeta la regla de cada rúbrica, no se
# inventa una común (extenderla a E1b tiraba «Kit 020-595» —11 chars, verbatim en el manual—).
MIN_CITA_NORM = {"E1": 12, "E1b": 1}
MAX_TOKENS_SONNET = 4000               # el pensamiento adaptativo consume max_tokens
EFFORT_SONNET = "medium"               # clasificación acotada con la evidencia delante (= E1b original)
MAX_TOKENS_GPT = 6000                  # razonamiento + JSON
HILOS = 5
EXTRA_CHUNKS_E1B = 6                   # = E1B.MAX_CHUNKS_EVIDENCIA

RECIBO_E1 = ROOT / "evals" / "s322g_e1_candidatos_triage_v1.json"
RECIBO_E1B = ROOT / "evals" / "s322_e1b_revisar_qa_v1.json"
DESTINO_JSON = ROOT / "evals" / "s324c_rejuicio_k5_v1.json"
DESTINO_MD = ROOT / "evals" / "s324c_rejuicio_k5_v1.md"
SCRATCH = Path(os.environ.get("S324C_SCRATCH", tempfile.gettempdir()))
CACHE = SCRATCH / "s324c_rejuicio_k5_cache.json"

# Tarifas USD por millón de tokens. Sonnet 5: lista (y precio intro vigente hasta el
# 2026-08-31, que es el que se factura HOY). gpt-5.5: NO consta tarifa oficial en el repo →
# estimación conservadora (declarada como tal en el recibo).
TARIFA = {
    MODELO_SONNET: {"lista": {"in": 3.0, "cache_w": 3.75, "cache_r": 0.30, "out": 15.0},
                    "intro": {"in": 2.0, "cache_w": 2.50, "cache_r": 0.20, "out": 10.0}},
    MODELO_GPT: {"conservadora": {"in": 2.5, "cache_r": 0.25, "out": 15.0}},
}

VEREDICTOS_E1B = {"CONFIRMAR", "RETIRAR", "NO_DECIDIBLE"}
VEREDICTOS_E1 = {"PRODUCTO_REAL", "ARTEFACTO_EXTRACCION", "NORMA_O_CERTIFICACION",
                 "ACCESORIO_DE_OTRO", "NO_DECIDIBLE"}
# lo que puede ir en BLOQUE (el resto, aun convergente, sigue individual)
BLOQUEABLES = {"E1b": {"CONFIRMAR", "RETIRAR"},
               "E1": {"PRODUCTO_REAL", "ARTEFACTO_EXTRACCION", "NORMA_O_CERTIFICACION"}}

# Observaciones del REDACTOR de este recibo (leídas en las citas al revisar el resultado; NO
# son votos ni cambian ninguna casilla): filas que los jueces confirman por la letra de la
# rúbrica («aparece listado como referencia») pero que Alberto puede querer mirar antes de
# firmar en bloque. Se muestran junto al bloque y viajan al JSON.
NOTAS_REDACTOR = {
    "unresolved:fl20xx-ei-hs": "patrones con comodín «XX» de una FAQ, no modelos concretos",
    "unresolved:mi-fl20xxxx-ei-hs": "patrones con comodín «XX» de una FAQ, no modelos concretos",
    "unresolved:nfxi-asd-xxxx-hs": "patrones con comodín «XX» de una FAQ, no modelos concretos",
    "notifier:nfs-plus": "identificador de manual/familia (pie de página), no tabla de modelos",
    "fidegas:03382": "referencias de repuesto del sensor S/2-T2",
    "fidegas:03383": "referencias de repuesto del sensor S/2-T2",
    "unresolved:55350007": "«REF» del propio manual TRMD-50X: ¿producto o código de documento?",
}

# ─────────────── rúbricas ORIGINALES, con la cabecera de evidencia retitulada ───────────────

_CAB_E1B_ORIG = ("EVIDENCIA DEL CORPUS — chunks cuyo CONTENIDO menciona «{modelo}» con frontera "
                 "de palabra ({n_frontera} chunks en total; se muestran {k}):")
_CAB_E1B_NUEVA = ("EVIDENCIA DEL CORPUS — TEXTO COMPLETO de {k}; «{modelo}» aparece con frontera "
                  "de palabra en {n_frontera} chunks del corpus hoy:")
assert E1B.PROMPT.count(_CAB_E1B_ORIG) == 1, "la rúbrica E1b original cambió: revisar el retitulado"
PROMPT_E1B = E1B.PROMPT.replace(_CAB_E1B_ORIG, _CAB_E1B_NUEVA)

_CAB_E1_PORTADA_ORIG = "INICIO DEL DOCUMENTO DE ORIGEN:"
_CAB_E1_PORTADA_NUEVA = "DOCUMENTO DE ORIGEN (TEXTO COMPLETO):"
_CAB_E1_PASAJES_ORIG = "PASAJES QUE MENCIONAN EL TÉRMINO (el término va marcado con «»):"
_CAB_E1_PASAJES_NUEVA = ("PASAJES DE OTROS DOCUMENTOS DEL CORPUS QUE MENCIONAN EL TÉRMINO "
                         "(muestra dirigida; el término va marcado con «»):")
assert E1.PROMPT.count(_CAB_E1_PORTADA_ORIG) == 1 and E1.PROMPT.count(_CAB_E1_PASAJES_ORIG) == 1, \
    "la rúbrica E1 original cambió: revisar el retitulado"
PROMPT_E1 = (E1.PROMPT.replace(_CAB_E1_PORTADA_ORIG, _CAB_E1_PORTADA_NUEVA)
             .replace(_CAB_E1_PASAJES_ORIG, _CAB_E1_PASAJES_NUEVA))


# ───────────────────────────── utilidades ─────────────────────────────

def _norm(s: str) -> str:
    """Normalización ÚNICA para verificar citas: espacios colapsados + minúsculas
    (idéntica a E1B._norm / E1._norm) + sin comillas angulares «» EN AMBOS LADOS. Las «»
    se quitan de la cita porque los pasajes E1 llevan el término marcado con ellas
    (E1.verificar_cita hace lo mismo); pero algunos manuales las traen en el TEXTO
    («ICA-6»), así que quitarlas solo de un lado fabricaba falsos negativos."""
    return re.sub(r"\s+", " ", (s or "").replace("«", "").replace("»", "")).strip().lower()


def _parse_json(txt: str) -> dict | None:
    txt = (txt or "").strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        if txt.lower().startswith("json"):
            txt = txt[4:]
    try:
        return json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
    except Exception:  # noqa: BLE001
        return None


def _verifica_cita(cita: str | None, texto_norm: str, packet: str) -> bool:
    """La cita ENTERA (hasta 200 chars) como subcadena del texto normalizado, con el mínimo de
    longitud del packet (E1 ≥12 chars; E1b sin mínimo — cada rúbrica con su regla)."""
    cn = _norm((cita or "")[:MAX_CITA])
    if len(cn) < MIN_CITA_NORM[packet]:
        return False
    return cn in texto_norm


def _texto_por_source_file(c, sf: str) -> list[str]:
    """Todos los chunks (content ORIGINAL, orden chunk_index) de un source_file."""
    trozos, off = [], 0
    while True:
        r = c.get(E1B.TABLA, headers=E1B.HS,
                  params={"select": "chunk_index,content", "source_file": f"eq.{sf}",
                          "order": "chunk_index.asc", "offset": str(off), "limit": "200"})
        r.raise_for_status()
        lote = r.json()
        trozos += [(x.get("content") or "") for x in lote]
        if len(lote) < 200:
            break
        off += 200
    return trozos


def _fmt_doc(sf: str, trozos: list[str]) -> str:
    cuerpo = "\n\n".join(re.sub(r"[ \t]+", " ", t).strip() for t in trozos)
    return f"=== DOCUMENTO «{sf}» (TEXTO COMPLETO, {len(trozos)} chunks) ===\n{cuerpo}\n=== FIN DE «{sf}» ==="


# ───────────────────────────── selección de filas ─────────────────────────────

def _filas_e1() -> list[dict]:
    rec = json.loads(RECIBO_E1.read_text(encoding="utf-8"))
    return [r for r in rec["seccion_1_individual"]
            if r.get("motivos_individual") and r["motivos_individual"][0].startswith("juez:confianza-media")]


def _filas_e1b() -> list[dict]:
    rec = json.loads(RECIBO_E1B.read_text(encoding="utf-8"))
    return [r for r in rec["secciones"]["1_individual"]
            if "confianza media" in (r.get("motivo_seccion") or "")]


def _prov_doc_e1b(fila: dict) -> str:
    """«s83:<source_file> (brand-tier=…) | …» → <source_file>. El original cortaba solo
    «(brand-tier=…)» final; algunas filas llevan cola «| x-brand→candidate»."""
    prov = (fila.get("provenance") or "").strip()
    prov = re.sub(r"^s\d+:", "", prov)
    return re.split(r"\s*\(brand-tier=", prov, maxsplit=1)[0].strip()


# ───────────────────────────── evidencia E1b ─────────────────────────────

def evidencia_e1b(c, fila: dict) -> dict:
    modelo = fila["modelo"]
    prov_doc = _prov_doc_e1b(fila)
    patron_pg = E1B.model_to_imatch_pattern(modelo)
    pat_py = E1B._patron_py(modelo)

    # documento(s) de procedencia por source_file (exacto; si no, renombrado por prefijo)
    sfs: list[str] = []
    n_exact = E1B._count(c, {"source_file": f"eq.{prov_doc}"}) if prov_doc else 0
    prov_estado = "no consta"
    if prov_doc:
        if n_exact:
            sfs, prov_estado = [prov_doc], "SIGUE"
        else:
            r = c.get(E1B.TABLA, headers=E1B.HS,
                      params={"select": "source_file", "source_file": f"ilike.{E1B._ilike(prov_doc)}*",
                              "limit": "100"})
            vistos = sorted({x["source_file"] for x in (r.json() if r.status_code in (200, 206) else [])})
            sfs = vistos[:2]
            prov_estado = "SIGUE (renombrado por revisión)" if sfs else "YA NO ESTÁ"
    docs = {sf: _texto_por_source_file(c, sf) for sf in sfs}
    texto_docs = "\n".join(" ".join(t) for t in docs.values())
    n_men_prov = len(pat_py.findall(texto_docs)) if pat_py else 0

    # chunks del corpus que mencionan el término con frontera (patrón canónico del retriever)
    r = c.get(E1B.TABLA, headers=E1B.HS,
              params={"select": "content,source_file,document_id,product_model,chunk_index",
                      "content": f"imatch.{patron_pg}", "limit": "200"})
    men = r.json() if r.status_code in (200, 206) else []
    n_frontera = E1B._count(c, {"content": f"imatch.{patron_pg}"})
    if n_frontera is None:
        n_frontera = len(men)

    # si la procedencia NO contiene el término (o no está): hasta 6 chunks ÍNTEGROS de otros docs
    extra: list[dict] = []
    if n_men_prov == 0:
        por_sf = Counter(x["source_file"] for x in men if x["source_file"] not in docs)
        cupo: Counter = Counter()
        for x in sorted((x for x in men if x["source_file"] not in docs),
                        key=lambda x: (-por_sf[x["source_file"]], x["source_file"], x["chunk_index"])):
            if len(extra) >= EXTRA_CHUNKS_E1B or cupo[x["source_file"]] >= 2:
                continue
            cupo[x["source_file"]] += 1
            extra.append(x)

    partes = [_fmt_doc(sf, t) for sf, t in docs.items()]
    if not partes:
        partes.append(f"(el documento de procedencia «{prov_doc or 'desconocido'}» YA NO ESTÁ en el corpus)")
    for x in extra:
        partes.append("--- chunk {} de «{}» (product_model: {}) — OTRO documento que menciona el término ---\n{}"
                      .format(x.get("chunk_index"), x.get("source_file"), x.get("product_model"),
                              x.get("content") or ""))
    evidencia = "\n\n".join(partes)

    k = (" + ".join(f"el documento de procedencia «{sf}» ({len(t)} chunks)" for sf, t in docs.items())
         or f"la procedencia «{prov_doc}» (ausente hoy)")
    if extra:
        k += f" y {len(extra)} chunks de otros documentos que mencionan el término"

    aviso = ""
    if fila.get("colision_catalogo"):
        aviso = ("\nATENCIÓN — ambigüedad estructural: «{}» también casa dentro de estos otros modelos "
                 "del catálogo: {}. Comprueba en la evidencia si la mención es de ESTE producto o del "
                 "otro.\n".format(modelo, ", ".join(fila["colision_catalogo"])))

    prompt = PROMPT_E1B.format(
        pid=fila["id"], modelo=modelo, marca=fila.get("marca") or "desconocida",
        prov=prov_doc or "desconocida", prov_estado=prov_estado, n_frontera=n_frontera,
        k=k, evidencia=evidencia, aviso=aviso)
    verif = _norm(texto_docs + " " + " ".join((x.get("content") or "") for x in extra))
    return {
        "prompt": prompt, "verif": verif,
        "meta": {"doc": " + ".join(docs) or prov_doc, "docs_texto_completo": list(docs),
                 "chunks_por_doc": {sf: len(t) for sf, t in docs.items()},
                 "prov_estado": prov_estado, "n_frontera_hoy": n_frontera,
                 "menciones_en_procedencia": n_men_prov,
                 "chunks_extra_de_otros_docs": [f"{x['source_file']}#{x['chunk_index']}" for x in extra],
                 "chars_evidencia": len(evidencia), "colision_catalogo": fila.get("colision_catalogo") or []},
    }


# ───────────────────────────── evidencia E1 ─────────────────────────────

def _muestra_global_e1(c, term: str, doc_id: str | None) -> tuple[dict, int, list[dict], str]:
    """Muestreo dirigido del RESTO del corpus (misma receta que E1.recolectar): chunks que
    mencionan el término (ilike por variantes + recorte regex), pasajes ±240 de OTROS docs
    (≤8, ≤2/doc, mayúsculas primero). Devuelve señales, nº docs, pasajes y texto de
    verificación extra (contenido ÍNTEGRO de los chunks muestreados)."""
    rx_f, rx_e = E1._rx_flexible(term), E1._rx_estricta(term)
    vistos: dict[str, dict] = {}
    for var in E1._variantes_ilike(term):
        try:
            for x in E1._get(c, "chunks_v2", {
                    "select": "document_id,source_file,section_title,chunk_index,product_model,content",
                    "content": f"ilike.*{var}*", "limit": str(E1.MUESTRA_GLOBAL)}):
                vistos.setdefault(f"{x['document_id']}:{x['chunk_index']}", x)
        except Exception:  # noqa: BLE001
            continue
    sen = {"flexibles": 0, "estrictas": 0, "mayusculas": 0, "como_fragmento": 0}
    docs_con: set[str] = set()
    globales = []
    for x in vistos.values():
        txt = re.sub(r"\s+", " ", x.get("content") or "")
        f_, e_, m_, fr_, sp = E1._menciones(rx_f, rx_e, txt)
        if not sp:
            continue
        sen["flexibles"] += f_; sen["estrictas"] += e_; sen["mayusculas"] += m_; sen["como_fragmento"] += fr_
        docs_con.add(x["document_id"])
        if x["document_id"] == doc_id:
            continue
        globales.append((x, txt, sp, m_))
    globales.sort(key=lambda t: (-t[3], t[0].get("source_file") or ""))
    pasajes, por_doc = [], Counter()
    for x, txt, sp, _m in globales:
        if len(pasajes) >= E1.CONTEXTOS_MAX or por_doc[x["document_id"]] >= 2:
            continue
        por_doc[x["document_id"]] += 1
        pasajes += E1._pasajes(txt, sp, f"OTRO DOC · {x.get('source_file')} · seccion={x.get('section_title')} "
                                        f"· pm={x.get('product_model')}", 1)
    verif_extra = " ".join((x.get("content") or "") for x in vistos.values())
    return sen, len(docs_con), pasajes, verif_extra


def evidencia_e1(c, fila: dict) -> dict:
    ev = E1.recolectar(fila)                       # doc de origen, hermanas, contadores (SOLO GET)
    doc = ev.get("documento") or {}
    doc_id = doc.get("id") or (fila.get("documento") or {}).get("id")
    trozos = []
    if doc_id:
        r_all, off = [], 0
        while True:
            r = c.get(f"{L.SB}/rest/v1/chunks_v2", headers=L.HS,
                      params={"select": "chunk_index,content", "document_id": f"eq.{doc_id}",
                              "order": "chunk_index.asc", "offset": str(off), "limit": "500"})
            r.raise_for_status()
            lote = r.json()
            r_all += lote
            if len(lote) < 500:
                break
            off += 500
        trozos = [(x.get("content") or "") for x in r_all]
    texto_doc = re.sub(r"\s+", " ", " ".join(trozos))
    term = ev["termino"]
    rx_f, rx_e = E1._rx_flexible(term), E1._rx_estricta(term)
    n_f, n_e, n_m, n_fr, _sp = E1._menciones(rx_f, rx_e, texto_doc)
    sen_g, n_docs_g, pasajes, verif_extra = _muestra_global_e1(c, term, doc_id)

    filename = doc.get("source_pdf_filename") or (fila.get("documento") or {}).get("source_pdf_filename") or ev["stem"]
    pasajes_txt = ("\n\n".join(f"[{p['etiqueta']}]\n{p['texto']}" for p in pasajes)
                   or "(ningún OTRO documento del corpus menciona el término en la muestra)")
    portada = (_fmt_doc(filename, trozos) if trozos
               else "(el documento de origen no tiene chunks en el corpus hoy)")
    prompt = PROMPT_E1.format(
        term=term, fab=fila["id"].split(":")[0], filename=filename,
        status=doc.get("status"), pm_doc=doc.get("product_model"),
        fab_doc=doc.get("manufacturer"), doc_type=doc.get("doc_type"),
        hermanas=json.dumps(ev["filas_mismo_fichero"], ensure_ascii=False)[:400],
        md_flex=n_f, md_estr=n_e, md_may=n_m,
        mg_flex=sen_g["flexibles"], mg_estr=sen_g["estrictas"], mg_may=sen_g["mayusculas"], mg_docs=n_docs_g,
        frag=n_fr, frag_g=sen_g["como_fragmento"],
        n_pm=ev["chunks_pm_exacto"], n_docs_pm=ev["docs_con_pm"],
        en_filename="sí" if ev["termino_en_filename"] else "no",
        portada=portada, pasajes=pasajes_txt[:9000])
    verif = _norm(texto_doc + " " + verif_extra)
    return {
        "prompt": prompt, "verif": verif,
        "meta": {"doc": filename, "doc_id": doc_id, "doc_status": doc.get("status"),
                 "pm_del_doc_hoy": doc.get("product_model"), "n_chunks_doc": len(trozos),
                 "chars_evidencia": len(portada) + len(pasajes_txt),
                 "menciones_doc": {"flexibles": n_f, "estrictas": n_e, "mayusculas": n_m, "como_fragmento": n_fr},
                 "menciones_muestra_global": {**sen_g, "documentos": n_docs_g},
                 "pasajes_otros_docs": len(pasajes),
                 "chunks_pm_exacto": ev["chunks_pm_exacto"], "docs_con_pm": ev["docs_con_pm"]},
    }


# ───────────────────────────── jueces ─────────────────────────────

_ANTH = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=300.0, max_retries=4)
_OAI = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=300.0, max_retries=4)


def voto_sonnet(prompt: str, idx: int) -> dict:
    """Una muestra de claude-sonnet-5. El bloque de texto lleva cache_control: los tres
    votos de la fila comparten prompt byte a byte → el 2º y 3º leen de caché (0,1×)."""
    ultimo = ""
    for intento in range(2):
        msg = _ANTH.messages.create(
            model=MODELO_SONNET, max_tokens=MAX_TOKENS_SONNET,
            output_config={"effort": EFFORT_SONNET},
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}}]}])
        u = msg.usage
        uso = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
               "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
               "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0}
        base = {"modelo_juez": MODELO_SONNET, "modelo_real": msg.model, "idx": idx, "uso": uso,
                "stop_reason": msg.stop_reason, "intentos": intento + 1}
        if msg.stop_reason == "refusal":
            return {**base, "json": None, "error": "refusal"}
        texto = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        js = _parse_json(texto)
        if js is not None:
            return {**base, "json": js, "error": None}
        ultimo = f"stop_reason={msg.stop_reason} texto={texto[:160]!r}"
        time.sleep(1.0)
    return {**base, "json": None, "error": f"sin JSON válido tras 2 intentos: {ultimo}"}


def voto_gpt(prompt: str, idx: int) -> dict:
    """Una muestra de gpt-5.5 (chat.completions + response_format json_object, como el
    juez de bvg_kmajority). Sin temperature/seed: gpt-5.5 fuerza temperature=1 (DEC-014)."""
    kwargs = dict(model=MODELO_GPT, response_format={"type": "json_object"},
                  messages=[{"role": "user", "content": prompt}],
                  max_completion_tokens=MAX_TOKENS_GPT)
    ultimo = ""
    base = {"modelo_juez": MODELO_GPT, "modelo_real": None, "idx": idx, "uso": None}
    for intento in range(3):
        try:
            resp = _OAI.chat.completions.create(**kwargs)
        except openai.BadRequestError as exc:
            if "max_completion_tokens" in str(exc) and "max_completion_tokens" in kwargs:
                kwargs.pop("max_completion_tokens")
                kwargs["max_tokens"] = MAX_TOKENS_GPT
                continue
            raise
        u = resp.usage
        det_p = getattr(u, "prompt_tokens_details", None)
        det_c = getattr(u, "completion_tokens_details", None)
        uso = {"input_tokens": u.prompt_tokens, "output_tokens": u.completion_tokens,
               "cached_input_tokens": (getattr(det_p, "cached_tokens", 0) or 0) if det_p else 0,
               "reasoning_tokens": (getattr(det_c, "reasoning_tokens", 0) or 0) if det_c else 0}
        base = {**base, "modelo_real": resp.model, "uso": uso, "intentos": intento + 1,
                "finish_reason": resp.choices[0].finish_reason}
        txt = resp.choices[0].message.content or ""
        js = _parse_json(txt)
        if js is not None:
            return {**base, "json": js, "error": None}
        ultimo = f"finish_reason={resp.choices[0].finish_reason} texto={txt[:160]!r}"
        time.sleep(1.0)
    return {**base, "json": None, "error": f"sin JSON válido: {ultimo}"}


# ───────────────────────────── coste ─────────────────────────────

def _coste_voto(v: dict) -> dict:
    u = v.get("uso") or {}
    if v["modelo_juez"] == MODELO_SONNET:
        out = {}
        for nombre, t in TARIFA[MODELO_SONNET].items():
            out[nombre] = (u.get("input_tokens", 0) * t["in"] + u.get("cache_creation_input_tokens", 0) * t["cache_w"]
                           + u.get("cache_read_input_tokens", 0) * t["cache_r"] + u.get("output_tokens", 0) * t["out"]) / 1e6
        return out
    t = TARIFA[MODELO_GPT]["conservadora"]
    cached = u.get("cached_input_tokens", 0)
    return {"conservadora": ((u.get("input_tokens", 0) - cached) * t["in"] + cached * t["cache_r"]
                             + u.get("output_tokens", 0) * t["out"]) / 1e6}


# ───────────────────────────── por fila ─────────────────────────────

_LOCK = threading.Lock()
_GASTO = {"sonnet_lista": 0.0, "sonnet_intro": 0.0, "gpt_conservadora": 0.0}
_STOP = {"presupuesto": False}


def _cargar_cache() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
    return {}


_CACHE = _cargar_cache()


def _guardar_cache() -> None:
    with _LOCK:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(_CACHE, ensure_ascii=False), encoding="utf-8")


def _suma_gasto(v: dict) -> None:
    c = _coste_voto(v)
    with _LOCK:
        if v["modelo_juez"] == MODELO_SONNET:
            _GASTO["sonnet_lista"] += c["lista"]
            _GASTO["sonnet_intro"] += c["intro"]
        else:
            _GASTO["gpt_conservadora"] += c["conservadora"]


def _gasto_total_conservador() -> float:
    with _LOCK:
        return _GASTO["sonnet_lista"] + _GASTO["gpt_conservadora"]


def juzgar_fila(packet: str, clave: str, prompt: str, verif: str, max_usd: float) -> list[dict]:
    """K=5 votos: 3 × sonnet (secuenciales, para que el 2º/3º lean la caché que escribe el
    1º) + 2 × gpt. Cada voto se cachea en disco por (clave, juez, idx)."""
    permitidos = VEREDICTOS_E1B if packet == "E1b" else VEREDICTOS_E1
    votos = []
    plan = [(MODELO_SONNET, i) for i in range(VOTOS_SONNET)] + [(MODELO_GPT, i) for i in range(VOTOS_GPT)]
    for juez, idx in plan:
        ck = f"{clave}|{juez}|{idx}"
        v = _CACHE.get(ck)
        if v is None:
            if _STOP["presupuesto"] or _gasto_total_conservador() > max_usd:
                _STOP["presupuesto"] = True
                v = {"modelo_juez": juez, "idx": idx, "json": None, "uso": None,
                     "error": f"NO LLAMADO: guardarraíl de gasto {max_usd} USD alcanzado"}
            else:
                try:
                    v = voto_sonnet(prompt, idx) if juez == MODELO_SONNET else voto_gpt(prompt, idx)
                except Exception as exc:  # noqa: BLE001
                    v = {"modelo_juez": juez, "idx": idx, "json": None, "uso": None,
                         "error": f"{type(exc).__name__}: {exc}"[:300]}
                if v.get("uso"):
                    _suma_gasto(v)
                # solo se cachea lo que costó dinero o dio veredicto; un error se reintenta en otra pasada
                if v.get("json") is not None or v.get("uso"):
                    with _LOCK:
                        _CACHE[ck] = v
                    _guardar_cache()
        else:
            if v.get("uso"):
                _suma_gasto(v)                       # el gasto ya hecho también cuenta en el total
        js = v.get("json") or {}
        ver = str(js.get("veredicto") or "").strip().upper() or None
        cita = js.get("cita") if isinstance(js.get("cita"), str) else None
        ok = _verifica_cita(cita, verif, packet) if cita else False
        valido = bool(ver in permitidos and ok)
        votos.append({
            "modelo_juez": v["modelo_juez"], "modelo_real": v.get("modelo_real"), "idx": idx,
            "veredicto": ver, "confianza": js.get("confianza"),
            "cita": (cita or None) and cita[:MAX_CITA], "cita_verificada": ok,
            "razon": js.get("razon"), "rol_en_texto": js.get("rol_en_texto"),
            "que_es": js.get("que_es"), "termino_real": js.get("termino_real"),
            "valido": valido, "uso": v.get("uso"), "coste_usd": _coste_voto(v) if v.get("uso") else None,
            "error": v.get("error"),
        })
    return votos


def _agrega(votos: list[dict], term: str) -> dict:
    validos = [v for v in votos if v["valido"]]
    cnt = Counter(v["veredicto"] for v in validos)
    modal, n_modal = (cnt.most_common(1)[0] if cnt else (None, 0))
    conv = n_modal >= UMBRAL_CONVERGENCIA
    rep = None
    if modal:
        cands = [v["cita"] for v in validos if v["veredicto"] == modal and v["cita"]]
        rep = max(cands, key=len) if cands else None
    # (E1) guardarraíl del original «juez:propone-otra-grafia»: si la mayoría propone OTRA
    # grafía para el modelo, se AVISA (el alta bajo un nombre falso es peor que no darla)
    grafia = None
    if modal:
        props = Counter(str(v.get("termino_real")).strip() for v in validos
                        if v["veredicto"] == modal and v.get("termino_real")
                        and E1._fold(str(v["termino_real"])) != E1._fold(term))
        if props and props.most_common(1)[0][1] >= 3:
            grafia = props.most_common(1)[0][0]
    por_juez = {}
    for v in votos:
        por_juez.setdefault(v["modelo_juez"], Counter())[v["veredicto"] or "sin_json"] += 1
    # ACUERDO BRUTO: coincidencia de veredicto SIN exigir cita verificada. NO decide nada (la
    # regla es «voto sin cita verificada no cuenta»), pero Alberto tiene que ver un 5/5
    # ARTEFACTO cuya cita es inverificable POR CONSTRUCCIÓN (el término no aparece en el
    # texto: la rúbrica E1 pide citar «el pasaje del que probablemente se derivó», que a
    # veces es el nombre del fichero — fuera del texto).
    bruto = Counter(v["veredicto"] for v in votos if v["veredicto"])
    bruto_modal, bruto_n = (bruto.most_common(1)[0] if bruto else (None, 0))
    return {"veredicto_mayoria": modal, "n_votos_validos": len(validos), "n_votos_mayoria": n_modal,
            "votos_por_veredicto": dict(Counter(v["veredicto"] or "sin_json" for v in votos)),
            "votos_por_juez": {k: dict(c) for k, c in por_juez.items()},
            "convergente": conv, "unanime": conv and len(validos) == K and len(cnt) == 1,
            "acuerdo_bruto": {"veredicto": bruto_modal, "n": bruto_n},
            "cita_representativa": rep, "grafia_propuesta_por_mayoria": grafia,
            "ninguna_cita_verificada": not any(v["cita_verificada"] for v in votos)}


# ───────────────────────────── informe MD ─────────────────────────────

def _corta(s: str | None, n: int) -> str:
    s = (s or "").replace("|", "\\|").replace("\n", " ")
    return s if len(s) <= n else s[:n - 1] + "…"


_ABREV_VER = {"ARTEFACTO_EXTRACCION": "ART", "PRODUCTO_REAL": "PROD", "NORMA_O_CERTIFICACION": "NORMA",
              "ACCESORIO_DE_OTRO": "ACC", "NO_DECIDIBLE": "ND", "CONFIRMAR": "CONF", "RETIRAR": "RET"}


def _md(res: list[dict], resumen: dict, coste: dict, ancho_cita: int) -> str:
    """Informe COMPACTO (≤900 palabras contando separadores): listas con una casilla por fila —
    id · modelo · doc · cita —, no tablas (cada «|» cuenta como palabra y 39 filas × 8 pipes se
    comían el cupo). Los veredictos van abreviados en la lista de no convergentes (leyenda)."""
    grupos = {("E1b", "CONFIRMAR"): [], ("E1b", "RETIRAR"): [], ("E1", "PRODUCTO_REAL"): [], ("E1", "ARTEFACTO"): []}
    otros_conv, no_conv = [], []
    for r in res:
        if r["en_bloque"]:
            g = r["veredicto_mayoria"]
            if r["packet"] == "E1" and g in ("ARTEFACTO_EXTRACCION", "NORMA_O_CERTIFICACION"):
                g = "ARTEFACTO"
            grupos[(r["packet"], g)].append(r)
        elif r["convergente"]:
            otros_conv.append(r)
        else:
            no_conv.append(r)
    n_aus = len(resumen.get("no_convergentes_ausente_con_acuerdo_bruto") or [])
    out = []
    out.append("# s324c — Re-juicio K=5 cross-model «confianza media» (E1 + E1b): PROPUESTA DE BLOQUE\n")
    out.append("**NADA APLICADO** (ni catálogo, ni Supabase, ni snapshot): propuesta para la firma de Alberto. "
               "Detalle completo (votos, citas, coste): `evals/s324c_rejuicio_k5_v1.json`.\n")
    out.append(f"**Método.** {resumen['total_filas']} filas (E1 {resumen['filas_e1']}, E1b {resumen['filas_e1b']}) "
               f"caídas del bloque solo por «confianza media» del juez único. K=5 por fila (3× `{MODELO_SONNET}` + "
               f"2× `{MODELO_GPT}`, mismo prompt, rúbrica ORIGINAL del packet, TEXTO COMPLETO del documento como "
               f"evidencia); voto válido = cita verificada a texto completo; convergente = ≥4/5 válidos con igual "
               f"veredicto. Casilla: `id` (modelo) doc: «cita» válidos/K; ↺ = veredicto del juez único.\n")
    out.append(f"**Recuento.** Bloque {resumen['en_bloque']}: E1b CONFIRMAR {len(grupos[('E1b','CONFIRMAR')])}, "
               f"E1b RETIRAR {len(grupos[('E1b','RETIRAR')])}, E1 PRODUCTO_REAL {len(grupos[('E1','PRODUCTO_REAL')])}, "
               f"E1 ARTEFACTO {len(grupos[('E1','ARTEFACTO')])}. No convergentes {len(no_conv)} "
               f"({n_aus} con término AUSENTE del texto y acuerdo bruto ≥4/5). Coste real {coste['resumen_texto']}.\n")
    titulos = {("E1b", "CONFIRMAR"): "E1b CONFIRMAR (candidate→confirmado)",
               ("E1b", "RETIRAR"): "E1b RETIRAR (candidate→fuera)",
               ("E1", "PRODUCTO_REAL"): "E1 PRODUCTO_REAL (alta→sí)",
               ("E1", "ARTEFACTO"): "E1 ARTEFACTO/NORMA (alta→no)"}
    for g, filas in grupos.items():
        out.append(f"\n## Bloque {titulos[g]}: {len(filas)}\n")
        if not filas:
            out.append("_(ninguna)_")
            continue
        for r in sorted(filas, key=lambda x: x["id"]):
            orig = (r.get("veredicto_original") or [None])[0]
            flip = f" ↺{_ABREV_VER.get(orig, orig)}" if orig and orig != r["veredicto_mayoria"] else ""
            out.append(f"- ☐`{r['id']}` ({_corta(r['modelo'], 22)}) {_corta(r['doc'], 14)}: "
                       f"«{_corta(r['cita_representativa'], ancho_cita)}» {r['n_votos_mayoria']}/{r['n_votos_validos']}{flip}")
        avisos = [(r["id"], (r.get("motivos_originales_extra") or [])
                   + ([f"grafía propuesta: «{r['grafia_propuesta_por_mayoria']}»"]
                      if r.get("grafia_propuesta_por_mayoria")
                      and not any(m.startswith("juez:propone-otra-grafia")
                                  for m in (r.get("motivos_originales_extra") or [])) else []))
                  for r in sorted(filas, key=lambda x: x["id"])]
        avisos = [(i, m) for i, m in avisos if m]
        if avisos:
            out.append("\nAvisos (triage original; no bloquean): "
                       + " · ".join(f"`{i}`: {'; '.join(m)}" for i, m in avisos))
        por_nota: dict[str, list[str]] = {}
        for r in sorted(filas, key=lambda x: x["id"]):
            if r["id"] in NOTAS_REDACTOR:
                por_nota.setdefault(NOTAS_REDACTOR[r["id"]], []).append(r["id"])
        if por_nota:
            out.append("\nNotas del redactor (no son votos; decide Alberto): "
                       + "; ".join(f"{', '.join(f'`{i}`' for i in ids)} = {n}" for n, ids in por_nota.items()))
    if otros_conv:
        out.append("\n## Convergentes NO bloqueables (una a una)\n")
        for r in sorted(otros_conv, key=lambda x: x["id"]):
            out.append(f"- `{r['id']}` ({r['packet']}, {_corta(r['modelo'], 24)}) → {r['veredicto_mayoria']} "
                       f"{r['n_votos_mayoria']}/{r['n_votos_validos']}; {r['motivo_no_bloque']}")
    out.append(f"\n## No convergentes, siguen una a una ({len(no_conv)})\n")
    out.append("S5 claude-sonnet-5, G gpt-5.5; ART/PROD/CONF/RET/ND artefacto/producto real/confirmar/retirar/no "
               "decidible; v válidos (cita verificada); AUSENTE = 0 menciones en el texto, cita inverificable "
               "(acuerdo bruto informativo).\n")
    abrev = {MODELO_SONNET: "S5", MODELO_GPT: "G"}
    for r in sorted(no_conv, key=lambda x: (x["packet"], x["id"])):
        vpj = ", ".join(f"{abrev.get(j, j)} " + "/".join(f"{_ABREV_VER.get(k, k)}×{n}"
                                                         for k, n in sorted(c.items(), key=lambda t: -t[1]))
                        for j, c in (r.get("votos_por_juez") or {}).items())
        br = r.get("acuerdo_bruto") or {}
        extra = ""
        if r.get("termino_ausente_del_texto") and br.get("n", 0) >= UMBRAL_CONVERGENCIA:
            extra = f", AUSENTE bruto {br['n']}/5 {_ABREV_VER.get(br['veredicto'], br['veredicto'])}"
        out.append(f"- {r['packet']} `{r['id']}`({_corta(r['modelo'], 20)}): {vpj}, v{r['n_votos_validos']}/5"
                   + extra
                   + (f", {r['motivo_no_bloque']}" if r.get("motivo_no_bloque") else "")
                   + (f", ERROR {r['error_fila']}" if r.get("error_fila") else ""))
    sin = [r for r in res if r["ninguna_cita_verificada"]]
    out.append(f"\n## Sin ninguna cita verificada ({len(sin)}): "
               + (", ".join(f"`{r['id']}`" for r in sorted(sin, key=lambda x: x["id"])) or "ninguna"))
    out.append("")
    return "\n".join(out)


# ───────────────────────────── main ─────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="", help="csv de ids (smoke; escribe en el scratch, no en evals/)")
    ap.add_argument("--max-usd", type=float, default=12.0, help="guardarraíl de gasto (tarifa conservadora)")
    ap.add_argument("--hilos", type=int, default=HILOS)
    args = ap.parse_args()

    filas = [("E1", r) for r in _filas_e1()] + [("E1b", r) for r in _filas_e1b()]
    solo = {x.strip() for x in args.ids.split(",") if x.strip()}
    if solo:
        filas = [(p, r) for p, r in filas if r["id"] in solo]
    dest_json, dest_md = DESTINO_JSON, DESTINO_MD
    if solo:
        dest_json = SCRATCH / "s324c_rejuicio_k5_SMOKE.json"
        dest_md = SCRATCH / "s324c_rejuicio_k5_SMOKE.md"
    print(f"filas {len(filas)} (E1 {sum(1 for p,_ in filas if p=='E1')} · E1b {sum(1 for p,_ in filas if p=='E1b')}) "
          f"· jueces {VOTOS_SONNET}×{MODELO_SONNET} + {VOTOS_GPT}×{MODELO_GPT} · caché {CACHE}", flush=True)

    hecho = [0]

    def _una(par):
        packet, fila = par
        t0 = time.time()
        try:
            with abierto(timeout=60.0, reintentos=2) as c:
                ev = evidencia_e1b(c, fila) if packet == "E1b" else evidencia_e1(c, fila)
            clave = f"{packet}|{fila['id']}|{fila.get('provenance','')}"
            votos = juzgar_fila(packet, clave, ev["prompt"], ev["verif"], args.max_usd)
            termino = fila.get("modelo") or fila.get("canonical_model")
            agg = _agrega(votos, termino)
            # motivos del triage original que NO son la confianza (grafía, id discordante,
            # radio de impacto, cita…): no deciden aquí, pero Alberto tiene que verlos
            motivos_orig = ([m for m in fila.get("motivos_individual", [])
                             if not m.startswith("juez:confianza") and not m.startswith("cita:")]
                            if packet == "E1" else
                            [m.strip() for m in (fila.get("motivo_seccion") or "").split(";")
                             if m.strip() and not m.strip().startswith("confianza")])
            # ¿el término NO aparece en el texto mostrado? (medido por regex, no por opinión):
            # E1 → 0 menciones flexibles en el doc de origen Y en la muestra del resto;
            # E1b → 0 menciones con frontera en el documento de procedencia
            m = ev["meta"]
            ausente = ((m["menciones_doc"]["flexibles"] == 0 and m["menciones_muestra_global"]["flexibles"] == 0)
                       if packet == "E1" else m["menciones_en_procedencia"] == 0)
            fila_out = {
                "packet": packet, "id": fila["id"],
                "modelo": termino,
                "canonical": fila.get("canonical_model") or fila.get("modelo"),
                "doc": ev["meta"]["doc"], "evidencia": ev["meta"],
                "termino_ausente_del_texto": ausente,
                "veredicto_original": ((fila.get("llm") or {}).get("veredicto"),
                                       (fila.get("llm") or {}).get("confianza")),
                "motivos_originales_extra": motivos_orig,
                "votos": votos, **agg,
                "prompt_chars": len(ev["prompt"]),
            }
        except Exception as exc:  # noqa: BLE001
            fila_out = {"packet": packet, "id": fila["id"],
                        "modelo": fila.get("modelo") or fila.get("canonical_model"),
                        "canonical": fila.get("canonical_model") or fila.get("modelo"),
                        "doc": None, "evidencia": None, "votos": [],
                        "veredicto_mayoria": None, "n_votos_validos": 0, "n_votos_mayoria": 0,
                        "votos_por_veredicto": {}, "convergente": False, "unanime": False,
                        "cita_representativa": None, "ninguna_cita_verificada": True,
                        "error_fila": f"{type(exc).__name__}: {exc}"[:400]}
        with _LOCK:
            hecho[0] += 1
            n = hecho[0]
        print(f"  {n}/{len(filas)} [{packet}] {fila['id']} → {fila_out.get('veredicto_mayoria')} "
              f"{fila_out.get('n_votos_mayoria')}/{fila_out.get('n_votos_validos')} "
              f"{'CONV' if fila_out.get('convergente') else 'no-conv'} "
              f"({time.time()-t0:.0f}s, gasto≈{_gasto_total_conservador():.2f}$)"
              + (f" ERROR {fila_out['error_fila']}" if fila_out.get("error_fila") else ""), flush=True)
        return fila_out

    with ThreadPoolExecutor(max_workers=args.hilos) as pool:
        res = list(pool.map(_una, filas))

    # ── bloque: convergente ∧ veredicto bloqueable ∧ (E1) id unánime entre sus filas ──
    for r in res:
        r["motivo_no_bloque"] = ""
        r["en_bloque"] = bool(r["convergente"] and r["veredicto_mayoria"] in BLOQUEABLES[r["packet"]])
        if r["convergente"] and not r["en_bloque"]:
            r["motivo_no_bloque"] = f"veredicto {r['veredicto_mayoria']} no es bloqueable"
    por_id = defaultdict(list)
    for r in res:
        if r["packet"] == "E1":
            por_id[r["id"]].append(r)
    for pid, grupo in por_id.items():
        if len(grupo) > 1 and (len({g["veredicto_mayoria"] for g in grupo}) > 1 or not all(g["en_bloque"] for g in grupo)):
            for g in grupo:
                if g["en_bloque"]:
                    g["en_bloque"] = False
                    g["motivo_no_bloque"] = "mismo id en otra fila del draft sin bloque/veredicto distinto (coherencia por id)"

    # ── coste ──
    coste = {
        "sonnet_5": {"tokens": Counter(), "usd_lista": 0.0, "usd_intro_vigente": 0.0},
        "gpt_5_5": {"tokens": Counter(), "usd_conservador": 0.0},
        "tarifas": TARIFA,
        "nota": ("Tokens REALES (usage de cada llamada). Sonnet 5: tarifa de lista y tarifa intro "
                 "vigente hasta 2026-08-31 (la que se factura hoy). gpt-5.5: no consta tarifa oficial "
                 "en el repo → estimación conservadora (2,5/0,25 cache/15 USD por M)."),
    }
    for r in res:
        for v in r["votos"]:
            if not v.get("uso"):
                continue
            if v["modelo_juez"] == MODELO_SONNET:
                coste["sonnet_5"]["tokens"].update(v["uso"])
                coste["sonnet_5"]["usd_lista"] += v["coste_usd"]["lista"]
                coste["sonnet_5"]["usd_intro_vigente"] += v["coste_usd"]["intro"]
            else:
                coste["gpt_5_5"]["tokens"].update(v["uso"])
                coste["gpt_5_5"]["usd_conservador"] += v["coste_usd"]["conservadora"]
    for k in ("sonnet_5", "gpt_5_5"):
        coste[k]["tokens"] = dict(coste[k]["tokens"])
    coste["total_usd_conservador"] = round(coste["sonnet_5"]["usd_lista"] + coste["gpt_5_5"]["usd_conservador"], 2)
    coste["total_usd_esperado_factura"] = round(coste["sonnet_5"]["usd_intro_vigente"] + coste["gpt_5_5"]["usd_conservador"], 2)
    coste["resumen_texto"] = (f"≈{coste['total_usd_esperado_factura']:.2f} USD (Sonnet 5 a tarifa intro vigente "
                              f"{coste['sonnet_5']['usd_intro_vigente']:.2f} + gpt-5.5 tarifa conservadora "
                              f"{coste['gpt_5_5']['usd_conservador']:.2f}; cota a tarifa de lista "
                              f"{coste['total_usd_conservador']:.2f})")

    n_conv = sum(1 for r in res if r["convergente"])
    resumen = {
        "total_filas": len(res), "filas_e1": sum(1 for r in res if r["packet"] == "E1"),
        "filas_e1b": sum(1 for r in res if r["packet"] == "E1b"),
        "convergentes": n_conv, "en_bloque": sum(1 for r in res if r["en_bloque"]),
        "no_convergentes": len(res) - n_conv,
        "convergentes_por_veredicto": dict(Counter(f"{r['packet']}:{r['veredicto_mayoria']}" for r in res if r["convergente"])),
        "en_bloque_por_veredicto": dict(Counter(f"{r['packet']}:{r['veredicto_mayoria']}" for r in res if r["en_bloque"])),
        "sin_ninguna_cita_verificada": [r["id"] for r in res if r["ninguna_cita_verificada"]],
        "no_convergentes_ausente_con_acuerdo_bruto": [
            f"{r['id']}:{(r.get('acuerdo_bruto') or {}).get('veredicto')}×{(r.get('acuerdo_bruto') or {}).get('n')}"
            for r in res if not r["convergente"] and r.get("termino_ausente_del_texto")
            and (r.get("acuerdo_bruto") or {}).get("n", 0) >= UMBRAL_CONVERGENCIA],
        "filas_con_error": [r["id"] for r in res if r.get("error_fila")],
        "votos_invalidos_por_juez": dict(Counter(v["modelo_juez"] for r in res for v in r["votos"] if not v["valido"])),
        "votos_error_llamada": sum(1 for r in res for v in r["votos"] if v.get("error")),
        "guardarrail_gasto_disparado": _STOP["presupuesto"],
    }
    recibo = {
        "que_es": ("Re-juicio K=5 cross-model (3× claude-sonnet-5 + 2× gpt-5.5, mismo prompt, rúbrica "
                   "ORIGINAL de cada packet, TEXTO COMPLETO del documento como evidencia) de las filas de "
                   "E1/E1b que cayeron del bloque solo por «confianza media». PROPUESTA para Alberto: NADA "
                   "aplicado (ni catálogo, ni Supabase, ni snapshot)."),
        "utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "no_se_aplico_nada": True,
        "fuentes": {"E1": str(RECIBO_E1.relative_to(ROOT)).replace("\\", "/"),
                    "E1b": str(RECIBO_E1B.relative_to(ROOT)).replace("\\", "/"),
                    "rubrica_E1": "scripts/s322g_e1_candidatos_triage.py::PROMPT (importada; cabeceras de evidencia retituladas)",
                    "rubrica_E1b": "scripts/s322_e1b_revisar_qa.py::PROMPT (importada; cabecera de evidencia retitulada)"},
        "jueces": {"anthropic": {"modelo": MODELO_SONNET, "votos": VOTOS_SONNET, "max_tokens": MAX_TOKENS_SONNET,
                                 "effort": EFFORT_SONNET, "temperature": "por defecto (no se envía)",
                                 "prompt_caching": "cache_control en el bloque del prompt (3 votos idénticos)"},
                   "openai": {"modelo": MODELO_GPT, "votos": VOTOS_GPT, "response_format": "json_object",
                              "max_completion_tokens": MAX_TOKENS_GPT, "temperature": "por defecto (no se envía)"}},
        "criterio": {"voto_valido": f"veredicto del conjunto permitido ∧ cita verificada a texto completo "
                                    f"(≤{MAX_CITA} chars, espacios/caja/«» normalizados en ambos lados, "
                                    f"mínimo por packet E1 ≥{MIN_CITA_NORM['E1']} chars / E1b sin mínimo, "
                                    f"como cada juez original)",
                     "convergente": f"≥{UMBRAL_CONVERGENCIA}/{K} votos válidos con el mismo veredicto",
                     "en_bloque": "convergente ∧ veredicto bloqueable (E1b: CONFIRMAR/RETIRAR; E1: PRODUCTO_REAL/"
                                  "ARTEFACTO_EXTRACCION/NORMA_O_CERTIFICACION) ∧ (E1) coherencia por id"},
        "notas_redactor": {"que_son": ("observaciones del redactor del recibo sobre filas convergentes, leídas en las "
                                       "citas; NO son votos ni cambian casillas — para que Alberto las mire antes de "
                                       "firmar en bloque"),
                           "notas": {k: v for k, v in NOTAS_REDACTOR.items()
                                     if any(r["id"] == k and r["en_bloque"] for r in res)}},
        "resumen": resumen, "coste": coste, "filas": res,
    }
    dest_json.write_text(json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")

    # MD ≤ 900 palabras: se acorta la cita hasta que quepa
    md = ""
    for ancho in (70, 60, 52, 46, 40, 36, 32, 28, 24):
        md = _md(res, resumen, coste, ancho)
        if len(md.split()) <= 900:
            break
    dest_md.write_text(md, encoding="utf-8")

    print(f"\nconvergentes {n_conv}/{len(res)} · en bloque {resumen['en_bloque']} "
          f"{resumen['en_bloque_por_veredicto']} · no convergentes {resumen['no_convergentes']}")
    print(f"sin cita verificada en ningún voto: {resumen['sin_ninguna_cita_verificada']}")
    print(f"coste: {coste['resumen_texto']}")
    print(f"tokens sonnet {coste['sonnet_5']['tokens']} · gpt {coste['gpt_5_5']['tokens']}")
    print(f"MD {len(md.split())} palabras → {dest_md}\nJSON → {dest_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
