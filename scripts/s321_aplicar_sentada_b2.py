#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s321_aplicar_sentada_b2.py — aplica al ruler las 6 adjudicaciones de la sentada B2.

Fuente de verdad de CADA cambio: `evals/s321_sentada_b2_conjunto_de_escritura_v4.md` + las
correcciones del dúo emparejado (Sol ts=2026-08-16T11:51:02 + Fable) + las lecturas al píxel de
`logs/render/s321/` con doble señal (`evals/s321_cross_verify_v1.txt`) + la localización ES+EN
(`evals/s321_localizacion_es_en_v1.json`).

Contrato: construye las entradas en memoria → `gold_store.validate_entry` sobre TODAS → si hay
UN error no escribe NADA → si no, `gold_store.upsert` una a una. Falla-cerrado.

Uso:
  python scripts/s321_aplicar_sentada_b2.py            # dry-run: valida e imprime el diff
  python scripts/s321_aplicar_sentada_b2.py --aplicar  # escribe el ruler
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts import gold_store as GS  # noqa: E402

HOY = "2026-08-16"
DUO = "dúo emparejado s321: Sol xhigh ts=2026-08-16T11:51:02 + Fable 5 (evals/adversarial_review_log.jsonl)"
RENDER = "logs/render/s321/*.png (160dpi, ±1 vecina) + evals/s321_cross_verify_v1.txt (GPT-5.5 en frío)"
LOCAL = "evals/s321_localizacion_es_en_v1.json (barrido por doc_map — TECH_DEBT #84 —, ES+EN)"


def _prov(g: dict) -> dict:
    g.setdefault("_provenance", {})
    return g["_provenance"]


def _add_verified_by(g: dict, txt: str) -> None:
    p = _prov(g)
    vb = p.setdefault("verificado_por", [])
    if txt not in vb:
        vb.append(txt)


def _add_citations(g: dict, cits: list[dict]) -> None:
    lst = g.setdefault("citations", None) or []
    for c in cits:
        if c not in lst:
            lst.append(c)
    g["citations"] = lst


# ─────────────────────────────────────────────────────────────────────────────
# Ítem 3 · hp017 — SIN split del #2 (release_guard s277 con anclas selladas; la migración habría
# tocado el sha del contrato). Se conserva (b) intacto y se AÑADE la Regla 2 como supplementary.
# ─────────────────────────────────────────────────────────────────────────────
def build_hp017(g: dict) -> dict:
    g = copy.deepcopy(g)
    facts = g["atomic_facts"]
    assert facts[2]["valor"] == "Editar Configuracion", "hp017#2 drift"
    facts.append({
        "texto": ("La advertencia general de A5.2 solo exige borrar la Regla 1, que anula la programacion "
                  "especifica. La Regla 2 (la tecla EVACUACION activa TODOS los equipos de salida) no esta en "
                  "esa advertencia; el paso 'deben eliminarse' las dos reglas por defecto aparece en el "
                  "Ejemplo 1 de A5.4, un caso de evacuacion por etapas en el que la programacion toca la "
                  "propia evacuacion"),
        "tipo": "supplementary",
        "estado": "presente",
        "valor": "Regla 2",
        "cita": "997-671-005-3 p43 (A5.2, f43) + p45 (A5.4 Ejemplo 1, f45)",
    })
    _add_citations(g, [
        {"manual": "997-671-005-3_Configuration_ES.pdf", "page": 43,
         "quote": "Es fundamental borrar la regla 1 si se va a realizar una programación específica, ya que, si no, esta será anulada."},
        {"manual": "997-671-005-3_Configuration_ES.pdf", "page": 45,
         "quote": "A5.4 Ejemplos de reglas de causa-efecto … Ejemplo 1 … el usuario encontrará aquí las dos reglas de causa-efecto por defecto. Deben eliminarse si se van a crear reglas de causa-efecto personalizadas."},
    ])
    p = _prov(g)
    p["nota"] = (p.get("nota", "").rstrip() + " || s321 (sentada B2 ítem 3, adjudicación Alberto): #2 se CONSERVA "
                 "(release_guard s277 con anclas selladas; nombra solo la Regla 1 = coherente con la lectura). Se "
                 "AÑADE suppl 'Regla 2' que NO afirma 'no anula' (Sol v2/v3): describe la diferencia de ALCANCE "
                 "entre A5.2 (advertencia general, una regla) y A5.4-Ej.1 (paso de un ejemplo de evacuación por "
                 "etapas, dos reglas). No condiciona PASS. Lectura de Alberto: la Regla 1 anula porque comparte "
                 "disparador con las reglas específicas; la Regla 2 se dispara con la tecla → no se cruza salvo "
                 "que se programe la propia evacuación (que es justo el caso del Ejemplo 1). DEC-221 aplicado.")
    _add_verified_by(g, f"s321 lectura verbatim p43/p45 en chunks_v2 + {DUO}")
    return g


