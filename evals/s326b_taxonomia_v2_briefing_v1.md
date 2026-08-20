# s326b — Taxonomía v2→v5 + migración 022: revisión del dúo

**Contexto**: el gate de acuerdo de la taxonomía v1 NO pasó (≈7 desacuerdos de asignación
sobre 35 ≈ 80 % < 85 %) y Alberto adjudicó SIETE cambios: (1) fusionar instalación +
configuración; (2) fusionar catálogo + especificaciones; (3) un mensaje de una sola palabra
(«ZX1e») → `otros`; (4) «¿cómo consigo 32 lazos en la CAD-250?» → catálogo, y compatibilidad
se ACOTA a «¿funciona X con Y?», típicamente entre marcas; (5) «¿qué diferencias hay entre X
e Y?» → catálogo; (6) «¿tienes productos de Luka Modric?» → catálogo; (7) «esto parece
incluir muchos más productos…» NO es una pregunta, es feedback.

**Estado**: cableado + **022 YA APLICADA en producción** por el conector y el histórico
re-clasificado (109/109). Impacto MEDIO (esquema: ALTER CHECK sobre tabla con datos + cambio
de la definición de producto). El diff contra HEAD es exactamente esta sesión.

## Alcance (lee con tools; ancla fichero:línea)

- `migrations/022_taxonomia_v2.sql` — DROP CHECK → mapa → CHECK nuevo → postcondiciones.
- `config/taxonomia_preguntas.yaml` — la lista vigente (v5) + su contrato de versionado.
  (`config/taxonomia_preguntas_v1.yaml` queda como recibo histórico, ya no lo lee nadie.)
- `src/clasificacion.py` — solo `RUTA_TAXONOMIA` y su comentario.
- `tests/test_s326_clasificacion.py` — el cruce YAML↔CHECK vigente y las puertas de la v2.

## Qué afirmamos (verifícalo o refútalo)

1. **El orden de la 022 es el que exige este diseño** (no el único posible — vaciar la tabla
   derivada y reconstruirla evita el estado intermedio, y es el patrón preferido para la
   próxima; corregido tras Sol): el primer intento puso el UPDATE antes del
   DROP y murió con 23514 (el CHECK v1 rechazaba el id v2 que el propio mapa escribía),
   revirtiendo entero. Ahora: DROP → mapa → ADD → postcondiciones, sin BEGIN/COMMIT propios.
2. **El mapa NO es la re-clasificación**: existe solo para que el CHECK nuevo pueda aplicarse
   sin vaciar la tabla; las filas conservan `taxonomia_version` viejo, así que el job las
   re-clasifica TODAS con el prompt nuevo (que es lo único que aplica los puntos 3-7).
3. **Las postcondiciones miran los DOS lados**: el CHECK admite los 8 ids nuevos, no admite
   los 4 retirados, y no quedan filas con id retirado.
4. **Una sola fuente de versión**: el nombre del fichero ya no la lleva (mordió: un cambio de
   descripciones no quiere fichero nuevo); vive en el campo `version`. Cambiar IDS exige
   migración hermana; cambiar descripciones, no — y el test cruza YAML↔CHECK vigente.
5. **La tabla sigue siendo derivada y desechable**: nada del rollback toca dato original.

## Gaps YA declarados (no los re-descubras; atácalos si crees que son más graves)

- `catalogo_especificaciones` = 61,5 % del histórico: la fusión que pidió Alberto hace una
  categoría dominante que discrimina poco. Declarado, no corregido (es su decisión).
- `no_es_pregunta` (11) MEZCLA ruido («ok, entendido») con quejas sustantivas de calidad
  («me has pasado información de la ID3000 que no es de Detnov»). Candidata a partirse en
  una versión futura CON datos, no ahora.
- Residual conocido: «¿me puedes dar las especificaciones técnicas del NC?» sigue en `otros`
  (el modelo no reconoce «NC» como producto). 1/109. Se PARÓ el tuneo aquí a propósito.
- 4 iteraciones de descripciones (v2→v5, ~$0,49 en total) contra el histórico: ¿hay
  overfitting al corpus de 109 filas? Es la pregunta que más nos interesa que ataques.

**Pregunta al revisor**: ¿hay algún camino por el que (a) la 022 deje datos incoherentes con
su CHECK, (b) el contrato YAML↔SQL pueda divergir sin que nada se ponga rojo, o (c) las
descripciones estén ajustadas al histórico de forma que no generalicen a tráfico nuevo?
