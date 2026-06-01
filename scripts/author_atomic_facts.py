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

# --- hp008: Notifier ID3000 — detectores de humo analogicos compatibles. Conducta=answer.
# VERIFICADO s33 (Fase 1): Apendice 3 "Equipos de lazo compatibles" (fisica p71 = impresa A3-2),
# digital-native, leida por Claude (multimodal + zoom clip) + gpt-5.5 (cross_verify, en frio). El
# cross-model cazo un misread mio: la etiqueta "Termico temp.alta-Tipo BS" es de k.FDX-551HTEM,
# no de g.SDX-551THE. Los FDX-551* (termicos) NO son de humo -> excluidos. CLIP y 99+99 en p69/p24.
HP008_FACTS = [
    {
        "texto": "Sensores ionicos de humo compatibles: CPX-551E (ION) y CPX-751E (ION, bajo perfil)",
        "tipo": "core", "estado": "presente", "valor": "CPX-551E", "cita": "p71 (A3-2)",
    },
    {
        "texto": "Sensores opticos de humo compatibles: SDX551E, SDX-751 y SDX-751EM (OPT)",
        "tipo": "core", "estado": "presente", "valor": "SDX-751", "cita": "p71 (A3-2)",
    },
    {
        "texto": ("Sensores multicriterio compatibles: IRX-751CTEM (SMART 4) e IRX-751TEM (SMART 3)"),
        "tipo": "core", "estado": "presente", "valor": "IRX-751CTEM", "cita": "p71 (A3-2)",
    },
    {
        "texto": "Sensor multicriterio optico-termico SDX-751-TEM (OptiPlex)",
        "tipo": "core", "estado": "presente", "valor": "SDX-751-TEM", "cita": "p71 (A3-2)",
    },
    {
        "texto": "Sensor de humo para ambientes hostiles HPX-751E (HARSH)",
        "tipo": "supplementary", "estado": "presente", "valor": "HPX-751E", "cita": "p71 (A3-2)",
    },
    {
        "texto": ("Sensor de humo para atmosferas peligrosas IDX-751 (HAZARD, seguridad "
                  "intrinseca con barrera Y72221)"),
        "tipo": "supplementary", "estado": "presente", "valor": "IDX-751", "cita": "p71 (A3-2)",
    },
    {
        "texto": "Sensores de humo por aspiracion/laser (VIEW): LPX-751 y FSL-751E",
        "tipo": "supplementary", "estado": "presente", "valor": "LPX-751", "cita": "p71 (A3-2)",
    },
    {
        "texto": ("Detectores de humo por rayo (haz proyectado): LPB500 (maximo 4 por lazo) "
                  "y LPB-700/-700T"),
        "tipo": "supplementary", "estado": "presente", "valor": "LPB500", "cita": "p71 (A3-2)",
    },
    {
        "texto": "La comunicacion con los equipos del lazo usa el protocolo CLIP de Notifier",
        "tipo": "supplementary", "estado": "presente", "valor": "CLIP", "cita": "p69",
    },
    {
        "texto": "Capacidad por lazo analogico: hasta 198 equipos = 99 sensores + 99 modulos",
        "tipo": "supplementary", "estado": "presente", "valor": "99", "cita": "p69 / p24 (4.1)",
    },
]
HP008_PROV = {
    "estado": "verificado",
    "metodo": "render_pdf + cross_model",
    "fuente": "MIDT190.pdf",
    "paginas": [71, 69, 24],
    "verificado_por": [
        "Claude (lectura multimodal de la lista 'Equipos de lazo compatibles' A3-2 p71, + zoom clip)",
        "gpt-5.5 (transcripcion independiente en frio de p71, scripts/cross_verify_image.py)",
    ],
    "acuerdo": ("total en la lista de sensores de humo (CPX ionicos, SDX opticos, IRX multicriterio, "
                "SDX-751-TEM, HPX HARSH, IDX HAZARD, LPX/FSL VIEW, LPB rayo); el cross-model cazo un "
                "misread mio (la etiqueta 'Termico temp.alta-Tipo BS' es de k.FDX-551HTEM, no de "
                "g.SDX-551THE)"),
    "fecha": "2026-05-31",
    "nota": ("PDF digital-native (no OCR) -> lectura fiable. Los FDX-551* (j/k/l, TERMICOS) se excluyen "
             "correctamente (pregunta = humo). SDX-551THE aparece en 'Otros sensores' SIN etiqueta de "
             "tipo en A3-2; el gold la clasifica MULTI (defendible por base optica SDX, no contradicho) "
             "-> no se autora como hecho. Discrepancia trivial gold j.FDX-551REM vs fuente FDX-551EM "
             "(termico, irrelevante). 99+99 por lazo confirmado en p24/p67/p69; CLIP en p69."),
    "localizacion": {
        "manuales_buscados": ["MIDT190.pdf"],
        "terminos": ["CPX-551E", "IRX-751CTEM", "Equipos de lazo compatibles", "protocolo CLIP",
                     "99 sensores"],
        "paginas": [71, 69, 24],
        "nota": ("lista A3-2 en fisica p71; CLIP en p69; 99+99 en p24/p67/p69. Sin offset "
                 "(fisica = citada por el gold)."),
    },
}

# --- hp020: Notifier INSPIRE — cambiar las contrasenas de codigo de acceso NA2/NA3. answer.
# VERIFICADO s33 (Fase 1): HOP-138-8ES (puesta en marcha), procedimiento integro en pagina
# fisica 49 (= impresa 49, sin offset; indice en p2 lo confirma). PDF digital-native (texto
# embebido, no OCR), pagina apaisada. Claude (multimodal p49) + gpt-5.5 (cross_verify en frio):
# acuerdo total. Sin codigos por defecto de fabrica en el manual. Nota CLSS en p5/p18.
HP020_FACTS = [
    {
        "texto": ("Regla por nivel: en nivel de acceso 2 solo se puede cambiar el codigo de NA2; "
                  "en nivel de acceso 3 se puede cambiar el codigo de NA2 o de NA3"),
        "tipo": "core", "estado": "presente", "valor": "nivel 2 o 3", "cita": "p49",
    },
    {
        "texto": ('Ruta: icono de menu > "Ajustes", iniciar sesion como usuario de nivel de acceso 3, '
                  'y seleccionar la opcion "Cambio del codigo de acceso"'),
        "tipo": "core", "estado": "presente", "valor": "Cambio del codigo de acceso", "cita": "p49",
    },
    {
        "texto": "El nuevo codigo de acceso debe tener entre 4 y 8 caracteres/digitos",
        "tipo": "core", "estado": "presente", "valor": "4 y 8", "cita": "p49",
    },
    {
        "texto": ('Tras introducir el nuevo codigo hay que re-introducirlo para confirmar (repetir los '
                  'pasos 03 a 06); aparece el mensaje "Cambio de codigo de acceso satisfactorio"'),
        "tipo": "core", "estado": "presente", "valor": "satisfactorio", "cita": "p49",
    },
    {
        "texto": ("Tras el cambio: sincronizar el programa de configuracion CLSS con la central y hacer "
                  "una copia de seguridad del cambio en la nube"),
        "tipo": "supplementary", "estado": "presente", "valor": "copia de seguridad", "cita": "p49",
    },
    {
        "texto": ("El portal CLSS Cloud, la app CLSS y el programa de configuracion CLSS comparten el "
                  "mismo usuario, codigo de acceso y contrasena"),
        "tipo": "supplementary", "estado": "presente", "valor": "CLSS", "cita": "p5 / p18",
    },
]
HP020_PROV = {
    "estado": "verificado",
    "metodo": "render_pdf + cross_model",
    "fuente": "HOP-138-8ES  issue 6_01-2026_Co.pdf",
    "paginas": [49, 5],
    "verificado_por": [
        "Claude (lectura multimodal de la p49 renderizada)",
        "gpt-5.5 (transcripcion independiente en frio de p49, scripts/cross_verify_image.py)",
    ],
    "acuerdo": ("total: regla por nivel (NA2 solo NA2; NA3 cambia NA2 o NA3), pasos 01-09, longitud "
                "4-8 caracteres, mensaje 'Cambio de codigo de acceso satisfactorio', sincronizar + "
                "backup en la nube; el cross-model transcribio identico a la lectura"),
    "fecha": "2026-05-31",
    "nota": ("PDF digital-native (texto embebido, no OCR) y pagina apaisada -> lectura fiable; el texto "
             "extraido PyMuPDF coincide con el render. El manual NO da codigos por defecto de fabrica "
             "(el gold no los afirma). Credenciales CLSS compartidas (portal/app/programa) en p5/p18."),
    "localizacion": {
        "manuales_buscados": ["HOP-138-8ES  issue 6_01-2026_Co.pdf"],
        "terminos": ["codigo de acceso", "nivel de acceso 2/3", "entre 4 y 8", "Cambio del codigo"],
        "paginas": [49, 5],
        "nota": ("impresa 49 = fisica 49 (sin offset; indice en p2 lo confirma). Procedimiento integro "
                 "en p49; nota CLSS en p5/p18."),
    },
}

