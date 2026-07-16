# S117 M2 — aclaración v2.3: dependencia sidecar sellada

Este addendum prevalece sobre la afirmación incompatible de v2 que decía que
el store contenía cero rutas de canal portal. La primera ejecución v2.2 se
detuvo, antes de abrir la base de datos, porque el guard detectó esa premisa
falsa.

## Hecho local reconciliado

Los 1.068 registros congelados incluyen 95 `source_path` bajo cuatro canales
declarados en `config/portal.yaml`: Aritech, Edwards, Kidde y Otros. Los 95
resuelven de forma exacta contra cuatro `_metadata.json` externos al worktree
limpio. B5 usa esos sidecars como provenance autoritativa de producto; ejecutar
el audit sin ellos produciría metadata distinta y un `metadata_miss`
artificial.

## Contrato v2.3

1. Capture y replay requieren un `--sidecar-root` explícito y read-only.
2. Antes de cualquier conexión se verifican ruta relativa, bytes, número de
   entradas, SHA-256 individual y SHA-256 del manifiesto de los cuatro sidecars.
3. La población local debe observar exactamente 95 rutas portal, 95 lookups
   resueltos y cero lookups ausentes.
4. Durante B5 el auditor enlaza temporalmente el root del módulo sidecar al root
   sellado, limpia sus caches antes y después y restaura siempre el estado aun
   si hay excepción. `config/portal.yaml` continúa siendo el fichero del
   worktree y conserva su hash congelado.
5. No se copian PDFs ni sidecars al worktree, no se modifica el corpus y esta
   corrección no cambia el SQL remoto, la taxonomía, el matching ni los límites
   de coste.

La corrección elimina una dependencia ambiental silenciosa. No autoriza acceso
adicional a la base, escrituras, payloads vectoriales ni llamadas a modelos.
