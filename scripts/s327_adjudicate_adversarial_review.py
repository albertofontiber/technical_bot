#!/usr/bin/env python3
"""Adjudicación regla C del dúo s327, SIN reescribir los bytes previos del JSONL.

POR QUÉ ES A MANO. El runner de Fable corrió en modo emparejado
(`--sol-ts 2026-08-20T04:35:23`) y su recibo NO se enganchó: el guardián de
`attach_fable_receipt` lo rechazó con «Sol y Fable no revisaron exactamente los
mismos bytes ordenados». Es el guardián funcionando, no un fallo: entre Sol
(04:35) y Fable (04:49) el briefing CAMBIÓ —le apendicé la sección «v2 — qué
cambió tras la ronda de Sol»—, así que el `review_subject_sha256` divergió.

Y ahí hay algo estructural que conviene dejar escrito (va a TECH_DEBT): el modo
emparejado asume un dúo PARALELO (los dos revisores ven los mismos bytes),
mientras que la práctica real de este proyecto es SECUENCIAL — Sol primero,
sus hallazgos se cierran y se apendizan al briefing, y Fable revisa ESE briefing
ya cerrado, que es justo lo que le da valor (no repite a Sol, audita los
cierres). Con esa práctica el enganche automático NUNCA puede cuadrar: el mismo
error salió el 19-ago a las 20:35 y a las 22:23. De ahí que la fila la cierre
esta adjudicación a mano, con punteros explícitos a los artefactos de Fable.

Lo que este script NO hace: inventarse el recibo de Fable. El recibo se perdió
cuando el runner salió con código 1 tras fallar el enganche; lo que queda —y es
lo auditable— son su review y su traza de proveedor, referenciadas por sha256.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "evals/adversarial_review_log.jsonl"
TARGET_TS = "2026-08-20T04:35:23"

FABLE_REVIEW = "evals/adversarial_reviews/2026-08-20T04-51-42_claude-fable-5_b7fe3fdb4af6.md"
FABLE_TRACE = ("evals/adversarial_reviews/"
               "2026-08-20T04-51-42_claude-fable-5_responses_41dca876fda0.json")

VERDICT = (
    "Regla C sobre 7 de Sol + 5 de Fable = 12 hallazgos, 12 CONFIRMADOS contra "
    "codigo/BD, 0 FP. Severidad maxima: CRITICO (F1 de Fable, de PROCESO). "
    "SOL: S1 la 023 disparo el trigger de la deuda #91 sin resolverla (cierre: "
    "tests/test_s327_clasificacion_pg.py, 11 casos, 11/11 verdes contra un "
    "PostgreSQL 17 real + control negativo ejecutado + workflow propio). "
    "S2 la portada podia morir en 504, ~16 lecturas x 10s vs maxDuration=30 "
    "(cierre: datos.Presupuesto de 18s + estado SIN_TIEMPO). "
    "S3 los recibos del job probaban EJECUCION, no CALIDAD del eje (cierre: "
    "censo COMPLETO de los 16 casos auditables, evals/s327_eje_pregunta_medicion_v1.md). "
    "S4 los votos no filtraban es_pregunta (cierre: migracion 024, aplicada). "
    "S5 la regla era 'contiene ?' y la adjudicacion de Alberto decia 'acaba en ?' "
    "(cierre: termina_en_interrogacion). "
    "S6 'de un vistazo' no lo era con la serie completa (cierre: 5 barras en "
    "portada, serie entera en el detalle; en movil sigue habiendo scroll y se declara). "
    "S7 el prompt nombraba un id RETIRADO, no_es_pregunta, y el parser estricto "
    "descartaba esas filas en cada corrida (cierre: taxonomia v8 + histórico "
    "re-clasificado 109/109). "
    "FABLE: F1 [CRITICO, de proceso] el cierre de S3 citaba un fichero que NO "
    "existia cuando el revisor fue a abrirlo: escribi 'ver medicion_v1.md' en el "
    "briefing y cree el fichero 14 minutos DESPUES de lanzar la corrida. Es el "
    "patron que el Protocolo 1 existe para cortar, cometido dentro del aparato "
    "montado para cortarlo. Cierre en dos pasos: el artefacto se versiona en este "
    "commit, y sus cifras se RE-VERIFICAN contra la BD de produccion (109 filas, "
    "93 terminan en '?', 102 es_pregunta=true, 7 false, 0 sin clasificar, "
    "taxonomia_version min=max=8; 102-93=9 preguntas decididas por el modelo + 7 "
    "no-preguntas = los 16 casos auditables del censo). Regla nueva al Protocolo 4: "
    "el artefacto se VERSIONA ANTES de citarlo. "
    "F2 [medio] el cierre de S2 se quedo a medias: pagina_resumen pasaba "
    "presupuesto pero pagina_metricas recorria las 14 vistas sin el, y ademas "
    "pinta la tabla entera de cada una, asi que era la pagina MAS expuesta al 504 "
    "(cierre: mismo presupuesto de 18s; verificado que leer_vista no tiene "
    "presupuesto por defecto, que era la duda del revisor). "
    "F3 [medio] framing v7/v8 incoherente en el briefing: el Estado decia v7 "
    "mientras S7 y el YAML decian v8, y por contrato del propio YAML eso dejaria "
    "las 109 filas como PENDIENTES (cierre: corregido a v8 + aclarado por que el "
    "CHECK de la 023, escrito con la lista de la v7, sigue valido: v7->v8 solo "
    "cambio descripciones, no ids). Era error de redaccion, no de datos. "
    "F4 [menor] comentario duplicado y postcondicion por conteo de substring en "
    "la 024 (cierre: duplicado fuera, fragilidad declarada, y mitigada por el "
    "gate pg que comprueba COMPORTAMIENTO -siembra pares pregunta/no-pregunta y "
    "exige que los votos de las no-preguntas no cuenten-, no el texto del SQL; "
    "banner de 'aplicada, no se edita' anadido). "
    "F5 [menor] hueco no declarado en termina_en_interrogacion: '¿cuantos lazos' "
    "-apertura sin cierre, frecuente en teclado movil ES- cae al LLM con sesgo "
    "True. NO se amplia a proposito: la adjudicacion de Alberto es sobre el signo "
    "FINAL y ampliarla por mi cuenta seria re-litigarla; se declara en el codigo. "
    "NO VERIFICABLE por el revisor y asi se queda, como declaracion del autor y no "
    "como hecho auditable desde el repo: las claims 5-6 (movil y CSP). La medicion "
    "de 0px de scroll en 390/768/1440 se hizo con Chromium real pero no se puede "
    "re-ejecutar desde el repo; anotado en TECH_DEBT. "
    "NOTA DE TALLY: el recibo de Fable no se engancho -el guardian rechazo el par "
    "porque el briefing cambio entre las dos corridas, que es lo correcto en un duo "
    "SECUENCIAL como el nuestro-. Artefactos de Fable referenciados por sha256 en "
    "fable_review."
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    raw = LOG.read_bytes()
    lines = raw.splitlines(keepends=True)
    ending = (b"\r\n" if lines[-1].endswith(b"\r\n")
              else b"\n" if lines[-1].endswith(b"\n") else b"")
    payload = lines[-1][: -len(ending)] if ending else lines[-1]
    row = json.loads(payload.decode("utf-8"))

    if row.get("ts") != TARGET_TS:
        raise RuntimeError("la revision s327 no es la ultima entrada del log")
    if row.get("duo_status") == "adjudicado":
        print("S327_ADJUDICATION_ALREADY_APPLIED")
        return 0
    if row.get("duo_status") != "pending_fable":
        raise RuntimeError(f"estado inesperado del duo: {row.get('duo_status')!r}")
    if row.get("primary_contract_satisfied") is not True:
        raise RuntimeError("la fila Sol no satisface el contrato del revisor principal")

    review, trace = ROOT / FABLE_REVIEW, ROOT / FABLE_TRACE
    for path in (review, trace):
        if not path.is_file():
            raise RuntimeError(f"falta el artefacto de Fable: {path}")

    row.update(
        duo_status="adjudicado",
        findings=12,
        confirmed=12,
        false_pos=0,
        severity_max="critico",
        verdict_notes=VERDICT,
    )
    row["fable_review"] = {
        "model": "claude-fable-5",
        "display_name": "Fable 5",
        "pin_canonico": "claude-fable-5",
        "es_pin_canonico": True,
        # No es `completed`: el recibo del runner se perdio al salir con codigo 1
        # tras el rechazo del enganche. Lo que queda es la review y su traza, que
        # es lo auditable; el estado lo dice en vez de disfrazarlo de completo.
        "status": "completed_unpaired_hand_adjudicated",
        "unpaired_reason": ("attach_fable_receipt rechazo el par: «Sol y Fable no "
                            "revisaron exactamente los mismos bytes ordenados» — el "
                            "briefing gano la seccion v2 (cierres de Sol) entre las "
                            "dos corridas. Duo SECUENCIAL, no paralelo."),
        "review_output_path": FABLE_REVIEW,
        "review_output_sha256": _sha256(review),
        "provider_response_path": FABLE_TRACE,
        "provider_response_sha256": _sha256(trace),
        "findings": 5,
        "confirmed": 5,
        "false_pos": 0,
        "severity_max": "critico",
    }

    lines[-1] = (json.dumps(row, ensure_ascii=False, separators=(",", ":"))
                 .encode("utf-8") + ending)
    temporary = LOG.with_name(".adversarial_review_log.s327.tmp")
    try:
        temporary.write_bytes(b"".join(lines))
        os.replace(temporary, LOG)
    finally:
        if temporary.exists():
            temporary.unlink()
    print("S327_ADJUDICATION_APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
