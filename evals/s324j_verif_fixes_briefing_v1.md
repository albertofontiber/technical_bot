# s324j — Ronda del dúo sobre los fixes de la RONDA DE VERIFICACIÓN (Protocolo 3, ALTO)

**Qué se revisa**: el commit `0e8d210`, que aplica los cuatro cierres de la
ronda de verificación (diff en `evals/s324j_verif_fixes.diff`; código en HEAD).
El cambio de PESO es de seguridad, así que va al dúo completo pese a ser
acotado.

**El cambio importante — reorden de `panel_puerta`** (`migrations/019_*.sql`):
el check de bloqueo ahora va ANTES de podar/sembrar (era al revés), para que un
intento ya bloqueado NO toque la tabla — cerrando el bypass del cap que un
atacante bloqueado por `ip:` podía forzar. La siembra-separada-antes-del-
FOR-UPDATE se RETIRÓ (el advisory lock global serializa las llamadas, y el
upsert final siembra). **Ataca esto**:
1. ¿El nuevo orden sigue produciendo EXACTAMENTE la semántica del doble en
   memoria `auth.Cerrojo.admitir` (check con `bloqueado()` que solo lee, luego
   `fallo()` que siembra+incrementa)? ¿Alguna secuencia donde diverjan?
2. ¿Retirar la siembra separada reintrodujo el bug S-C3 (la ráfaga contra
   clave fresca entrando entera)? El argumento es que el advisory lock lo
   impide — ¿es correcto bajo READ COMMITTED con el lock de transacción?
3. ¿El upsert final sigue cerrando S6-M2 (acierto concurrente borra la fila)?
4. ¿El check de bloqueo con SELECT simple (sin FOR UPDATE) bajo el advisory
   lock es coherente, o hace falta el FOR UPDATE?

**Los otros tres** (menores): revertir F-m2 (autocontrol vuelve a solo
`24:00:00`), revertir S-m3 (path de test_s295 devuelto al trigger), y el
límite del reloj de pared de `clock_timestamp()` declarado + su test. Verifica
que las reversiones dicen la verdad.

**Verificación del autor** (audítala): gate pg REAL 17/17 —incluye el bypass
del cap cerrado (`test_un_intento_bloqueado_no_siembra_ni_poda`) y la monotonía
de `ultimo` bajo 8 hilos—; suite completa 4517 passed / 62 skipped / 2 xfailed.

**Fuera de alcance**: el diseño v9, el cableado base y su primera ronda de
fixes (ya con veredicto FIEL), el deploy real, la medición XFF.
