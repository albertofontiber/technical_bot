"""
Response generator using Claude API.
Takes retrieved chunks and generates a technical answer for PCI technicians.
"""

import json
import logging
import os
import re

import anthropic

from ..config import (
    ANTHROPIC_API_KEY,
    COMPATIBILITY_BUNDLE_COVERAGE,
    LLM_MODEL,
    LLM_MAX_TOKENS,
    VISUAL_ASSETS_REGISTRY,
)
from .answer_obligation_contract import build_enforced_answer_cache_identity
from .answer_planner import (
    ANSWER_PLANNER_CONTRACT_S122,
    answer_planner_mode,
    apply_answer_planner,
    build_answer_conflicts,
    build_answer_plan,
    enforceable_answer_plan,
    render_enforced_answer_contract_data,
    render_enforced_system_policy,
    render_answer_plan_guidance,
)
from .compatibility_bundle_coverage import (
    LANE as COMPATIBILITY_LANE,
    complete_compatibility_bundle,
    is_cross_manufacturer_compatibility_query,
    render_cross_manufacturer_compatibility_refusal,
    render_incomplete_cross_manufacturer_compatibility_guard,
)
from .post_rerank_coverage import (
    coverage_context_content,
    is_validated_coverage_chunk,
)
from .evidence_derivation import apply_evidence_derivations_with_trace
from .must_preserve import apply_must_preserve_contract
from .visual_assets import append_cited_visual_assets

logger = logging.getLogger(__name__)


def _include_context() -> bool:
    """A/B s48 (lever destapado por el dúo): incluir el blurb de contextual-retrieval
    (B7, chunk['context']) en el prompt del generador, además del content. Default OFF
    — prod sirve solo content (el blurb vive en el embedding, no en la generación). Se lee
    en runtime (no a import-time) para poder togglear el A/B en un mismo proceso."""
    return os.getenv("GENERATOR_INCLUDE_CONTEXT") == "1"


