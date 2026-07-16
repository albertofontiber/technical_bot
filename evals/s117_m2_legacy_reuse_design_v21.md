# S117 M2 — addendum v2.1

Este addendum prevalece sobre cualquier cláusula incompatible de
`s117_m2_legacy_reuse_design_v2.md`.

## Orden exacto de la política B1/B2/B5

La población comparable reproduce literalmente este orden:

1. `profile_document(raw)`;
2. si `verdict == register_only`, todos sus chunks estructurales se clasifican
   `policy_excluded_register_only`; no se ejecutan B1/B5 ni entran en costes;
3. si el documento es indexable, `chunk_document(raw)`;
4. `detect_language(content)` por chunk;
5. excluir `fr|it|pt|de` como `policy_excluded_language`;
6. en los conservados, `unknown` hereda `profile.dominant`;
7. el ordinal renumerado se calcula solo como diagnóstico y no cambia el ID
   estructural S117 ni participa en matching;
8. B5 usa `sample = " ".join(content de los primeros cuatro conservados)` y
   aplica metadata únicamente a los conservados.

El total terminal `policy_excluded` se descompone en `register_only` e idioma.

## Runtime congelado

M2 exige exactamente:

- Python `3.14.3`;
- `lingua-language-detector==2.2.0`;
- `psycopg2-binary==2.9.11`;
- `PyYAML==6.0.3`.

Cualquier drift da NO-GO antes de abrir la conexión.

## Estado documental productivo

El target debe resolver por SHA exacto y único y su fila `documents` debe tener
`status='active'`, coherente con el filtro productivo actual. Otros estados
(`superseded`, `draft`, `retired`, `needs_review` o desconocidos) caen en
`document_status_excluded`, se desglosan por estado y no entran en el residual
productivo.

`target_document_unresolved` queda reservado para ausencia, placeholder o
ambigüedad del SHA. El status del `document_id` legacy del donor sigue siendo
solo diagnóstico y nunca se copia.

## Workloads de coste reproducibles

No se calculan USD ni se consultan precios.

Para el **residual estricto** y el **techo estructural** se reporta:

- contextualizaciones necesarias;
- caracteres exactos efectivos de input contextual, después de truncar
  documento a 200.000 y chunk a 6.000 e incluyendo los wrappers/instrucción;
- proxy de tokens de input `ceil(caracteres/4)`, rotulado como estimación;
- techo de tokens de output `llamadas * 200`;
- embeddings necesarios;
- para filas con contexto reutilizado pero vector no reutilizable, caracteres
  exactos efectivos del embedding;
- para filas cuyo contexto debe generarse, límite inferior de caracteres
  (contenido efectivo) y límite superior `16.000 * filas`, más sus proxies
  `ceil(chars/4)`; no se inventa el tamaño del contexto aún no generado.

`policy_excluded`, `target_document_unresolved` y
`document_status_excluded` nunca se suman al workload productivo. El techo
estructural es una oportunidad no autorizante, no una previsión de gasto.
