# `scripts/archive/` — scripts one-shot retirados de la superficie activa

Contenido: instrumentos de una sola sesión (probes, gates ya ejecutados, fixes de datos ya
aplicados, freezes/replays cuya evidencia vive en `evals/`) que en el momento de archivarlos tenían
**cero referencias vivas** en `tests/`, `.github/`, `src/`, `docs/`, `config/`, `supabase/`,
`migrations/`, `evals/`, `CLAUDE.md` y el resto de `scripts/`.

**Nada se borró:** están aquí, con su historial de git intacto (`git mv`), y sus artefactos de
salida siguen en `evals/` sin mover — los tests que leen `evals/<stem>_v1.json` no se enteran.

**Antes de resucitar uno:** casi todos resuelven la raíz del repo con
`Path(__file__).resolve().parents[1]`, que aquí apunta a `scripts/` y no a la raíz. Ajusta el índice
del `parents[...]` (o devuélvelo a `scripts/`) antes de ejecutarlo.

Manifiesto completo (qué es cada uno, de qué sesión, por qué se archivó):
[`evals/s284_hygiene_manifest_v1.md`](../../evals/s284_hygiene_manifest_v1.md).