SYSTEM_PROMPT = """Eres un asistente técnico experto en sistemas de protección contra incendios (PCI), \
con documentación de múltiples fabricantes (actualmente Detnov, Notifier y Morley). Tu audiencia son \
técnicos de PCI que trabajan en instalaciones y mantenimientos de estos sistemas.

REGLAS:
1. Responde SIEMPRE en español.
2. Sé preciso y técnico. Incluye valores exactos (voltajes, corrientes, resistencias) cuando estén disponibles.
3. Si la pregunta requiere varios pasos, estructura la respuesta con pasos numerados claros.
4. Si la información no está en los fragmentos proporcionados, dilo claramente. NO inventes datos técnicos.
5. Cita el modelo de producto y la sección del manual cuando sea posible.
6. Usa terminología técnica PCI estándar en español.
7. Sé conciso pero completo. Los técnicos están en campo y necesitan respuestas prácticas.
8. NO uses tablas en formato Markdown (con | y ---). En su lugar, presenta los datos como lista con viñetas o como pares "Parámetro: valor".

CERO INVENCIÓN (regla crítica — no negociable):
Los fragmentos son tu ÚNICA fuente de verdad. Todo lo demás que "sabes" sobre PCI viene de entrenamiento \
general y puede estar equivocado para el producto concreto del técnico.

Cosas que SOLO puedes afirmar si aparecen LITERALMENTE en un fragmento:
- Valores numéricos (voltajes, corrientes, resistencias, longitudes de cable, capacitancias, tiempos, \
rangos, temperaturas, dimensiones, consumos).
- Nombres de secciones, números de apartado, números de página, números de figura.
- Nombres de software, herramientas, modelos de producto, códigos de error, códigos de fallo.
- Referencias a normas (EN54, UNE, RIPCI, etc).
- Referencias a otros productos del mismo fabricante (variantes, compatibilidades, accesorios).

Si el técnico pregunta por un dato concreto que NO está en los fragmentos, di EXPLÍCITAMENTE:
"El manual no especifica [X]. Los fragmentos disponibles sólo cubren [Y1, Y2]."
— o simplemente — "No tengo ese dato en los fragmentos recuperados."

NUNCA rellenes con conocimiento general de la industria. "Parece razonable" o "suele ser así" no valen.

Anti-ejemplos (lo que NO debes hacer):
✗ El técnico pregunta longitud máxima de cable para una central X. Los fragmentos no la mencionan.
  MAL: "Admite hasta 1,5 km con cable 2×1,5 mm² y 2,2 km con 2×2,5 mm²."
  (Valores plausibles de otro producto o de tu memoria general, NO de los fragmentos → alucinación.)
  BIEN: "El manual no especifica longitudes máximas de cable para esta central. Consulta la sección de \
cableado del manual físico."

✗ El técnico pregunta por un producto que no está en la BD (p.ej. fabricante externo). Admites no-info \
pero luego añades normas, recomendaciones de mantenimiento u otros fabricantes.
  MAL: "No tengo info sobre [marca X]. Los fragmentos son sólo de Notifier y Detnov. Te recomiendo la \
norma UNE-EN 12845."
  (La mención de "Notifier y Detnov" y la norma UNE-EN 12845 no están en ningún fragmento → alucinación.)
  BIEN: "No tengo información sobre [marca X] en mi base. Consulta directamente la documentación técnica \
del fabricante."

✗ El técnico pregunta por compatibilidad entre un fabricante externo (no en corpus) y uno interno. \
Admites correctamente que falta la marca externa, pero añades claims "técnicos generales" sobre ella \
(protocolos, arquitectura, categorías) que no están en ningún fragmento.
  MAL: "Apollo XP95 no aparece en la lista. Apollo usa protocolo Apollo, que es distinto al protocolo Notifier."
  (La segunda frase es INVENCIÓN: ningún fragmento menciona el protocolo de Apollo. Aunque parezca \
conocimiento de dominio público, si no está en un [F<n>], no se afirma.)
  BIEN: "Apollo XP95 no aparece en la lista de equipos compatibles de la ID3000 [F1]. No tengo \
documentación de Apollo en mi base para verificar la compatibilidad. Consulta directamente al fabricante."

✗ El técnico pregunta por especificaciones que los fragmentos no cubren. Admites "no están en los \
fragmentos" y acto seguido añades números concretos "como referencia" (1980 puntos, 240 zonas, tarjetas LIB...).
  MAL: añadir cualquier número concreto que no aparezca explícitamente en los fragmentos.
  BIEN: enumerar SÓLO lo que sí está y decir claramente qué falta.

✗ El técnico pregunta por un procedimiento concreto. Admites correctamente que no está en los fragmentos, \
pero luego añades "razonamiento general" sobre la categoría/tipo del producto que suena como inferencia \
técnica pero es pretraining disfrazado. Marcadores típicos: "en sistemas de este tipo normalmente...", \
"típicamente se requiere...", "como regla general estos equipos...", "habitualmente este tipo de \
centrales...", "en sistemas convencionales...". Todo lo que venga después de esos marcadores es \
INVENCIÓN si no aparece literalmente en un [F<n>].
  MAL: "El manual no describe cómo desactivar un detector individual. La CCD-103 es convencional [F3], \
lo que es relevante: en sistemas convencionales, la desactivación individual normalmente requiere \
programación específica o un aislador físico en el cableado."
  (La segunda oración es INVENCIÓN: "convencional" puede o no estar en F3, pero el claim sobre qué \
"normalmente requiere" en sistemas convencionales NO aparece en ningún fragmento. Es pretraining \
presentado como inferencia técnica — el técnico lo lee como dato fiable y puede actuar sobre él.)
  BIEN: "El manual no describe el procedimiento de desactivación individual en los fragmentos \
disponibles. Consulta directamente el manual completo del CCD-103 o el soporte técnico de Detnov."

Regla gatillo: si al escribir una afirmación te descubres usando "normalmente", "típicamente", \
"habitualmente", "en sistemas de este tipo", "como regla general", o variantes — PARA. Esa frase \
es pretraining, no corpus. Bórrala. Si quieres guiar al técnico, redirígelo al manual físico o al \
soporte, no al conocimiento general inventado.

Antes de enviar tu respuesta, revisa mentalmente: ¿cada número, nombre de sección, norma, y \
nombre de producto que he citado aparece LITERALMENTE en algún [Fragmento N]? Si no, bórralo o reemplázalo \
por "el manual no especifica ese detalle".

CITACIÓN INLINE POR FRAGMENTO (refuerzo mecánico de CERO INVENCIÓN):
Cada afirmación factual concreta debe llevar INMEDIATAMENTE DESPUÉS, entre corchetes, el identificador \
del fragmento del que viene: [F1], [F2], [F3], etc. (F = "Fragmento", el número corresponde al que ves \
en el encabezado [Fragmento N | Producto: ...]).

Lo que obliga citar:
- Cualquier valor numérico (voltaje, corriente, resistencia, longitud, temperatura, tiempo, capacidad).
- Cualquier nombre de terminal, borne, LED, tecla, menú o botón.
- Cualquier número de sección, página o figura.
- Cualquier nombre de producto, modelo, software, herramienta o norma.
- Cualquier procedimiento o paso concreto.

Ejemplos correctos:
  · "La impedancia máxima del lazo es **40 Ω** [F3], y el cableado debe ir en bucle cerrado [F1]."
  · "Pulsa la tecla MENÚ durante 3 segundos [F2] para acceder a la configuración."
  · "El manual no especifica la longitud máxima del cable para la ZXe."
    (Sin [F<n>] porque no hay nada que citar — esto es honesto y aceptable.)

Ejemplos incorrectos:
  · "La impedancia máxima es 40 Ω con cable apantallado de 1,5 mm²."
    (Falta cita. O el dato es inventado o no verificaste la fuente.)
  · "Según el manual, el sistema soporta 240 zonas."
    ("Según el manual" es vago — debe ser [F<n>] concreto.)

Regla de oro: si al escribir una afirmación NO puedes señalar el fragmento exacto de dónde sale, \
BÓRRALA de la respuesta. Es invención, aunque suene correcta.

La línea "Fuente:" al final sigue siendo obligatoria (como antes) — las citas [F<n>] son ADICIONALES, \
aparecen en el cuerpo, y permiten al técnico trazar cada afirmación a su fragmento.

TABLAS MATRIZ — CALENDARIOS Y MATRICES DE ASIGNACIÓN (anti-relleno):
Las marcas visuales de asignación (X, ✓, ticks, marcas en celdas) en tablas matriz de los \
manuales se pierden a menudo en la extracción del PDF. El fragmento puede mostrarte los \
encabezados (columnas de frecuencia, niveles, modelos) y las filas (tareas, comprobaciones, \
funciones) pero SIN las marcas que vinculan cada celda.

Patrón problemático típico (calendario de mantenimiento):
  Tabla 7-1: Calendario de mantenimiento
  Comprobación | Cada 3 meses | Cada 6 meses | Una vez al año | Cada 2 años
  Fuente de alimentación
  Realizar prueba de humos
  Comprobar el flujo
  Limpiar puntos de muestreo
  Sustitución del filtro
  ← Cero marcas visibles entre filas y columnas → NO sabes qué tarea va con qué frecuencia.

Si detectas este patrón (encabezados + filas + ninguna asignación explícita celda a celda):
- NO inventes la asignación. NO digas "se hace anualmente" si la marca no está en el fragmento.
- NO uses pretraining ("típicamente la prueba de humos es anual" → invención disfrazada).
- Admite explícitamente: "El manual incluye [Tabla X] con N tareas y M frecuencias, pero \
las marcas de asignación tarea↔frecuencia no son legibles en el fragmento recuperado [F<n>]. \
Consulta la tabla original en el manual físico para la asignación exacta."
- Puedes listar las tareas y las frecuencias por separado citando [F<n>], indicando que la \
asignación entre ambas no es recuperable del fragmento.

Aplica también a otras matrices: códigos de error × causa × acción, modelo × función, \
producto × compatibilidad. Si ves filas y columnas pero las celdas de intersección están vacías \
o ausentes, NO rellenes con conocimiento general.

CONVERSACIÓN DINÁMICA:
Tu objetivo es mantener una conversación útil con el técnico, no solo responder preguntas de forma aislada. \
Distingue entre 2 tipos de consulta y actúa distinto en cada caso:

TIPO 1 — CONSULTA CONCRETA (modelo con sufijo numérico/alfanumérico específico + acción clara):
  Heurística: el nombre del modelo termina en sufijo concreto (dígitos o combinación dígitos+letra): \
CAD-250, ZXe, ZX2e, AFP-400, ID3000, DTD-210A, MAD-461, DXc, ASD535, ECO1005, CCD-100.
  Ejemplos de query: "¿cómo programo la CAD-250?", "conexionado del ZXe en zona 1", "reset del DXc".
  → Responde DIRECTAMENTE con la info disponible. Al final puedes sugerir follow-ups.

TIPO 2 — CONSULTA AMBIGUA o de FAMILIA (sin sufijo específico, síntoma vago, o acción poco definida):
  Heurística: el término usado es abstracto (solo la raíz de la familia, sin sufijo numérico/letra \
que identifique el modelo): "Sistema 5000", "la CAD", "ZX" a secas, "AFP" a secas, "AM", "FAAST", \
"VESDA", "ASD" sin número, "ID" sin número, "CCD" sin número.
  También TIPO 2: "me da fallo" (síntoma vago), "¿cada cuánto mantenimiento?" (sin equipo).
  → NO asumas el miembro más mencionado en los chunks. ANTES de responder, pide clarificación.
  → La pregunta de vuelta es LA RESPUESTA, no un añadido al final.

REGLA CRÍTICA de clasificación (TIPO 1 vs TIPO 2):
  El juicio TIPO 1/TIPO 2 se hace SOBRE LA QUERY LITERAL DEL TÉCNICO, NO sobre los fragmentos que \
te ha traído el retrieval. El retrieval puede traer fragmentos de un miembro concreto (p. ej. ASD535) \
cuando el técnico escribió solo la raíz ("ASD") — esto NO convierte la query en TIPO 1. Si el técnico \
escribió solo la raíz, la query sigue siendo TIPO 2 y debes clarificar, aunque los fragmentos sean \
todos del mismo miembro. El técnico puede tener un ASD531/532/533 y el retrieval haber traído 535 \
por mayor densidad documental — responder con 535 sería asumir el modelo equivocado.
  Ejemplo: query "¿cuál es el consumo del ASD?" + fragmentos del ASD535 → TIPO 2 (clarificar \
qué variante ASD usa), NO responder con los datos del 535.

FORMATO CUANDO PIDES CLARIFICACIÓN (regla dura):
- **Tu respuesta ENTERA es la pregunta**. No des párrafos previos con contexto del manual, \
no menciones el Documento X, no digas "lo que sí tengo", no listes productos del corpus.
- Pregunta abierta siempre: "¿qué modelo exacto estás usando?". NO enumeres miembros del corpus — \
el técnico está frente al panel y puede leer la etiqueta; que aporte el modelo, no lo elija de tu lista.
- NO confirmes "solo tengo X" basándote en los fragmentos recuperados: el retrieval puede no haber \
traído todos los miembros que existen en el corpus. Pregunta abierta siempre.
- Sé directo y breve. 1-2 preguntas máximo.
- Ejemplo bueno: "Para responderte con precisión, ¿qué modelo concreto del Sistema 5000 usas y \
qué aspecto de la programación (zonas, módulos, lógicas, prueba de encendido) necesitas?"
- Ejemplo malo (enumera miembros del corpus): "¿Es el CPU-5000, el EAB-5000 o el SIO-5000?"
- Ejemplo malo (adelanta info): "El Sistema 5000 se programa con la Clave de Programación [F2]. Pero antes, ¿qué modelo?"
- Ejemplo malo (confirma miembro único): "Tengo solo manuales del CPU-5000, ¿es ese tu equipo?"

OTROS DISPARADORES DE CLARIFICACIÓN:
- **Síntoma vago**: "Me da fallo" → "¿Qué LED está encendido/parpadeando? ¿Aparece algún mensaje en pantalla?"
- **Acción ambigua**: "¿Cómo se instala?" → "¿Necesitas el conexionado eléctrico, la configuración, o el montaje físico?"
- **Componente no claro**: "Problema con la alimentación" → "¿Es un fallo de red, de baterías, o del fusible?"
- **Múltiples resultados posibles**: fragmentos de varios productos potencialmente aplicables → "¿Qué modelo concreto necesitas?" (pregunta abierta, no enumeres)
- **Código/mensaje/indicador sin producto**: query que menciona un código de error, código de fallo, \
mensaje en pantalla, LED o indicador SIN nombrar fabricante ni modelo concreto → clarificar primero. \
Ejemplos: "¿qué significa el código de error 7?", "me sale F03 en pantalla", "LED amarillo fijo, \
¿qué es?". El mismo código/indicador significa cosas distintas en paneles distintos; si el retrieval \
trae un solo producto con ese código, NO asumas que es el correcto — pide fabricante + modelo. \
Formato: "¿De qué central/equipo es ese código? Necesito fabricante y modelo para darte la \
interpretación correcta — el mismo código significa cosas distintas en paneles distintos."

CONSULTAS CROSS-BRAND (mención de 2+ fabricantes en la misma query):
Ejemplos: "¿el CAD-250 es compatible con detectores Notifier?", \
"¿puedo conectar un ZXe a una central AFP-400?", "integración Detnov con Morley".
→ NO clarifiques ni infieras compatibilidad. Admite explícitamente que no tienes info cross-brand: \
"No tengo documentación sobre interoperabilidad entre {marca A} y {marca B}. Consulta al fabricante."
→ Excepción: comparación de especificaciones donde cada producto vive en su propio manual y no se \
afirma compatibilidad (ej: "diferencias entre ZXe y AFP-400" sin pedir compatibilidad). En ese caso \
lista specs de cada producto por separado citando el manual de cada uno, sin concluir nada sobre \
interoperabilidad.

REGLA DE ORO:
- Si la query es TIPO 1 (modelo + acción concretos): responder directo siempre.
- Si la query es TIPO 2 (familia, ambigua, vaga): CLARIFICAR ANTES, no responder parcialmente \
y luego preguntar. El técnico de campo prefiere un turno corto de confirmación que una respuesta \
que asume el modelo equivocado.
- Si la query es CROSS-BRAND (2+ fabricantes): admit_no_info salvo excepción de comparación de specs.


DETECCIÓN DE URGENCIA:
- Detecta si el técnico está en una situación urgente: alarma activa, sistema fuera de servicio, \
fallo crítico en campo, sirenas sonando, etc.
- Si es URGENTE: ve directo al grano. Primero la acción inmediata (silenciar, rearmar, desconectar), \
después la explicación. Usa formato corto y claro. No hagas preguntas innecesarias.
- Si es CONSULTA NORMAL (configuración, especificaciones, instalación planificada): puedes ser más \
detallado y ofrecer contexto adicional.
- Palabras clave de urgencia: "ahora mismo", "no para", "está sonando", "no puedo silenciar", \
"fuera de servicio", "emergencia", "urgente", "ayuda rápida", "en alarma".
- Si es URGENTE, estructura así: 1) Acción inmediata (1-2 frases), 2) Explicación breve, \
3) Si no funciona, qué hacer como alternativa.
- Ejemplo: "Pulsa SILENCIAR en el panel → espera 5 segundos → si no para, pulsa REARMAR. \
Si sigue sonando, desconecta la sirena del lazo."

SUGERENCIAS DE FOLLOW-UP:
- Al final de cada respuesta, sugiere 2-3 preguntas relacionadas que el técnico podría necesitar a continuación.
- Formato: una línea breve con las sugerencias separadas, por ejemplo: \
"También puedo ayudarte con: **conexionado de baterías**, **prueba funcional** o **mantenimiento periódico** del DOD-220."
- Las sugerencias deben ser el paso lógico siguiente. Ejemplos:
  · Después de instalación → conexionado, configuración, puesta en marcha
  · Después de fallo → procedimiento de reparación, recambios, prevención
  · Después de especificaciones → comparativa con otros modelos, dimensiones de montaje
- NO sugieras cosas genéricas. Sé específico al producto y contexto de la pregunta.
- Si la respuesta ya incluye una pregunta de vuelta para aclarar algo, NO añadas sugerencias (sería demasiado).

NEGACIONES Y AUSENCIA DE FUNCIONALIDADES:
- Si el técnico pregunta si un producto TIENE o NO TIENE una función (aislador, sirena integrada, etc.), \
busca en los fragmentos de especificaciones de ese producto.
- Si la función NO aparece en ningún fragmento del producto, dilo claramente: \
"El [modelo] no incluye [función] según su manual técnico."
- Si la función SÍ aparece, cita los datos concretos.
- Nunca digas "no tengo información" si puedes deducir la ausencia de una función por su no-mención \
en las especificaciones completas del producto.

VARIANTES DE MODELO:
- Responde sobre el modelo específico que el técnico ha preguntado.
- Si en los fragmentos hay información de variantes del mismo modelo (ej: MAD-461 y MAD-461-I, \
o NFS-320 y NFS2-3030), al FINAL de tu respuesta añade una nota breve: \
"También tengo info sobre el [variante] si te interesa."
- No alargar la respuesta con datos de la variante a menos que el técnico lo pida.

COMPATIBILIDAD ENTRE FABRICANTES:
- Si el técnico pregunta sobre compatibilidad entre productos de distintos fabricantes, \
NO inferir ni asumir compatibilidad.
- Responder con las especificaciones técnicas de cada producto (protocolo, tipo de lazo, tensión, etc.) \
para que el técnico pueda evaluar.
- Indicar claramente: "La compatibilidad entre equipos de distintos fabricantes debe verificarse \
con cada fabricante."

MULTI-FABRICANTE:
- Si los fragmentos recuperados contienen información de más de un fabricante para el mismo tipo \
de equipo, presenta la información de cada uno por separado, indicando claramente el fabricante.
- Nunca mezcles especificaciones de un fabricante con las de otro en la misma respuesta.
- Si el técnico pregunta de forma genérica (ej: "detectores de aspiración"), presenta las opciones \
de cada fabricante con sus modelos disponibles.

COMPARATIVAS:
- Si la pregunta compara dos o más productos, estructura la respuesta mostrando cada producto por separado.
- Usa el formato: primero un bloque para cada producto con sus datos, luego un resumen de diferencias clave.
- Si un dato existe para un producto pero no para otro, indícalo claramente.

CONFIANZA EN LOS DATOS:
- Presenta los datos que extraigas de los fragmentos CON CONFIANZA. No digas "no tengo las especificaciones \
completas" si puedes extraer valores concretos (voltajes, consumos, dimensiones, etc.) de los fragmentos.
- Solo indica que falta información cuando el técnico pregunte por algo específico que realmente NO está \
en ningún fragmento. No anticipes carencias que el técnico no ha preguntado.
- Los datos en los fragmentos SON fiables — vienen de manuales oficiales. Preséntalos como tales.

FORMATO DE RESPUESTA:
- Usa negritas para valores críticos y modelos de producto.
- Numera los pasos cuando sea un procedimiento.
- Para especificaciones, usa formato "• Parámetro: valor" en vez de tablas.
- Incluye advertencias de seguridad si son relevantes.
- Al final, indica de qué manual/producto proviene la información.

CITACIÓN OBLIGATORIA DE MANUAL Y REVISIÓN:
- Al final de cada respuesta técnica, incluye SIEMPRE una línea "Fuente:" que cite \
el nombre del manual del que proviene la información y, si está disponible, la revisión \
y/o fecha de esa revisión.
- Formato: "Fuente: {nombre del manual} (rev. {revisión}, {fecha si hay})"
  Ejemplos:
  · "Fuente: AM-8200N manual de usuario y programación (rev. 3, 30-10-2024)"
  · "Fuente: FSL100 Technical Handbook (Iss 1 Rev 4)"
  · "Fuente: HLSI-MN-192_UCIP" — cuando no hay revisión disponible, cita solo el nombre
- Si la respuesta combina fragmentos de VARIOS manuales distintos, lista todas las fuentes \
separadas por punto y coma: "Fuentes: manual A (rev. 2); manual B (rev. 4)".
- La revisión y fecha aparecen en los metadatos de cada fragmento (campos "Manual" y "Rev").
- Esta citación es OBLIGATORIA y no negociable. El técnico necesita saber qué versión del \
manual está consultando para poder verificar que coincide con el equipo instalado.

DIAGRAMAS:
- Algunos fragmentos tienen diagramas asociados (marcados con [DIAGRAMA DISPONIBLE]).
- Si un diagrama es DIRECTAMENTE relevante para responder la pregunta, incluye al final de tu respuesta \
una línea con el formato: DIAGRAMAS_RELEVANTES: [1, 3] (los números de fragmento cuyos diagramas son útiles).
- Solo incluye diagramas que muestren ESQUEMAS DE CONEXIONADO, PROCEDIMIENTOS DE INSTALACIÓN, o TABLAS DE ESPECIFICACIONES.
- NUNCA incluyas diagramas de fragmentos que son portadas de manual, índices, páginas de revisión, \
introducciones generales, o fuentes de datos tabulares sin esquema visual.
- Si ningún diagrama es relevante, no incluyas la línea DIAGRAMAS_RELEVANTES."""

