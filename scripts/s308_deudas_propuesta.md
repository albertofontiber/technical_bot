# s308 — Propuesta a atacar: backfill #65 + alias #67 + seam de modelo (commit 2d6b43e)

Rama `claude/s308-deudas`. Impacto MEDIO en zona de dolor: la migración ESCRIBE identidad
en `documents` (corpus). Corre `git show 2d6b43e` para el delta.

## OBJETIVO + MÉTRICA (declarados)

Tres GOs explícitos de Alberto: (1) **#65** backfill one-shot de `documents.product_model`
desde los chunks CURADOS (stale post-H0: `MADT235` = `AFP4000` allí, `ART1194` en chunks
curados; casi entra como fuente del inventario en s307); (2) **#67** alias curados de
marca (`lda`→`LDA audioTech`, `argus`→`Argus Security`); (3) `LLM_MODEL` por entorno para
el swap a **Opus 5** (GO de Alberto CON DEC-186 en mano: la clase medida no mejora — el
swap compra lo NO medido; primera eval post-swap exigirá re-baseline, declarado).
**Métrica**: ningún lever de eval; serving byte-idéntico sin variables nuevas; la
migración solo toca los **591 inequívocos** (dimensionado vivo: 0 ambiguos, 413
coinciden, 165 sin chunks curados intactos).

## Qué hay

1. Migración `20260808100000_s308_backfill_documents_pm_v1.sql`: respaldo
   `_s308_backup_documents_pm` (old+new+ts) ANTES del UPDATE; UPDATE desde el respaldo;
   postcondiciones que abortan la transacción entera (n_backup≥500 · MADT235=ART1194 ·
   0 inequívocos residuales); rollback de una sentencia documentado en el header.
2. Alias: `resolve_manufacturer_alias()` (identidad para lo no listado) en
   `manufacturer_in_db` + alias-primero en `_marca_en_consulta` + resolución en la
   entrada de `_inventario_fabricante`.
3. `LLM_MODEL = os.getenv(..., "claude-sonnet-4-6")` — default INERTE (patrón
   CHUNKS_TABLE); smoke e2e REAL con `claude-opus-5`: el aprendizaje de `temperature`
   (#64) disparó en vivo, el testigo confirma el modelo enviado, respuesta citada.

## Claims a atacar

- C1: la migración es segura — respaldo completo ANTES del UPDATE; postcondiciones
  abortan todo; rollback una sentencia. ¿Puede el UPDATE escribir algo sin respaldo?
  ¿El `ON CONFLICT DO NOTHING` deja el respaldo INCOMPLETO si se corre dos veces con
  datos cambiados entre medias?
- C2: nada del serving LEE `documents.product_model` hoy (por eso #65 era latente).
  Grep exhaustivo: ¿qué consumidores existen y alguno cambia de conducta?
- C3: los alias no rompen nada — ¿algún caller dependía del `False` de
  `manufacturer_in_db("lda")`? ¿El mismatch-flow (DEC-059) cambia?
- C4: el seam es inerte sin variable; el smoke pasó por el camino real. ¿Queda algo que
  hardcodee el modelo del generador o se rompa con razonamiento (streaming, budgets)?
- C5: ¿qué NO comprueban las postcondiciones que debería abortar? (¿docs no-activos?
  ¿cadenas supersedes divergentes?)

## Preguntas duras

- La migración toca TAMBIÉN retired/superseded/needs_review — ¿backfillear identidad en
  no-activos es correcto? ¿Alguna cadena de revisiones queda inconsistente?
- ¿`LLM_MAX_TOKENS=3500` va bien con Opus 5 + razonamiento, o el thinking consume del
  budget de salida y trunca? Verifica cómo cuenta la API los tokens de thinking.
- ¿Faltan alias obvios (esser, morley-ias)? ¿El test por subproceso es frágil en CI?
