# s324j — SELLO del dúo sobre el SEGUIMIENTO (v2) — ronda FRESCA que SUPERSEDE

**Briefing COMPACTO y ACOTADO a los tres cierres** (clase DEC-236). **NO** releas
el cableado entero ni `evals/s324j_cableado_terminal.diff` (artefacto de la ronda
anterior, superado). Lee SOLO las regiones que citan los cierres, con tools, y ancla
`fichero:línea`. El diff a atacar es `evals/s324j_seguimiento.diff` (≈300 líneas).

## Qué es esta ronda (y qué NO es)

Ronda **FRESCA** del dúo sobre el SEGUIMIENTO, que **SUPERSEDE —no "completa"—** la
ronda final-seal anterior. Aquélla quedó con el 2º revisor frontera sin cerrar
(`pending_fable`) sobre el snapshot del cableado (SHA `8298c74`); ese snapshot ya no
está intacto —el seguimiento modifica `019`, el test y el workflow— así que **no cabe
emparejar retroactivamente** (el canon liga la pareja por SHA): se sella ESTE snapshot
y se declara el anterior superado. Honestamente: la PR #296 se mergeó a `main`
mientras aquella ronda seguía pendiente, contra el «no mergear» de DEC-240; por eso
esto es rama nueva + PR nueva, y la S-M1 que el revisor cross-model cazó viaja en
`main` hasta que este seguimiento la corrige.

## Los tres cierres a atacar (léelos en el código)

- **S-M1 — el cap volvía a no ser techo** (`migrations/019_panel_usuarios_cerrojo.sql`,
  `panel_puerta`, el bloque del cap, ~líneas 255-285). El DELETE del cap no excluía
  las claves de la PROPIA admisión → con la tabla llena y `[u:existente-más-antigua,
  ip:nueva]` borraba la `u:` existente y el upsert de (4) la recreaba → `cap+1`.
  Cierre: `WHERE clave <> ALL(claves)`. **Ya cableado además** (de la ronda 1 del
  dúo): (a) PRECONDICIÓN declarada `len(claves) <= cap` (estructural: ≤2 claves,
  `cap`=miles; con `cap<len(claves)`, solo en un test, rebasaría — declarado, no
  validado); (b) el comentario ya NO afirma igualdad EXACTA incondicional: el TECHO
  (`<= cap`) se mantiene siempre, la igualdad exacta vale en ausencia de `acierto`
  concurrente (uno que borre una fila ajena entre el conteo y el DELETE deja el
  resultado POR DEBAJO de `cap`, nunca por encima). **Muerde:** ¿la exclusión y la
  aritmética son correctas? ¿la precondición y la cota (`<= cap`, nunca `>`) se
  sostienen en todos los caminos?

- **S-M2 — la carrera exigida, ahora ejercida Y con rigor**
  (`tests/test_s324j_panel_pg.py::test_acierto_concurrente_no_deja_admisiones_sin_contar`).
  v9 §4(c) (908-910) exigía ejercitar con hilos el DELETE concurrente
  `acierto`↔`admitir`. Aserción = LEY DE CONSERVACIÓN
  `admitidos == fallos_finales + retirados` (cada admisión suma 1 vía upsert; cada
  `acierto` retira los `fallos` que borra; un `admitir` bloqueado no suma). **Ya
  endurecido** (ronda 1): captura excepciones de AMBOS hilos (`errores` vacío),
  exige que terminaran (`not is_alive()`) y que el martillo completara las `N`
  admisiones (`hechas == N`) — sin esto una ejecución parcial pasaría la ley en
  vacío. Para entender la semántica lee SOLO `dashboard/auth.py::Cerrojo.admitir` y
  el `acierto` de `dashboard/cerrojo.py` (unas decenas de líneas cada uno). **Muerde:**
  ¿la ley es correcta bajo READ COMMITTED + el advisory lock? ¿un `admitir`
  UPDATE-en-vez-de-upsert la rompería (lo que debe discriminar)? ¿queda alguna vía de
  verde-en-vacío?

- **S-M3 — cobertura del gate** (`.github/workflows/s324j-panel-pg.yml` + el fixture
  `panel` de `tests/test_s324j_panel_pg.py`). (a) El trigger `on.push.paths` ya
  incluye la cola `supabase/migration_proposals/*s295..s299*.sql` y la 016 —
  dependencias de IMPORT del fixture. (b) El fixture aplica la **016 CANÓNICA**
  (`migrations/016_allowlist_invitaciones.sql`) en vez de una copia estrecha que
  divergía en AMBOS sentidos: le faltaban los CHECK `token_hash ~ '^[0-9a-f]{64}$'`
  y de caducidad ≤ 7 días (más laxa), e imponía `nota NOT NULL` donde la 016 la deja
  NULLable (más estricta). Por eso los tokens legacy son ahora hex-64. **Muerde:**
  ¿falta algún path de dependencia real? ¿aplicar la 016 entera contamina algún test
  del panel (su bootstrap puebla `bot_allowlist` desde `user_consent`)? ¿el DROP de
  las dos tablas deja el fixture idempotente entre tests?

## Verificación del autor (audítala contra el código, no la asumas)

- Gate pg contra **PostgreSQL 17 REAL: 19/19** (incluye los 2 tests nuevos).
  CONTROL NEGATIVO ejecutado: quitando `<> ALL(claves)`,
  `test_el_cap_no_sacrifica_una_clave_de_la_propia_admision` falla con `assert 6 == 5`
  (el `cap+1`), y el test viejo de dos-claves-nuevas sigue verde → el test nuevo es el
  discriminante.
- Suite sin red completa (`python -m pytest -q`): **4517 passed, 64 skipped, 2 xfailed**
  (el conteo no cambia: los 2 tests pg nuevos se saltan sin `RGPD_TEST_DATABASE_URL`).
- **NO** afirmo "CI verde": no es auditable desde este snapshot. Cito solo lo corrido aquí.

## Fuera de alcance

El diseño v9 (adjudicado, DEC-239), el cableado ya mergeado salvo donde el
seguimiento lo toca, el deploy real, y la medición XFF (`ip:` apagada).