# ─────────────────────────────────────────────────────────────────────────────
# Ítem 4 · cat018 — split de #2 en (a) asociación CBE + (b) Tipo SW/TIPO ID con la regla de p65
# ─────────────────────────────────────────────────────────────────────────────
def build_cat018(g: dict) -> dict:
    g = copy.deepcopy(g)
    facts = g["atomic_facts"]
    old = facts[2]
    assert old["valor"] == "Tipo SW / asociacion CBE", "cat018#2 drift"
    fa = {
        "texto": ("Un modulo de salida se dispara cuando se cumple su ecuacion CBE (se activa 'por asociacion "
                  "CBE'); es una via de activacion distinta de la del Tipo SW"),
        "tipo": "core", "estado": "presente", "valor": "asociacion CBE",
        "cita": "AM-8200-manu-prog-spa p7 (impresa 4) + p65 (impresa 62)",
    }
    fb = {
        "texto": ("Cada modulo de salida lleva un Tipo SW (el manual tambien lo llama TIPO ID), y ese tipo "
                  "determina si admite CBE: la central NO PERMITE programar una ecuacion a un modulo con TIPO ID "
                  "para senalizaciones de caracter general — los de la tabla 'Modulos de salida para "
                  "senalizaciones generales' (PWRC, GPND, GAC, GTC, GAS, GTS, SND, STR...), que se activan por "
                  "su propia funcion; p. ej. SND es el tipo de la salida sirena"),
        "tipo": "core", "estado": "presente", "valor": "Tipo SW / TIPO ID",
        "cita": "AM-8200-manu-prog-spa p65 (impresa 62, NOTA en negrita: mecanismo) + p40-41 (impresas 37-38, tabla)",
    }
    g["atomic_facts"] = facts[:2] + [fa, fb] + facts[3:]
    # gold_answer punto 3
    ga = g["gold_answer"]
    viejo = ("3. LA SALIDA: los modulos de salida llevan un Tipo SW (por ejemplo SND para sirena); un modulo de "
             "salida se dispara cuando su ecuacion CBE se cumple (se activa 'por asociacion CBE').")
    nuevo = ("3. LA SALIDA: un modulo de salida se dispara cuando su ecuacion CBE se cumple (se activa 'por "
             "asociacion CBE'). Ojo al Tipo SW (TIPO ID) del modulo: la central NO permite programar una "
             "ecuacion a un modulo con TIPO ID para senalizaciones de caracter general (tabla p40-41: PWRC, "
             "GAC, GTC, GAS, GTS, SND, STR...); esos se activan por su propia funcion, p. ej. SND es el tipo "
             "de la salida sirena.")
    assert viejo in ga, "cat018 gold_answer punto 3 no encontrado"
    g["gold_answer"] = ga.replace(viejo, nuevo, 1)
    _add_citations(g, [
        {"manual": "AM-8200-manu-prog-spa.pdf", "page": 65,
         "quote": "NOTA: para los módulos de salida, la central no permite programar una ecuación si el módulo tiene un TIPO ID para señalizaciones de carácter general."},
        {"manual": "AM-8200-manu-prog-spa.pdf", "page": 41,
         "quote": "MÓDULOS DE SALIDA PARA SEÑALIZACIONES GENERALES … GASV · GTSV · ZFLTV · MAINFV · REMV · SND · STR … Nota: los módulos de salida utilizados para las funciones arriba indicadas no aceptan CBE."},
        {"manual": "AM-8200-manu-prog-spa.pdf", "page": 40,
         "quote": "MÓDULOS DE SALIDA PARA SEÑALIZACIONES GENERALES … PWRC · GPND · APND · GAC · TPND · GTC · TRS · ZFLT · ZDIS · MAINF · REM · GAS · GTS · ZFLTC · MAINFC · REMC"},
        {"manual": "AM-8200-manu-prog-spa.pdf", "page": 7,
         "quote": "En caso de alarma, se activan los siguientes dispositivos: • Salida sirena • Módulos de salida programados con tipo-SW SND • Todos los módulos de salida activados por asociación CBE"},
    ])
    p = _prov(g)
    p["acuerdo"] = (p.get("acuerdo", "").rstrip() + " || s321: split #2 → asociación-CBE (core) + Tipo SW/TIPO ID (core, "
                    "adjudicación Alberto 'ambas CORE — no quiero falsear los misses'); regla de bloqueo p65 verificada "
                    "al píxel + GPT-5.5 en frío; tabla p40-41 (23 tipos) al píxel; iconos SND=sirena/STR=flash confirman "
                    "SND como tipo de sirena. Corroborado por ediciones IT/EN públicas de Honeywell (M-173.1 ITA p.38/63, "
                    "M-162.1-ENG p.38/63) — usadas para saber DÓNDE mirar, no como cita.")
    p["nota"] = (p.get("nota", "").rstrip() + f" || s321 render+doble señal: {RENDER}. Localización ES+EN: {LOCAL} — la regla "
                 "está en AM-8200-manu-prog-spa y AM-8200N (mismas p41/p65), ausente en los 3 manuales de instalación "
                 "(coherente: doctrina de programación). NO entra en el hecho «FORC/CON/CONV/GSND/GSTR sí aceptan CBE»: "
                 "p39 solo los lista.")
    _add_verified_by(g, "GPT-5.5 en frío sobre render p65/p41/p40 (evals/s321_cross_verify_v1.txt): NOTA literal, 7+16 tipos, iconos")
    _add_verified_by(g, f"Claude s321 lectura al píxel p65/p41/p40 + {DUO}")
    loc = p.setdefault("localizacion", {})
    loc.setdefault("manuales_buscados", [])
    for m in ["AM-8200-manu-prog-spa", "AM-8200N manual de usuario y programacion rev 3 30-10-2024",
              "AM-8200 Manual Instalacion", "AM 8200G manual instalacion Rv 3", "AM 8200N-manual instalacion RV 4 30-01-2025",
              "UCIP MODBUS AM8200 V5.1", "Guia Rapida H_GTW"]:
        if m not in loc["manuales_buscados"]:
            loc["manuales_buscados"].append(m)
    loc.setdefault("terminos", [])
    for t in ["no aceptan CBE", "no permite programar una ecuacion", "TIPO ID", "Tipo SW", "do not accept CBE"]:
        if t not in loc["terminos"]:
            loc["terminos"].append(t)
    return g


