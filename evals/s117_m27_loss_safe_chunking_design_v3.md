# S117 M2.7C — addendum de binding por intervalos v3

Este addendum supersede v2 únicamente en el contrato `contenido ↔ span` del
probe. Conserva identidad, autoridad, población, delta, prohibiciones y Capa C
de v2.

## Evidencia del intento v1

Los dos seeds preregistrados v1 fallaron de forma idéntica y antes de escribir
salida. El gate exact-span-group rechazó seis filas en tres documentos. No era
una pérdida: un bloque largo se divide en varias filas con el mismo span raw y
`_cleanup` puede fusionar el último fragmento corto con el bloque siguiente.
Esto produce de forma legítima spans consecutivos `(n,n)` y `(n,n+1)`.

Por tanto, exigir grupos de spans exactos no solapados confunde intervalos de
contenido con particiones de bloques. Relajar el check sin un modelo más fuerte
sería un falso GO.

## Contrato v3

La autoridad continúa siendo exclusivamente la superficie whitespace-only de
los bloques parseados. Su representación operacional son tokens `text.split()`.

1. Los bloques raw, en orden, definen intervalos contiguos y no vacíos sobre un
   único stream global de tokens.
2. Las filas treatment, en orden canónico, definen intervalos contiguos y no
   vacíos sobre su stream global.
3. Ambos streams globales deben ser exactamente iguales token por token.
4. Para cada fila, su span esperado es el primer y último bloque raw cuyos
   intervalos intersectan el intervalo de tokens de esa fila.
5. `source_block_start/end` debe ser exactamente ese span esperado.

Esto permite de forma demostrable splits que comparten bloque y una fila que
cubre el final de un bloque más el siguiente. A la vez rechaza el exploit en el
que `alpha beta` declara span de `alpha` y `gamma` declara spans de
`beta..gamma`: el stream global coincide, pero los intervalos declarados no.

## Implementación diagnóstica

El runner v1 y su prereg quedan inmutables como evidencia del intento fallido.
Un wrapper v2 hash-bound reutiliza su lógica cerrada de población y delta, y
sustituye en scope restaurado únicamente:

- el loader de una preregistración v2 separada;
- el validator exact-span-group por el validator de intervalos descrito arriba;
- la identidad del runner usada en `treatment_contract_sha256`.

Todos los globals sustituidos se restauran en `finally`. La prereg v2 debe
hash-bindear tanto el runner base v1 como el wrapper v2 y sus tests.

## Controles obligatorios

- exploit de desplazamiento contenido/span: rechazo;
- metadata de span manipulada con stream global exacto: rechazo;
- reorder global: rechazo;
- oversized compartido `(n,n)` repetido: aceptación;
- oversized más tail merge `(n,n)` seguido de `(n,n+1)`: aceptación;
- restauración de loader, validator y `__file__` incluso ante excepción;
- todos los gates de v2, dos seeds byte/logical identical y 0 coste externo.

No se autoriza implementación, policy, DB, load, serving, modelos ni M3.