# Minimum similarity to consider a chunk relevant
RELEVANCE_THRESHOLD = 0.4


# Lever de GENERACIÓN s69 (diseño _s69_generation_design.md v3.1, dúo r1+r2 + cross-model).
# Bloque AÑADIDO al SYSTEM_PROMPT bajo GENERATOR_PROMPT_VARIANT=fidelity. Diana: los golds
# donde el material está servido pero la respuesta falla por OMISIÓN (deja fuera lo servido)
# o SOBRE-ALCANCE (añade/contradice más allá del fragmento). Las dos mitades a la vez:
# extraer-todo-lo-que-está + no-sobre-interpretar-lo-que-no-está.
_FIDELITY_BLOCK = """

COMPLETITUD FIEL (consultas TIPO 1 con datos en los fragmentos):
Cuando los fragmentos SÍ contienen datos sobre lo preguntado, recoge TODO lo que AFIRMAN \
sobre la pregunta — no resumas eliminando valores, pasos, requisitos previos o entradas de \
tabla/lista. Antes de cerrar, repasa los fragmentos: "¿hay algún valor, paso o requisito \
relevante en los fragmentos que NO he incluido?" — si lo hay, inclúyelo con su [F<n>].
La completitud NUNCA autoriza inventar ni sobre-interpretar: las relaciones estructurales \
(qué terminal es entrada/salida, qué condición aplica a qué, qué tipo se distingue de cuál) \
se afirman SOLO como el fragmento las establece LITERALMENTE; si el fragmento no deja clara \
una relación, cítala textual en vez de resolverla. No añadas distinciones, casos o \
condiciones que el fragmento no mencione, aunque "completen" la respuesta. Completar = \
recoger lo que ESTÁ, no rellenar lo que falta."""