# ─────────────────────────────────────────────────────────────────────────────
# Ítem 5 · hp006 — demote #2 + reescritura + gold_answer (2 frases) + provenance + citations NUEVO
# ─────────────────────────────────────────────────────────────────────────────
def build_hp006(g: dict) -> dict:
    g = copy.deepcopy(g)
    f = g["atomic_facts"][2]
    assert f["valor"] == "ISO-X", "hp006#2 drift"
    f["tipo"] = "supplementary"
    f["texto"] = ("Los modulos aisladores ISO-X aislan del resto del lazo la rama en la que se produce un "
                  "CORTOCIRCUITO (MIDT170: 'El ISO-X detecta este cortocircuito y desconecta la ramificacion en "
                  "averia abriendo el lado positivo del lazo'), y son requisito del Estilo 7 de NFPA. NO intervienen "
                  "en un fallo de TIERRA: la tabla 'Funcionamiento del Lazo' da el mismo resultado para Tierra en "
                  "Estilo 6 y en Estilo 7, y solo mejora la fila Corto")
    f["cita"] = "MIDT170 p70 (f77, seccion ISO-X: mecanismo) + p64 (f71, tabla Funcionamiento del Lazo)"
    ga = g["gold_answer"]
    v1 = "- Para acotar un fallo en el lazo se emplean los modulos aisladores ISO-X, que aislan la rama en averia del resto del lazo (MIDT170)."
    n1 = "- Los modulos aisladores ISO-X (requeridos en Estilo 7) aislan cortocircuitos del lazo; no intervienen en un fallo de tierra (MIDT170)."
    v2 = "El metodo general consiste en aislar/desconectar circuitos progresivamente -en el lazo, mediante los aisladores ISO-X- hasta que desaparece el aviso"
    n2 = "El metodo general consiste en aislar/desconectar circuitos progresivamente hasta que desaparece el aviso"
    assert v1 in ga and v2 in ga, "hp006 gold_answer frases no encontradas"
    g["gold_answer"] = ga.replace(v1, n1, 1).replace(v2, n2, 1)
    _add_citations(g, [
        {"manual": "MIDT170.pdf", "page": 77,
         "quote": "Un cortocircuito en el lazo rearma el relé. El ISO-X detecta este cortocircuito y desconecta la ramificación en avería abriendo el lado positivo del lazo (terminal 4)."},
        {"manual": "MIDT170.pdf", "page": 71,
         "quote": "Funcionamiento del Lazo de Comunicaciones — Tierra: Alarma/Fallo · Alarma/Avería · Alarma/Avería | Corto: Avería · Avería · Alarma/Avería (Estilo 4 · 6 · 7)"},
        {"manual": "MIDT170.pdf", "page": 54,
         "quote": "LEDS para fallo de tierra … (MPS-400: LED 'Fallo de Tierra', terminal TB1-3, puente JP2)"},
    ])
    p = _prov(g)
    p["acuerdo"] = ("render confirma: MPS-400 con LED 'Fallo de Tierra' + TB1-3 + JP2 (f54); 'Tierra' como condicion de "
                    "averia del lazo (f71); los ISO-X aislan CORTOCIRCUITOS (f77) y NO intervienen en tierra (tabla f71: "
                    "fila Tierra igual en Estilo 6 y 7, solo mejora Corto) — DEC-223; sin procedimiento de localizacion "
                    "paso-a-paso en los manuales")
    p["nota"] = (p.get("nota", "").replace("MIDT170 OFFSET +8 (impresa = fisica - 8; pie 'MI-DT-170c 46'/'63' en f54/f71)",
                                          "MIDT170 OFFSET +7 (impresa = fisica - 7; pie 'MI-DT-170c 64'/'70' en f71/f77 — el +8 "
                                          "registrado en s27 estaba corrido una pagina; s321)")
                 + " || s321 (sentada B2 ítem 5, adjudicación Alberto = demote): DEC-223. 50253SP SÍ es manual de la "
                   "AFP-400 (doc_map primary de afp-300 Y afp-400); su p98 escribe la misma frase con 'corto circuito'.")
    _add_verified_by(g, f"s321 · DEC-223 · workflow wf_38d0cbac-aaf + verificación manual chunks_v2 f71/f77 + {DUO}")
    return g


