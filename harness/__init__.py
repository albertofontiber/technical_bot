"""harness/ — la isla de instrumentos de eval/gates, FUERA de `src/` (L2a, s310).

Estos módulos solo los importan `scripts/` y `tests/` (censo s300, contrato L0). El
producto NO puede importarlos: la regla de raíces prohibidas del contrato de imports
(`src/` no importa `harness.*`) nació cerrada ANTES de que este paquete existiera.
Quedan 2 módulos de la isla ANCLADOS en `src/rag/` (`visual_gold`,
`omission_correction`): el probe sellado s270 los importa function-local y el gate C1
rechaza rutas fuera de `scripts/`|`src/` — se mudarán si el probe se re-sella o el
gate se retira (trigger declarado en el blueprint §4-L2a).
"""
