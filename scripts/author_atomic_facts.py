#!/usr/bin/env python3
"""author_atomic_facts.py — autoría de hechos atómicos del slice (Fase 1/2).

Capa de AUTORÍA sobre gold_store (la capa de ALMACENAMIENTO). No edita el YAML a
mano: carga la entrada verificada existente, le adjunta `atomic_facts` y la reescribe
vía gold_store.upsert() (que valida esquema + round-trip). Idempotente y re-ejecutable.

Los hechos se transcriben FIELMENTE del gold_answer ya verificado contra la fuente
(render + cross-model + dominio en s30-31); esto NO re-verifica, solo reestructura a
hechos atómicos (core/supplementary, presente/ausente-probado) para el scorer atómico.

Esquema de un hecho (igual que hp007, plantilla): texto / tipo / estado / valor / cita.
  - valor = el dato distintivo que el scorer buscará en la respuesta del bot (número,
    código o término); null si el hecho es cualitativo.

Uso: python scripts/author_atomic_facts.py [--apply]   (sin --apply = dry-run)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gold_store  # noqa: E402

# --- hp011: Morley RP1r-Supra — tras descarga de extinción no rearma. ¿Qué comprobar?
# Conducta=answer. Fuente HLSI-MN-103. Params 7-seg r.1/t.A VERIFICADOS (render +
# cross-model + Alberto, s30): el gold original fabricó labels OCR (P.18->r.1, P.02->t.A)
# y un default erróneo (295s -> "--"). Ver _provenance.correccion + feedback_7segment_reading.
HP011_FACTS = [
    {
        "texto": ("Entrada ABORT (paro de emergencia): por defecto enclavada (latched); "
                  "una vez activada requiere rearme manual de la central para rehabilitar "
                  "el proceso de extincion"),
        "tipo": "core", "estado": "presente", "valor": "ABORT", "cita": "p44",
    },
    {
        "texto": ('Parametro r.1 "Rearme inhibido tras extincion": "--"=inhibido hasta '
                  'finalizar la extincion o agotar t.A; "00"=rearme permitido en cualquier '
                  'momento (POR DEFECTO); "01" a "30"=inhibido durante ese intervalo en minutos'),
        "tipo": "core", "estado": "presente", "valor": "r.1", "cita": "p63",
    },
    {
        "texto": ('Parametro t.A "Duracion de la descarga" (soak time): variable de 05 a 295 '
                  'seg en pasos de 5 s; "--"=circuito activado hasta el rearme de la central '
                  "(POR DEFECTO)"),
        "tipo": "core", "estado": "presente", "valor": "05 a 295 seg", "cita": "p56",
    },
    {
        "texto": ("Averias enclavadas: por defecto todas las averias son enclavadas y "
                  "requieren rearme manual de la central para su restablecimiento"),
        "tipo": "core", "estado": "presente", "valor": "enclavadas", "cita": "p53",
    },
    {
        "texto": ("Entrada Flow Press (senal de flujo): su activacion implica un rearme "
                  "manual de la central"),
        "tipo": "supplementary", "estado": "presente", "valor": "flujo", "cita": "p45",
    },
    {
        "texto": ('Procedimiento de rearme: desde nivel de acceso 2 (llave de desbloqueo), '
                  'pulsar la tecla "Rearme"'),
        "tipo": "supplementary", "estado": "presente", "valor": None, "cita": "p44",
    },
]

# --- hp017: Notifier PEARL — programar el retardo de salida de alarma principal.
# Conducta=answer (corregida de admit en s30: el Manual de configuracion 997-671-005-3
# SI cubre el tema y esta en chunks_v2; el gold original solo tenia la guia basica).
# Fuente 997-671-005-3 Apendice 5 (causa-efecto).
HP017_FACTS = [
    {
        "texto": ("El retardo de las salidas se programa mediante PROGRAMACION CAUSA-EFECTO "
                  "(reglas) en el Manual de configuracion 997-671-005-3 (Apendice 5), NO con "
                  'un parametro unico de "retardo de salida"'),
        "tipo": "core", "estado": "presente", "valor": "causa-efecto", "cita": "997-671-005-3 Ap.5",
    },
    {
        "texto": ("Una regla consta de una INSTRUCCION DE ENTRADA (condicion, p.ej. alarma en "
                  "zona/lazo) y una INSTRUCCION DE SALIDA (equipo a accionar: sirenas o reles)"),
        "tipo": "core", "estado": "presente", "valor": "instruccion de entrada", "cita": "p42",
    },
    {
        "texto": ('Acceder a la pantalla "Causa y Efecto" desde el menu "Editar Configuracion"; '
                  "borrar la Regla 1 por defecto (CUALQUIER entrada de alarma activa TODOS los "
                  "equipos de salida) si se va a hacer una programacion especifica"),
        "tipo": "core", "estado": "presente", "valor": "Editar Configuracion", "cita": "p43",
    },
    {
        "texto": ('Asignar a la regla uno de los SEIS tipos de retardo de salida (seccion A5.3 '
                  '"Tipos de retardo"), que determina el comportamiento del retardo y su control '
                  "por teclas (SILENCIAR SIRENAS / SONIDO ALARMAS)"),
        "tipo": "core", "estado": "presente", "valor": "seis tipos de retardo", "cita": "p44 (A5.3)",
    },
    {
        "texto": ('A nivel de equipo/zona existe el parametro "Retardo de alarma" en la '
                  "programacion del lazo; el retardo de confirmacion de coincidencia puede "
                  "ajustarse hasta 240 s (4 min)"),
        "tipo": "supplementary", "estado": "presente", "valor": "240 s", "cita": "p20",
    },
    {
        "texto": ('Maximo 512 reglas; en la columna "Lazo" un "0" significa TODOS'),
        "tipo": "supplementary", "estado": "presente", "valor": "512", "cita": "p43",
    },
]

RETROFITS = {"hp011": HP011_FACTS, "hp017": HP017_FACTS}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    apply = "--apply" in sys.argv

    for qid, facts in RETROFITS.items():
        g = gold_store.get(qid)
        if g is None:
            print(f"[ERROR] {qid} no existe en el gold")
            return 1
        if gold_store._estado(g) != "verificado":
            print(f"[ERROR] {qid} no esta verificado (estado={gold_store._estado(g)}) — "
                  "no se autoran hechos sobre un gold sin verificar")
            return 1
        n_core = sum(1 for f in facts if f["tipo"] == "core")
        print(f"{qid}: {len(facts)} hechos ({n_core} core, {len(facts)-n_core} supplementary)"
              + ("  [ya tenia atomic_facts — se sobreescriben]" if g.get("atomic_facts") else ""))
        g["atomic_facts"] = facts
        # Validacion del esquema ANTES de escribir (mismo check que CI).
        issues = gold_store.validate_entry(g)
        errs = [i for i in issues if i.severity == "error"]
        for i in issues:
            print(f"    {i}")
        if errs:
            print(f"[ERROR] {qid} tiene errores de esquema — no se escribe")
            return 1
        if apply:
            gold_store.upsert(g)
            print(f"    -> escrito vía gold_store.upsert")

    if not apply:
        print("\n(dry-run; usa --apply para escribir)")
    else:
        print("\nListo. Re-valida con: python scripts/gold_store.py validate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
