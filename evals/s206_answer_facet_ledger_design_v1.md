# S206 — ledger acotado de facetas de respuesta

## Hipótesis y límite

Los 12 facts residuales de síntesis tienen el contexto necesario ya servido. El
fallo observado es de transmisión: se comprimen relaciones parciales o se omiten
prerrequisitos, límites, estados especiales, advertencias y verificación. S206
prueba si una lista corta de facetas por arquetipo de tarea mejora esa transmisión
sin seleccionar evidencia, inyectar facts ni codificar productos.

El runtime reutiliza el clasificador versionado
`config/retrieval_facets_v4.yaml`; no crea otro router. La primera versión solo
habilita los dos arquetipos medidos: `fault_reset_recovery` y
`program_delay_cause_effect`. Los otros siete quedan byte-inertes. Además, el
ledger solo se renderiza si la pregunta contiene una identidad de producto
reconocida por el catálogo/extractor existente. Una consulta ambigua como
«¿cómo rearmo?» conserva el prompt base y el comportamiento de aclaración.

La taxonomía sigue siendo una hipótesis, no evidencia de generalización. El
mapping residual→faceta del gate local es solo una comprobación de factibilidad;
no cuenta como resultado ni como validación independiente.

## Diferencia respecto de líneas cerradas

- no reconstruye obligaciones S141 ni selecciona IDs o spans;
- no extrae relaciones tipadas, no añade texto determinista y no corrige la respuesta;
- no cambia retrieval, rerank, chunks ni los contextos congelados;
- no activa arquetipos sin medición ni consultas sin producto reconocido;
- `ANSWER_FACET_LEDGER=off` es el default y deja el prompt byte-idéntico.

## Evaluación causal ejecutable

Se ejecutan control y treatment contemporáneos sobre los mismos bytes y con el
mismo Sonnet 4.6. Por cada pregunta hay dos réplicas control y dos treatment, en
orden fijo simétrico `control-1, treatment-1, treatment-2, control-2`, temperatura
cero y sin reintentos. La no-determinación residual del proveedor se trata como
ruido: una relación solo gana crédito si las dos treatment la cubren y ninguna
control la cubre. Cualquier resultado mixto es inconcluso, nunca ganancia.

La cohorte pagada queda congelada antes de abrir outputs:

- targets: `cat018`, `hp002`, `hp011`, `hp017`;
- guardrails del mismo arquetipo con gold versionado: `cat019`, `hp005`;
- canary fault no-target: `s147_src_05`, procedente de un excerpt versionado
  antes de S206. Su pregunta se liga al `product_model`
  mediante una regla determinista y general (prefijo «En el {product_model}»),
  necesaria para satisfacer el guard de identidad; cuatro checks conservadores
  se autoran manualmente desde el excerpt y se congelan antes del A/B;
- control negativo sin coste: la pregunta ambigua y la pregunta held-out `ho006`
  no reciben ledger porque el extractor no resuelve una identidad inequívoca.

No se usan logs orgánicos como validación externa: son demos y ecos del eval.

## Scorer y gate

`scripts/s206_score_answer_facet_ab.py` define el gate causal y mecánico local:

- reconstruye las obligaciones S141 congeladas y usa `validate_answer_plan`;
- exige que la relación y su cita `[F<n>]` coexistan en una ventana acotada que
  satisface `obligation_covered`, y rechaza citas fuera del rango del contexto;
- una pregunta target es completa cuando las dos treatment cubren todas sus
  obligaciones S141; solo cuenta como ganancia si ninguna control era completa;
- protege toda relación previamente cubierta en S163;
- para guardrails, puntúa facts core versionados con el matcher mecánico existente;
- aplica un screen heurístico conservador a la contradicción de cardinalidad de
  `hp017`; no se presenta como detector semántico exhaustivo;
- rechaza `max_tokens`, regresiones estables, citas inválidas o contradicciones;
- el GO local queda pendiente del contrato ejecutable y pre-output
  `s206_semantic_result_review_contract_v1.yaml`. Un runner con JSON Schema obliga
  a GPT-5.6 Sol xhigh y Fable 5 a revisar independientemente las 14 respuestas
  treatment contra todos los fragmentos servidos y los facts protegidos. Cualquier
  unsupported claim, contradicción, cita mal ligada, regresión o desacuerdo veta;
  la revisión no puede rescatar un gate local fallido.

El gate de integración requiere al menos 4 relaciones residuales estables y 2
preguntas target completas, con cero regresiones. Las relaciones S141 son un proxy
diagnóstico, no el KPI canónico. Aunque el gate gane 11 relaciones, alcanzar 98%
solo se declara tras una adjudicación atómica separada que mueva al menos 11 facts
a OK. Un GO menor puede integrarse default-off, pero no se presenta como 98%.

## Límites operativos

Todos los flags, archivos de implementación, contextos y request-envelope hashes
se sellan en el preflight y en un permiso de ejecución posterior a la rerevisión.
El runner exige que no exista ningún checkpoint previo: se ejecuta una sola vez y
no admite resume. Cada recibo se escribe append-only para auditoría; una caída tras
cualquier intento cierra la ejecución sin retry. Un bound conservador de coste se
comprueba sobre las 28 llamadas antes de la primera. No hay retrieval, rerank ni
escritura de base de datos.

`chunks_v3` permanece `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`. Railway es demo y no
condiciona una PR o merge con CI verde.