# --- hp001: Detnov CAD-250 — entrar al menu de programacion avanzada (admin). answer.
# VERIFICADO s33 (Fase 1): Guia de Configuracion MC-380 (digital-native, sin offset: impresa=
# fisica 20/21). Claude (multimodal p20 acceso + p21 tabla 6 secciones) + gpt-5.5 (cross_verify
# de la tabla de 6 secciones): acuerdo total. Claves 1111 (usuario) y 2222 (admin) corroboradas
# en los otros 2 manuales (MU-376 p10, MI-372). "Programacion avanzada" = nivel de admin (3.2).
HP001_FACTS = [
    {
        "texto": ("Desde la PANTALLA DE REPOSO, tocar con el dedo el icono del candado en la pantalla "
                  "tactil -> accede a la PANTALLA DE ACCESO, que pide el codigo/password"),
        "tipo": "core", "estado": "presente", "valor": "candado", "cita": "MC-380 p20 (4.1)",
    },
    {
        "texto": ("Introducir la clave de ADMINISTRADOR por defecto 2222 -> da acceso al nivel de "
                  "configuracion/administrador (donde se configuran todos los parametros)"),
        "tipo": "core", "estado": "presente", "valor": "2222", "cita": "MC-380 p20 + MI-372",
    },
    {
        "texto": ("La clave de USUARIO por defecto es 1111, que NO da acceso a la configuracion "
                  "avanzada completa (solo el nivel de usuario)"),
        "tipo": "core", "estado": "presente", "valor": "1111", "cita": "MU-376 p10",
    },
    {
        "texto": ("Con la clave correcta se accede a la PANTALLA DE ADMINISTRADOR, dividida en 6 "
                  "secciones: Menu Principal (izq), Submenu (der), Barra de Navegacion, Vista "
                  "Principal, Barra de Estado y Barra de Mensajes"),
        "tipo": "supplementary", "estado": "presente", "valor": "PANTALLA DE ADMINISTRADOR",
        "cita": "MC-380 p21 (4.2)",
    },
    {
        "texto": ("Desde el MENU PRINCIPAL se accede a: Lazos, Sectorizacion, Maniobras, Logs, Red, "
                  "Ajustes e Instalacion"),
        "tipo": "supplementary", "estado": "presente", "valor": "Sectorizacion", "cita": "MC-380 p21",
    },
    {
        "texto": ("AVISO de seguridad: el uso indebido del nivel de administrador puede provocar mal "
                  "funcionamiento; se recomienda cambiar la clave por defecto desde Ajustes > Usuarios"),
        "tipo": "supplementary", "estado": "presente", "valor": None, "cita": "MC-380 p20",
    },
]
HP001_PROV = {
    "estado": "verificado",
    "metodo": "render_pdf + cross_model",
    "fuente": "CAD-250-MC-380-es.pdf (Guia de Configuracion)",
    "paginas": [20, 21],
    "verificado_por": [
        "Claude (lectura multimodal de p20 'Acceso como administrador' + p21 tabla de 6 secciones)",
        "gpt-5.5 (transcripcion independiente en frio de la tabla de 6 secciones p21)",
    ],
    "acuerdo": ("total: candado -> PANTALLA DE ACCESO -> clave admin 2222; PANTALLA DE ADMINISTRADOR "
                "dividida en 6 secciones identicas (Menu Principal/Submenu/Barra Navegacion/Vista "
                "Principal/Barra Estado/Barra Mensajes); claves 1111 (usuario) y 2222 (instalacion) "
                "corroboradas en los otros 2 manuales"),
    "fecha": "2026-05-31",
    "nota": ("3 manuales digital-native -> lectura fiable. MC-380 sin offset (impresa=fisica 20/21). "
             "MI-372: el 2222 esta en fisica p29 (el gold lo citaba como p31 -> offset impresa+2 o "
             "numeracion del gold; el DATO es correcto). El gold_answer menciona un 'nivel 4' (apertura "
             "fisica PC/Pendrive/TOTEM) que NO se verifico aqui (fuera de p20-21) -> no autorado."),
    "localizacion": {
        "manuales_buscados": ["CAD-250-MC-380-es.pdf",
                              "Manual instalacion CAD-250 (MI_372_es_2024 e).pdf",
                              "Manual usuario CAD-250 (MU 376 es 2024 f).pdf"],
        "terminos": ["candado", "2222", "1111", "PANTALLA DE ADMINISTRADOR", "varias secciones",
                     "nivel de configuracion"],
        "paginas": [20, 21],
        "nota": ("MC-380 sin offset (impresa=fisica 20/21). 2222 admin tambien en MI-372 fisica p29 "
                 "(gold citaba p31); 1111 usuario en MU-376 fisica p10."),
    },
}

# --- hp005: Notifier ID3000 — programar zona para activar sirena con coincidencia de 2 detectores.
# answer. VERIFICADO s33 (Fase 1): MPDT190 (Manual de programacion del panel) — OFFSET +7 (impresa =
# fisica - 7), confirmado por footer "MP-DT-190_D 66"/"108" en f73/f115. El gold cito paginas IMPRESAS
# correctas (66/70/108). Claude (multimodal f73 coincidencia+PUL + f115 niveles) + gpt-5.5 (cross_verify
# de f73): acuerdo total. La regla EN54-2 7.1.4 (no-PUL + 2 instrucciones) SI esta en MPDT190 f73 ademas
# de en MCDT191. Camino software PK-ID3000 (MCDT191) corroborado por texto extraido.
HP005_FACTS = [
    {
        "texto": ("La coincidencia se configura creando una instruccion en la MATRIZ DE CONTROL con la "
                  "definicion de ENTRADA = ALARMA, sobre la zona deseada"),
        "tipo": "core", "estado": "presente", "valor": "Matriz de control", "cita": "MPDT190 p66 (f73)",
    },
    {
        "texto": ('En el menu "Indique tipo de coincidencia" seleccionar la opcion 2: COINCIDENCIA 2 '
                  "EQUIPOS"),
        "tipo": "core", "estado": "presente", "valor": "COINCIDENCIA 2 EQUIPOS", "cita": "MPDT190 p66 (f73)",
    },
    {
        "texto": ("Para que se produzca la coincidencia, los equipos en alarma deben estar en la misma "
                  "zona o subzona"),
        "tipo": "core", "estado": "presente", "valor": "misma zona o subzona", "cita": "MPDT190 p66 (f73)",
    },
    {
        "texto": ('Definir la SALIDA: "Salidas activadas" -> "CIRCUITO SIRENA/RELE" (un circuito de '
                  'sirena concreto) o "TODAS SALIDAS: Subzona/Zona/Central" limitando por tipo a los '
                  "modulos de sirena"),
        "tipo": "core", "estado": "presente", "valor": "CIRCUITO SIRENA", "cita": "MPDT190 p70 (f77)",
    },
    {
        "texto": ("Requisito EN54-2 7.1.4: NO incluir pulsadores manuales (PUL) en el grupo de "
                  "coincidencia; si se quieren incluir, usar dos instrucciones separadas (PUL como "
                  "UN UNICO EQUIPO sin coincidencia + sensores con coincidencia)"),
        "tipo": "supplementary", "estado": "presente", "valor": "7.1.4", "cita": "MPDT190 p66 (f73)",
    },
    {
        "texto": ("Niveles de coincidencia para EQUIPOS: Nivel 1 = 1 y Nivel 2 = 2 son FIJOS (no se "
                  "configuran); otros niveles (3-99) se definen en Coincidencia de alarma de la "
                  "Configuracion de la central"),
        "tipo": "supplementary", "estado": "presente", "valor": "Nivel 2 = 2", "cita": "MPDT190 p108 (f115)",
    },
    {
        "texto": ("Con el programa PK-ID3000 (Windows), el equivalente se hace en la ventana 'Editar "
                  "Matriz de Control' marcando la casilla de coincidencia y seleccionando 2 equipos"),
        "tipo": "supplementary", "estado": "presente", "valor": "PK-ID3000", "cita": "MCDT191 p75",
    },
]
HP005_PROV = {
    "estado": "verificado",
    "metodo": "render_pdf + cross_model",
    "fuente": "MPDT190.pdf (Manual de programacion del panel) + MCDT191.pdf (programa PK-ID3000)",
    "paginas": [73, 77, 115],
    "verificado_por": [
        "Claude (multimodal de f73 'tipo de coincidencia' + EN54-2 7.1.4 + f115 niveles)",
        "gpt-5.5 (transcripcion independiente en frio de f73, scripts/cross_verify_image.py)",
    ],
    "acuerdo": ("total: opcion 2 COINCIDENCIA 2 EQUIPOS, equipos en misma zona/subzona, EN54-2 7.1.4 "
                "no-PUL + 2 instrucciones (i UN UNICO EQUIPO sin coincidencia / ii sensores con "
                "coincidencia), niveles 1=1 y 2=2 fijos; salida CIRCUITO SIRENA/TODAS SALIDAS en f77"),
    "fecha": "2026-05-31",
    "nota": ("MPDT190 OFFSET +7 (impresa = fisica - 7), CONFIRMADO por footer 'MP-DT-190_D 66'/'108' en "
             "f73/f115. El gold cito paginas IMPRESAS correctas (66/70/108) -> no era mis-atribucion. "
             "PDF digital-native (capturas de panel legibles). La regla PUL/2-instrucciones SI esta en "
             "MPDT190 f73 (impresa 66), ademas de en MCDT191. Camino software PK-ID3000 corroborado por "
             "texto extraido de MCDT191 (casilla de coincidencia + 2 equipos)."),
    "localizacion": {
        "manuales_buscados": ["MPDT190.pdf", "MCDT191.pdf"],
        "terminos": ["COINCIDENCIA 2 EQUIPOS", "Indique tipo de coincidencia", "EN54-2 7.1.4",
                     "Niveles COINCIDENCIA en ALARMA", "CIRCUITO SIRENA"],
        "paginas": [73, 77, 115],
        "nota": ("MPDT190 impresas 66/70/108 = fisicas 73/77/115 (offset +7, footer confirma). MCDT191 "
                 "(software) impresa ~75; offset MCDT191 +6 (footer 'MC-DT-191_F ... 40' en f46)."),
    },
}

