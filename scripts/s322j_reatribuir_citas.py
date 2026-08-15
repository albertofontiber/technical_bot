# -*- coding: utf-8 -*-
"""s322j — Cierra el ítem BLOQUEANTE del dúo r29: las 39 citas de bloque cuya
cita existe en el corpus pero NO en el documento que se les atribuye.

Origen: el verificador adversarial (s322h) re-ejecutó el censo COMPLETO de las
570 citas de bloque y encontró 0 inventadas, pero 39 que solo verifican en OTRO
documento. Sol lo elevó a bloqueante: «los packets presentan procedencia+cita
como una sola traza, así que hallarlas en otro manual demuestra existencia, no
sustenta esa atribución».

Qué hace, por fila (nunca a ojo: siempre re-verificando contra el corpus):
 1. Toma el documento REAL que el censo ya identificó (por document_id o por
    source_file).
 2. RE-VERIFICA la cita completa (hasta 200 chars, espacios normalizados)
    contra el contenido ENTERO de ese documento.
 3. Si verifica -> corrige la atribución en el recibo y deja `reatribuida`.
    Si NO verifica -> la fila SALE del bloque a individual (jamás se fuerza).
NO aplica nada al catálogo/DB/snapshot: solo reescribe recibos de evals/.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)
import os
from src.http_pool import abierto

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}

BOLSAS = {   # bolsa del censo -> (fichero de recibo, ruta de la lista de bloque, ruta individual)
    "e1b_encoger/bloque": ("s322f_e1b_confirmar_encoger_v1.json",
                           ("detalle", "bloque"), ("detalle", "individual")),
    "g1_triage/0a_alta": ("s322g_e1_candidatos_triage_v1.json",
                          ("seccion_0a_alta_en_bloque",), ("seccion_1_individual",)),
    "e1b_qa/0_bloque_confirmar": ("s322_e1b_revisar_qa_v1.json",
                                  ("secciones", "0_bloque_confirmar"), ("secciones", "1_individual")),
    "e1b_qa/0_bloque_retirar": ("s322_e1b_revisar_qa_v1.json",
                                ("secciones", "0_bloque_retirar"), ("secciones", "1_individual")),
}


def _norm(s): return re.sub(r"\s+", " ", (s or "").lower()).strip()


def _get(d, ruta):
    for k in ruta:
        d = d[k]
    return d


cache: dict[str, str] = {}


def _doc_texto(c, *, doc_id=None, source_file=None) -> str:
    clave = doc_id or source_file
    if clave in cache:
        return cache[clave]
    filtro = {"document_id": f"eq.{doc_id}"} if doc_id else {"source_file": f"eq.{source_file}"}
    trozos, off = [], 0
    while True:
        r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                  params={"select": "content", **filtro, "order": "chunk_index.asc",
                          "offset": str(off), "limit": "100"})
        r.raise_for_status()
        lote = r.json()
        trozos += [(x.get("content") or "") for x in lote]
        if len(lote) < 100:
            break
        off += 100
    cache[clave] = _norm("\n".join(trozos))
    return cache[clave]


censo = json.loads((ROOT / "evals" / "s322h_verificacion_adversarial_v1.json")
                   .read_text(encoding="utf-8"))
malas = censo["d_citas_reejecutadas"]["d2_censo_completo"]["verifican_solo_en_otro_doc"]
recibos: dict[str, dict] = {}
acciones = []

with abierto(timeout=30.0) as c:
    for m in malas:
        fichero, ruta_b, ruta_i = BOLSAS[m["bolsa"]]
        rec = recibos.setdefault(fichero, json.loads(
            (ROOT / "evals" / fichero).read_text(encoding="utf-8")))
        bloque, individual = _get(rec, ruta_b), _get(rec, ruta_i)
        sujeto = m.get("sujeto")
        fila = next((f for f in bloque if f.get("id") == sujeto), None)
        if fila is None:
            acciones.append({"sujeto": sujeto, "accion": "no-encontrada-en-bloque"})
            continue
        real = m.get("mi_verificacion") or {}
        doc_id, sf = real.get("doc"), real.get("source_file")
        texto = _doc_texto(c, doc_id=doc_id, source_file=sf) if (doc_id or sf) else ""
        verifica = _norm((m.get("cita") or "")[:200]) in texto if texto else False
        if verifica:
            fila["atribucion_corregida_s322j"] = {
                "antes": m.get("doc_atribuido"),
                "ahora_document_id": doc_id, "ahora_source_file": sf,
                "motivo": "la cita verifica full-text en este documento, no en el anterior"}
            acciones.append({"sujeto": sujeto, "accion": "reatribuida",
                             "doc": doc_id or sf})
        else:
            fila["sacada_del_bloque_s322j"] = (
                "su cita no verifica ni en el documento atribuido ni en el que el "
                "censo señalaba: no se fuerza, decide Alberto")
            bloque.remove(fila)
            individual.append(fila)
            acciones.append({"sujeto": sujeto, "accion": "movida-a-individual"})

for fichero, rec in recibos.items():
    rec["s322j_reatribucion"] = ("Ítem bloqueante del dúo r29 cerrado: citas "
                                 "re-atribuidas al documento donde verifican, o "
                                 "sacadas del bloque si no verifican en ninguno.")
    (ROOT / "evals" / fichero).write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")

utc = censo.get("utc", "")
res = {"que_es": __doc__.strip().splitlines()[0], "base_censo_utc": utc,
       "filas": len(malas),
       "reatribuidas": sum(1 for a in acciones if a["accion"] == "reatribuida"),
       "movidas_a_individual": sum(1 for a in acciones if a["accion"] == "movida-a-individual"),
       "no_encontradas": sum(1 for a in acciones if a["accion"] == "no-encontrada-en-bloque"),
       "detalle": acciones}
(ROOT / "evals" / "s322j_reatribucion_citas_v1.json").write_text(
    json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"filas {res['filas']} · reatribuidas {res['reatribuidas']} · "
      f"a individual {res['movidas_a_individual']} · no encontradas {res['no_encontradas']}")
