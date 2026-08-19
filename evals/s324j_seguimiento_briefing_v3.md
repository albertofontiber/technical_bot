# s324j — SELLO del dúo sobre el SEGUIMIENTO (v3) — DELTA, con el alcance declarado

**Briefing COMPACTO y ACOTADO al delta** (clase DEC-236). El diff a atacar es
`evals/s324j_seguimiento.diff` (~370 líneas). Lee SOLO las regiones que citan los
cierres, con tools, y ancla `fichero:línea`. **NO** releas el cableado entero ni
`evals/s324j_cableado_terminal.diff`.

## Alcance HONESTO de esta ronda (lo que sella y lo que NO)

Esta ronda **SOMETE A DÚO COMPLETO EL DELTA DEL SEGUIMIENTO** —los cierres
S-M1/S-M2/S-M3 y sus refinamientos— (cross-model + 2º frontera) sobre el MISMO
snapshot; el sello lo da el veredicto, no este briefing.
**NO pretende cerrar el `pending_fable` de DEC-240 sobre el cableado ENTERO**: eso
sería heredar una cobertura que no existe. El cableado se mergeó (PR #296) antes de
que el 2º revisor frontera pudiera verlo (contra el «no mergear» de DEC-240, decisión
de Alberto), y ese revisor no puede ingerir todo el cableado en una pasada (DEC-236,
recurrente: reventó por presupuesto dos veces). Consecuencia declarada, sin adorno:

- **Delta del seguimiento** → dúo completo (esta ronda). Se sella aquí.
- **`panel_puerta` + `cerrojo.admitir`** (el núcleo de seguridad) → el 2º frontera SÍ
  los ve, porque revisar S-M1/S-M2 obliga a leerlos. Cobertura incidental, real.
- **Resto del cableado** (rutas, sello, sesión, gestión) → solo cross-model (Sol),
  como en las rondas previas. **`pending_fable` de DEC-240 SIGUE ABIERTO para esto**
  — es un gap declarado, no dispensado; Alberto decide si se paga con una revisión
  por trozos.

## Los cierres a atacar (ya cableados; verifícalos en el código)

- **S-M1 — el cap volvía a no ser techo** (`migrations/019_panel_usuarios_cerrojo.sql`,
  `panel_puerta`, bloque del cap ~líneas 268-290). Cierre: `WHERE clave <> ALL(claves)`
  en el DELETE del cap (el upsert de (4) recrea las claves de la admisión; sin excluir,
  borrar la `u:` existente-más-antigua daba `cap+1`).
- **Precondición del techo ENFORÇADA y NULL-safe** (paso (0) de `panel_puerta`,
  rondas 1+2+3 de Sol): `IF cap IS NULL OR cardinality(claves) > cap THEN RAISE`.
  El `cap IS NULL` cierra la vía en que un `cap` NULL volvería NULL/falso toda
  comparación `> cap` y colaría el upsert sin cota. Hace el techo INCONDICIONAL en
  vez de depender del caller. Inalcanzable en prod (≤2 claves, cap=miles, nunca
  NULL); si pasara, >=400 → `CerrojoNoDisponible` → 503 (fail-CERRAR, verificado en
  `cerrojo.py:197` / `app.py:296`). El comentario del cap ya no dice «SIEMPRE»
  incondicional, y aclara que la igualdad EXACTA a `cap` sólo vale sin `acierto`
  concurrente (uno ajeno entre el conteo y el DELETE deja el resultado POR DEBAJO de
  `cap`, nunca por encima). **Muerde:** ¿la exclusión + el guard cierran de verdad la
  cota `<= cap` en todos los caminos? ¿el guard aborta sin sembrar? ¿la sonda con
  claves vacías (cardinality 0) sigue pasando?

- **S-M2 — estrés concurrente AÑADIDO, con el alcance declarado sin adorno**
  (`tests/test_s324j_panel_pg.py::test_acierto_concurrente_no_deja_admisiones_sin_contar`).
  El cierre del contrato «el DELETE concurrente no deja admisiones sin contar» queda
  CONDICIONADO a tres patas, y así se declara: (1) la prueba DETERMINISTA de
  upsert-no-UPDATE es el test secuencial `test_el_upsert_recrea_la_fila_que_acierto_borro`;
  (2) el razonamiento READ COMMITTED + advisory lock (documentado en el SQL); (3) este
  test de ESTRÉS PROBABILÍSTICO, que hace PROBABLE la ventana check→DELETE→upsert pero
  NO garantiza haberla tocado en una corrida concreta (declarado en su docstring — una
  corrida puede caer entera entre RPC cerradas). NO se afirma «carrera observada». Ley
  de conservación `sembrado(1) + admitidos == fallos_finales + retirados`, con fila
  SEMBRADA y borrador do-while → `retirados >= 1` determinista (sin rojo espurio).
  Guardas de rigor: `errores` vacío, hilos `not is_alive()`, `hechas == N`. Para la
  semántica lee SOLO `dashboard/auth.py::Cerrojo.admitir` y `acierto` de
  `dashboard/cerrojo.py`. **Muerde:** ¿la ley (con el término `sembrado`) es correcta?
  ¿queda alguna vía de verde-en-vacío? ¿las tres patas juntas cierran el contrato o
  falta algo?

- **S-M3 — cobertura del gate** (`.github/workflows/s324j-panel-pg.yml` + fixture
  `panel`). (a) El trigger ya incluye la cola `supabase/migration_proposals/*s295..s299*`
  y la 016. (b) El fixture aplica la **016 CANÓNICA** en vez de una copia estrecha que
  divergía en AMBOS sentidos: le faltaban los CHECK `token_hash` y de caducidad ≤ 7 días
  (más laxa) e imponía `nota NOT NULL` donde la 016 la deja NULLable (más estricta). Por
  eso los tokens legacy son hex-64. **Muerde:** ¿falta algún path de dependencia? ¿el
  bootstrap de la 016 (puebla `bot_allowlist` desde `user_consent`) contamina algún
  conteo? ¿el DROP de las dos tablas deja el fixture idempotente?

## Verificación del autor (audítala contra el código, no la asumas)

- Gate pg contra **PostgreSQL 17 REAL: 20/20** (2 tests de cap nuevos + el concurrente
  + el guard). CONTROL NEGATIVO ejecutado: quitando `<> ALL(claves)`,
  `test_el_cap_no_sacrifica...` falla con `assert 6 == 5`; el test viejo de
  dos-claves-nuevas sigue verde → el nuevo es el discriminante.
- Suite sin red (`python -m pytest -q`): **4517 passed, 64 skipped, 2 xfailed** (los
  tests pg nuevos se saltan sin DSN; el conteo no cambia).
- **NO** afirmo "CI verde": no auditable desde aquí. Cito solo lo corrido en esta máquina.

## Fuera de alcance

El diseño v9 (adjudicado, DEC-239), el cableado ya mergeado salvo donde el seguimiento
lo toca, el deploy real, la medición XFF (`ip:` apagada), y —declarado arriba— la
revisión 2º-frontera del cableado COMPLETO (gap abierto de DEC-240).

---

## ADDENDUM post-sello (adjudicación de la ronda final, no visto por los revisores)

Las cifras del cuerpo de arriba quedaron desactualizadas al parametrizar el test del
guard DESPUÉS de escribirlas (lo cazó Sol en la ronda final): el gate pg real es
**22/22** contra PostgreSQL 17 (17 originales + concurrente S-M2 + cap-propio S-M1 +
guard ×3), y la suite sin red es **4517 passed, 67 skipped, 2 xfailed** (62 skips
canónicos + los 5 pg nuevos sin DSN; ejecutada completa tras aplicar los nits de
adjudicación). Los cinco nits del dúo final (2 Sol + 3 Fable, todos de
framing/comentario, cero semántica) están aplicados; el gate se re-corrió en verde
después. El texto de arriba se conserva tal como lo vieron los revisores.
