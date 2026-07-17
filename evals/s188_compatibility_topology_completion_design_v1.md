# S188 — complemento exacto de topología en compatibilidad

## Causa observada

El bundle S126 recuperaba el parent correcto de topología, pero su única tarjeta
exacta conservaba la terminación de salida/retorno y omitía la declaración
literal de topología cerrada situada antes en el mismo chunk. El renderer no
podía expresar esa propiedad sin inferirla.

## Cambio acotado

Versionar el contrato de compatibilidad para permitir hasta dos spans exactos
de `loop_topology`, dentro del límite de cuatro tarjetas por parent del selector
(cinco como máximo en el bundle final al sumar el recibo exacto de roster). La selección
sigue siendo determinista, basada en vocabulario de faceta y sin QID, facts,
respuesta esperada ni texto generado. Se usan raíces morfológicas técnicas
(`cerrad`, `retorn`, `salid`) para cubrir género y número en español.

## Límites de decisión

- El cambio permanece detrás de `COMPATIBILITY_BUNDLE_COVERAGE`, cuyo default es
  `off`.
- Una tarjeta parcial, alterada o con procedencia incompleta continúa fallando
  cerrada.
- El renderer continúa negándose a afirmar interoperabilidad cross-brand.
- El replay conocido puede medir cascada retrieval→respuesta, pero no prueba
  generalización externa ni autoriza producción.
- El NO-GO S127 para inferir compatibilidad desde facetas independientes no se
  reabre ni se contradice.

## Gate local

GO local solo si el bundle conserva tres parents/tres facetas, todos los spans
son exactos, la respuesta incluye la declaración literal de bucle cerrado y
CLIP, no afirma compatibilidad directa, no llama a modelos, no escribe en DB y
la regresión dirigida queda verde.
