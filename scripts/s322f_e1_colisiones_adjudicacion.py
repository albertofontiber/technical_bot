#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s322f — Adjudicación DETERMINISTA de las 49 COLISIONES de identidad del packet E1.

QUÉ RESUELVE
------------
`evals/s320_e1_packet_adjudicacion_v1.md` §1 afirma, para 49 manuales, que «el doc_map
apunta a un document_id que SIGUE VIVO en documents, pero el documento activo actual con
ese filename tiene OTRO id → DOS FILAS ACTIVAS para el mismo manual». Esa afirmación es
la que hay que adjudicar: cuál se queda y cuál se marca superseded.

POR QUÉ SIN LLM
---------------
La pregunta «¿estas dos filas son el mismo documento?» se contesta con hechos duros
(status, sha, nº de chunks, revisión de portada, referencias entrantes). Meter un juez
aquí sólo añadiría una fuente de invención sobre datos que ya son inequívocos. El único
sitio donde el texto importa —la REVISIÓN DE PORTADA— se extrae con regex y se VERIFICA
verbatim contra el contenido completo del documento (ver `_verificar_cita`).

REGLA DEL REPO QUE SE RESPETA
-----------------------------
«Un sha distinto NO es un documento nuevo»: el sha JAMÁS decide por sí solo. Lo que manda
para declarar "supersedida" es la REVISIÓN IMPRESA EN PORTADA. El sha sólo se usa en la
dirección segura (sha REAL idéntico ⇒ mismo blob) y para detectar pseudo-shas de backfill.

SOLO LECTURA — CONTRATO DURO
----------------------------
Este script NO escribe en `data/catalog/*.jsonl`, NI en Supabase (cero PATCH/POST/DELETE),
NI en `data/model_catalog.json`. Su único efecto es el fichero de recibo en `evals/`.
Todas las llamadas HTTP son `GET`. Es una PROPUESTA para que Alberto adjudique.

USO
---
    python scripts/s322f_e1_colisiones_adjudicacion.py
    python scripts/s322f_e1_colisiones_adjudicacion.py --salida evals/otro_nombre.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

from src.http_pool import abierto  # noqa: E402
from src.rag.catalog_store import CATALOG_DIR, FILES, _read_jsonl  # noqa: E402  (SOLO LECTURA)
# s278 §4 — el comparador CANÓNICO de identidad de blob del repo. Se reutiliza en vez de
# reinventar la normalización: la única deriva que cierra es `<stem>.pdf` vs `<stem>`, y
# falla-cerrado ante variantes de caja o sufijos raros. Reimplementarlo aquí sería una
# segunda definición de identidad divergiendo en silencio de la que usa el serving.
from src.rag.document_local_coverage import blob_identity_match  # noqa: E402
# Seam de ATESTACIÓN del anexo must_preserve: hace join por `document_id` entre el chunk
# servido y el doc_map. Se importa para MEDIR (no para cambiar) si el desajuste de ids que
# adjudicamos aquí tiene consecuencia real en serving. Protocolo 1: la consecuencia se
# mide, no se teoriza.
from src.rag.must_preserve import attest_identity  # noqa: E402

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}

CENSO = ROOT / "evals" / "s320_e1_reconciliacion_censo_v1.json"
SALIDA_DEFAULT = ROOT / "evals" / "s322f_e1_colisiones_adjudicacion_v1.json"

# Tablas satélite que referencian `document_id`. Se auditan porque una propuesta de
# "repuntar/retirar" sólo es segura si conocemos el radio de impacto COMPLETO: si el id
# viejo tuviera assets o miembros de grupo colgando, retirarlo dejaría huérfanos.
TABLAS_SATELITE = ("chunks_v2", "chunks", "chunks_v2_enunciados",
                   "document_visual_assets", "document_group_members")

# Ficheros del catálogo gobernado distintos de doc_map: si el id apareciera también ahí,
# el repunte del doc_map NO bastaría (habría más sitios que tocar).
OTROS_FICHEROS_CATALOGO = ("products", "aliases", "umbrellas", "relations",
                           "docrel", "homonyms")


# ───────────────────────── utilidades de lectura ─────────────────────────

def _norm(texto: str) -> str:
    """Normalización de espacios para comparar citas contra el texto fuente.

    Lección cara ya pagada: verificar sólo un prefijo de 50 chars dejó pasar una cita
    inventada (la cola parafraseada no estaba en el documento). Aquí se compara la cita
    ENTERA contra el contenido COMPLETO, con espacios colapsados y en minúsculas.
    """
    return re.sub(r"\s+", " ", (texto or "")).strip().lower()


