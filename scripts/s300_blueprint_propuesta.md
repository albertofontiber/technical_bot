# s300 — Propuesta a atacar: blueprint de modernización + L0 (contrato de imports en CI)

## OBJETIVO + MÉTRICA (declarados)

**Objetivo**: convertir la arquitectura de `src/` en un invariante de CI (no disciplina)
y fijar el mapa objetivo + lotes de la modernización, SIN reescritura y SIN tocar nada
medido. **Métrica**: no toca ningún lever de eval — es estructura. Listón: (a) el
contrato nace VERDE (8/8) sobre el árbol actual con exactamente las 6 excepciones
verificadas; (b) cero cambios de conducta (L0 es un test + docs); (c) los lotes L1-L3
declaran TODOS sus ajustes de sello antes de mover (los sellos históricos jamás se
reescriben).

## Qué se construyó (commit e41f086, rama claude/s300-blueprint-l0)

1. `tests/test_import_contract.py` — matriz de paquetes (raiz/ingestion/rag/reingest/
   orchestrator/bot), 6 excepciones con ancla+trigger y TRINQUETE (la arista debe
   existir; retirarla obliga a borrar la excepción en el mismo diff), 2 ciclos
   permitidos (SCC>1 exacta contra allowlist; crecer = fallo), cuarentena de
   `rerank_pool_coverage` (3 deudores), cuarentena LÓGICA de la isla (35 módulos),
   precondición 0-imports-dinámicos, cifras de control (113 módulos). Recolector AST
   propio: top-level Y function-local, relativos por `node.level`, stems de scripts/,
   mutaciones de sys.path, Tarjan inline.
2. `docs/BLUEPRINT_MODERNIZACION.md` — diagnóstico medido (acreción, no bola de barro),
   mapa objetivo (src 113→82; harness/ top-level para la isla con alternativa barata
   comparada y criterio de éxito declarado), secuencia L1→L3 con ajustes de sello
   enumerados (incluye los 2 ALTOS del verify previo: `s270_etapa2_probe` sellado
   importa 2 módulos isla function-local; el product adapter sellado importa
   `src.reingest.embed:1204`; `ci.yml:61` invoca catalog_store por ruta), L2b RECORTADO
   (flags.py nuevo sin migrar lectores sellados), lo-que-NO-se-hace, incertidumbres.
3. `docs/PLAN_RAG_2026.md` — frentes (6) dashboard-sin-app (DEC-162f sigue vigente; se
   abren grifos ya construidos), (7) automatización proporcionada (prematuros
   declarados), (8) modernización dirigida por blueprint.

## Claims fuertes del autor (atácalas)

- C1: el contrato nace verde con EXACTAMENTE 6 excepciones (8 aristas) y no hay
  violación de matriz sin listar — el recolector ve top-level y function-local, y el
  trinquete lo hace no-vacuo.
- C2: la cuarentena lógica de la isla da la garantía estructural HOY; el movimiento
  físico (L2a) es legibilidad + sacar la isla del alcance de
  `_implementation_module_index`, no seguridad.
- C3: la lista ISLA (35) es exactamente la isla real: ningún módulo vivo de src/
  importa ninguno; `fake_convo_store` correctamente EXCLUIDO (lo exporta el __init__
  del paquete orchestrator).
- C4: el recolector no tiene falsos negativos relevantes (resolución de relativos,
  `from . import x`, imports de paquete, aliases) — un import que viole la matriz no
  puede colarse sin poner el test rojo.
- C5: los lotes L1-L3 del blueprint enumeran TODOS los ficheros sellados y anclas de
  ruta que cada movimiento exige tocar (tras incorporar los hallazgos del verify).
- C6: L2b recortado y L2a justificado resuelven los dos hallazgos de proporcionalidad
  sin perder el beneficio (registro de flags completo por test-grep; isla protegida por
  contrato desde L0).

## Riesgos YA declarados (atácalos si la mitigación es débil)

- El contrato solo mira `src/` (scripts/tests libres): un script sellado que importe
  módulos isla NO lo caza el contrato — por eso L2a declara la edición del script
  sellado; ¿hay más casos de esa clase?
- La partición a nivel símbolo de L2c queda pendiente-de-diseño declarada (el residual
  será un shim de re-exports, declarado como tal).
- El test de cifras de control (113 módulos) es fricción deliberada: cada módulo nuevo
  en src/ exige tocar el contrato — ¿es proporcionado o va a ser ruido?
- `test_import_contract.py` corre en la suite normal (CI ya la ejecuta); no se añadió
  workflow nuevo.
