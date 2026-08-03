# Propuesta s295 (RONDA 4 — delta de usabilidad del aviso) — acotada

> **Alcance de ESTA revisión**: solo el delta que sigue. El diseño de retención (rol dedicado,
> políticas RLS, trigger, job) ya pasó tres rondas y está verificado contra un PostgreSQL real
> en CI (12/12 verdes). No lo re-revises salvo que el delta lo rompa.

## OBJETIVO + MÉTRICA

**Objetivo**: bajar la fricción del aviso sin perder completitud legal, y declarar la base
jurídica, que no estaba declarada en ninguna parte.

**Métrica**: ninguna de calidad de respuesta (no toca retrieval ni generación). El criterio es
que el aviso siga siendo completo y exacto, y que la primera capa sea legible.

## Contexto: la pregunta de Alberto

Preguntó si convenía **alargar los términos ahora** para cubrir cosas futuras y así evitar
re-aceptaciones. Mi respuesta fue que no: un consentimiento debe ser específico, y una cláusula
que cubra «mejoras futuras» no autoriza nada — solo hace el aviso más vago hoy. Y que el lever
real es **la base jurídica**, no la redacción.

## El delta

1. **Aviso en DOS CAPAS.** `_CONSENT_TERMS` pasa de **1.803 chars / 25 líneas** a **892 / 16**:
   qué se guarda, cuánto, quién lo ve, que hay terceros fuera de la UE, canal de derechos, y un
   puente a `/privacidad`. El detalle completo va a `_PRIVACY_DETAIL` (1.685 chars), servido por
   un comando nuevo **`/privacidad`** registrado **sin gate de consentimiento** (poder leerlo
   antes de aceptar es la condición para que la primera capa cuente como informada). Listado en
   `/help`.
2. **Destinatarios por CATEGORÍA + lista actual** («_Búsqueda en los manuales_: Voyage AI»).
   El RGPD pide «destinatarios *o categorías de destinatarios*»; así, cambiar de proveedor
   dentro de la misma categoría no altera lo aceptado.
3. **Base jurídica declarada en la matriz** como `[DECIDIR]`, con el estado real (hoy:
   consentimiento, vía el gate `/accept`) y la recomendación (interés legítimo para la
   herramienta de trabajo; consentimiento explícito solo para lo que lo requiera, p.ej. memoria
   durable opt-in). Se explica que **la churn de re-aceptaciones es consecuencia de la base
   elegida**, no de la redacción.
4. Todo va en el **mismo salto a `TERMS_VERSION` v5** ⇒ una sola re-aceptación, no dos.

## Tests (29 en el fichero, verdes)

Primera capa lleva lo imprescindible · **techo de 1.000 chars** para que no vuelva a ser un muro
· la segunda capa declara los 6 encargados **y** las 6 categorías · `privacy_command` **no**
consulta `has_consent` (comprobado sobre el código de la función) · comando registrado y
listado · mapa hash↔versión actualizado.

## Gaps y riesgos declarados

1. **No soy asesor legal**; la base jurídica y la suficiencia del aviso las valida cumplimiento.
2. La primera capa dice «proveedores de IA y de alojamiento **fuera de la UE**» sin nombrarlos:
   los nombres están en la segunda capa. Si eso se considerase insuficiente para la primera,
   habría que subirlos — a costa de la longitud.
3. El techo de 1.000 chars es un juicio mío, no una norma.
4. `/privacidad` es un comando: si alguien no lo teclea, no lo lee. Un aviso en dos capas
   siempre apuesta a que la primera basta para decidir.
5. Cambiar la base jurídica NO está hecho: solo declarado como decisión pendiente.

## Lo que te pido que ataques

¿La primera capa omite algo que una persona necesita para decidir? ¿Hay alguna afirmación de la
primera o la segunda capa que ya no case con lo que el código hace? ¿El criterio de
«categorías» está bien aplicado, o hay categorías demasiado vagas? ¿La sección de base jurídica
afirma de más sobre derecho? ¿Los 5 tests nuevos prueban lo que dicen probar?