# --- hp010: Morley DXc — anadir un detector nuevo al lazo tras la puesta en marcha. answer.
# VERIFICADO s33 (Fase 1): DXc_Manual de configuracion.pdf §5.3.5.2 "Autobusqueda de equipos"
# (fisica p48-49, SIN offset: f49 muestra "- PAGINA 49 -"). Digital-native. Claude (multimodal
# p48-49) + gpt-5.5 (cross_verify del resumen p49): acuerdo en el procedimiento (discrepancia
# trivial en los numeros de EJEMPLO de la pantalla, irrelevante). EQUIPO NUEVO en config f89 +
# doc Eventos-Averias p1. 2 copias identicas del PDF (Manuales_Morley / _Privado).
HP010_FACTS = [
    {
        "texto": ("Para anadir un equipo nuevo al lazo tras la puesta en marcha se ejecuta una "
                  "AUTOBUSQUEDA de equipos (la central detecta automaticamente los equipos del lazo; "
                  "no se anaden de uno en uno manualmente)"),
        "tipo": "core", "estado": "presente", "valor": "Autobusqueda", "cita": "DXc-config p48 (5.3.5.2)",
    },
    {
        "texto": ("Procedimiento: acceder al Nivel 3 (clave de acceso) y desbloquear la memoria; en el "
                  "menu de Lazos pulsar la tecla '2' para 'Autobusqueda', seleccionar el numero de lazo "
                  "y confirmar la autobusqueda de todos los equipos del lazo"),
        "tipo": "core", "estado": "presente", "valor": "Nivel 3", "cita": "DXc-config p48 + p29/p37",
    },
    {
        "texto": ("Al finalizar, la central muestra un RESUMEN con los equipos nuevos, eliminados y "
                  "modificados, y el total por tipo; comprobar que coincide con los equipos instalados"),
        "tipo": "core", "estado": "presente", "valor": "nuevos, eliminados y modificados",
        "cita": "DXc-config p49",
    },
    {
        "texto": ("Si se ha realizado un cambio de protocolo, ESPERAR dos minutos antes de la "
                  "autobusqueda (la central necesita tiempo para rearmar los equipos del lazo)"),
        "tipo": "supplementary", "estado": "presente", "valor": "dos minutos", "cita": "DXc-config p48",
    },
    {
        "texto": ('Si la central indica el evento "EQUIPO NUEVO" (equipo detectado en el lazo pero no '
                  "aceptado), la solucion es ejecutar la autobusqueda para aceptarlo"),
        "tipo": "supplementary", "estado": "presente", "valor": "EQUIPO NUEVO",
        "cita": "Eventos-Averias p1 / DXc-config p89",
    },
    {
        "texto": ("Tras la autobusqueda se pueden editar las propiedades del nuevo equipo (texto "
                  "descriptivo, zona asignada, grupo de anulacion, accion) mediante 'Editar Equipos'"),
        "tipo": "supplementary", "estado": "presente", "valor": "Editar Equipos", "cita": "DXc-config p41 (5.3.5.1)",
    },
]
HP010_PROV = {
    "estado": "verificado",
    "metodo": "render_pdf + cross_model",
    "fuente": "DXc_Manual de configuracion.pdf + Eventos-Averias-de-Equipos-en-DXc.pdf",
    "paginas": [48, 49],
    "verificado_por": [
        "Claude (lectura multimodal de f48-49 'Autobusqueda de equipos')",
        "gpt-5.5 (transcripcion independiente en frio del resumen de autobusqueda f49)",
    ],
    "acuerdo": ("total en el procedimiento: autobusqueda via tecla '2' en menu de Lazos, seleccionar "
                "lazo y confirmar, resumen de nuevos/eliminados/modificados + total por tipo, ESPERE "
                "2 min tras cambio de protocolo; discrepancia trivial solo en los numeros de EJEMPLO "
                "de la pantalla (linea de tipos: 'TMP:2' vs 'TMP:1 MLT:2') -> irrelevante (ilustrativos)"),
    "fecha": "2026-05-31",
    "nota": ("DXc_Manual de configuracion digital-native, SIN offset (f49 muestra '- PAGINA 49 -'); el "
             "gold cito p48-49 correctamente. 'EQUIPO NUEVO -> autobusqueda para aceptar' confirmado en "
             "config f89 y en el doc Eventos-Averias (gold lo cita de Eventos p1). 2 copias identicas del "
             "PDF (Manuales_Morley / _Privado); usada Manuales_Morley."),
    "localizacion": {
        "manuales_buscados": ["DXc_Manual de configuracion.pdf", "Eventos-Averias-de-Equipos-en-DXc.pdf"],
        "terminos": ["Autobusqueda", "ESPERE dos minutos", "cambio de protocolo", "EQUIPO NUEVO",
                     "Nivel 3"],
        "paginas": [48, 49],
        "nota": "sin offset (f48-49 = impresas 48-49); EQUIPO NUEVO en config f89 + Eventos p1.",
    },
}

# --- hp014: Notifier ID2000 — conectar un modulo de aislamiento de linea en el lazo. answer.
# VERIFICADO s33 (Fase 1): MIDT180 (Manual de instalacion ID2000) — OFFSET +4 (impresa = fisica - 4),
# confirmado por footer "MI-DT-180 16"/"42" en f20/f46. El gold cito paginas IMPRESAS correctas
# (16/42/14) + apendice A3-1/A3-4 = fisicas f70/f73. Claude (multimodal f20 reglas + f46 terminales)
# + gpt-5.5 (cross_verify f20): acuerdo total. El manual NO da el esquema terminal-a-terminal del
# modulo (remite a las instrucciones del equipo) -> answer parcial-por-diseno (gold confidence media).
HP014_FACTS = [
    {
        "texto": ("Los aisladores se instalan en CADA lazo analogico para separar sensores y "
                  "pulsadores; maximo 32 equipos de lazo entre aisladores (EN54-2), pero en la ID2000 "
                  "no mas de 25 equipos entre aisladores (20 si son aisladores tipo FET, p.ej. B524IEFT)"),
        "tipo": "core", "estado": "presente", "valor": "25", "cita": "p16 (f20) 4.1.2",
    },
    {
        "texto": ("Las comprobaciones de continuidad del lazo deben realizarse ANTES de conectar los "
                  "aisladores (usar multimetro de baja tension, nunca de alta tension tipo 'Megger')"),
        "tipo": "core", "estado": "presente", "valor": "continuidad", "cita": "p16 (f20) 4.2",
    },
    {
        "texto": ("Para las pruebas, desconectar temporalmente los aisladores cortocircuitando los "
                  "terminales 2 y 4 de cada aislador; tras verificar polaridad/continuidad, RETIRAR las "
                  "conexiones temporales antes de conectar el lazo al panel (extremos A y B)"),
        "tipo": "core", "estado": "presente", "valor": "terminales 2 y 4", "cita": "p42 (f46) 8.4.2/8.4.3",
    },
    {
        "texto": ("La pantalla del cable debe ser continua y conectarse a tierra SOLO en el panel; la "
                  "resistencia maxima del lazo no debe superar 35 ohmios (uniendo B+/B- y midiendo en A+/A-)"),
        "tipo": "core", "estado": "presente", "valor": "35", "cita": "p14 (f18)",
    },
    {
        "texto": ("Para asegurar que los aisladores se cierran al alimentar, maximo 25 unidades de inicio "
                  "(SU) entre aisladores estandar (20 entre aisladores FET)"),
        "tipo": "supplementary", "estado": "presente", "valor": "unidades de inicio", "cita": "A3-1 (f70)",
    },
    {
        "texto": ("Resistencia anadida al lazo por cada aislador: FET B524IEFT = 0,29 ohm (Rf = Nf x 0,29); "
                  "otros aisladores B524IE / ISO-X = 0,1 ohm (Ri = Ni x 0,1)"),
        "tipo": "supplementary", "estado": "presente", "valor": "0,29", "cita": "A3-4 (f73)",
    },
    {
        "texto": ("El manual NO incluye el esquema de conexion terminal-a-terminal del modulo aislador: "
                  "remite a las instrucciones que acompanan a cada equipo para las interconexiones"),
        "tipo": "supplementary", "estado": "presente", "valor": None, "cita": "p16 (f20) cap.4",
    },
]
HP014_PROV = {
    "estado": "verificado",
    "metodo": "render_pdf + cross_model",
    "fuente": "MIDT180.pdf (Manual de instalacion y puesta en marcha ID2000)",
    "paginas": [20, 46, 18, 70, 73],
    "verificado_por": [
        "Claude (multimodal de f20 '4.1.2 aisladores' + f46 'terminales 2 y 4')",
        "gpt-5.5 (transcripcion independiente en frio de f20, scripts/cross_verify_image.py)",
    ],
    "acuerdo": ("total: aisladores en cada lazo, max 32 equipos / 25 en ID2000 / 20 FET, continuidad "
                "ANTES de conectar, terminales 2 y 4 para desconexion temporal y retirar antes de "
                "conectar al panel, pantalla a tierra solo en panel + 35 ohm; 25 SU y Rf=Nf*0,29 / "
                "Ri=Ni*0,1 confirmados en texto del apendice f70/f73"),
    "fecha": "2026-05-31",
    "nota": ("MIDT180 OFFSET +4 (impresa = fisica - 4): el nº de pagina impresa visible en el pie es 16 "
             "en f20 y 42 en f46 (el identificador 'MI-DT-180' y el numero aparecen en extremos opuestos "
             "del pie, NO contiguos en el texto extraido). El gold cito paginas IMPRESAS correctas "
             "(16/42/14) + apendice A3-1/A3-4 = fisicas f70/f73. Digital-native. El manual NO da el "
             "esquema terminal-a-terminal del modulo aislador (remite a las instrucciones del equipo) -> "
             "answer correctamente parcial (gold confidence media)."),
    "localizacion": {
        "manuales_buscados": ["MIDT180.pdf"],
        "terminos": ["aisladores se deben utilizar", "32 equipos de lazo", "terminales 2 y 4",
                     "unidades de inicio", "Rf = Nf x 0,29", "35 ohmios"],
        "paginas": [18, 20, 46, 70, 73],
        "nota": ("offset +4 (impresa = fisica - 4; el nº de pagina impresa en el pie lo confirma). "
                 "Apendice A3-x = fisica 69+x (A3-1 = f70, A3-4 = f73)."),
    },
}