# ─────────────────────────────────────────────────────────────────────────────
# Ítem 6 · cat020 — valor = el de Alberto; texto con los dos ejes
# ─────────────────────────────────────────────────────────────────────────────
def build_cat020(g: dict) -> dict:
    g = copy.deepcopy(g)
    f = g["atomic_facts"][2]
    assert f["valor"] == "manual de variaciones Espana", "cat020#2 drift"
    f["valor"] = "niveles por defecto del protocolo Morley-IAS"
    f["texto"] = ("Estos valores por defecto son los de la VERSION ESPANA para el PROTOCOLO MORLEY-IAS: figuran en el "
                  "Manual de variaciones para Espana, en la seccion §5.3.10.5 'Informacion especifica segun el "
                  "protocolo' → §5.3.10.5.1 'para protocolo Morley-IAS', que COMPLEMENTA el manual de configuracion "
                  "base (996-203-005-X) donde esta la configuracion general del nivel de alarma (seccion Modos Horarios)")
    f["cita"] = "DXc Manual de variaciones Espana p6 (§5.3.10.5 → §5.3.10.5.1) + p2-3"
    _add_citations(g, [
        {"manual": "DXc_Manual variaciones de mercado.pdf", "page": 6,
         "quote": "5.3.10.5 Información específica según el protocolo → 5.3.10.5.1 Información específica para protocolo Morley-IAS: … el nivel de prealarma por defecto es el 80% y el nivel de alarma por defecto es el 100%. • El ajuste máximo para el nivel de alarma es el 108%."},
    ])
    p = _prov(g)
    p["nota"] = (p.get("nota", "").rstrip() + " || s321 (sentada B2 ítem 6, adjudicación Alberto ✏️): el `valor` deja de "
                 "empezar por 'Manual' (ya no dispara _is_meta_ref → entra al denominador de factlevel; atomic_scorer "
                 "ya lo puntuaba). El texto CONSERVA los dos ejes (España + protocolo — Sol v2): el documento es de "
                 "variaciones para España, la sección que porta los valores es 'según el PROTOCOLO'. valor = el "
                 "marcado por Alberto (Fable v4 cazó que v2-v4 lo habían cambiado sin declarar).")
    _add_verified_by(g, f"s321 lectura verbatim p6 en chunks_v2 + {DUO}")
    return g