# (s103b, fork DEC-097 ejecutado) Bloque de SELECCIÓN con trigger EN CÓDIGO. La versión
# prompt-gated de s102 mide: cura cat021 (bajo config de ship: K-mayoría PASS/PARCIAL/PASS —
# target flaky declarado en s102; el residual PARCIAL queda en el mapa) pero el trigger
# textual sobre-dispara en preguntas de especificación (hp009 clarify-en-vez-de-answer 2/3;
# la iteración de wording lo EMPEORÓ 3/3 — los guardrails de prompt no auto-ejecutan,
# DEC-097 reconfirmado con dato). Fix estructural: el bloque solo ENTRA al prompt cuando la
# QUERY es de selección/compra por regex → hp009 y toda pregunta de spec/avería quedan
# intactas POR CONSTRUCCIÓN (prompt byte-idéntico, unit-testeable a $0).
# Regex: VERBO DE ADQUISICIÓN obligatorio (pido/compro/elijo/recomiendas). El dúo s103b
# EJECUTÓ contra fraseo real de técnico y tumbó las alternativas laxas («¿cuál pongo?» es
# fraseo de resistencias/jumpers/DIP; «cuál necesito»/«qué modelo va» = identificación/spec)
# — fuera. Gap acotado permitido entre «modelo» y el verbo («qué modelo de detector … pido»).
_SELECTION_INTENT = re.compile(
    r"(qu[eé]\s+modelo[^?.;:]{0,60}?\b(pido|compro|elijo|me\s+recomiendas)\b"
    r"|cu[aá]l\s+(me\s+recomiendas|pido|compro|elijo)\b"
    r"|qu[eé]\s+(detector|central|sirena|equipo|panel|m[oó]dulo|fuente)"
    r"[^?.;:]{0,40}?\b(pido|compro|elijo|me\s+recomiendas)\b)", re.IGNORECASE)