# --- hp002: Securiton ASD 535 (Detnov OEM) — alarma intermitente de flujo bajo: causa + diagnostico.
# answer. VERIFICADO s33 (Fase 1): mismo PDF que hp019 (digital-native, SIN offset; footer "28/134" y
# "101/134" confirma fisica=impresa). Claude (multimodal p28 criterio + p101 lectura flujo cap 7.6.1) +
# gpt-5.5 (cross_verify de p28): transcripcion LITERAL identica. Sub-rangos del gold (sensibilidad
# +-1..70 %, retardo 2-60 min) NO re-renderizados aqui (cap 7.2.1) -> no autorados; +-20% y 300 s SI.
HP002_FACTS = [
    {
        "texto": ('El ASD 535 no da una "alarma de flujo bajo" como tal, sino un aviso "fallo flujo de '
                  'aire" cuando el flujo varia respecto al nominal (reset inicial con conducto limpio = '
                  "100 %) mas alla de la ventana de monitorizacion (por defecto +-20 %, EN 54-20)"),
        "tipo": "core", "estado": "presente", "valor": "fallo flujo de aire", "cita": "p28 (2.2.10)",
    },
    {
        "texto": ("Causa mas probable de flujo BAJO (por debajo del 80 % / valor < 100 %): obstruccion "
                  "del conducto de aspiracion (orificios sucios/obstruidos, filtro sucio, trampa de "
                  "polvo/separador); un valor por encima del 120 % (> 100 %) apunta a rotura de tubo/fugas"),
        "tipo": "core", "estado": "presente", "valor": "80 %", "cita": "p28 + p101 (7.6.1)",
    },
    {
        "texto": ("El aviso «fallo flujo de aire» se dispara una vez transcurrido el tiempo de retardo de "
                  "300 s de la LS-Ü (retardo ajustable que descarta turbulencias)"),
        "tipo": "core", "estado": "presente", "valor": "300 s", "cita": "p28 (2.2.10)",
    },
    {
        "texto": ("Diagnostico: leer el valor actual del flujo de aire (cap 7.6.1) -> posicion de "
                  "conmutador V, V01 (conducto I) y V02 (conducto II); interpretacion: valor < 100 % "
                  "apunta a obstruccion, > 100 % apunta a rotura de tubo"),
        "tipo": "core", "estado": "presente", "valor": "7.6.1", "cita": "p101 (7.6.1)",
    },
    {
        "texto": ("Tras solucionar la causa (limpiar conducto/filtro, reparar), ejecutar un nuevo RESET "
                  "INICIAL (cap 7.3.5) SOLO con el conducto de aspiracion limpio e intacto (si no, los "
                  "valores nominales quedarian mal y la alarma podria no dispararse)"),
        "tipo": "core", "estado": "presente", "valor": "reset inicial", "cita": "p32 (2.2.17.3) + cap 7.3.5",
    },
    {
        "texto": ("En entornos con grandes turbulencias de aire u oscilaciones termicas puede ser "
                  "necesario aumentar el tiempo de retardo o el tamano de la ventana; pero por encima de "
                  "+-20 % deja de cumplir EN 54-20 (consultar con el fabricante)"),
        "tipo": "supplementary", "estado": "presente", "valor": "turbulencias", "cita": "p28 + p58",
    },
]
HP002_PROV = {
    "estado": "verificado",
    "metodo": "render_pdf + cross_model",
    "fuente": "ASD535_TD_T131192es_h.pdf (Securiton; Detnov = marca OEM/distribuidor)",
    "paginas": [28, 101],
    "verificado_por": [
        "Claude (multimodal de p28 criterio 'fallo flujo de aire' + p101 lectura del flujo cap 7.6.1)",
        "gpt-5.5 (transcripcion independiente en frio de p28, scripts/cross_verify_image.py)",
    ],
    "acuerdo": ("total y LITERAL: ventana +-20 % sobre el nominal 100 %; por debajo del 80 % "
                "suciedad/obstruccion, por encima del 120 % rotura de tubo; retardo 300 s de la LS-Ü; "
                "lectura del flujo via conmutador V/V01/V02 con < 100 % obstruccion y > 100 % rotura; "
                "nuevo reset inicial (cap 7.3.5) solo con el conducto limpio"),
    "fecha": "2026-05-31",
    "nota": ("Mismo PDF que hp019: digital-native, SIN offset (footer 'ASD 535 ... 28/134' y '101/134' "
             "confirma fisica = impresa). El gold cito paginas correctas (p22/28/31/32/58/101). Los "
             "sub-rangos del gold_answer (sensibilidad LS-Ü +-1 a +-70 %, retardo 2 a 60 min) NO se "
             "re-renderizaron aqui (viven en cap 7.2.1) -> no autorados como hechos; +-20 % y 300 s SI "
             "verificados. Equipo = Securiton ASD 535 (Detnov OEM); el gold lo advierte correctamente."),
    "localizacion": {
        "manuales_buscados": ["ASD535_TD_T131192es_h.pdf"],
        "terminos": ["fallo flujo de aire", "20 %", "80 %", "120 %", "300 s", "7.6.1", "reset inicial"],
        "paginas": [28, 101],
        "nota": ("sin offset (footer confirma fisica = impresa). Criterio de fallo en p28 (2.2.10); "
                 "lectura del flujo y umbrales < 100 %/> 100 % en p101 (7.6.1)."),
    },
}

# --- hp004: Detnov DGD-600 (detector de gas) — tension de funcionamiento y consumo en reposo. clarify.
# VERIFICADO s33 (Fase 1 / Tier B): datasheet 55360004 (2 pags, ES/EN/FR/IT). Tabla "Especificaciones
# detector" con DOS columnas (24V / 220V) -> la pregunta no fija la version y los valores difieren ->
# clarify (D6, confianza media: candidatos acotados 24V/220V). Render p1 (Claude multimodal) + texto
# extraido identico en los 4 idiomas (corroboracion cruzada). Sin offset.
HP004_FACTS = [
    {
        "texto": ("El DGD-600 existe en DOS versiones de alimentacion (24V y 220V) con especificaciones "
                  "electricas distintas; la pregunta no indica cual -> ofrecer ambas y pedir aclaracion"),
        "tipo": "core", "estado": "presente", "valor": "24V y 220V", "cita": "p1 (Especificaciones detector)",
    },
    {
        "texto": ("Version 24V: tension de funcionamiento de 22V a 38V; consumo en reposo 45 mA "
                  "(consumo en alarma 65 mA)"),
        "tipo": "core", "estado": "presente", "valor": "22V a 38V", "cita": "p1",
    },
    {
        "texto": ("Version 220V: tension de funcionamiento de 180V a 240V; consumo en reposo 70 mA "
                  "(consumo en alarma 70 mA)"),
        "tipo": "core", "estado": "presente", "valor": "180V a 240V", "cita": "p1",
    },
]
HP004_PROV = {
    "estado": "verificado",
    "metodo": "render_pdf + extraccion multi-idioma",
    "fuente": "55360004 Manual Detector Gas DGD-600 ES EN IT FR.pdf",
    "paginas": [1],
    "verificado_por": [
        "Claude (lectura multimodal de la tabla 'Especificaciones detector' p1 renderizada)",
        "texto extraido identico en ES/EN/FR/IT (corroboracion cruzada de los valores)",
    ],
    "acuerdo": ("la tabla tiene dos columnas 24V/220V; 24V = 22-38V / 45 mA reposo; 220V = 180-240V / "
                "70 mA reposo; identico en los 4 idiomas"),
    "fecha": "2026-05-31",
    "nota": ("Datasheet digital-native (2 pags), tabla de dos columnas legible; sin offset. CONDUCTA "
             "clarify (migrada de ask_clarification): la pregunta no especifica la version y los valores "
             "difieren entre 24V y 220V -> D6 espectro de confianza media -> ofrecer ambos candidatos "
             "acotados (24V/220V) y pedir aclaracion. El gold ya surfacea ambos + pregunta."),
    "localizacion": {
        "manuales_buscados": ["55360004 Manual Detector Gas DGD-600 ES EN IT FR.pdf"],
        "terminos": ["Tension de funcionamiento", "Consumo en reposo", "24V", "220V", "45 mA", "70 mA"],
        "paginas": [1],
        "corpus_chunks_v2": "4 chunks del datasheet (servable)",
        "nota": "tabla de specs en p1 (sin offset, datasheet 2 pags).",
    },
}

# --- hp015: Detnov CCD-103 — desactivar un detector individual sin afectar al lazo. answer (corregida
# de admit). VERIFICADO s33 (Fase 1 / Tier B): la CCD-103 es una central CONVENCIONAL (f7 = impresa 5),
# por lo que NO existe direccionamiento/desactivacion individual de detectores; la desconexion es por
# ZONA (2 pulsaciones de la tecla de zona, f30 = impresa 28). Render f7 + f30 (Claude multimodal). El
# corpus SI cubre la respuesta correcta -> el bot debe RESPONDER corrigiendo la premisa, no admitir.
HP015_ANSWER = (
    "En la central Detnov CCD-103 NO es posible desactivar un detector de forma individual: al ser una "
    "central CONVENCIONAL (3 zonas de deteccion + 1 de extincion), no direcciona los detectores uno a uno. "
    "La desconexion/anulacion se realiza por ZONA completa: con la llave en posicion ON, pulsando 2 veces "
    "la tecla de la zona correspondiente, la zona queda desconectada (se enciende el indicador 'Anular' y "
    "el LED de fallo/anular/prueba de esa zona). Al desconectar la zona se anulan TODOS sus detectores "
    "(maximo 32 por zona), no uno solo.\n\n"
    "Si necesita actuar sobre un detector concreto, debe hacerse en la instalacion a traves del "
    "instalador/servicio tecnico; tenga en cuenta que cada zona se supervisa con una resistencia de fin de "
    "linea de 4K7, por lo que cualquier intervencion fisica en la zona afecta a esa supervision. El manual "
    "de la CCD-103 no contempla la desactivacion individual de detectores desde la central."
)
HP015_FACTS = [
    {
        "texto": ("La CCD-103 es una central CONVENCIONAL (3 zonas de deteccion + 1 de extincion); no "
                  "direcciona equipos individualmente, por lo que NO existe desactivar un detector "
                  "concreto desde la central"),
        "tipo": "core", "estado": "presente", "valor": "convencional", "cita": "p5 (f7) 1.1",
    },
    {
        "texto": ("La desconexion se hace por ZONA completa: con la llave en posicion ON, pulsar 2 veces "
                  "la tecla de la zona -> 'Zona desconectada' (se enciende el indicador Anular y el LED de "
                  "fallo/anular/prueba de esa zona)"),
        "tipo": "core", "estado": "presente", "valor": "2 veces la tecla de zona", "cita": "p28 (f30) 6.4.4",
    },
    {
        "texto": ("Cada zona admite como maximo 32 detectores/pulsadores; al desconectar la zona se "
                  "desactivan TODOS sus detectores (no se puede aislar uno solo desde la central)"),
        "tipo": "core", "estado": "presente", "valor": "32", "cita": "p13 (f15)",
    },
    {
        "texto": ("El manual no contempla desactivar un detector individual desde la central; cualquier "
                  "actuacion sobre un detector concreto se hace en la instalacion (via instalador) y afecta "
                  "a la supervision de la zona, que usa una resistencia de fin de linea de 4K7"),
        "tipo": "supplementary", "estado": "presente", "valor": "4K7", "cita": "p13-14 (f15-16)",
    },
    {
        "texto": ("En modo desconexion la central no refleja eventos de la zona anulada -> conviene "
                  "limitar el uso de esta maniobra"),
        "tipo": "supplementary", "estado": "presente", "valor": "modo desconexion", "cita": "p28 (f30)",
    },
]
HP015_PROV = {
    "estado": "verificado",
    "metodo": "render_pdf",
    "fuente": "CCD-103_Manual_ES_FR_GB_IT.pdf",
    "paginas_impresas": [5, 13, 28],
    "paginas_fisicas": [7, 15, 30],
    "verificado_por": [
        "Claude (lectura multimodal de f7 'central convencional de 3 zonas' + f30 'desconexion por zona, "
        "2 pulsaciones de la tecla de zona')",
    ],
    "acuerdo": ("render confirma: central CONVENCIONAL (f7); desconexion por ZONA via 2 pulsaciones de la "
                "tecla de zona (f30); 4K7 EOL por zona/salidas (f15-16/f19)"),
    "fecha": "2026-05-31",
    "nota": ("Manual multilingue ES/FR/GB/IT; offset impresa+2 = fisica (impresa 28 = fisica 30). PDF "
             "digital-native (texto extraido = render). CONDUCTA CORREGIDA admit_no_info -> answer: la "
             "pregunta asume una funcion (desactivar UN detector) que NO existe en una central "
             "convencional; el corpus SI cubre la respuesta correcta (desconexion por zona + aislamiento "
             "fisico) -> el bot debe RESPONDER corrigiendo la premisa, no admitir. Mismo patron que hp017."),
    "localizacion": {
        "manuales_buscados": ["CCD-103_Manual_ES_FR_GB_IT.pdf"],
        "terminos": ["convencional", "desconectar zona", "2 veces la tecla de zona", "32 detectores", "4K7"],
        "paginas_fisicas": [7, 15, 16, 30],
        "corpus_chunks_v2": "109 chunks del manual (servable)",
        "nota": "offset impresa+2 = fisica. Desconexion por zona en f30; 4K7 EOL en f15-16/f19.",
    },
}