# ─────────────────────────────────────────────────────────────────────────────
# Ítem 8 · hp002 — enunciado INTACTO; core 'Securiton AG' al final; SIN meta-instrucción
# ─────────────────────────────────────────────────────────────────────────────
def build_hp002(g: dict) -> dict:
    g = copy.deepcopy(g)
    g["atomic_facts"].append({
        "texto": ("El ASD535 es un detector de humos por aspiracion cuyo FABRICANTE es Securiton (Securiton AG, "
                  "Alpenstrasse 20, 3052 Zollikofen, Suiza); en la tabla de terminos del manual: 'Fabricante = Securiton'"),
        "tipo": "core", "estado": "presente", "valor": "Securiton AG",
        "cita": "ASD535_TD_T131192es_h p1 (portada: logo SECURITON + pie 'Securiton AG Alpenstrasse 20 3052 Zollikofen Suiza') + p18 (tabla de terminos '| Fabricante | = Securiton |')",
    })
    _add_citations(g, [
        {"manual": "ASD535_TD_T131192es_h.pdf", "page": 1,
         "quote": "SECURITON — ASD 535 Detector de humos por aspiración — Descripción técnica — Securiton AG Alpenstrasse 20 3052 Zollikofen Suiza"},
        {"manual": "ASD535_TD_T131192es_h.pdf", "page": 18,
         "quote": "| Fabricante | = Securiton | … | OEM | = Original Equipment Manufacturer (fabricante o distribuidor del equipo original) |"},
    ])
    p = _prov(g)
    p["nota"] = (p.get("nota", "").rstrip() + " || s321 (sentada B2 ítem 8, decisión de PRODUCTO de Alberto = conducta (a): "
                 "corregir la marca Y responder en el mismo turno). El ENUNCIADO se conserva 'de Detnov' A PROPÓSITO: es el "
                 "estímulo del estrato oem-relabel (hp019 es el control con la marca correcta — asimetría deliberada, NO "
                 "armonizar). Core 'Securiton AG' = HECHO de fabricante (portada + p18 verbatim), SIN meta-instrucción "
                 "(Fable v4). LÍMITE DECLARADO (Sol v4 crítico 1, confirmado): el harness (test_bot_vs_gold.run_bot) llama a "
                 "execute_rag_turn directo y NO atraviesa la ruta `mismatch` de turn_plan/telegram_bot ⇒ este gold mide si "
                 "el GENERADOR nombra a Securiton, no la conducta de serving; la corrección de marca en el bot se prueba con "
                 "smoke del bot real (DEC-224). match_fact con valor de 2 tokens ('Securiton AG') es proxy; el juez conveyed "
                 "es quien acredita. Ningún chunk del manual ASD535 menciona Detnov (barrido) ⇒ 'distribuido por Detnov' NO "
                 "es hecho del corpus y no se exige.")
    _add_verified_by(g, "GPT-5.5 en frío sobre render p1 (evals/s321_cross_verify_v1.txt): logo SECURITON, ASD 535, Securiton AG Zollikofen")
    _add_verified_by(g, f"Claude s321 lectura al píxel p1 + chunk p18 'Fabricante = Securiton' + {DUO}")
    loc = p.setdefault("localizacion", {})
    loc["manuales_buscados"] = sorted(set(loc.get("manuales_buscados", []) + ["ASD535_TD_T131192es_h"]))
    loc["terminos"] = sorted(set(loc.get("terminos", []) + ["Securiton", "Detnov", "fabricante", "manufacturer"]))
    return g