def _get(cliente, tabla: str, params: dict) -> list[dict]:
    r = cliente.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=H, params=params)
    r.raise_for_status()
    return r.json()


def _contar(cliente, tabla: str, document_id: str) -> int | None:
    """COUNT exacto vía cabecera Content-Range (no baja filas: barato y sin límite de
    paginación, que es justo donde un `len(rows)` mentiría al topar el limit por defecto).
    Devuelve None si la tabla no tiene la columna (satélite no aplicable)."""
    h = dict(H, **{"Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"})
    r = cliente.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=h,
                    params={"select": "*", "document_id": f"eq.{document_id}"})
    if r.status_code >= 400:
        return None
    return int(r.headers["content-range"].split("/")[-1])


def _documents_por_id(cliente, ids: list[str]) -> dict[str, dict]:
    """Trae TODAS las columnas de documents para los ids dados (en lotes: la URL de un
    `in.()` con 98 UUIDs supera límites razonables de query string)."""
    out: dict[str, dict] = {}
    for i in range(0, len(ids), 40):
        lote = ids[i:i + 40]
        for fila in _get(cliente, "documents",
                         {"select": "*", "id": "in.(" + ",".join(lote) + ")"}):
            out[fila["id"]] = fila
    return out


# ───────────────────────── revisión de portada ─────────────────────────

# Batería de patrones de revisión tal y como se IMPRIMEN en portadas de manuales de PCI.
# Orden = prioridad: los explícitos ("rev. 002") antes que los sueltos ("2024 e").
PATRONES_REVISION = (
    re.compile(r"\brev(?:isi[oó]n|\.)?\s*[:\-]?\s*([A-Z]?\d{1,3}(?:\.\d{1,2})?[A-Z]?)\b", re.I),
    re.compile(r"\brev\.?\s*([A-Z]\d{0,2})\b", re.I),
    re.compile(r"\bissue\s*([0-9]{1,3}[A-Z]?)\b", re.I),
    re.compile(r"\b(?:ed(?:ition|ici[oó]n)|edic\.)\s*[:\-]?\s*([0-9]{1,3}[A-Z]?)\b", re.I),
    re.compile(r"\bversi[oó]n\s*[:\-]?\s*(v?[0-9]{1,3}(?:[.\-][0-9]{1,3})?)\b", re.I),
    re.compile(r"\bv\.?\s?([0-9]{1,2}[.\-][0-9]{1,2})\b", re.I),
    re.compile(r"\bdoc(?:umento)?\.?\s*n[ºo°]?\s*([A-Z0-9\-]{4,})\b", re.I),
)

# Nº de chunks de cabecera donde se busca la portada. La portada vive al principio; ir más
# allá arrastraría "rev." de tablas de piezas y produciría falsos positivos de revisión.
CHUNKS_DE_PORTADA = 3


def _extraer_revision(chunks_ordenados: list[dict], texto_completo_norm: str) -> dict:
    """Extrae la revisión declarada en portada + la CITA que la sostiene, y verifica la
    cita completa contra el documento entero.

    Devuelve `{revision, cita, cita_verificada, patron}`. `revision=None` significa
    "la portada no declara revisión" — que NO es lo mismo que "no hay revisión": por eso
    la clasificación nunca usa una ausencia de revisión como prueba de igualdad.
    """
    cabecera = " ".join((c.get("content") or "") for c in chunks_ordenados[:CHUNKS_DE_PORTADA])
    for patron in PATRONES_REVISION:
        m = patron.search(cabecera)
        if not m:
            continue
        # La cita es la ventana alrededor del match (hasta 200 chars), que es lo que se
        # ALMACENA en el recibo. Se verifica ENTERA — no un prefijo.
        a = max(0, m.start() - 90)
        b = min(len(cabecera), m.end() + 90)
        cita = re.sub(r"\s+", " ", cabecera[a:b]).strip()[:200]
        return {
            "revision": m.group(1).strip(),
            "cita": cita,
            "cita_verificada": _norm(cita) in texto_completo_norm,
            "patron": patron.pattern[:40],
        }
    return {"revision": None, "cita": None, "cita_verificada": None, "patron": None}