# --- hp013: Detnov/Securiton ADW 535 — cambiar la bateria tampon sin perder configuracion. answer
# (parcial, corregida de admit). VERIFICADO s33 (Fase 1 / Tier B): doc T 140 358 (digital-native limpio,
# sin offset; impresa 'NNN/119' = fisica). Render f68 (Fig.31: 'Bateria de litio' en el Main Board LMB 35)
# + f103 (9.4 Sustitucion de componentes: solo placas LMB/LEB/LSU, sin procedimiento de bateria). El ADW
# no tiene bateria standby propia (alimentacion externa +9..30 VCC); la config va en EEPROM (no volatil).
HP013_FACTS = [
    {
        "texto": ("La configuracion especifica del sistema se almacena en una EEPROM (memoria NO volatil); "
                  "el firmware en Flash PROM -> la configuracion se CONSERVA aunque se cambie la bateria"),
        "tipo": "core", "estado": "presente", "valor": "EEPROM", "cita": "p14 (1.7/2.2.2)",
    },
    {
        "texto": ("El ADW 535 se alimenta externamente (borne PWR +9 a +30 V-CC) con una entrada de "
                  "alimentacion REDUNDANTE PWR-R; el respaldo es esa alimentacion redundante, NO una bateria "
                  "tampon a bordo. La unica bateria es de LITIO, en la placa LMB 35, para el reloj RTC"),
        "tipo": "core", "estado": "presente", "valor": "PWR-R", "cita": "p12 (glosario) / p29 / p56",
    },
    {
        "texto": ("El manual NO documenta un procedimiento de sustitucion de la bateria de litio del reloj; "
                  "el cap. 9.4 solo cubre la sustitucion de PLACAS (LSU/LMB/LEB). Para una sustitucion "
                  "aislada de la bateria, consultar al fabricante (Securiton)"),
        "tipo": "core", "estado": "ausente-probado", "valor": None, "cita": "p103-104 (9.4: solo placas)",
    },
    {
        "texto": ("Solo el reloj RTC (fecha/hora) depende de la bateria de litio ('Fallo bateria de litio / "
                  "reloj'); tras el cambio habria que reajustar el reloj, no la configuracion"),
        "tipo": "supplementary", "estado": "presente", "valor": "reloj RTC", "cita": "p70 / p24",
    },
    {
        "texto": ("Tras sustituir el LMB 35 es obligatorio un nuevo reset inicial (cap. 7.3.5) y una "
                  "verificacion de la transmision de alarmas (cap. 7.7.1)"),
        "tipo": "supplementary", "estado": "presente", "valor": "reset inicial", "cita": "p104",
    },
]
HP013_PROV = {
    "estado": "verificado",
    "metodo": "render_pdf",
    "fuente": "ADW535_TD_T140358es_e.pdf (Securiton; Detnov = marca OEM/distribuidor)",
    "paginas": [68, 103, 104, 29],
    "verificado_por": [
        "Claude (lectura multimodal de f68 Fig.31 'Bateria de litio' en el LMB 35 + f103 '9.4 Sustitucion "
        "de componentes' = solo placas, sin procedimiento de bateria)",
    ],
    "acuerdo": ("render confirma: la bateria de litio esta en el Main Board LMB 35 (Fig.31, f68); el cap. "
                "9.4 documenta sustitucion de PLACAS (LSU/LMB/LEB), no de la bateria; config en EEPROM"),
    "fecha": "2026-05-31",
    "nota": ("Doc digital-native limpio (texto extraido = render); sin offset (impresa 'NNN/119' = fisica). "
             "CONDUCTA CORREGIDA admit_no_info -> answer (parcial, como hp014): la premisa 'bateria tampon' "
             "es inexacta (no hay bateria standby; si una bateria de litio en placa para el RTC). El corpus "
             "SI responde lo sustantivo (config en EEPROM se conserva; bateria soldada en el LMB 35 -> se "
             "sustituye la placa 9.4.2; NO hay procedimiento autonomo de bateria = ausente-probado). El bot "
             "debe RESPONDER con esto, no admitir. Securiton OEM (Detnov distribuye)."),
    "localizacion": {
        "manuales_buscados": ["ADW535_TD_T140358es_e.pdf", "ADW 535-1 ATEX_TD_003 007_en_a.pdf"],
        "terminos": ["bateria de litio", "EEPROM", "Sustitucion de componentes 9.4", "LMB 35", "reset inicial"],
        "paginas": [14, 29, 68, 103, 104],
        "corpus_chunks_v2": "201 chunks (ADW535_TD) + 16 (ATEX en) (servable)",
        "nota": "sin offset (impresa NNN/119 = fisica). 9.4 cubre sustitucion de PLACAS, no de la bateria.",
    },
}

