# S135 — enmienda v2 de consulta y gold de procedencia

Esta enmienda conserva la cohorte, población, metadatos, brazos, pesos FTS,
PostgreSQL, límites de coste, autorizaciones y gates de V1. Sustituye únicamente
dos partes que V1 demostró no medibles:

1. la pregunta completa con `plainto_tsquery` devolvió 0/24 golds incluso en el
   brazo v2, porque exige simultáneamente todos los lexemas de una pregunta
   natural;
2. la igualdad byte a byte enlazó 22/24 golds. Los otros dos estaban preservados
   exactamente en raw pero divididos en dos chunks v3 contiguos (349 = 323+26
   tokens y 173 = 152+21 tokens).

V1 queda retenido como control negativo y no se reinterpreta como evidencia de
retrieval.

## Consulta v2

La consulta se planifica con `extract_search_keywords` del retriever productivo,
congelado por SHA-256 y anterior a este experimento. Sus hasta tres términos se
unen con OR mediante `websearch_to_tsquery` sobre `spanish_unaccent`. No se
añaden términos, sinónimos ni reglas específicas de la cohorte.

Esto sigue siendo un probe léxico común, no una reproducción del RAG completo:
no incluye vector, HyDE, multi-vector, reranker ni síntesis.

## Gold v3 por procedencia exacta

Para cada gold v2:

1. se tokeniza solo por whitespace, sin minúsculas, stemming ni normalización
   semántica;
2. su secuencia completa debe aparecer exactamente una vez en la secuencia de
   bloques del raw de la misma extracción;
3. ese intervalo se proyecta a sus índices de bloque;
4. los chunks v3 solapados, ordenados por `chunk_index`, deben tener como
   concatenación exactamente la misma secuencia de tokens y cubrir el intervalo
   sin huecos.

El gold candidato es ese bundle de uno o más chunks. Un hit@K exige que todos los
miembros del bundle estén presentes en top K; su rank es el peor rank del bundle.
Cualquier ausencia, ocurrencia múltiple, hueco o token distinto falla cerrado.

Este puente es mecánico y reutilizable para cualquier fabricante. No usa página,
similitud de texto, LLM, adjudicación manual ni conocimiento de la respuesta.

## Gates

Se mantienen 24/24 bundles mapeados, cero pérdidas top-10, Recall@10 y MRR@10 no
inferiores, cero fabricantes con pérdida neta, dos semillas byte-idénticas y
coste externo cero. Un GO continúa siendo solo autorización para avanzar con el
shadow versionado, nunca promoción productiva.
