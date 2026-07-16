# S135 — shadow representativo `chunks_v2` frente a `chunks_v3`

## Pregunta que responde

¿El chunker candidato conserva la capacidad de recuperar evidencia conocida en
una cohorte independiente y anterior a su diseño, cuando ambos brazos usan el
mismo retrieval léxico y los mismos metadatos documentales?

Este instrumento aísla el efecto de chunking y continuidad de contexto. No mide
retrieval vectorial, reranking, síntesis, calidad visual ni fidelidad frente al
PDF. Un GO permite continuar con la integración shadow; no autoriza producción.

## Cohorte congelada

Se usan las 24 preguntas `chosen` de S114: dos por fabricante para doce
fabricantes. S114 se congeló antes de `chunks_v3`; no se escribe ni sustituye
ninguna pregunta y no se seleccionan ejemplos según el resultado.

Cada pregunta conserva como gold el `chunk_id` v2 y su fila fuente exacta.
El gold candidato es el conjunto de filas v3 de la misma extracción cuyo
`content` coincide byte a byte con el contenido gold. Debe existir al menos una
para las 24 preguntas. No se permiten similitud difusa, mismo número de página,
LLM ni adjudicación manual. Si falta una identidad exacta, la ejecución falla
cerrada y se diseña después un puente de procedencia, sin cambiar la cohorte.

## Población comparable

El universo documental procede del manifest canónico S134. Se incluyen todos
los documentos activos cuyo par exacto `(manufacturer, product_model)` aparece
en la cohorte y todas sus extracciones activas. Esto conserva la competencia que
puede sobrevivir a los filtros exactos de la RPC sin procesar fabricantes ajenos.

- brazo v2: chunks base del snapshot congelado;
- brazo v3: materialización local determinista del raw store congelado mediante
  el chunker candidato y el materializador S117;
- ambos brazos: metadatos heredados del registro S134, sin reinferencia.

## Contexto y retrieval común

El índice PostgreSQL usa el contrato productivo de pesos:

- `section_path` o `section_title`: A;
- `content`: B;
- `context`: C;
- configuración `spanish_unaccent` y `plainto_tsquery`.

V2 conserva su contexto congelado. V3 solo reutiliza un contexto v2 cuando hay
un único donante en la misma extracción con igualdad exacta de `content`,
`section_title`, `section_path` y `page_number`; en cualquier otro caso queda
nulo. No se generan contextos, embeddings ni preguntas. Esta regla es
conservadora: una degradación por contexto ausente queda visible como coste de
regeneración necesario, no se oculta mediante heurísticas.

Cada pregunta filtra por fabricante y modelo exactos y solicita hasta 200
resultados para calcular el rank observado. Se publican Recall@5, Recall@10,
MRR@10, número de hits y pérdidas por fabricante.

## Gates preregistrados

GO exige simultáneamente:

1. 24 preguntas, doce fabricantes y dos preguntas por fabricante;
2. todos los documentos/extracciones requeridos presentes en snapshot y raw;
3. 24/24 golds candidatos enlazados por identidad exacta;
4. cero pérdida de un gold v2 que estuviera en top 10;
5. Recall@10 candidato mayor o igual que Recall@10 v2;
6. MRR@10 candidato mayor o igual que MRR@10 v2;
7. cero fabricantes con pérdida neta de hits@10;
8. dos ejecuciones byte-idénticas;
9. PostgreSQL real local, cero red, modelos, embeddings y base de datos remota.

Recall bajo en ambos brazos no invalida por sí solo el chunker, pero abre un
hallazgo downstream de retrieval. Cualquier mejora observada es evidencia de
shadow, no mueve facts a OK sin la regresión congelada correspondiente.

## Límites de coste y autorización

Se autoriza lectura local del snapshot, S114, S134 y de los raw JSON necesarios,
además de escrituras exclusivamente en un PostgreSQL desechable local. Quedan
prohibidos red, APIs, modelos, embeddings, producción, migraciones remotas,
serving y deploy. Coste externo máximo: 0 USD.