# --- hp006: Notifier AFP-400 — aviso 'Tierra' (Earth Fault): que significa y como se localiza. answer
# (parcial, corregida de admit) + LIMPIEZA de cruft (gold_answer malformado de s27). VERIFICADO s33
# (Fase 1 / Tier B): el corpus SI cubre el fallo de tierra en manuales que el autor NO consulto —
# MIDT170 (instalacion AFP-400, 58 chunks): MPS-400 con LED 'Fallo de Tierra' + TB1-3 + JP2 (f54) y tabla
# de averia del lazo con 'Tierra' + aisladores ISO-X (f71). El autor s27 solo uso MADT380_01 (hoja NAM-232)
# + 50253SP (PSU). Solo el procedimiento de localizacion paso-a-paso es ausente-probado (MFDT170, el
# manual de funcionamiento, no menciona 'Tierra'). Render f54 + f71 (Claude multimodal). Patron hp017.
HP006_ANSWER = (
    "En la AFP-400 el aviso 'Tierra' (Earth Fault) corresponde a un fallo de aislamiento a tierra: algun "
    "conductor de un circuito (lazo, zona, salidas o alimentacion) hace contacto con masa/tierra, y la "
    "central lo senaliza como averia del sistema.\n\n"
    "Lo que documentan los manuales disponibles:\n"
    "- La fuente MPS-400 dispone de deteccion de fallo de tierra: LED dedicado 'Fallo de Tierra', terminal "
    "de toma de tierra TB1-3 y puente JP2 para inhabilitar la deteccion. Es imprescindible conectar TB1-3 a "
    "una toma de tierra solida (p.ej. tuberia metalica de agua fria) para la inmunidad del panel "
    "(MIDT170 / 50253SP).\n"
    "- En el lazo de comunicaciones (SLC), 'Tierra' es una de las condiciones de averia que la central "
    "reconoce y muestra (tabla de Funcionamiento del Lazo, Estilos 4/6/7) (MIDT170).\n"
    "- En red, la deteccion de fallo de tierra por canal A/B se habilita/inhabilita con los conmutadores "
    "SW2/SW3 del modulo NAM-232W (MADT380_01).\n"
    "- Para acotar un fallo en el lazo se emplean los modulos aisladores ISO-X, que aislan la rama en "
    "averia del resto del lazo (MIDT170).\n\n"
    "Para localizar el punto exacto del fallo: los manuales disponibles NO incluyen un procedimiento "
    "paso a paso (el manual de funcionamiento MFDT170 no detalla este aviso). El metodo general consiste "
    "en aislar/desconectar circuitos progresivamente -en el lazo, mediante los aisladores ISO-X- hasta que "
    "desaparece el aviso; para el procedimiento detallado, consultar al servicio tecnico de Notifier."
)
HP006_FACTS = [
    {
        "texto": ("La fuente MPS-400 de la AFP-400 dispone de deteccion de fallo de tierra: LED dedicado "
                  "'Fallo de Tierra' (MIDT170) + terminal TB1-1 'Falla de Tierra' / TB1-3 toma de tierra; el "
                  "puente JP2 'Corte para inhabilitar la deteccion de la Falla de Tierra' (50253SP 2-44)"),
        "tipo": "core", "estado": "presente", "valor": "Fallo de Tierra", "cita": "MIDT170 f54 + 50253SP 2-44 (f80)",
    },
    {
        "texto": ("En el lazo de comunicaciones (SLC) 'Tierra' es una de las condiciones de averia que la "
                  "central reconoce y senaliza (tabla 'Funcionamiento del Lazo', Estilos 4/6/7)"),
        "tipo": "core", "estado": "presente", "valor": "Tierra", "cita": "MIDT170 p63 (f71)",
    },
    {
        "texto": ("Para acotar un fallo en el lazo se usan los modulos aisladores ISO-X, que aislan la rama "
                  "en averia del resto del lazo (requeridos para Estilo 7 segun NFPA)"),
        "tipo": "core", "estado": "presente", "valor": "ISO-X", "cita": "MIDT170 p63 (f71)",
    },
    {
        "texto": ("Es imprescindible conectar el terminal de toma de tierra (MPS-400 TB1-3) a una toma de "
                  "tierra solida para mantener la inmunidad del panel"),
        "tipo": "supplementary", "estado": "presente", "valor": "TB1-3", "cita": "50253SP / MIDT170 (f54)",
    },
    {
        "texto": ("En red, la deteccion de fallo de tierra por canal A/B se habilita o inhabilita con los "
                  "conmutadores SW2/SW3 del modulo NAM-232W"),
        "tipo": "supplementary", "estado": "presente", "valor": "SW2/SW3", "cita": "MADT380_01 p1",
    },
    {
        "texto": ("Los manuales disponibles NO incluyen un procedimiento paso a paso para localizar el "
                  "punto exacto del fallo de tierra (el manual de funcionamiento MFDT170 no menciona el "
                  "aviso 'Tierra')"),
        "tipo": "core", "estado": "ausente-probado", "valor": None, "cita": "MFDT170 (0 menciones de 'Tierra')",
    },
]
HP006_PROV = {
    "estado": "verificado",
    "metodo": "render_pdf + pdf_grep + corpus_check",
    "fuente": "MIDT170.pdf (instalacion AFP-400) + 50253SP.pdf (MPS-400) + MADT380_01.pdf (NAM-232W)",
    "paginas": [54, 71],
    "verificado_por": [
        "Claude (multimodal de MIDT170 f54 'Fallo de Tierra' de la MPS-400 + f71 tabla de averia del "
        "lazo / aisladores ISO-X)",
        "pdf_grep MFDT170 (manual de funcionamiento) = 0 menciones de 'Tierra' -> sin narrativa de "
        "interpretacion/localizacion",
        "pdf_grep 50253SP 2-44 (f80): confirma JP2 'Corte para inhabilitar la deteccion de la Falla de "
        "Tierra' + pinout TB1 (TB1-1 Falla de Tierra) -> claim del gold s27 VERIFICADO contra la fuente "
        "(un revisor lo marco como no-probado por mirar solo MIDT170; rule C)",
    ],
    "acuerdo": ("render confirma: MPS-400 con LED 'Fallo de Tierra' + TB1-3 + JP2 (f54); 'Tierra' como "
                "condicion de averia del lazo (f71) + aisladores ISO-X; sin procedimiento de localizacion "
                "paso-a-paso en los manuales"),
    "fecha": "2026-05-31",
    "nota": ("MIDT170 OFFSET +8 (impresa = fisica - 8; pie 'MI-DT-170c 46'/'63' en f54/f71). Digital-native. "
             "CONDUCTA CORREGIDA admit_no_info -> answer (parcial) + LIMPIEZA: el gold_answer de s27 venia "
             "malformado (JSON-en-string truncado por un parse error); raw/_needs_human_review/_review_note "
             "eliminados. El corpus SI cubre el fallo de tierra (deteccion MPS-400, condicion de averia del "
             "lazo, aisladores ISO-X) en MIDT170, que el autor NO consulto; solo el walk-down de "
             "localizacion es ausente-probado. Mismo patron que hp017 (subset de PDFs demasiado estrecho)."),
    "localizacion": {
        "manuales_buscados": ["MADT380_01 (NAM-232W)", "50253SP (MPS-400)", "MIDT170 (instalacion)",
                              "MFDT170 (funcionamiento)", "MPDT170 (programacion)", "MADT170/171 (AFP-300)"],
        "terminos": ["tierra", "fallo de tierra", "Earth Fault", "JP2", "TB1", "ISO-X", "localiz", "averia"],
        "paginas": [54, 71],
        "corpus_chunks_v2": ("AFP-400/300 en chunks_v2: MIDT170(58), MFDT170(14), MPDT170(10), 50253SP(290), "
                             "MADT170/171/231/232/236, MADT380_01(3) -> tema cubierto, servable"),
        "nota": ("offset MIDT170 +8 (impresa = fisica - 8). El gold s27 solo uso MADT380_01 + 50253SP; "
                 "MIDT170 (instalacion) cubre la deteccion + tabla de averia del lazo + ISO-X."),
    },
}

# --- hp009: Morley ZXe — resistencia de fin de linea (RFL) para los lazos. answer (corregida de admit).
# VERIFICADO s33 (Fase 1 / Tier B): el lazo analogico direccionable de la ZXe NO lleva RFL — se cablea
# como BUCLE CERRADO (LAZO+/- de salida y RETORNO LAZO+/- de vuelta), con aisladores de cortocircuito.
# RE-ANCLADO s33 Tier C: en Tier B se ancló a MIE-MI-310, que es el manual de ZXAE/ZXEE (convencional/2000),
# NO el e-series ZX2e/ZX5e que pregunta la "ZXe" (mismo error que hp018). La SUSTANCIA (lazo direccionable =
# bucle cerrado SIN RFL) se RE-VERIFICÓ contra MIE-MI-530 (ZX2e/ZX5e, digital-native, f19 3.4.3.1 Fig 9/10)
# -> re-anclado a MI-530 como fuente primaria; MI-310 (ZXAE/ZXEE) corrobora la misma topologia. El bot debe
# RESPONDER corrigiendo la premisa (el lazo no usa RFL). (MIE-MI-300rv02 es scan: grep invalido.)
HP009_ANSWER = (
    "El lazo analogico direccionable de la central Morley ZXe (e-series ZX2e/ZX5e) NO lleva resistencia de "
    "fin de linea (RFL). El lazo se cablea como un BUCLE CERRADO: los terminales de salida del panel (Inicio "
    "Lazo +/- OUT) recorren los equipos direccionables y el final del lazo VUELVE al panel por los terminales "
    "de Retorno (+/-) del mismo conector de lazo (manual de instalacion MIE-MI-530, seccion 3.4.3.1, Figuras "
    "9 y 10). Cada lazo dispone de aisladores de cortocircuito INTERNOS en el panel; se recomienda intercalar "
    "aisladores adicionales en campo (maximo 32 sensores/pulsadores entre aisladores segun EN54-2 12.5.2, o "
    "por zona fisica segun EN54-14) para que un corto o un circuito abierto no deje sin comunicacion a todo "
    "el lazo.\n\n"
    "La 'resistencia de fin de linea' (RFL/EOL) es un concepto de los circuitos CONVENCIONALES supervisados "
    "(zonas convencionales, salidas de sirena monitorizadas que en la ZXe usan 6K8), NO del lazo "
    "direccionable. Por eso ningun manual de la ZXe especifica una RFL para el lazo: el lazo se supervisa por "
    "su topologia de bucle cerrado + aisladores, no con una resistencia. (El mismo cableado de bucle cerrado "
    "sin RFL aparece en los paneles convencionales-direccionables ZXAE/ZXEE, manual MIE-MI-310, Fig 11/12/13.)"
)
HP009_FACTS = [
    {
        "texto": ("El lazo analogico direccionable de la ZXe (ZX2e/ZX5e) se cablea como BUCLE CERRADO: salida "
                  "del panel (Inicio Lazo +/- OUT) y vuelta por los terminales de Retorno (+/-) del mismo "
                  "conector de lazo; NO se cierra con una resistencia de fin de linea"),
        "tipo": "core", "estado": "presente", "valor": "Retorno", "cita": "MIE-MI-530 p19 (3.4.3.1, Fig 9/10)",
    },
    {
        "texto": ("Cada lazo dispone de aisladores de cortocircuito INTERNOS en el panel; el cableado del lazo "
                  "debe realizarse en bucle cerrado con los aisladores necesarios (EN54-14 / EN54-2)"),
        "tipo": "core", "estado": "presente", "valor": "aisladores internos", "cita": "MIE-MI-530 p17 / p20",
    },
    {
        "texto": ("Maximo 32 sensores/pulsadores entre aisladores (EN54-2 12.5.2); se recomienda un aislador "
                  "cada 32 equipos o por zona fisica (EN54-14) para acotar corto/abierto, no una RFL"),
        "tipo": "supplementary", "estado": "presente", "valor": "32", "cita": "MIE-MI-530 p19",
    },
    {
        "texto": ("Ningun manual de la ZXe especifica un valor de resistencia de fin de linea para el LAZO "
                  "direccionable, porque el lazo es un bucle cerrado y no la usa (la RFL pertenece a los "
                  "circuitos convencionales supervisados, p.ej. las salidas de sirena con 6K8)"),
        "tipo": "core", "estado": "ausente-probado", "valor": None,
        "cita": "MIE-MI-530 (lazo sin RFL) + MIE-MI-310 Fig 11/12/13",
    },
]
HP009_PROV = {
    "estado": "verificado",
    "metodo": "render_pdf",
    "fuente": ("MIE-MI-530rv001.pdf (ZX2e/ZX5e, e-series ZXe) — PRIMARIA; MIE-MI-310.pdf (ZXAE/ZXEE) "
               "corrobora la misma topologia de bucle cerrado"),
    "paginas": [17, 19, 20],
    "verificado_por": [
        "Claude (multimodal de MI-530 f19 '3.4.3.1 Conexionado lazo analogico' Fig 9/10 = Inicio Lazo +/- OUT "
        "+ Retorno +/-, bucle cerrado SIN RFL; f17/f20 'bucle cerrado con aisladores' + aisladores internos "
        "en el panel) -> re-anclaje s33 Tier C; MI-310 (ZXAE/ZXEE) Fig 11/12/13 muestra la misma topologia",
    ],
    "acuerdo": ("render MI-530 confirma: lazo direccionable = bucle cerrado (Inicio Lazo +/- OUT y Retorno "
                "+/-), aisladores internos en el panel + recomendados <=32 equipos (EN54); NO hay resistencia "
                "de fin de linea en el lazo. MI-310 (ZXAE/ZXEE) coincide en la topologia (Fig 11/12/13)"),
    "fecha": "2026-06-01",
    "nota": ("RE-ANCLADO en s33 Tier C: en Tier B este gold se ancló a MIE-MI-310, que es el manual de los "
             "paneles ZXAE/ZXEE (convencionales-direccionables, 2000), NO el e-series ZX2e/ZX5e que pregunta "
             "la 'ZXe' (mismo descubrimiento que hp018). La SUSTANCIA (lazo direccionable = bucle cerrado sin "
             "RFL) se RE-VERIFICÓ correcta contra MIE-MI-530 (ZX2e/ZX5e, digital-native, f19 sin offset, pie "
             "'Pagina 19 de 50') -> re-anclado a MI-530 como fuente primaria; MI-310 queda como corroboracion "
             "de la familia hermana. CONDUCTA = answer (corrige la premisa: el lazo no usa RFL). "
             "MIE-MI-300rv02 es un scan (grep invalido: 1 hit en 107 pp)."),
    "localizacion": {
        "manuales_buscados": ["MIE-MI-530rv001 (ZX2e/ZX5e, digital-native)",
                              "MIE-MI-310 (ZXAE/ZXEE, imagen-only/scan: grep invalido, leido por render)",
                              "MIE-MI-300rv02 (SCAN: grep invalido)", "MIE-MP-310", "MIE-MU-310"],
        "terminos": ["bucle cerrado", "Inicio Lazo", "Retorno", "aisladores", "fin de linea", "RFL", "EOL"],
        "paginas": [17, 19, 20],
        "corpus_chunks_v2": ("MIE-MI-530rv001=64 (digital, servable), MI-310=42, MI-300=126(scan), "
                             "MP-310=75, MU-310=31"),
        "nota": ("fin de linea/RFL = 0 hits para el LAZO en MI-530 (solo aparece para las salidas de sirena, "
                 "6K8). Bucle cerrado (Inicio Lazo OUT + Retorno) confirmado al pixel en f19 Fig 9/10. "
                 "Regla de scans: MI-310 imagen-only -> leido por render."),
    },
}

