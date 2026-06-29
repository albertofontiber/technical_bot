# Revisión adversarial FINAL — fold-in corregido de los 29 (s83, zona de dolor identidad) — pre-DB-apply

## Contexto
Tablas de identidad de los 1014 docs PCI. 29 conflicts adjudicados por Alberto (ground-truth de dominio) + foldeados.
Desde la ronda 11 del dúo, **la lógica del fold-in se reescribió de raíz** para arreglar un bug medido: el fold-in
construía el registro de cada conflict DESDE el diff del conflicto, descartando el **set ACORDADO** (módulos que AMBOS
modelos extrajeron) → **78 productos perdidos** en centrales multi-producto (MIDT170, MNDT060, 15088SP). Esta pasada
valida el fold-in CORREGIDO **antes del DB-apply** (stop-line de Alberto). Nada está en DB (tablas `_final`, branch-local).

## Qué cambió desde la ronda 11 (lo que se revisa)
1. **base-unión**: cada conflict ahora parte de la **unión canónica** (`build_models`, MISMA función que los 985:
   Fix1 merge-key=model+canonical + higiene de aliases) y la adjudicación MODIFICA encima. → no se pierde el set acordado.
2. **modo `replace`** (solo FAD/FS): cuando la resolución es un OVERRIDE de limpieza (la extracción tenía descriptivos
   falsos: "FAD-905 2A", "Central Convencional 1 Zona"), `replace:true` ignora la base cruda y usa solo los buckets.
3. **drop por-substring de códigos `NNN-NNN`** (solo MNDT021): refs internas de PCB (124-142/143/128) ambiguas/misleading
   (criterio de Alberto) → se quitan aunque vayan embebidas en el nombre.
4. **buckets de adjudicación**: `software`→primary (doc ES del software), `package`→secondary (bundle/umbrella, p.ej.
   BE-XP/BE-400), `mention`→NO covered (SCD250, MK-DXC, FCPS-24E), `compat`→compatible_with (aplicabilidad), `drop`, `candidate`.
5. correcciones de fidelidad: Pearl PRL-D-1/D-2 → 3 primarios firmes (Alberto confirmó: Pearl=12Ah, D-1/D-2=230V);
   SCD250/MK-DXC → mention; CAD-250 recuperada; BE-XP/BE-400 → package; RS485 = entidad separada.

## Insumos
- `scripts/s83_finalize_tables.py` — `build_resolved` reescrito (base-unión + replace + drop-substring + apply de buckets). LÉELO entero.
- `evals/s83_conflicts_resolved.yaml` — la resolución (buckets por doc).
- `evals/s83_conflicts_groundtruth.yaml` — la prosa de Alberto (LA VERDAD de fidelidad).
- `evals/s83_29_final_dump.md` — el registro final de los 29.
- `evals/s83_document_models_final.jsonl` — las 1014 tablas (2766 productos).

## Lo que pido (bite concreto, anclado)
1. **base-unión correcta**: ¿recupera el set acordado SIN re-introducir ruido? Busca docs donde la unión (a) **sobre-incluya**
   ruido de extracción que debería limpiarse (descriptivos, placeholders, duplicados) — ¿falta algún `replace`?; o (b) **siga
   perdiendo** un producto extraído-por-ambos.
2. **`replace` bien acotado**: ¿solo FAD/FS lo necesitan, o hay otro doc-limpieza contaminado por la unión? ¿algún `replace`
   tira un producto legítimo?
3. **drop-substring** (MNDT021): ¿correcto? ¿el patrón `^\d+-\d+$` puede borrar de más en OTRO doc? (solo MNDT021 lo usa)
4. **fidelidad de buckets vs prosa de Alberto**: recorre los 29. ¿`software`/`package`/`mention`/`compat`/`candidate`
   reflejan lo que Alberto escribió? (p.ej. ¿SCD250/MK-DXC/FCPS-24E bien como mention? ¿BE-XP/BE-400 bien como package?
   ¿Pearl 3 primarios? ¿la central es primary y los módulos secondary?)
5. **bugs en `build_resolved`**: orden de `apply`, `find_record` (match por keyset), manejo de aliases explícitos, `enrich`
   para los Alberto-añadidos. ¿algún registro sin canonical, found_by mal, o alias cross-producto?
6. ¿algo que IMPIDA dar las tablas por buenas para DB-apply?

Distingue BUG (infiel a la prosa / objetivamente mal) de DECISIÓN (criterio defendible). Verifica contra los ficheros (regla C).
