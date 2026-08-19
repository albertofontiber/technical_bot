# s324j — SELLO FINAL del dúo sobre el cableado (Protocolo 3, ALTO) — con el 2º revisor frontera

**Qué es esta ronda**: el dúo COMPLETO (cross-model Sol + 2º revisor frontera
Anthropic) sobre el estado TERMINAL del cableado del panel a Vercel. El crédito
de Anthropic —agotado durante las rondas anteriores, que corrieron solo Sol— se
recargó, así que ESTA ronda cierra el `pending_fable` de DEC-240 con ambos
revisores viendo el mismo snapshot.

**El contrato es `evals/s324i_panel_vercel_propuesta_v9.md`** (diseño validado en
6 rondas, DEC-239) MÁS su ADDENDUM al final (la supersesión de §3.2 por el
cableado: check-de-bloqueo ANTES de sembrar/podar). La pregunta: ¿el código en
HEAD implementa fielmente el contrato + su addendum, sin agujeros?

**El diff a revisar**: `evals/s324j_cableado_terminal.diff` (código en HEAD;
léelo con tools). 21 ficheros: `dashboard/` (auth, cerrojo NUEVO, app, gestion,
datos, sesion), `migrations/019_*.sql` y `020_*.sql`, `scripts/s324j_panel_usuario.py`
(NUEVO) y `s324e_invitaciones.py`, `api/index.py`, 7 tests nuevos + 2
actualizados, el workflow pg.

**Historial de lo ya cazado y cerrado** (para que no re-litigues, pero sí
verifiques que los cierres son fieles) — cuatro rondas de Sol sobre el diff:
- **el fallo de seguridad**: `panel_puerta` sembraba antes de comprobar el
  bloqueo → un atacante bloqueado por `ip:` inflaba el cap. Cerrado
  reordenando (check primero, sin sembrar/podar). ¿El orden en HEAD es
  EXACTAMENTE el del doble en memoria `auth.Cerrojo.admitir`?
- la sonda de arranque fail-CIERRA ante httpx (runtime fail-open); el reloj es
  `clock_timestamp()` tras el lock; origen+CSRF antes de la revalidación de
  sello; paridad acotada a bloqueo/backoff (poda diverge por RGPD); autocontrol
  de la ventana declarado best-effort.

**Dónde morder de nuevo**: (1) el SQL de `panel_puerta` vs el doble en memoria,
línea a línea; (2) la ACL de las migraciones — ¿algún camino que el código
ejerce sin GRANT, o de más?; (3) el mapeo de estados a
`IdentidadNoDisponible`/`CerrojoNoDisponible`/señuelo/503; (4) la puerta de
`despachar` (sello + /salir local + orden de checks); (5) ¿los tests afirman
las conductas del contrato o su propia implementación?

**Verificación del autor** (audítala, no la asumas): suite **4517 passed**; gate
pg contra Postgres 17 REAL **17/17** (ráfaga concurrente admite `FALLOS_LIBRES+1`,
bypass del cap cerrado, política-como-ventana, 020 backfill); CI verde en el head.

**Fuera de alcance**: el diseño v9 (adjudicado), el deploy real, la medición XFF
(gate declarado, `ip:` apagada).