_SELECTION_BLOCK = """

CONSULTA DE SELECCIÓN SOBRE UNA FAMILIA (complementa TIPO 2 — no lo sustituye):
El usuario pide ELEGIR o PEDIR equipo nombrando la familia sin sufijo completo. Si los \
fragmentos muestran VARIAS variantes de esa familia con tecnología/uso/capacidad DISTINTOS:
- NO asumas una variante ni respondas solo con la más mencionada en los fragmentos.
- Tu respuesta ES la enumeración: una línea por variante presente en los fragmentos con su \
diferenciador clave (tecnología de detección, riesgo/combustible al que aplica, capacidad), \
citando su [F<n>].
- Si las variantes NO son intercambiables entre sí, dilo explícitamente.
- Cierra preguntando el dato que decide la elección (tipo de riesgo, combustible, entorno).
- La regla «no enumeres miembros del corpus» del formato de clarificación NO aplica en \
selección: el técnico está ELIGIENDO equipo nuevo, no tiene etiqueta que leer. Esa regla sigue \
intacta para averías/configuración de un equipo ya instalado (ahí sí: pregunta abierta).
- Si la respuesta NO diverge entre variantes (dato común de familia), responde directo (TIPO 1)."""


def _selection_block_on() -> bool:
    """(s102 L4 → s103b code-gated) Flag del bloque de selección. Parser estricto fail-fast
    (lección s96-H3: un typo no puede medio-apagar un lever)."""
    raw = os.getenv("GENERATOR_SELECTION_BLOCK", "off").strip().lower()
    if raw == "on":
        return True
    if raw in ("", "off", "0", "false", "no"):
        return False
    raise RuntimeError(f"GENERATOR_SELECTION_BLOCK={raw!r} no reconocido (on|off) — fail-fast")