def _perfil_documento(cliente, document_id: str) -> dict:
    """Reúne TODA la evidencia dura de una fila de `documents`: metadatos, censo de filas
    entrantes en cada tabla satélite, y la revisión de portada con cita verificada."""
    conteos = {t: _contar(cliente, t, document_id) for t in TABLAS_SATELITE}
    chunks: list[dict] = []
    if (conteos.get("chunks_v2") or 0) > 0:
        chunks = _get(cliente, "chunks_v2", {
            "select": "chunk_index,page_number,source_file,content",
            "document_id": f"eq.{document_id}",
            "order": "chunk_index.asc", "limit": "1000"})
    # Texto completo del documento = concatenación de TODOS sus chunks. Es el patrón
    # contra el que se valida la cita entera (no contra el trozo del que se extrajo).
    texto_completo_norm = _norm(" ".join((c.get("content") or "") for c in chunks))
    return {
        "conteos": conteos,
        "source_files_en_chunks": sorted({c.get("source_file") for c in chunks if c.get("source_file")}),
        "n_chunks_leidos": len(chunks),
        "portada": _extraer_revision(chunks, texto_completo_norm),
    }


# ───────────────────────── reglas de clasificación ─────────────────────────

# Un pseudo-sha `backfill:<hex>` NO es el hash del PDF: lo estampó la migración Fase 1 al
# inventar filas de `documents` a partir de los metadatos de chunks pre-migración. Por eso
# nunca puede usarse para afirmar "mismo blob" ni "blob distinto".
RX_PSEUDO_SHA = re.compile(r"^backfill:", re.I)
# Nota que dejó s65 capaB A4 al retirar los duplicados-fantasma, con puntero al superviviente.
RX_PUNTERO_FANTASMA = re.compile(r"duplicado-fantasma de ([0-9a-f]{8}-[0-9a-f-]{27,})", re.I)