# --- hp012: Notifier AM2020/AFP1010 — nº de lazos SLC y dispositivos por lazo. answer-con-conflicto
# (corregida de answer plano). VERIFICADO s33 (Fase 1 / Tier C): el AFP1010 difiere entre la doc de
# Notifier Espana (MFDT280/MPDT280: 2 lazos / 396) y la de Notifier US (15088SP PN:H 1998: 4 lazos /
# 792) = DOCUMENTOS DISTINTOS -> surfacear ambos (conducta 2). AM2020 (10 lazos) y disp/lazo (99+99)
# consistentes. Render MPDT280 p3 + 15088SP p151 (Claude) + sub-agente (p6/p14/p112) + cross-model GPT-5.5.
HP012_ANSWER = (
    "La AM2020 y la AFP1010 comparten la arquitectura de lazos SLC, pero difieren en el numero de "
    "lazos:\n\n"
    "- La AM2020 soporta hasta 10 lazos SLC.\n"
    "- La AFP1010: los manuales disponibles NO coinciden. La documentacion de Notifier Espana "
    "(MFDT280/MPDT280) la limita a un maximo de 2 lazos (2 tarjetas LIB-200), con un total de 396 "
    "dispositivos en el sistema. La documentacion de Notifier US (PN 15088SP) indica un maximo de 4 "
    "lazos (4 LIB-200 o 2 LIB-400), con un total de 792 dispositivos.\n\n"
    "Cada lazo SLC admite hasta 99 detectores analogicos + 99 modulos monitores o de control (198 "
    "dispositivos por lazo) en ambos casos; asi la AM2020 alcanza 1980 dispositivos. El cableado del "
    "lazo sigue los requisitos NFPA Estilo 4 o Estilo 6.\n\n"
    "La discrepancia del AFP1010 (2 vs 4 lazos) procede de documentos distintos (Notifier Espana vs "
    "Notifier US); con la informacion disponible no es posible determinar cual aplica sin identificar "
    "la documentacion o configuracion del panel concretamente instalado. Conviene verificar contra el "
    "manual correspondiente al equipo en campo."
)
HP012_FACTS = [
    {
        "texto": "La AM2020 soporta hasta 10 lazos SLC (consistente en la doc de Espana y la de US)",
        "tipo": "core", "estado": "presente", "valor": "10 lazos", "cita": "MFDT280 p6 / 15088SP p112,p151",
    },
    {
        "texto": ("Cada lazo SLC admite hasta 99 detectores analogicos + 99 modulos monitores/de control "
                  "= 198 dispositivos por lazo (consistente en ambos mercados)"),
        "tipo": "core", "estado": "presente", "valor": "99 + 99", "cita": "MFDT280 p4 / 15088SP p61",
    },
    {
        "texto": ("AFP1010 segun la doc de Notifier ESPANA (MFDT280/MPDT280): maximo 2 tarjetas LIB-200 "
                  "= 2 lazos / 396 dispositivos en el sistema"),
        "tipo": "core", "estado": "presente", "valor": "2 lazos / 396", "cita": "MPDT280 p3 / MFDT280 p6",
    },
    {
        "texto": ("AFP1010 segun la doc de Notifier US (PN 15088SP, 1998): maximo 4 LIBs (4 LIB-200 o 2 "
                  "LIB-400) = 4 lazos / 792 dispositivos -> EN CONFLICTO con la doc de Espana"),
        "tipo": "core", "estado": "presente", "valor": "4 lazos / 792", "cita": "15088SP p14,p112,p151",
    },
    {
        "texto": "El AM2020 alcanza un total de 10 x 198 = 1980 dispositivos direccionables en el sistema",
        "tipo": "supplementary", "estado": "presente", "valor": "1980", "cita": "15088SP p151",
    },
    {
        "texto": "El cableado del lazo SLC sigue los requisitos NFPA Estilo 4 o Estilo 6 (la doc US anade Estilo 7)",
        "tipo": "supplementary", "estado": "presente", "valor": "Estilo 4", "cita": "MFDT280 p4 / 15088SP p242",
    },
]
HP012_PROV = {
    "estado": "verificado",
    "metodo": "render_pdf + cross_model",
    "fuente": ("MFDT280.pdf + MPDT280.pdf (Notifier Espana) + 15088SP.pdf (Notifier US, "
               "PN 15088SP:H 10/21/98)"),
    "paginas": [3, 6, 14, 151],
    "verificado_por": [
        "Claude (lectura multimodal de MPDT280 p3 'AFP1010 maximo 2 LIB-200/396' + 15088SP p151 'AFP1010 "
        "maximo 4 LIBs/792, AM2020 10 LIBs/1980')",
        "sub-agente Claude (Protocolo 3: render/grep de MFDT280 p6 '1 a 10 AM2020 / 1 a 2 AFP1010' + "
        "15088SP p14,p112; 13 confirmados, 0 falsos-positivos)",
        "gpt-5.5 cross-model (revisor adversarial: refino del framing del conflicto, ver nota)",
    ],
    "acuerdo": ("ES (MFDT280/MPDT280): AFP1010 = 2 LIB-200 / 396, AM2020 = 10 lazos. US (15088SP): "
                "AFP1010 = 4 LIBs / 792, AM2020 = 10 LIBs / 1980. AM2020 y disp/lazo (99+99) consistentes; "
                "el AFP1010 difiere (2 vs 4 lazos)"),
    "fecha": "2026-05-31",
    "nota": ("CONDUCTA CORREGIDA answer -> answer-con-conflicto: el gold s27 daba solo el lado ES (2 "
             "lazos/396) como answer plano, omitiendo la variante US (4 lazos/792). Son DOCUMENTOS "
             "DISTINTOS (Notifier Espana vs Notifier US PN 15088SP/1998), no revisiones del mismo manual "
             "-> surfacear ambos (conducta 2), no elegir ganador. GAP DECLARADO (rule C, cross-model "
             "GPT-5.5): sin metadata de revision/fecha de los manuales ES no se puede establecer "
             "supersesion ni probar 'variante de mercado' vs edicion/config distinta; por eso la "
             "respuesta atribuye cada valor a su fuente y remite a la doc del panel instalado, sin adjudicar."),
    "localizacion": {
        "manuales_buscados": ["MFDT280 (operacion ES, digital)", "MPDT280 (programacion ES, digital)",
                              "15088SP (instalacion US, digital)", "15090SP", "15092SP", "MADT370"],
        "terminos": ["LIB-200", "lazos", "396", "792", "1 a 10", "1 al 4", "99 detectores", "1980"],
        "paginas": [3, 6, 14, 112, 151],
        "corpus_chunks_v2": ("ES servable: MFDT280=50, MPDT280=127; US servable: 15088SP=342 (+15090SP=134, "
                             "15092SP=92, MADT370=15) -> ambas variantes del conflicto son recuperables"),
        "nota": "los 3 manuales son digital-native (texto extraible). 15088SP esta en castellano pese a ser PN US.",
    },
}