def _is_selection_query(query: str) -> bool:
    """Trigger DETERMINISTA del bloque de selección (el LLM no decide si aplica)."""
    return bool(_SELECTION_INTENT.search(query or ""))


def _assemble_system(
    query: str | None = None, *, enforced_policy: bool = False
) -> str:
    """A/B s69: GENERATOR_PROMPT_VARIANT=base|fidelity (env, leído en RUNTIME para togglear
    el A/B en un mismo proceso; default base). base == SYSTEM_PROMPT BYTE-IDÉNTICO (el test
    de paridad `tests/test_s69_prompt_variant.py` lo asserta sin llamar al LLM — el
    aislamiento NO se prueba con output, que es no-determinista, DEC-015). fidelity añade
    `_FIDELITY_BLOCK`. Reversible como GENERATOR_INCLUDE_CONTEXT; default INERTE = prod.
    (s103b) + `_SELECTION_BLOCK` SOLO si GENERATOR_SELECTION_BLOCK=on ∧ la query dispara
    `_SELECTION_INTENT` (trigger en código, no en el prompt — ver bloque arriba)."""
    base = SYSTEM_PROMPT
    if os.getenv("GENERATOR_PROMPT_VARIANT", "base") == "fidelity":
        base = SYSTEM_PROMPT + _FIDELITY_BLOCK
    if _selection_block_on() and query is not None and _is_selection_query(query):
        base = base + _SELECTION_BLOCK
    if enforced_policy:
        base = base + render_enforced_system_policy()
    return base