def clasificar(mapa: dict, actual: dict, perf_mapa: dict, perf_actual: dict,
               doc_map_source_file: str, id_en_otros_ficheros: bool) -> dict:
    """LA REGLA. Devuelve `{clase, destino, propuesta, motivo, gates}`.

    Escalera, de la evidencia más fuerte a la más débil:

    A) `fantasma_ya_retirado` — la fila del mapa NO está activa, tiene CERO filas en TODAS
       las tablas satélite (no es un documento: es una ficha vacía), la fila actual sí está
       activa y sirve chunks, ambas nombran el MISMO blob y la nota de retirada apunta
       explícitamente a la actual. No hay contenido que comparar porque un lado no tiene
       ninguno → no puede haber pérdida. BLOQUE.
       Propuesta: NADA que tocar en `documents` (la retirada YA está aplicada); la acción
       viva es repuntar `doc_map.document_id` del fantasma al activo.
       Deliberadamente NO se propone `supersede`: supersede modela "revisión vieja
       sustituida por nueva", y una ficha de 0 chunks nunca fue una revisión.

    B) `duplicado_exacto` — ambas activas y mismo contenido: shas REALES idénticos, o mismo
       nº de chunks + misma revisión de portada (con cita verificada). BLOQUE.

    C) `revision_distinta` — ambas portadas declaran revisión y son DIFERENTES, con ambas
       citas verificadas full-text. BLOQUE (supersede real: la vieja apunta a la nueva).

    D) `divergente` — todo lo demás. INDIVIDUAL, con la evidencia cruda para Alberto.
    """
    c_mapa, c_act = perf_mapa["conteos"], perf_actual["conteos"]
    port_mapa, port_act = perf_mapa["portada"], perf_actual["portada"]

    sha_mapa = str(mapa.get("source_pdf_sha256") or "")
    sha_act = str(actual.get("source_pdf_sha256") or "")
    puntero = RX_PUNTERO_FANTASMA.search(str(mapa.get("notes") or ""))

    gates = {
        "mapa_status": mapa.get("status"),
        "actual_status": actual.get("status"),
        "mapa_sin_filas_en_ninguna_satelite": all((v or 0) == 0 for v in c_mapa.values()),
        "actual_sirve_chunks_v2": (c_act.get("chunks_v2") or 0) > 0,
        "mismo_blob_por_nombre": blob_identity_match(
            str(actual.get("source_pdf_filename") or ""),
            str(mapa.get("source_pdf_filename") or "")),
        "nota_apunta_al_actual": bool(puntero) and puntero.group(1) == actual["id"],
        "sha_mapa_es_pseudo_backfill": bool(RX_PSEUDO_SHA.match(sha_mapa)),
        "doc_map_source_file_coincide_con_chunks_del_actual":
            [doc_map_source_file] == perf_actual["source_files_en_chunks"],
        "id_mapa_en_otros_ficheros_del_catalogo": id_en_otros_ficheros,
    }

    # ── A) fantasma sin contenido, retirada YA aplicada ───────────────────
    if (gates["mapa_status"] != "active"
            and gates["mapa_sin_filas_en_ninguna_satelite"]
            and gates["actual_status"] == "active"
            and gates["actual_sirve_chunks_v2"]
            and gates["mismo_blob_por_nombre"]
            and gates["nota_apunta_al_actual"]
            and not gates["id_mapa_en_otros_ficheros_del_catalogo"]):
        # El repunte sólo es limpio si el `source_file` del doc_map ya es el que llevan los
        # chunks del activo: entonces cambia UN campo y el seam de `allowed_sources`
        # (que indexa por source_file) no se mueve ni un milímetro.
        if not gates["doc_map_source_file_coincide_con_chunks_del_actual"]:
            return {"clase": "divergente", "destino": "individual",
                    "propuesta": None,
                    "motivo": ("fantasma de 0 chunks, pero el source_file del doc_map no es "
                               "el de los chunks del activo → el repunte movería DOS campos"),
                    "gates": gates}
        return {
            "clase": "fantasma_ya_retirado",
            "destino": "bloque",
            "propuesta": {
                "documents": "NADA (la fila del mapa ya está retirada desde s65 capaB A4)",
                "doc_map": "repuntar document_id: <id_mapa> → <id_actual> (source_file intacto)",
                "supersede": "NO — una ficha de 0 chunks nunca fue una revisión",
            },
            "motivo": ("la fila del mapa está {} con CERO filas en chunks_v2/chunks/"
                       "enunciados/visual_assets/group_members, su sha es pseudo-backfill, "
                       "su nota apunta al id actual, y ambas nombran el mismo blob"
                       ).format(gates["mapa_status"]),
            "gates": gates,
        }

    # ── B) duplicado exacto entre dos filas ACTIVAS ───────────────────────
    ambas_activas = gates["mapa_status"] == "active" and gates["actual_status"] == "active"
    shas_reales = sha_mapa and sha_act and not RX_PSEUDO_SHA.match(sha_mapa) and not RX_PSEUDO_SHA.match(sha_act)
    if ambas_activas and gates["mismo_blob_por_nombre"]:
        if shas_reales and sha_mapa == sha_act:
            return {"clase": "duplicado_exacto", "destino": "bloque",
                    "propuesta": {"documents": "conservar la fila con chunks servibles; "
                                               "marcar la otra superseded",
                                  "doc_map": "repuntar al superviviente"},
                    "motivo": "sha256 REAL idéntico en ambas filas", "gates": gates}
        mismo_n = (c_mapa.get("chunks_v2") or 0) == (c_act.get("chunks_v2") or 0)
        misma_portada = (port_mapa["revision"] is not None
                         and port_mapa["revision"] == port_act["revision"]
                         and port_mapa["cita_verificada"] and port_act["cita_verificada"])
        if mismo_n and misma_portada:
            return {"clase": "duplicado_exacto", "destino": "bloque",
                    "propuesta": {"documents": "conservar la que referencia el doc_map / la "
                                               "que tiene chunks servibles; otra superseded",
                                  "doc_map": "repuntar al superviviente"},
                    "motivo": "mismo nº de chunks y MISMA revisión de portada (citas verificadas)",
                    "gates": gates}

    # ── C) revisiones de portada diferentes ───────────────────────────────
    if (port_mapa["revision"] and port_act["revision"]
            and port_mapa["revision"] != port_act["revision"]
            and port_mapa["cita_verificada"] and port_act["cita_verificada"]):
        return {"clase": "revision_distinta", "destino": "bloque",
                "propuesta": {"documents": "supersede REAL: la vieja apunta a la nueva "
                                           "(superseded_by_id) y pasa a status superseded",
                              "doc_map": "repuntar a la revisión vigente"},
                "motivo": f"portadas declaran revisiones distintas: "
                          f"{port_mapa['revision']!r} vs {port_act['revision']!r}",
                "gates": gates}

    # ── D) residuo ────────────────────────────────────────────────────────
    return {"clase": "divergente", "destino": "individual", "propuesta": None,
            "motivo": "no se puede explicar la diferencia con la evidencia disponible",
            "gates": gates}


