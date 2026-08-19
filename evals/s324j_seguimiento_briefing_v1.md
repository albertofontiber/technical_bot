# s324j — SELLO del dúo sobre el SEGUIMIENTO (Protocolo 3) + cierre del `pending_fable`

**Briefing COMPACTO a propósito** (clase DEC-236): el intento anterior del 2º
revisor frontera murió en `max_tokens` leyendo `evals/s324j_cableado_terminal.diff`
(3768 líneas) entero. **NO leas ese fichero** — es artefacto de la ronda anterior,
superado. Lee los ficheros de código CONCRETOS que se citan abajo, con tools, y
ancla `fichero:línea`.

## Qué es esta ronda (dos cosas en un solo pase)

1. **Cierra el `pending_fable` de DEC-240.** El cableado del panel a Vercel se
   mergeó (PR #296) mientras el dúo final-seal aún corría: el revisor cross-model
   (Sol, ts=2026-08-19T12:25:33) lo vio y cazó S-M1/S-M2/S-M3; el 2º revisor
   frontera no llegó a verlo. Aquí lo ve por primera vez.
2. **Dúo sobre el SEGUIMIENTO.** Los tres cierres que pidió esa ronda Sol, ya
   cableados en el árbol de trabajo (los ves en el manifiesto de cambios del
   snapshot y en `evals/s324j_seguimiento.diff`). Verifícalos: correctos,
   completos, mínimos.

## Contexto: el merge ya ocurrió

La PR #296 se mergeó a `main` con la S-M1 dentro (era menor y está gateada por
`ip:` apagada). Por eso esto es SEGUIMIENTO = rama reiniciada desde `main` + PR
nueva, no reapertura. El seguimiento corrige la S-M1 en `main`.

## Los tres cierres a atacar (léelos en el código)

- **S-M1 — el cap dejaba de ser techo** (`migrations/019_panel_usuarios_cerrojo.sql`,
  función `panel_puerta`, el DELETE del techo, ~líneas 255-278). El DELETE del cap
  no excluía las claves de la PROPIA admisión: con la tabla llena y una admisión
  `[u:existente-más-antigua, ip:nueva]`, borraba la `u:` existente y el upsert de
  (4) la recreaba → la tabla acababa en `cap+1`. Cierre: `WHERE clave <> ALL(claves)`
  en el SELECT interno del DELETE. **Muerde:** ¿es correcto y completo? ¿algún caso
  —`claves` vacías, la poda previa de (2), `len(claves) > cap`, empates de `ultimo`—
  donde el techo se rompa o se borre de más? ¿La aritmética `v_count + v_nuevas - cap`
  sigue cuadrando con la exclusión?

- **S-M2 — la carrera exigida, ahora ejercida**
  (`tests/test_s324j_panel_pg.py::test_acierto_concurrente_no_deja_admisiones_sin_contar`).
  v9 §4(c) (líneas 908-910) exigía EJERCITAR con hilos el DELETE concurrente
  `acierto`↔`admitir`, no modelarlo en secuencia. Añadido: un hilo martillea
  `admitir`, otro `acierto` (`DELETE ... RETURNING fallos`) sobre la misma clave;
  la aserción es una LEY DE CONSERVACIÓN: `admitidos == fallos_finales + retirados`.
  **Muerde:** ¿la ley es correcta bajo READ COMMITTED + el advisory lock? ¿hay una
  carrera en el PROPIO test (conteo compartido entre hilos, `RETURNING`, GIL,
  la poda/cap interna contaminando `retirados`) que la haga pasar vacía o de más?
  ¿`retirados >= 1` garantiza de verdad que la carrera ocurrió y el test no es
  trivialmente verde? ¿Un `admitir` UPDATE-en-vez-de-upsert la rompería (que es
  lo que debe discriminar)?

- **S-M3 — cobertura del gate** (`.github/workflows/s324j-panel-pg.yml` +
  fixture `panel` de `tests/test_s324j_panel_pg.py`). (a) El trigger `on.push.paths`
  ahora incluye la cola `supabase/migration_proposals/*s295..s299*.sql` y la 016 —
  dependencias de IMPORT del fixture que antes no re-disparaban el gate. (b) El
  fixture aplica la **016 CANÓNICA** (`migrations/016_allowlist_invitaciones.sql`)
  en vez de una copia estrecha que había divergido (le faltaba el CHECK
  `token_hash ~ '^[0-9a-f]{64}$'`, la caducidad ≤ 7 días, `nota NOT NULL`), así que
  la 020 se probaba contra una 016 de ficción. **Muerde:** ¿falta algún path de
  dependencia real del fixture? ¿aplicar la 016 entera introduce un efecto que
  contamine los tests del panel (su bootstrap puebla `bot_allowlist` desde
  `user_consent`)? ¿los tokens legacy hex-64 y el DROP de las dos tablas dejan el
  fixture idempotente?

## Dónde morder de nuevo en el CABLEADO (primera vez del 2º revisor; el cross-model ya lo vio)

Lee ficheros, no un diff gigante:
- `migrations/019` `panel_puerta` completo: orden `advisory lock → check-bloqueo →
  poda → cap → upsert-contar`, y `clock_timestamp()` tras el lock. Contrástalo con
  el doble en memoria `dashboard/auth.py::Cerrojo.admitir`. ¿El orden es EXACTO?
- `dashboard/cerrojo.py` `admitir`/`sonda`: fail-OPEN en runtime ante `httpx.HTTPError`,
  fail-CIERRA en la sonda de arranque, `≥400 → CerrojoNoDisponible`, `INCLUIR_CLAVE_IP=False`.
- `dashboard/auth.py`: el sello (`sello_de_registro`, `BackendSupabase.autenticar`,
  `IdentidadNoDisponible`, el señuelo `_SENUELO` una-vez-por-rama), `validar_registro_estricto`.
- `dashboard/app.py` `despachar`: origin+CSRF (local) ANTES de revalidar el sello
  (un RTT), `/salir` exento, `503` sin matar la cookie.
- ACL de `migrations/019`/`020`: ¿algún camino que el código ejerce sin GRANT, o un
  GRANT de más?

## Verificación del autor (audítala contra el código y el snapshot, no la asumas)

- Gate pg contra **PostgreSQL 17 REAL: 19/19** (incluye los 2 tests nuevos).
  CONTROL NEGATIVO ejecutado: quitando `<> ALL(claves)`,
  `test_el_cap_no_sacrifica_una_clave_de_la_propia_admision` falla con `assert 6 == 5`
  (el `cap+1`), y el test viejo de dos-claves-nuevas sigue verde → el test nuevo es
  el discriminante, no ritual.
- Suite sin red completa (`python -m pytest -q`): **4517 passed, 64 skipped, 2 xfailed**
  (el conteo no cambia: los 2 tests pg nuevos se saltan sin `RGPD_TEST_DATABASE_URL`).
- **NO** afirmo "CI verde": no es auditable desde este snapshot (la S-m1 de la ronda
  anterior). Cito solo lo que corrí en esta máquina.

## Fuera de alcance

El diseño v9 (adjudicado, DEC-239), el deploy real, la medición XFF (`ip:` apagada),
y la S-M1 tal como quedó en `main` (este seguimiento la corrige).
