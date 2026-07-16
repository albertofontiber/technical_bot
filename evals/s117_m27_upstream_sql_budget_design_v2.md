# S117 M2.7 — correcciones de contrato v2

Este documento supersede M2.7 v1 en los puntos siguientes. El resto de su
alcance, prohibiciones y fuentes autoritativas permanece vigente.

## 1. Policy y canonicalidad son ejes distintos

La precedencia M2.6 se conserva:

`register_only -> unsupported_language -> duplicate -> eligible`.

`retrieval_policy_class` describe ese resultado. `duplicate_of` describe
canonicalidad. No son equivalentes porque una fila register/language puede ser
además duplicada.

El contrato SQL será:

- `retrieval_policy_class = 'eligible'` exige `duplicate_of IS NULL`;
- `retrieval_policy_class = 'duplicate'` exige `duplicate_of IS NOT NULL`;
- `register_only|unsupported_language` admiten ambos estados de canonicalidad;
- `retrieval_eligible` es generated stored desde
  `retrieval_policy_class = 'eligible' AND duplicate_of IS NULL`.

La frontera común mantiene explícitamente ambos checks aunque el segundo sea
redundante como defensa en profundidad:

```sql
WHERE c.retrieval_eligible
  AND c.duplicate_of IS NULL
```

## 2. La view es frontera lógica, no barrera de privilegios

`security_invoker` obliga al invocador a tener permisos en view y relaciones
base. La especificación declarará grants base explícitos y mínimos para
`service_role` sobre:

- las columnas servidas y de filtro de `chunks_v3`, incluido embedding y
  search_vector usados dentro de las RPC;
- `chunk_materializations_v1(id, state)`;
- `documents(id, source_pdf_sha256, status)`.

También concede SELECT en la view y EXECUTE en las RPC. Revoca view/RPC a
`PUBLIC`, `anon` y `authenticated`. RLS de las tablas base permanece activo;
grants y RLS siguen siendo capas distintas.

La view es la única fuente **lógica**: tests estáticos exigirán que las dos RPC
referencien la view y no `chunks_v3`, materializations o documents directamente.
No se afirma que impida a `service_role` leer las tablas base. La view usa solo
identificadores fully-qualified; `search_path=''` se exige a las funciones, no
a la view.

No habrá SQL HNSW ejecutable en M2.7. Un índice global multigeneración puede
consumir vecinos retired antes del filtro active. La estrategia
generation-scoped/partition y los parámetros iterative scan requieren un gate
posterior con pgvector, EXPLAIN y recall.

FTS queda congelado a:

- config `public.spanish_unaccent`;
- `plainto_tsquery` calculado una vez por request;
- paridad exacta de `product/category/manufacturer` y caps entre canales;
- GIN parcial solo con columnas estáticas de `chunks_v3`.

Inputs inválidos (`limit <= 0`, cap excedido, threshold fuera de rango o query
FTS vacía) deben normalizarse o fallar según regla explícita y testeada; nunca
quedan a semántica accidental de PostgreSQL.

## 3. Presupuesto por request, documento y escenario

La población congelada contiene exactamente:

- 8.493 requests de contexto;
- 405 extraction/document SHAs distintos;
- 8.088 requests posteriores al primero dentro de su documento.

Esos números no prueban cache hits. El runner reportará:

1. escenario `no_cache_conservative`: todo documento+instrucción a input base;
2. escenario `ideal_cache_proxy`: 405 cache-write attempts y 8.088 cache-read
   attempts, usando `ceil(chars/4)`;
3. escenario `minimum_cacheable_char4_proxy`: solo bloques cuyo proxy alcance
   4.096 tokens se tratan como cacheables.

Los tres son planning proxies. Cache creation/read tokens reales y billing solo
se conocerán por usage receipts durante un piloto autorizado.

Antes de generar contexto, los batches Voyage no son exactos. Se publican:

- 8.493 inputs;
- bounds de caracteres/tokens para `context + content`;
- lower/upper bounds de requests bajo los límites congelados de 128 textos y
  320.000 caracteres;
- coste list-price bound sin asumir free tier.

El batch manifest exacto se calcula únicamente después de disponer de los
contextos generados.

## 4. Fidelity exige evidencia o adjudicación

`590/590 classified` no es un criterio de aceptación suficiente.

Para igualdad normalizada o secuencia exacta se registra número de ocurrencias:

- una única ocurrencia exacta + receipts internos válidos puede cerrar la fila
  como `exact_resegmentation_evidence`;
- múltiples donors u ocurrencias exactas pasan a
  `ambiguous_exact_requires_adjudication`.

`near_resegmentation` nunca cierra fidelity automáticamente. Requiere:

- comparación explícita de tokens técnicos protegidos: números, decimales,
  rangos, unidades, códigos y operadores;
- adjudicación de la fila, aunque los tokens protegidos coincidan.

Toda fila live termina en exactamente uno de:

- `exact_resegmentation_evidence`;
- `structure_only_delta` con receipt de campos divergentes;
- `adjudicated_benign_delta` con receipt de adjudicación;
- `material_fidelity_risk`;
- `unresolved_requires_adjudication`.

`LOCAL_READINESS_GO` exige 590/590 con evidencia exacta o adjudicación, cero
`unresolved_requires_adjudication` y cero `material_fidelity_risk`. Si aparece
un riesgo material, se detiene el downstream y se diseña un fix upstream
separado; el auditor no lo corrige.

Projected conserva exactamente la misma taxonomía, pero sus adjudicaciones son
diagnósticas y nunca desbloquean carga live.
