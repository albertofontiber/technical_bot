# -*- coding: utf-8 -*-
"""s323 fase C — INVARIANTES de coherencia de identidad corpus↔catálogo (#80/#81).

Vive en `src/` y NO en `scripts/` porque es lógica de PRODUCCIÓN: la ingesta la
ejecuta en cada corrida. El contrato de imports del repo
(`tests/test_import_contract.py`) prohíbe que `src/` importe de `scripts/`, y
tenía razón — el primer cableado lo violaba.

Los invariantes se formulan sobre el PUNTERO (`document_id`), nunca sobre
`source_file`: el nombre solo corrobora una identidad ya ligada, así que usarlo
como clave contradiría el contrato canónico de identidad (dúo r32).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from ..http_pool import abierto
from .catalog_store import CATALOG_DIR, _read_jsonl

MANIFIESTO = CATALOG_DIR / "identidad_excepciones.json"


def _credenciales() -> tuple[str, dict]:
    """Credenciales PEREZOSAS (duo r34, critico de Sol): leerlas a nivel de
    modulo hacia que importar este fichero exigiera SUPABASE_* — y la CI corre
    pytest SIN secretos (conftest.py no los inyecta), asi que el test que lo
    importa habria reventado la COLECCION de toda la suite."""
    sb = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return sb, {"apikey": key, "Authorization": f"Bearer {key}"}


def _censo(c) -> dict:
    SB, HS = _credenciales()
    """Estado vivo de los cinco invariantes. Solo lectura."""
    doc_map = _read_jsonl(CATALOG_DIR / "doc_map.jsonl")
    ids = sorted({d["document_id"] for d in doc_map if d.get("document_id")})

    estado: dict[str, str] = {}
    for i in range(0, len(ids), 50):
        lote = ids[i:i + 50]
        r = c.get(f"{SB}/rest/v1/documents", headers=HS,
                  params={"select": "id,status", "id": "in.(" + ",".join(lote) + ")"})
        r.raise_for_status()
        for x in r.json():
            estado[x["id"]] = x["status"]

    # Conjunto EXACTO de documentos con chunks: se pagina el universo entero.
    # (Un `in.(...)` por lotes con `limit` TRUNCA y produce falsos positivos de
    # I3 — probado en s323: reportó 211 documentos «sin chunks» que tenían 30,
    # 134, 50 y 29. Contar por muestreo es la clase de fallo que este gate
    # existe para evitar; no se comete aquí dentro.)
    con_chunks: set[str] = set()
    offset = 0
    while True:
        r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                  params={"select": "document_id", "order": "id.asc",
                          "offset": str(offset), "limit": "1000"})
        r.raise_for_status()
        lote = r.json()
        con_chunks |= {x["document_id"] for x in lote if x.get("document_id")}
        if len(lote) < 1000:
            break
        offset += 1000

    v: dict[str, list] = {"I1_puntero_inexistente": [], "I2_puntero_no_activo": [],
                          "I3_puntero_sin_chunks": [], "I4_document_id_duplicado": [],
                          "I5_chunks_huerfanos": []}
    vistos: set[str] = set()
    for d in doc_map:
        did, sf = d.get("document_id"), d.get("source_file")
        if not did:
            continue
        if did in vistos:
            v["I4_document_id_duplicado"].append({"document_id": did, "source_file": sf})
        vistos.add(did)
        if did not in estado:
            v["I1_puntero_inexistente"].append({"document_id": did, "source_file": sf})
        elif estado[did] != "active":
            v["I2_puntero_no_activo"].append({"document_id": did, "source_file": sf,
                                              "status": estado[did]})
        elif did not in con_chunks:
            v["I3_puntero_sin_chunks"].append({"document_id": did, "source_file": sf})

    # I5 PAGINADO: pedir solo Range 0-999 omitiria filas a partir de 1.000
    # huerfanos — la MISMA clase de truncado que ya falseo I3 en este mismo
    # gate. Un censo que no puede contar mas alla de su ventana no es un censo.
    huerfanos, offset = [], 0
    while True:
        r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                  params={"select": "id,source_file", "document_id": "is.null",
                          "order": "id.asc", "offset": str(offset), "limit": "1000"})
        r.raise_for_status()
        lote = r.json()
        huerfanos += [{"chunk_id": x["id"], "source_file": x.get("source_file")}
                      for x in lote]
        if len(lote) < 1000:
            break
        offset += 1000
    v["I5_chunks_huerfanos"] = huerfanos
    return v


def _clave(inv: str, fila: dict) -> str:
    """Identidad EXACTA de una violación (para el manifiesto). Nunca el nombre solo."""
    return (f"{inv}|{fila['chunk_id']}" if inv == "I5_chunks_huerfanos"
            else f"{inv}|{fila['document_id']}")


def evaluar() -> dict:
    """Evalúa el gate y devuelve el veredicto (para llamadores, no solo CLI).

    `ok` es False solo si hay violaciones NUEVAS respecto al manifiesto: las
    preexistentes están gobernadas y no deben teñir de rojo cada ejecución —
    si lo hicieran, nadie miraría el gate y volveríamos al punto de partida.
    """
    with abierto(timeout=60.0) as c:
        v = _censo(c)
    previas = {}
    if MANIFIESTO.exists():
        previas = json.loads(MANIFIESTO.read_text(encoding="utf-8")).get("excepciones", {})
    nuevas = [{"invariante": inv, **f} for inv, filas in v.items() for f in filas
              if _clave(inv, f) not in previas]
    # Excepciones RESUELTAS (duo r34): una whitelist permanente envejece mal —
    # si se repara una violacion y el manifiesto la sigue autorizando, su
    # reaparicion futura pasaria inadvertida. Se reportan para forzar el
    # re-sellado tras cada reparacion.
    vivas = {_clave(inv, f) for inv, filas in v.items() for f in filas}
    resueltas = sorted(set(previas) - vivas)
    return {"ok": not nuevas, "nuevas": len(nuevas),
            "total": sum(len(x) for x in v.values()),
            "por_invariante": {k: len(x) for k, x in v.items()},
            "detalle_nuevas": nuevas,
            "excepciones_resueltas": resueltas,
            "manifiesto_stale": bool(resueltas)}




def sellar() -> int:
    """Regenera el manifiesto de excepciones. Acto DELIBERADO: si sellar fuera un
    efecto colateral de ejecutar el gate, cualquier violación nueva se
    auto-autorizaría y el gate no valdría nada."""
    with abierto(timeout=60.0) as c:
        v = _censo(c)
    total = sum(len(x) for x in v.values())
    MANIFIESTO.write_text(json.dumps({
        "que_es": ("Excepciones GOBERNADAS del gate de identidad (s323 fase C). "
                   "Incumplimientos PREEXISTENTES con su identidad exacta, motivo "
                   "y fecha. El gate falla por lo NUEVO."),
        "sellado_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "excepciones": {_clave(inv, f): {**f, "invariante": inv,
                                         "motivo": "preexistente al sellar el gate"}
                        for inv, filas in v.items() for f in filas},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return total