def _medir_seam_atestacion(doc_map_row: dict, id_actual: str, id_mapa: str) -> dict:
    """¿Tiene el desajuste de ids consecuencia REAL en serving, o es cosmético?

    `must_preserve.attest_identity(chunk["document_id"], modelos_resueltos)` recorre el
    doc_map buscando una fila cuyo `document_id` sea el del CHUNK servido. Los chunks
    llevan el id ACTIVO; el doc_map guarda el del FANTASMA ⇒ el join no encuentra nada y
    la atestación devuelve False (fail-closed): el anexo NUNCA actúa para estos manuales.

    Se mide en ambas direcciones para que el recibo pruebe la asimetría en vez de
    afirmarla. `atesta_con_id_actual=False` + `atesta_con_id_fantasma=True` ES la firma
    del bug, y ambas se invierten en cuanto se repunte el doc_map.
    """
    entradas = doc_map_row.get("entries") or []
    principal = next((e["id"] for e in entradas if e.get("role") == "primary"),
                     entradas[0]["id"] if entradas else None)
    if not principal:
        return {"medible": False}
    return {
        "medible": True,
        "modelo_sonda": principal,
        "atesta_con_id_actual": attest_identity(id_actual, [principal]),
        "atesta_con_id_fantasma": attest_identity(id_mapa, [principal]),
    }


# ───────────────────────────────── main ─────────────────────────────────

