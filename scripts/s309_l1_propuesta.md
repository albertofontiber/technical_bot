# s309/L1 — Propuesta a atacar: catalog_store graduado a src/rag/ (commit 0b40207)

Rama `claude/s309-l1-catalog-store`. Impacto MEDIO en zona de dolor (legacy/estructura +
sello C1). Corre `git show 0b40207` para el delta.

## OBJETIVO + MÉTRICA (declarados)

L1 del blueprint (GO de Alberto): graduar la puerta D1 del catálogo de `scripts/` a
`src/rag/`, retirando E1 del contrato de imports. Byte-invariante: git mv + solo
imports/rutas; ajustes de sello ENUMERADOS antes de mover; ci.yml en el mismo PR.
**Métrica**: ningún lever; paridad de conducta; 299 tests afectados verdes; suite
completa + assessment smoke en curso (el `pipe_sha` cambia → fila en el scoreboard,
como el blueprint predijo).

## Qué se hizo

git mv + `ROOT` parents[2] (el primer smoke cazó al CLI buscando el catálogo en
`src/data`, 0/7 — 36 tests del resolver caían por esa raíz) · resolver con
`from . import catalog_store` estático y sys.path RETIRADO · 6 scripts + 2 tests
migrados · sello :295 ruta nueva y :403 dinámica eliminada · ci.yml Gold gate a la
ruta nueva · contrato L0: E1 borrada (6→5), `SYS_PATH_EXCEPCIONES = set()`, censo
113→114 explicado.

## Claims a atacar

- C1: paridad byte-de-conducta. ¿DOBLE IMPORT bajo dos nombres (`catalog_store` bare vs
  `src.rag.catalog_store`) con estado module-level duplicado en algún camino vivo?
- C2: ¿referencias muertas a `scripts/catalog_store` en el mecanismo del gate
  (stem-alias :1240-1246, release_config, live_receipts)?
- C3: ¿el CLI `python src/rag/catalog_store.py validate` falla en algún entorno (CI
  limpio, cwd distinto)?
- C4: ¿comentarios/reglas stale en test_import_contract tras retirar E1 (docstring :11,
  ejemplo del stem :55, «la vía bare-stem…con E1» ~:302)?
- C5: ¿algo sigue importando por la vía vieja en TODO el repo?

## Preguntas duras

- ¿`sys` sin uso en catalog_resolver? ¿Alguien escribía vía CATALOG_DIR asumiendo la
  ruta vieja? ¿El test de la vía bare-stem sigue teniendo sentido sin E1? ¿El smoke
  basta antes del merge o falta algo?