# ─────────────────────────────────────────────────────────────────────────────
# Ítem 9 · hp021 — alta
# ─────────────────────────────────────────────────────────────────────────────
def build_hp021() -> dict:
    return {
        "qid": "hp021",
        "question": "¿Cómo se accede al menú de configuración avanzada en la Detnov CAD-171?",
        "conducta_esperada": "answer",
        "split": "dev",
        "estrato": ["sintesis-completitud"],
        "gold_answer": (
            "En la Detnov CAD-171 el menu de configuracion avanzada esta en AJUSTES (Menu principal) > AVANZADO "
            "(Submenu). Para llegar hay que entrar como administrador: desde la PANTALLA DE REPOSO tocar el icono "
            "del candado, que abre la PANTALLA DE ACCESO, e introducir la clave de administrador (por defecto 2222). "
            "El manual de la CAD-171 (MI-716) remite a la Guia Avanzada de Configuracion para el detalle de "
            "configuracion; el uso indebido del nivel de administrador puede provocar un mal funcionamiento de la "
            "instalacion."
        ),
        "atomic_facts": [
            {"texto": "La ruta al menu de configuracion avanzada es AJUSTES (Menu principal) > AVANZADO (Submenu)",
             "tipo": "core", "estado": "presente", "valor": "AJUSTES > AVANZADO",
             "cita": "MI-716 p27 (§6.3, diagrama de navegacion: AJUSTES resaltado en Menu principal; columna Submenu GENERAL·VERSIONES·USUARIOS·AVANZADO·CONECTIVIDAD·IMPRESORA·LOGS·TEST·INICIO) + p34/p35"},
            {"texto": ("El acceso esta protegido: tocar el icono del candado en la PANTALLA DE REPOSO abre la PANTALLA "
                       "DE ACCESO, e introducir la clave de administrador por defecto 2222"),
             "tipo": "core", "estado": "presente", "valor": "candado + 2222",
             "cita": "MI-716 p25 §6.1 'Acceso como administrador' ('Introduzca la clave de administrador por defecto, 2222.')"},
            {"texto": "El MI-716 remite a la Guia Avanzada de Configuracion para el detalle de utilizacion y configuracion",
             "tipo": "supplementary", "estado": "presente", "valor": "Guia Avanzada",
             "cita": "MI-716 p25 ('Si desea informacion detallada de utilizacion y configuracion de la central consulte la Guia Avanzada de Configuracion')"},
            {"texto": ("AVISO de seguridad (recuadro rojo): el uso indebido o negligente del nivel de acceso con privilegios "
                       "de ADMINISTRADOR puede provocar un mal funcionamiento de la instalacion"),
             "tipo": "supplementary", "estado": "presente", "valor": None,
             "cita": "MI-716 p25 (recuadro de advertencia — capa visual, TECH_DEBT #83)"},
        ],
        "citations": [
            {"manual": "Manual_CAD-171-MI-716-es.pdf", "page": 25,
             "quote": "Toque la pantalla táctil con el dedo sobre la figura del candado (🔒). Al hacerlo accederá a la PANTALLA DE ACCESO solicitando el código de acceso o password."},
            {"manual": "Manual_CAD-171-MI-716-es.pdf", "page": 25,
             "quote": "Introduzca la clave de administrador por defecto, 2222."},
            {"manual": "Manual_CAD-171-MI-716-es.pdf", "page": 27,
             "quote": "6.3. Configuración … Menú principal: LAZO · SECTORIZACIÓN · MANIOBRAS · LOGS · RED · AJUSTES (resaltado) · INSTALACIÓN · MAPAS → Submenú: GENERAL · VERSIONES · USUARIOS · AVANZADO · CONECTIVIDAD · IMPRESORA · LOGS · TEST · INICIO"},
            {"manual": "Manual_CAD-171-MI-716-es.pdf", "page": 25,
             "quote": "Si desea información detallada de utilización y configuración de la central consulte la Guía Avanzada de Configuración."},
            {"manual": "Manual_CAD-171-MI-716-es.pdf", "page": 25,
             "quote": "El uso indebido o negligente del nivel de acceso con PRIVILEGIOS DE ADMINISTRADOR pueden provocar un mal funcionamiento de la instalación que puede provocar la pérdida de vidas humanas."},
        ],
        "notes": ("La equivalencia 'Guia Avanzada de Configuracion' = MC-380 NO la dice el MI-716 por su nombre: se ancla en "
                  "el catálogo (doc_map: CAD-250_Manual-Configuracion-MC-380 es primary de detnov:cad-171) y en que el "
                  "MC-380 documenta el submenu AVANZADO (8 páginas) y el mismo acceso candado→2222 (p18). Va aqui como "
                  "nota, no como hecho."),
        "confidence": "alta",
        "pdfs_used": ["Manual_CAD-171-MI-716-es.pdf"],
        "_provenance": {
            "estado": "verificado",
            "metodo": "render_pdf (160dpi, ±1) + cross_model (GPT-5.5 en frío) + corpus_check (chunks_v2, aplicabilidad por doc_map) + no-duplicado ejecutado",
            "fuente": "Manual_CAD-171-MI-716-es.pdf (manual de la CAD-171)",
            "paginas": [25, 27, 34, 35],
            "verificado_por": [
                "Claude s321 lectura al píxel p25 (§6.1 candado/2222/Guía Avanzada/aviso rojo) y p27 (§6.3 diagrama con AVANZADO en Submenú); ±1: p24/p26 (p26 = §6.2 SIN 'AVANZADO' — el chunk 'p26' del corpus mezclaba las páginas físicas 26 y 27)",
                "GPT-5.5 en frío sobre render p25/p26/p27 (evals/s321_cross_verify_v1.txt): 'Introduzca la clave de administrador por defecto, 2222'; Submenú GENERAL…AVANZADO…INICIO en p27; p26 sin AVANZADO — MISMO off-by-one cazado por ambos modelos",
                DUO,
            ],
            "acuerdo": ("total: ruta AJUSTES > AVANZADO en el diagrama de p27 (cita de DIAGRAMA, no de prosa — por eso ningún "
                        "barrido por cabeceras la encontraba); acceso p25 literal '2222'; Guía Avanzada p25 literal; aviso rojo p25"),
            "fecha": HOY,
            "nota": ("OFF-BY-ONE cazado por el render ±1 (RULER_DESIGN §2 paso 3): el chunk 'p26' de chunks_v2 contiene el "
                     "diagrama que físicamente está en la p27 (PDF apaisado, dos páginas impresas por hoja: 26|27). Cita = p27. "
                     "NO-DUPLICADO (DEC-025): hp001 = menú avanzado de la CAD-250 (MC-380 compartido); ho008 = puntos/zonas de la "
                     "CAD-171; ninguno cubre la RUTA de la CAD-171 con su manual propio. Génesis: incidente DEC-185 (bot encabezó "
                     "AJUSTES>GENERAL con AVANZADO servido); el gold se ancla en MI-716, no en el fallo. Estrato = "
                     "sintesis-completitud (fusiona p25 acceso + p27 ruta del mismo manual; mismo estrato que ho008); NO "
                     "familia-ambigua (la pregunta identifica CAD-171 sin ambigüedad — Sol v3). Acceso como UN core (adjudicación "
                     "Alberto s321), no dos como hp001. Staleness: la conducta congelada era de sonnet-4-6; si con Opus 5 no se "
                     "reproduce, nace como centinela anti-regresión."),
            "localizacion": {
                "manuales_buscados": ["Manual_CAD-171-MI-716-es", "Datasheet_CAD-171-DS-736-es", "Datasheet-CAD-171-DS-737-en",
                                      "CAD-250_Manual-Configuracion-MC-380-es-2026-c", "CAD-250_Manual-software-configuracion-MS-416-es-2026-b"],
                "terminos": ["AVANZADO", "ADVANCED", "2222", "candado", "padlock", "administrador", "administrator", "Guía Avanzada"],
                "paginas": [25, 27, 34, 35],
                "nota": (f"{LOCAL}. MI-716: AVANZADO p26(chunk)/34/35, 2222+candado p25. MC-380 (primary de cad-171 en doc_map): "
                         "AVANZADO en 8 pp, candado+2222 p18 (mismo procedimiento). DS-737-en: 'Advanced' solo como marketing "
                         "('advanced features'), no la ruta ⇒ sin conflicto ES/EN. DS-736-es sin match. Ausencia 'MI-716 no "
                         "documenta AVANZADO' NO se afirma como hecho (exigiría render de las 48 pp)."),
            },
        },
    }