def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=str(SALIDA_DEFAULT))
    args = ap.parse_args()

    censo = json.loads(CENSO.read_text(encoding="utf-8"))
    colisiones = censo["detalle"]["colision"]

    # doc_map indexado por document_id (SOLO LECTURA). Sirve para el gate de DRIFT: si el
    # id del censo ya no está en el mapa, la fila del packet caducó.
    doc_map = {r["document_id"]: r for r in _read_jsonl(CATALOG_DIR / FILES["doc_map"])}

    # Presencia de los ids en el RESTO del catálogo: si un id sólo vive en doc_map, el
    # repunte es un cambio de un campo en un fichero; si vive en más sitios, no lo es.
    otros_txt = "\n".join((CATALOG_DIR / FILES[f]).read_text(encoding="utf-8")
                          for f in OTROS_FICHEROS_CATALOGO)

    ids: list[str] = []
    for fila in colisiones:
        ids.append(fila["document_id_actual"])
        ids.extend(fila["ids_stale_aun_vivos"])

    filas_salida: list[dict] = []
    with abierto(timeout=60.0) as cliente:
        docs = _documents_por_id(cliente, ids)
        perfiles: dict[str, dict] = {}
        for i, did in enumerate(ids, 1):
            if did in docs:
                perfiles[did] = _perfil_documento(cliente, did)
            print(f"  perfilando {i}/{len(ids)}", end="\r")
    print()

    for fila in colisiones:
        sf = fila["source_file"]
        id_act = fila["document_id_actual"]
        stale = fila["ids_stale_aun_vivos"]

        # DRIFT 1 — más de un id stale: la regla binaria no aplica, va a mano.
        if len(stale) != 1:
            filas_salida.append({"source_file": sf, "tier": fila["tier"], "clase": "divergente",
                                 "destino": "individual",
                                 "motivo": f"{len(stale)} ids stale, no un par",
                                 "id_mapa": stale, "id_actual": id_act})
            continue
        id_mapa = stale[0]

        # DRIFT 2 — alguna de las dos filas ya no existe en documents.
        if id_mapa not in docs or id_act not in docs:
            filas_salida.append({"source_file": sf, "tier": fila["tier"], "clase": "ya_no_aplica",
                                 "destino": "ninguno",
                                 "motivo": "una de las dos filas ya no existe en documents",
                                 "id_mapa": id_mapa, "id_actual": id_act})
            continue

        # DRIFT 3 — el doc_map ya no apunta al id viejo (alguien lo repuntó).
        dm = doc_map.get(id_mapa)
        if dm is None:
            filas_salida.append({"source_file": sf, "tier": fila["tier"], "clase": "ya_no_aplica",
                                 "destino": "ninguno",
                                 "motivo": "el doc_map ya no referencia el id viejo",
                                 "id_mapa": id_mapa, "id_actual": id_act})
            continue

        mapa, actual = docs[id_mapa], docs[id_act]
        pm, pa = perfiles[id_mapa], perfiles[id_act]
        veredicto = clasificar(mapa, actual, pm, pa, dm.get("source_file") or "",
                               id_mapa in otros_txt or id_act in otros_txt)

        filas_salida.append({
            "source_file": sf,
            "tier": fila["tier"],
            "n_entries_adjudicadas": fila["n_entries_adjudicadas"],
            "clase": veredicto["clase"],
            "destino": veredicto["destino"],
            "motivo": veredicto["motivo"],
            "propuesta": veredicto["propuesta"],
            "gates": veredicto["gates"],
            "doc_map": {"document_id": dm["document_id"],
                        "source_file": dm.get("source_file"),
                        "n_entries": len(dm.get("entries") or [])},
            "seam_atestacion": _medir_seam_atestacion(dm, id_act, id_mapa),
            "fila_mapa": {
                "id": id_mapa, "status": mapa.get("status"),
                "source_pdf_filename": mapa.get("source_pdf_filename"),
                "sha": mapa.get("source_pdf_sha256"), "source_url": mapa.get("source_url"),
                "product_model": mapa.get("product_model"),
                "manufacturer": mapa.get("manufacturer"),
                "revision_columna": mapa.get("revision"),
                "ingested_at": mapa.get("ingested_at"), "notes": mapa.get("notes"),
                "conteos": pm["conteos"], "portada": pm["portada"],
            },
            "fila_actual": {
                "id": id_act, "status": actual.get("status"),
                "source_pdf_filename": actual.get("source_pdf_filename"),
                "sha": actual.get("source_pdf_sha256"), "source_url": actual.get("source_url"),
                "product_model": actual.get("product_model"),
                "manufacturer": actual.get("manufacturer"),
                "revision_columna": actual.get("revision"),
                "ingested_at": actual.get("ingested_at"),
                "conteos": pa["conteos"], "portada": pa["portada"],
                "source_files_en_chunks": pa["source_files_en_chunks"],
            },
        })

    bloque = [f for f in filas_salida if f["destino"] == "bloque"]
    individual = [f for f in filas_salida if f["destino"] == "individual"]
    ninguno = [f for f in filas_salida if f["destino"] == "ninguno"]

    recibo = {
        "que_es": ("s322f — adjudicación determinista (sin LLM) de las 49 COLISIONES de "
                   "identidad del packet E1 §1. PROPUESTA: nada aplicado."),
        "utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "fuente": str(CENSO.relative_to(ROOT)).replace("\\", "/"),
        "solo_lectura": True,
        "totales": {
            "analizadas": len(filas_salida),
            "bloque": len(bloque),
            "individual": len(individual),
            "ya_no_aplica": len(ninguno),
            "entries_del_catalogo_afectadas": sum(f.get("n_entries_adjudicadas", 0)
                                                  for f in filas_salida),
        },
        "por_clase": {c: sum(1 for f in filas_salida if f["clase"] == c)
                      for c in sorted({f["clase"] for f in filas_salida})},
        "consecuencia_medida": {
            "que_es": ("Impacto REAL del desajuste de ids en el anexo must_preserve "
                       "(join por document_id). Medido, no teorizado."),
            "docs_donde_la_atestacion_falla_con_el_id_servido":
                sum(1 for f in filas_salida
                    if f.get("seam_atestacion", {}).get("medible")
                    and not f["seam_atestacion"]["atesta_con_id_actual"]),
            "docs_donde_atestaria_con_el_id_fantasma":
                sum(1 for f in filas_salida
                    if f.get("seam_atestacion", {}).get("medible")
                    and f["seam_atestacion"]["atesta_con_id_fantasma"]),
            "seam_allowed_sources": ("INTACTO — catalog_resolver indexa por source_file y "
                                     "el del doc_map coincide exactamente con el de los "
                                     "chunks del activo en las 49"),
        },
        "seccion_0_bloque": bloque,
        "seccion_1_individual": individual,
        "seccion_ya_no_aplica": ninguno,
    }

    salida = Path(args.salida)
    if not salida.is_absolute():
        salida = ROOT / salida
    salida.write_text(json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"recibo -> {salida}")
    print(json.dumps(recibo["totales"], ensure_ascii=False, indent=1))
    print(json.dumps(recibo["por_clase"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
