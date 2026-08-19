# s324j — Briefing del dúo sobre el CABLEADO de la v9 (Protocolo 3, ALTO)

**Qué se revisa**: el commit de cableado del panel (diff completo en
`evals/s324j_cableado_v9.diff`; el código YA está en HEAD — léelo con tools).
**El contrato es `evals/s324i_panel_vercel_propuesta_v9.md`** (DEC-239): el
diseño validado en seis rondas del dúo (r1-r6, tally en
`evals/adversarial_review_log.jsonl`). La pregunta de ESTA revisión no es si el
diseño es bueno — eso ya se adjudicó — sino si el CÓDIGO lo implementa sin
traicionarlo y sin abrir agujeros nuevos.

**Ficheros del cableado** (22): `dashboard/auth.py` (sello, IdentidadNoDisponible,
BackendSupabase, validar_registro_estricto, admitir), `dashboard/cerrojo.py`
(NUEVO — CerrojoSupabase, claves seudónimas, ip: apagada, sonda),
`dashboard/app.py` (puerta con sello + 503 + /salir local + op),
`dashboard/gestion.py` (DUPLICADO, op, revocada_por), `dashboard/datos.py`
(select explícito + 42703), `dashboard/sesion.py` (solo docstring),
`api/index.py` (enchufe), `scripts/s324j_panel_usuario.py` (NUEVO),
`scripts/s324e_invitaciones.py` (PATCH condicional), `migrations/019_*.sql` y
`migrations/020_*.sql`, 7 ficheros de tests nuevos + 2 actualizados, workflow
`.github/workflows/s324j-panel-pg.yml`, runbook `docs/DASHBOARD_DESPLIEGUE.md`.

**Dónde morder (sugerencias, no límites)**:
1. ¿El SQL de `panel_puerta` implementa EXACTAMENTE la semántica del doble en
   memoria (`auth.Cerrojo.admitir`) y la tabla de casos comentada en la 019?
2. ¿La ACL de las migraciones deja algún camino que el código ejerce sin GRANT
   (la clase S-C1), o concede de más?
3. ¿El mapeo de estados a `IdentidadNoDisponible`/`CerrojoNoDisponible`/señuelo
   cubre TODOS los caminos reales del transporte, sin uno que acabe en 500 o en
   «credenciales incorrectas» falso?
4. ¿La puerta de `despachar` (sello + /salir local + cookie borrada) tiene
   algún orden de comprobaciones explotable?
5. ¿Los tests nuevos afirman las conductas del contrato o solo su propia
   implementación? ¿Falta alguna puerta de la v9 §11?

**Verificación ya hecha por el autor** (audítala, no la asumas): suite completa
4515 passed / 60 skipped / 2 xfailed; el gate pg ejecutado contra un Postgres
17 REAL local — 15/15 (ráfaga de 12 hilos admite exactamente FALLOS_LIBRES+1;
cap exacto; política-como-ventana; hermana con recibo; 020 backfill único por
fila); s295 pg intacto 42/42.

**Fuera de alcance**: re-litigar decisiones de la v9 (adjudicadas); el deploy
real (gates del runbook); la medición XFF (gate declarado, ip: apagada).