# --- hp018: Morley ZXe — conectar una sirena convencional en las salidas de sirena. answer (corregida).
# VERIFICADO s33 (Fase 1 / Tier C): el gold s27 estaba MAL DOS VECES: citaba MIE-MI-310 = ZXAE/ZXEE
# (convencional, mayo 2000), producto DISTINTO del e-series ZXe; y valores fabricados (ZX5e=5 salidas /
# 10kOhm / 500mA). Re-anclado a MIE-MI-530rv001 (ZX2e/ZX5e, digital-native, 64 chunks). Render MI-530
# p12/p21/p44 + MI-310 p1/p18 (descarte producto) (Claude) + sub-agente + cross-model GPT-5.5.
HP018_ANSWER = (
    "En la Morley ZXe (e-series, paneles ZX2e/ZX5e) las salidas de sirena son circuitos convencionales "
    "supervisados en la placa base:\n\n"
    "- Numero de salidas: la ZX2e tiene 2 circuitos de sirena (Sirenas A y B); la ZX5e tiene 4 (Sirenas "
    "A, B, C y D).\n"
    "- Caracteristicas: supervisados ante cortocircuito y circuito abierto, limitados en corriente, "
    "maximo 1 A por circuito.\n\n"
    "Conexion de una sirena convencional:\n"
    "1) Conecte la sirena en el terminal del circuito de sirena correspondiente de la placa base "
    "(Figura 13 ZX2e / Figura 14 ZX5e), respetando la polaridad +/- de la salida.\n"
    "2) Cada sirena debe llevar un diodo integrado: en reposo la linea esta polarizada en inverso (para "
    "la supervision) y, al dispararse la salida, se invierte la polaridad y la sirena suena. Si la "
    "sirena no es polarizada, anada un diodo de polarizacion y proteccion en cada una.\n"
    "3) Instale una resistencia de fin de linea (RFL) de 6,8 kOhm (6K8), 0,5 W minimo, en el final del "
    "circuito (en la ultima sirena) para la supervision.\n"
    "4) Use el calibre de cable indicado en la seccion 3.4.13 del manual.\n\n"
    "Las RFL de 6k8 se suministran con el panel (2 con la ZX2e, 4 con la ZX5e).\n\n"
    "Nota: los paneles convencionales ZXAE/ZXEE (manual MIE-MI-310) usan el mismo valor de RFL (6K8) y "
    "la misma corriente (1 A), variando solo el numero de salidas (ZXAE 2 / ZXEE 4)."
)
HP018_FACTS = [
    {
        "texto": ("La ZX5e dispone de 4 circuitos/salidas de sirena de placa (la ZX2e, 2: Sirenas A y B); "
                  "supervisados ante cortocircuito y circuito abierto, limitados en corriente"),
        "tipo": "core", "estado": "presente", "valor": "4 circuitos", "cita": "MI-530 p12 / p21 (3.4.4) / p44",
    },
    {
        "texto": ("Resistencia de fin de linea (RFL) = 6,8 kOhm (6K8), 0,5 W minimo, en el final de cada "
                  "circuito de sirena (en la ultima sirena) para la supervision"),
        "tipo": "core", "estado": "presente", "valor": "6K8", "cita": "MI-530 p21 / p44",
    },
    {
        "texto": ("Cada sirena debe llevar un diodo integrado; el circuito se polariza en inverso en "
                  "reposo (supervision) y cambia a polarizacion normal al dispararse; los dispositivos no "
                  "polarizados requieren anadir un diodo en cada uno"),
        "tipo": "core", "estado": "presente", "valor": "diodo", "cita": "MI-530 p21",
    },
    {
        "texto": ("La conexion se hace en el bloque de terminales de circuitos de sirena de la placa base "
                  "(Figura 13 ZX2e / Figura 14 ZX5e), respetando la polaridad +/- de cada salida (A/B/C/D)"),
        "tipo": "core", "estado": "presente", "valor": "Sirenas A,B,C,D", "cita": "MI-530 p21 (Fig 13/14)",
    },
    {
        "texto": "Carga maxima 1 A por circuito/salida de sirena",
        "tipo": "core", "estado": "presente", "valor": "1 A", "cita": "MI-530 p21 / p44",
    },
    {
        "texto": "Las resistencias de fin de linea de 6k8 (1/4 W) se suministran con el panel (2 con la ZX2e, 4 con la ZX5e)",
        "tipo": "supplementary", "estado": "presente", "valor": "627-682", "cita": "MI-530 p8",
    },
    {
        "texto": "Para el calibre de cable recomendado de los circuitos de sirena, ver la seccion 3.4.13 del manual",
        "tipo": "supplementary", "estado": "presente", "valor": "3.4.13", "cita": "MI-530 p21",
    },
]
HP018_PROV = {
    "estado": "verificado",
    "metodo": "render_pdf + cross_model",
    "fuente": "MIE-MI-530rv001.pdf (ZX2e/ZX5e, el e-series 'ZXe')",
    "paginas": [12, 21, 44],
    "verificado_por": [
        "Claude (multimodal de MI-530 p12 'Placa Base' 2/4 salidas + p21 '3.4.4 Circuitos de Sirenas' "
        "Fig 13/14 (RFL 6K8, diodo, 1A, polaridad) + p44 'Tabla 8' specs ZX5e; y render de MIE-MI-310 "
        "p1/p18 que prueba que MI-310 = ZXAE/ZXEE convencional (mayo 2000), producto DISTINTO)",
        "sub-agente Claude (Protocolo 3: 13 confirmados, 0 falsos-positivos; 3er respaldo p21 3.4.4)",
        "gpt-5.5 cross-model (revisor adversarial: 3 refinos de framing aplicados, ver nota)",
    ],
    "acuerdo": ("render confirma: ZX2e=2 / ZX5e=4 circuitos de sirena (p12, p21 3.4.4, p44); RFL 6K8 0,5W "
                "al final del circuito (p21, p44); diodo integrado por sirena + polarizacion inversa en "
                "reposo (p21); 1 A max por salida (p21, p44). MI-310 p1 = ZXAE/ZXEE convencional = "
                "producto distinto. NO hay conflicto MI-310 vs MI-530: ambos 6K8 y 1 A"),
    "fecha": "2026-05-31",
    "nota": ("CONDUCTA = answer (corregida). El gold s27 estaba MAL DOS VECES: (1) PRODUCTO EQUIVOCADO -- "
             "citaba MIE-MI-310, que es el manual de los paneles ZXAE/ZXEE (convencionales, mayo 2000), NO "
             "el e-series direccionable ZXe; (2) VALORES que NO aparecen en los manuales identificados de "
             "la ZXe (ZX5e=5 salidas / EOL 10kOhm / 500mA -> los reales son 4 / 6K8 / 1 A). Re-anclado a "
             "MIE-MI-530rv001 (ZX2e/ZX5e). 'ZXe' = e-series ZX2e/ZX5e (no hay ZX1e en el corpus); los "
             "convencionales ZXAE/ZXEE comparten 6K8 y 1 A, varian solo en nº de salidas. Patron hp009/"
             "hp017 (manual equivocado/estrecho) intensificado. GAP DECLARADO (rule C, cross-model "
             "GPT-5.5): la afirmacion 'valores fabricados' se acota a los manuales identificados de la ZXe "
             "(MI-310 + MI-530), no a una busqueda exhaustiva de todo el corpus."),
    "localizacion": {
        "manuales_buscados": ["MIE-MI-530rv001 (ZX2e/ZX5e, DIGITAL-NATIVE: texto extraible limpio)",
                              "MIE-MI-310 (ZXAE/ZXEE, IMAGEN/scan: pdf_grep 0 hits en 36 pp -> grep "
                              "INVALIDO, leido por RENDER)", "MIE-MI-300rv02 (scan)", "MIE-MP-310", "MIE-MU-310"],
        "terminos": ["circuitos de sirena", "salidas de sirena", "fin de linea", "6K8", "diodo", "1 Amp",
                     "supervisada", "polaridad"],
        "paginas": [12, 21, 44],
        "corpus_chunks_v2": ("MIE-MI-530rv001 = 64 chunks (digital, SERVABLE); MI-310=42, MI-300=126, "
                             "MP-310=75, MU-310=31. La respuesta correcta es servible desde MI-530."),
        "nota": ("Regla de scans (s33): MI-310 es imagen-only (grep invalido) -> identidad y valores leidos "
                 "por RENDER (evidencia positiva); MI-530 es digital-native -> servible. Modalidad "
                 "registrada por-manual. CAVEAT hp009: ese gold (Tier B) tambien uso MIE-MI-310 (ZXAE/"
                 "ZXEE) para responder sobre el lazo de la ZXe -> revisar si conviene re-anclar a MI-530."),
    },
}

# qid -> {facts, [provenance], [conducta]}. provenance presente = el gold se VERIFICA aquí.
RECORDS = {
    "hp011": {"facts": HP011_FACTS},
    "hp017": {"facts": HP017_FACTS},
    "hp019": {"facts": HP019_FACTS, "conducta": "answer", "provenance": HP019_PROV},
    "hp003": {"facts": HP003_FACTS, "conducta": "answer", "provenance": HP003_PROV},
    "hp008": {"facts": HP008_FACTS, "conducta": "answer", "provenance": HP008_PROV},
    "hp020": {"facts": HP020_FACTS, "conducta": "answer", "provenance": HP020_PROV},
    "hp001": {"facts": HP001_FACTS, "conducta": "answer", "provenance": HP001_PROV},
    "hp005": {"facts": HP005_FACTS, "conducta": "answer", "provenance": HP005_PROV},
    "hp010": {"facts": HP010_FACTS, "conducta": "answer", "provenance": HP010_PROV},
    "hp014": {"facts": HP014_FACTS, "conducta": "answer", "provenance": HP014_PROV},
    "hp002": {"facts": HP002_FACTS, "conducta": "answer", "provenance": HP002_PROV},
    # Tier B (s33): conducta corregida de admit/ask_clarification. hp015/hp013 = answer corregida
    # (el corpus SI cubre, desde manuales que el autor s27 no consulto — patron hp017); hp004 = clarify.
    "hp004": {"facts": HP004_FACTS, "conducta": "clarify", "provenance": HP004_PROV},
    "hp015": {"facts": HP015_FACTS, "conducta": "answer", "provenance": HP015_PROV,
              "gold_answer": HP015_ANSWER},
    "hp013": {"facts": HP013_FACTS, "conducta": "answer", "provenance": HP013_PROV},
    "hp006": {"facts": HP006_FACTS, "conducta": "answer", "provenance": HP006_PROV,
              "gold_answer": HP006_ANSWER, "drop": ["raw", "_needs_human_review", "_review_note"]},
    "hp009": {"facts": HP009_FACTS, "conducta": "answer", "provenance": HP009_PROV,
              "gold_answer": HP009_ANSWER, "drop": ["notes"]},
    # Tier C (s33): los 2 golds diferidos en s30 a "tecnico + PDF renderizable". Resueltos sin tecnico
    # via render: hp012 = answer-con-conflicto (conflicto real ES-vs-US); hp018 = answer (gold s27 cito
    # producto equivocado ZXAE/ZXEE + valores fabricados -> re-anclado a MI-530 ZX2e/ZX5e).
    "hp012": {"facts": HP012_FACTS, "conducta": "answer-con-conflicto", "provenance": HP012_PROV,
              "gold_answer": HP012_ANSWER, "drop": ["notes"]},
    "hp018": {"facts": HP018_FACTS, "conducta": "answer", "provenance": HP018_PROV,
              "gold_answer": HP018_ANSWER, "drop": ["notes"]},
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
        if rec.get("gold_answer"):
            g["gold_answer"] = rec["gold_answer"]  # reescritura (p.ej. hp006: gold_answer malformado)
        for campo in rec.get("drop", []):
            g.pop(campo, None)  # limpieza de cruft (raw/_needs_human_review/_review_note)
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