def main() -> int:
    aplicar = "--aplicar" in sys.argv
    actuales = {g["qid"]: g for g in GS.load()}
    nuevos = {
        "hp017": build_hp017(actuales["hp017"]),
        "cat018": build_cat018(actuales["cat018"]),
        "hp006": build_hp006(actuales["hp006"]),
        "cat020": build_cat020(actuales["cat020"]),
        "hp002": build_hp002(actuales["hp002"]),
        "hp021": build_hp021(),
    }
    errores = 0
    for qid, g in nuevos.items():
        issues = GS.validate_entry(g)
        errs = [i for i in issues if i.severity == "error"]
        warns = [i for i in issues if i.severity == "warning"]
        errores += len(errs)
        cores_antes = sum(1 for f in (actuales.get(qid, {}).get("atomic_facts") or []) if f.get("tipo") == "core")
        cores_desp = sum(1 for f in g["atomic_facts"] if f.get("tipo") == "core")
        print(f"[{qid}] cores {cores_antes}→{cores_desp} · facts {len(actuales.get(qid, {}).get('atomic_facts') or [])}→{len(g['atomic_facts'])} · errores={len(errs)} warnings={len(warns)}")
        for i in errs:
            print(f"    ERROR   {i.msg}")
        for i in warns:
            print(f"    warning {i.msg}")
    if errores:
        print(f"\n✗ {errores} error(es): NO se escribe nada (falla-cerrado)")
        return 2
    if not aplicar:
        print("\n(dry-run) 0 errores. Pasa --aplicar para escribir.")
        return 0
    for qid, g in nuevos.items():
        GS.upsert(g)
        print(f"  upsert {qid} ✓")
    post = GS.validate()
    errs = [i for i in post if i.severity == "error"]
    print(f"\nvalidate() global tras escribir: {len(errs)} errores")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
