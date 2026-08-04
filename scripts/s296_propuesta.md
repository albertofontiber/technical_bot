# Propuesta s296 — seudónimo estable, consentimiento append-only, enlace y marca de calidad

> Revisión NUEVA sobre artefactos NUEVOS. El diseño de retención de s295 (rol dedicado,
> ventana RLS, trigger) ya pasó cuatro rondas y está verde contra PostgreSQL real; aquí se
> le añade encima. Atácalo entero, no des por bueno lo de abajo si el delta lo rompe.

## OBJETIVO + MÉTRICA

**Objetivo**: (a) que la retención no destruya la agrupación del histórico de un técnico;
(b) que los exports dejen de llevar identificadores; (c) poder demostrar qué versión de los
términos aceptó cada uno; (d) habilitar un reconocimiento por CALIDAD del feedback.

**Métrica**: NINGUNA de calidad de respuesta. No toca retrieval ni generación; no hay delta
de eval y no se reclama ninguno. El criterio es corrección del mecanismo y exactitud de lo
declarado al usuario.

## Lo que pidió Alberto, en sus términos

Le expliqué los pendientes de la matriz en lenguaje llano y respondió: le da miedo perder las
consultas de un buen técnico que se vaya («para no perder sus consultas para entrenar al
bot»); quiere que los exports permitan trazar que las preguntas son del mismo técnico; quiere
ser él quien borre a petición, para conservar el material; y quiere poder poner **un bonus por
calidad** al feedback valioso, con la pieza de «cualificar la calidad al revisar».

## El diseño

1. **Seudónimo estable**: código aleatorio por persona en `persona_seudonimo`. Al vencer el
   plazo se ESTAMPA en los registros y se retira el identificador **en la misma sentencia**;
   después se BORRA la correspondencia (punto de no retorno), **solo** para quien ya no tiene
   ninguna fila identificada. Alternativa descartada: HMAC con clave (espacio de ids de
   Telegram enumerable ⇒ reversible con la clave).
2. **Exports**: `_seudonimizar()` sustituye `telegram_user_id`/`display_name` por el código en
   un único punto, y el script **deja de traer `user_consent`** (se traía solo para pegar el
   nombre).
3. **`user_consent` append-only**: PK nueva + UNIQUE (persona, versión); el upsert resuelve
   sobre (persona, versión) en vez de sobre la persona.
4. **`feedback.query_log_id`** con CASCADE, rellenado en escrituras nuevas y solo si la fila
   padre está CONFIRMADA (si no, la FK fallaría y se perdería el feedback entero).
5. **Marca de utilidad** en `answer_feedback` (`corrigio`/`gold`/`corpus`/`ninguna`) +
   `utilidad_revisada_at`. **`service_role` pierde el UPDATE de TABLA** y recibe UPDATE de
   COLUMNA sobre lo que el voto necesita ⇒ el dato que sostendría un bonus no es escribible
   desde el canal por el que habla el interesado.
6. **`TERMS_VERSION` v6 → v7**: el aviso decía «no se usa para perfilarte ni para decisiones
   sobre ti» y un bonus lo es. Ahora declara el reconocimiento, que la marca la pone una
   persona y que cualquier decisión la toma una persona.

## Verificado

**19/19 contra PostgreSQL real en CI** (las dos migraciones aplicadas en orden): corpus
agrupado bajo el MISMO código tras la retención · vínculo destruido solo cuando no queda nada
identificado · el bot sin acceso a la marca ni al seudónimo · aceptación conservada por
versión · `feedback` cascadea · nadie se queda fuera por no tener código. Suite completa: en
ejecución al escribir esto.

**Dos fallos que el CI destapó y van corregidos**: (a) quien no tuviera código quedaba fuera
de la retención en silencio; (b) el borrado del vínculo no veía las filas recientes —la propia
política de ventana se las oculta al rol— y lo destruía antes de tiempo, partiendo el corpus
en dos códigos; resuelto con `rgpd_quedan_identificados()`, SECURITY DEFINER.

## Gaps y riesgos declarados

1. `persona_seudonimo` **es dato personal mientras existe**; entra en la matriz y en la
   supresión a petición.
2. `user_consent` queda FUERA de `rgpd_quedan_identificados()` a propósito: si contase, el
   vínculo no se destruiría jamás. Consecuencia declarada: puede quedar una fila de
   consentimiento con el identificador tras la retención.
3. La emisión del código en `/accept` es **fail-open**.
4. Las filas de `feedback` anteriores a s296 quedan huérfanas (solo tienen texto).
5. Riesgo de PRODUCTO, no legal: pagar por feedback cambia lo que el feedback mide.
6. No soy asesor legal.
7. Deuda declarada y no resuelta: dos canales de feedback donde lo BP sería uno.

## Lo que te pido que ataques

¿El seudónimo es realmente estable y único por persona en todos los caminos (emisión en
`/accept`, backfill, emisión desde el job)? ¿Hay alguna carrera que pueda dar dos códigos a la
misma persona, o el mismo a dos? ¿El orden estampar→borrar es correcto ante fallo parcial?
¿`rgpd_quedan_identificados` como SECURITY DEFINER abre algo? ¿La pérdida del UPDATE de tabla
en `answer_feedback` rompe el upsert del voto en algún caso? ¿El aviso v7 declara de más o de
menos sobre el reconocimiento? ¿Los tests nuevos prueban lo que dicen?