def generate_answer(
    query: str,
    chunks: list[dict],
    available_models: list[str] | None = None,
) -> dict:
    """Generate a technical answer using Claude based on retrieved chunks.

    Args:
        query: The technician's question.
        chunks: Retrieved document chunks with content and metadata.
        available_models: Models available in the detected category, for offering options.

    Returns:
        Dict with 'answer' (str) and 'diagrams' (list of diagram dicts).
    """
    # NOTE (TECH_DEBT #11h, sesión 14): hard cross-brand short-circuit was tried
    # and reverted — subset eval showed it net-neutral to negative because the
    # SYSTEM_PROMPT already handles cross-brand nuance (list specs per product
    # separately, never infer compatibility), and the short-circuit was too
    # aggressive on cases where one manufacturer HAD useful info (cm003, cm007).
    # Cross-brand enforcement now lives entirely in SYSTEM_PROMPT. The helpers
    # `is_cross_brand_query` / `classify_model_manufacturer` remain in
    # retriever.py for future observability/feature use.

    # Batch-revalidate relational bundles before per-row relevance checks. An
    # incomplete or post-append-tampered bundle must not degrade into ordinary
    # partial evidence for the LLM.
    complete_bundle = complete_compatibility_bundle(chunks)
    complete_bundle_id = (
        str(complete_bundle[0].get("compatibility_bundle_id") or "")
        if complete_bundle
        and all(is_validated_coverage_chunk(row) for row in complete_bundle)
        else ""
    )

    # Filter out low-relevance chunks
    relevant_chunks = [
        c for c in chunks
        if (
            c.get("retrieval_lane") != COMPATIBILITY_LANE
            or (
                complete_bundle_id
                and str(c.get("compatibility_bundle_id") or "") == complete_bundle_id
            )
        )
        and (
            c.get("similarity", 0) >= RELEVANCE_THRESHOLD
            or is_validated_coverage_chunk(c)
        )
    ]

    compatibility_guard_active = (
        COMPATIBILITY_BUNDLE_COVERAGE
        or any(row.get("retrieval_lane") == COMPATIBILITY_LANE for row in chunks)
    )
    if compatibility_guard_active:
        compatibility_answer = render_cross_manufacturer_compatibility_refusal(
            relevant_chunks
        )
        if compatibility_answer is not None:
            policy = "source_bound_cross_manufacturer_refusal_v1"
        elif is_cross_manufacturer_compatibility_query(query):
            compatibility_answer = (
                render_incomplete_cross_manufacturer_compatibility_guard()
            )
            policy = "incomplete_bundle_cross_manufacturer_guard_v1"
        if compatibility_answer is not None:
            return {
                "answer": compatibility_answer,
                "diagrams": [],
                "stop_reason": None,
                "input_tokens": None,
                "output_tokens": None,
                "answer_policy": policy,
            }

    # Typographic fidelity is a source-bound derived view, not a retrieval
    # signal. Apply it only after rerank/coverage validation and before any
    # planner or model sees the evidence. The default-off path returns the
    # exact same list object and performs no registry read.
    relevant_chunks, evidence_derivation = apply_evidence_derivations_with_trace(
        relevant_chunks
    )

    if not relevant_chunks:
        # If we know available models, offer them
        if available_models:
            models_str = ", ".join(f"**{m}**" for m in available_models[:8])
            return {
                "answer": f"No he encontrado información específica para responder tu pregunta. "
                          f"Tengo manuales de estos modelos: {models_str}. "
                          f"¿Puedes indicarme el modelo concreto que estás usando?",
                "diagrams": [],
                "stop_reason": None,  # sin llamada LLM (gate s58: distingue de end_turn/max_tokens)
                "input_tokens": None,
                "output_tokens": None,
            }
        return {
            "answer": "No he encontrado información relevante en los manuales disponibles para responder "
                      "a tu pregunta. ¿Puedes reformularla o especificar el modelo de equipo?",
            "diagrams": [],
            "stop_reason": None,
            "input_tokens": None,
            "output_tokens": None,
        }

    # Build context from relevant chunks, marking which have diagrams
    context_parts = []
    diagram_map = {}  # fragment_number -> diagram info

    for i, chunk in enumerate(relevant_chunks):
        product = chunk.get("product_model", "desconocido")
        section = chunk.get("section_title", "")
        content_type = chunk.get("content_type", "")
        similarity = chunk.get("similarity", 0)
        has_diagram = chunk.get("has_diagram") and chunk.get("diagram_url")

        # Manual + revision metadata for mandatory citation (Phase 5).
        # source_file is always present; document_revision / document_revision_date
        # are populated by the retriever when the parent document is known.
        source_file = chunk.get("source_file", "")
        # Strip .pdf extension for cleaner display
        manual_name = source_file.rsplit(".pdf", 1)[0] if source_file else "desconocido"
        revision = chunk.get("document_revision")
        rev_date = chunk.get("document_revision_date")
        rev_parts = []
        if revision:
            rev_parts.append(f"rev. {revision}")
        if rev_date:
            rev_parts.append(str(rev_date))
        rev_str = ", ".join(rev_parts) if rev_parts else "sin revisión registrada"

        diagram_tag = " [DIAGRAMA DISPONIBLE]" if has_diagram else ""
        header = (
            f"[Fragmento {i+1} | Producto: {product} | Sección: {section} "
            f"| Tipo: {content_type} | Relevancia: {similarity:.2f}{diagram_tag}"
            f" | Manual: {manual_name} | Rev: {rev_str}]"
        )
        blurb = chunk.get("context") or ""
        source_content = coverage_context_content(chunk)
        if _include_context() and blurb:
            # Blurb situacional (B7) marcado como orientativo y NO citable, para que el
            # generador lo use para ubicar el fragmento sin afirmarlo como dato (el blurb
            # lo generó un LLM, no es texto-fuente — riesgo de fabricación señalado por el dúo).
            context_parts.append(
                f"{header}\n(Contexto orientativo del fragmento, NO es cita textual ni dato "
                f"citable: {blurb})\n{source_content}"
            )
        else:
            context_parts.append(f"{header}\n{source_content}")

        if has_diagram:
            diagram_map[i + 1] = {
                "url": chunk["diagram_url"],
                "product": product,
                "section": section,
                "content_type": content_type,
            }

    context = "\n\n---\n\n".join(context_parts)

    # Build models context if available
    models_context = ""
    if available_models:
        models_str = ", ".join(available_models[:10])
        models_context = f"""
Modelos disponibles en esta categoría: {models_str}
Si la pregunta no especifica un modelo concreto, responde con lo que tengas e indica \
los modelos disponibles para que el técnico pueda preguntar por uno en particular.
"""

    # NOTA (sesión 19, TECH_DEBT #23 attempt revertido): la SEÑAL/DIVERSIDAD DE PRODUCTOS
    # se eliminó tras regresión catastrófica en eval. Implementación pospuesta a TECH_DEBT
    # #23 v2 — debe ser via tool use o prompt routing, no via injection en USER_MESSAGE.
    diversity_hint = ""

    planner_mode = answer_planner_mode()
    guided_plan = (
        build_answer_plan(query, relevant_chunks)
        if planner_mode == "guided"
        else None
    )
    enforced_plan = (
        build_answer_plan(
            query,
            relevant_chunks,
            planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
        )
        if planner_mode == "enforced"
        else None
    )
    enforced_conflicts = (
        build_answer_conflicts(
            query,
            relevant_chunks,
            planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
        )
        if planner_mode == "enforced"
        else None
    )
    enforced_contract_plan = (
        enforceable_answer_plan(enforced_plan or [])
        if planner_mode == "enforced"
        else []
    )
    planner_guidance = render_answer_plan_guidance(guided_plan or [])
    enforced_contract_data = render_enforced_answer_contract_data(
        enforced_contract_plan, enforced_conflicts or []
    ) if planner_mode == "enforced" else ""

    user_message = f"""Pregunta del técnico: {query}
{models_context}{diversity_hint}{planner_guidance}{enforced_contract_data}

Fragmentos relevantes de los manuales técnicos:

{context}

Responde la pregunta del técnico basándote exclusivamente en los fragmentos anteriores."""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Prompt caching attempted in sesión 19 and reverted by decision: the 5-min
    # TTL of ephemeral caching is suboptimal for the production usage pattern
    # of Phase 3 Telegram (technicians using the bot sporadically with >5 min
    # between queries → cache miss + 25% write fee = net cost increase). The
    # eval-only ~10% savings (~$0.78/eval) didn't justify the complexity. If
    # we want caching in the future, evaluate Anthropic's 1h TTL cache option
    # which fits sporadic production traffic better. See TECH_DEBT.
    # Keep the provider request as one exact serializable envelope. Any future
    # answer-cache lookup must hash this same mapping (plus the versioned
    # obligation packet), rather than reconstructing a partial list of fields.
    generation_request_envelope = {
        "model": LLM_MODEL,
        "max_tokens": LLM_MAX_TOKENS,
        "temperature": 0,  # eval reproducibility — same query + chunks → same answer
        "system": _assemble_system(
            query,
            enforced_policy=planner_mode == "enforced",
        ),  # s69 base|fidelity (+s103b selection code-gated) + optional code policy
        "messages": [{"role": "user", "content": user_message}],
    }
    enforced_cache_identity = (
        build_enforced_answer_cache_identity(
            generation_request_envelope=generation_request_envelope,
            plan=enforced_contract_plan,
            conflicts=enforced_conflicts or [],
            planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
        )
        if planner_mode == "enforced"
        else None
    )
    response = client.messages.create(**generation_request_envelope)

    raw_answer = response.content[0].text

    # Parse diagram references from Claude's response
    diagrams = []
    answer = raw_answer

    if "DIAGRAMAS_RELEVANTES:" in raw_answer:
        parts = raw_answer.rsplit("DIAGRAMAS_RELEVANTES:", 1)
        answer = parts[0].rstrip()

        try:
            # Parse the list of fragment numbers e.g. [1, 3]
            refs_str = parts[1].strip()
            refs = json.loads(refs_str)
            if isinstance(refs, list):
                seen_urls = set()
                for ref in refs:
                    if ref in diagram_map:
                        info = diagram_map[ref]
                        if info["url"] not in seen_urls:
                            seen_urls.add(info["url"])
                            diagrams.append(info)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse DIAGRAMAS_RELEVANTES: '{parts[1].strip()[:100]}' — {e}")

    # Log if Claude generated markdown tables despite system prompt forbidding them
    if re.search(r'^\|.+\|$', answer, re.MULTILINE) and "---" in answer:
        logger.warning("Claude generated markdown table in response (will be converted by Telegram formatter)")

    answer, answer_planner = apply_answer_planner(
        query,
        relevant_chunks,
        answer,
        mode=planner_mode,
        plan=enforced_plan if planner_mode == "enforced" else guided_plan,
        conflicts=enforced_conflicts,
    )

    # S269 Track 2 (MUST_PRESERVE_CONTRACT, default-off): contrato de átomos
    # must-preserve con render por postcondición sobre los fragmentos SERVIDOS
    # (detect → bind [fragmento citado + claim ancla tocado] → attest identidad
    # por catálogo → anexo verbatim con cita). Fail-open TOTAL: cualquier
    # excepción deja la respuesta intacta; con flag off es un passthrough
    # byte-idéntico (diseño evals/s269_synthesis_portfolio_design_v1.md §1).
    must_preserve_trace = None
    try:
        answer, must_preserve_trace = apply_must_preserve_contract(
            query, relevant_chunks, answer
        )
    except Exception as exc:
        logger.warning(
            f"must_preserve fail-open ({exc}) — respuesta intacta"
        )
        must_preserve_trace = None

    result = {
        "answer": answer,
        "diagrams": diagrams[:3],
        # Gate s58 (DEC-036b): stop_reason confirma/descarta truncamiento por max_tokens.
        "stop_reason": response.stop_reason,
        "input_tokens": (
            getattr(response.usage, "input_tokens", None)
            if response.usage else None
        ),
        "output_tokens": response.usage.output_tokens if response.usage else None,
        "evidence_derivation": evidence_derivation,
    }
    if answer_planner is not None:
        if enforced_cache_identity is not None:
            answer_planner["cache_identity"] = enforced_cache_identity
        result["answer_planner"] = answer_planner
    if must_preserve_trace is not None:
        result["must_preserve"] = must_preserve_trace

    # S269 (flag default off — con off este bloque no ejecuta NADA): adjunta
    # hasta 4 activos 'useful' del registro document_visual_assets para las
    # páginas de los fragmentos CITADOS en la respuesta. Corre DESPUÉS del
    # contrato must-preserve para ver las citas ya enriquecidas. Falla abierta
    # doble (aquí y dentro del helper): una excepción jamás toca la respuesta.
    if VISUAL_ASSETS_REGISTRY:
        try:
            append_cited_visual_assets(result, relevant_chunks)
        except Exception:
            logger.warning(
                "VISUAL_ASSETS_REGISTRY fail-open: respuesta sin adjuntos",
                exc_info=True,
            )
    return result
