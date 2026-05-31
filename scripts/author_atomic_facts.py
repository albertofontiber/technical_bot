#!/usr/bin/env python3
"""author_atomic_facts.py — ledger de AUTORÍA de golds verificados (Fase 1/2).

Capa de AUTORÍA sobre gold_store (la capa de ALMACENAMIENTO). No edita el YAML a
mano: carga la entrada, le adjunta `atomic_facts` (+ conducta + `_provenance` para
golds recién verificados) y la reescribe vía gold_store.upsert() (valida esquema +
round-trip). Idempotente y re-ejecutable. Es el registro durable de "cómo se autoró
cada gold" → sustituye los scripts throwaway (D10).

Dos modos por entrada en RECORDS:
  - solo `facts`: el gold YA está verificado (hp011/hp017, verificados en s30) → solo
    se le reestructuran los hechos atómicos. Si no está verificado, ERROR.
  - `facts` + `provenance` (+ `conducta`): el gold se VERIFICA aquí (Fase 1) — el
    `_provenance` (estado=verificado + evidencia render/cross-model) es el acto de
    verificación. Los hechos se transcriben de la fuente confirmada, no del gold viejo.

Esquema de un hecho (plantilla hp007): texto / tipo / estado / valor / cita.
  - valor = dato DISTINTIVO que el scorer busca en la respuesta (número/código/término);
    NO una frecuencia/etiqueta compartida (lección s32, hp007). null si es cualitativo.

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

# --- hp019: ASD535 (Securiton) — rango de temperatura de funcionamiento. Conducta=answer.
# VERIFICADO en s32 (Fase 1, 1ª rebanada): tabla "Datos tecnicos" p133 (digital-native)
# leida por Claude (multimodal) + gpt-5.5 (cross_verify_image, transcripcion en frio) —
# acuerdo total en valores; ultracongelacion confirmada en p131 §11.5. valor = el nº
# distintivo de cada hecho (un solo core = el rango -30/+60; el resto, refinamientos).
HP019_FACTS = [
    {
        "texto": ("Rango de temperatura de funcionamiento (caja del detector y conducto de "
                  "aspiracion): -30 a +60 °C"),
        "tipo": "core", "estado": "presente", "valor": "-30 a +60", "cita": "p133 (Datos tecnicos)",
    },
    {
        "texto": "Limite segun UL/FM para la caja del detector: maximo +40 °C",
        "tipo": "supplementary", "estado": "presente", "valor": "+40", "cita": "p133",
    },
    {
        "texto": "Limite segun estandar australiano AS 1603.8 (caja y conducto): -30 a +55 °C",
        "tipo": "supplementary", "estado": "presente", "valor": "+55", "cita": "p133",
    },
    {
        "texto": ("Fluctuacion de temperatura maxima permitida durante el funcionamiento "
                  "(caja y conducto): 20 °C"),
        "tipo": "supplementary", "estado": "presente", "valor": "20 °C", "cita": "p133",
    },
    {
        "texto": "Temperatura de almacenamiento permitida (sin condensacion): -30 a +70 °C",
        "tipo": "supplementary", "estado": "presente", "valor": "+70", "cita": "p133",
    },
    {
        "texto": ("Uso en almacenes de ultracongelacion: rango restringido a -30 a 0 °C; "
                  "respetar la directriz T 131 390"),
        "tipo": "supplementary", "estado": "presente", "valor": "T 131 390", "cita": "p131 (11.5)",
    },
]
HP019_PROV = {
    "estado": "verificado",
    "metodo": "render_pdf + cross_model",
    "fuente": "ASD535_TD_T131192es_h.pdf",
    "paginas": [133, 131],
    "verificado_por": [
        "Claude (lectura multimodal de la tabla 'Datos tecnicos' p133 renderizada)",
        "gpt-5.5 (transcripcion independiente en frio de p133, scripts/cross_verify_image.py)",
    ],
    "acuerdo": ("total en los valores nucleo (-30/+60, UL +40, AS +55, fluctuacion 20, "
                "almacenamiento +70); discrepancia trivial de wording (UL/FM<= vs UL max), "
                "valor +40 unanime"),
    "fecha": "2026-05-31",
    "nota": ("Tabla digital-native (no OCR/7-seg) -> lectura fiable; el texto extraido del "
             "corpus corrobora. Ultracongelacion (-30 a 0 + T 131 390) confirmada en p131 11.5."),
    "localizacion": {
        "manuales_buscados": ["ASD535_TD_T131192es_h.pdf"],
        "terminos": ["Rango de temperatura", "Datos tecnicos", "ultracongelacion", "T 131 390"],
        "pagina_fisica": 133,
        "nota": ("impresa 133 = fisica 133 (sin offset; PDF 134 pags). Localizado por busqueda "
                 "PyMuPDF de 'Rango de temperatura' -> tabla de specs en p133."),
    },
}

# --- hp003: Detnov CAD-150 — conexión de las baterías de 24V. Conducta=answer.
# VERIFICADO s32 (Fase 1): manual 55315013 (multilingüe ES/FR/GB/IT, offset impresa+2=física).
# §2.5 (física p9) leída por Claude (multimodal) + gpt-5.5 (cross_verify, en frío) — acuerdo
# total; orden red->baterías y >24V confirmados en física p10 (§3.2/§3.1).
HP003_FACTS = [
    {
        "texto": "Dos baterias de 12V conectadas en SERIE (suman los 24V del sistema), capacidad 7A/h",
        "tipo": "core", "estado": "presente", "valor": "12V", "cita": "p7/f9 (§2.5)",
    },
    {
        "texto": "Cable puente: une el polo POSITIVO de una bateria con el NEGATIVO de la otra",
        "tipo": "core", "estado": "presente", "valor": "cable puente", "cita": "p7/f9 (§2.5)",
    },
    {
        "texto": ("Los cables que salen del circuito (ROJO y NEGRO) se conectan al positivo y "
                  "negativo de las baterias (conectar antes el puente entre baterias)"),
        "tipo": "core", "estado": "presente", "valor": "rojo y negro", "cita": "p7/f9 (§2.5)",
    },
    {
        "texto": ("Orden de conexion por seguridad: PRIMERO la red (230VAC, magnetotermico "
                  "bipolar), DESPUES las baterias (no respetarlo puede danar el equipo)"),
        "tipo": "core", "estado": "presente", "valor": "primero la red", "cita": "p8/f10 (§3.2) + Usuario p7",
    },
    {
        "texto": ("Antes de alimentar, comprobar con voltimetro que las baterias tienen una "
                  "tension superior a 24V"),
        "tipo": "supplementary", "estado": "presente", "valor": "24V", "cita": "p8/f10 (§3.1)",
    },
    {
        "texto": "Las baterias se colocan en la parte inferior de la caja, en vertical",
        "tipo": "supplementary", "estado": "presente", "valor": "parte inferior", "cita": "p7/f9 (§2.5)",
    },
    {
        "texto": "Desconectar el magnetotermico bipolar exterior antes de manipular la central",
        "tipo": "supplementary", "estado": "presente", "valor": "magnetotermico", "cita": "p6/f8 (§2.3)",
    },
]
HP003_PROV = {
    "estado": "verificado",
    "metodo": "render_pdf + cross_model",
    "fuente": "55315013 Manual Centrales Analogicas CAD-150-8 Instalacion ES FR GB IT.pdf",
    "paginas_impresas": [6, 7, 8],
    "paginas_fisicas": [8, 9, 10],
    "verificado_por": [
        "Claude (lectura multimodal de §2.5 p9 + §3.1/§3.2 p10 + §2.3 p8 renderizadas)",
        "gpt-5.5 (transcripcion independiente en frio de §2.5 p9, scripts/cross_verify_image.py)",
    ],
    "acuerdo": ("total en §2.5 (dos baterias 12V 7A/h en serie, cable puente +/-, cables rojo/negro, "
                "ubicacion inferior vertical); orden red->baterias confirmado en p10 §3.2; >24V en p10 §3.1"),
    "fecha": "2026-05-31",
    "nota": ("Manual multilingue ES/FR/GB/IT; offset impresa+2=fisica (impresa 7 = fisica 9). El "
             "gold_answer menciona 18/24 A/h, fusible 2A y pulsador BAT que NO aparecen en las paginas "
             "citadas (p6-8) -> NO incluidos como hechos (no verificados aqui; posiblemente en otras paginas)."),
    "localizacion": {
        "manuales_buscados": ["55315013 ... CAD-150-8 Instalacion ES FR GB IT.pdf"],
        "terminos": ["baterias", "cable puente", "serie", "24V", "230VAC", "magnetotermico"],
        "paginas_fisicas": [8, 9, 10],
        "nota": "localizado por busqueda PyMuPDF (bater* + puente/serie/230/24V) -> §2.5 fisica p9; offset +2.",
    },
}

# qid -> {facts, [provenance], [conducta]}. provenance presente = el gold se VERIFICA aquí.
RECORDS = {
    "hp011": {"facts": HP011_FACTS},
    "hp017": {"facts": HP017_FACTS},
    "hp019": {"facts": HP019_FACTS, "conducta": "answer", "provenance": HP019_PROV},
    "hp003": {"facts": HP003_FACTS, "conducta": "answer", "provenance": HP003_PROV},
}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    apply = "--apply" in sys.argv

    for qid, rec in RECORDS.items():
        facts = rec["facts"]
        g = gold_store.get(qid)
        if g is None:
            print(f"[ERROR] {qid} no existe en el gold")
            return 1
        nuevo = bool(rec.get("provenance"))
        if nuevo:
            g["_provenance"] = rec["provenance"]  # acto de verificación (marca verificado)
        if rec.get("conducta"):
            g["conducta_esperada"] = rec["conducta"]
        if gold_store._estado(g) != "verificado":
            print(f"[ERROR] {qid} no verificado y el record no aporta _provenance verificado "
                  "— no se autoran hechos sobre un gold sin verificar")
            return 1
        n_core = sum(1 for f in facts if f["tipo"] == "core")
        tag = " [VERIFICA aquí]" if nuevo else ("  [reescribe atomic_facts]" if g.get("atomic_facts") else "")
        print(f"{qid}: {len(facts)} hechos ({n_core} core, {len(facts)-n_core} supp){tag}")
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
            print("    -> escrito vía gold_store.upsert")

    if not apply:
        print("\n(dry-run; usa --apply para escribir)")
    else:
        print("\nListo. Re-valida con: python scripts/gold_store.py validate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
