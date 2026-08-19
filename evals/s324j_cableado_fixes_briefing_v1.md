# s324j — Ronda de VERIFICACIÓN de los fixes del cableado (Protocolo 3, ALTO)

**Qué se revisa**: el commit `051d0e8`, que aplica los OCHO cierres de la ronda
anterior del dúo sobre el cableado (diff en `evals/s324j_cableado_fixes.diff`;
el código está en HEAD, léelo con tools). El cableado base ya recibió el
veredicto **«FIEL al contrato v9, cerca de SÓLIDO»** (Fable) / 0 críticos
(ambos). Esta ronda NO reabre ni el diseño (v9, adjudicado) ni el cableado (ya
revisado): verifica SOLO que los tres fixes de CÓDIGO no introdujeron una
regresión ni un agujero nuevo.

**Los tres fixes de código a atacar**:
1. `dashboard/cerrojo.py` — `admitir(_sonda=True)` re-lanza el `httpx.HTTPError`
   como `CerrojoNoDisponible` (la sonda de arranque fail-CIERRA; el runtime
   sigue fail-open). ¿El flag puede filtrarse a una llamada de runtime? ¿La
   sonda cubre ahora todos los modos de fallo del arranque?
2. `migrations/019_*.sql` — `panel_puerta` lee el reloj con `clock_timestamp()`
   DESPUÉS del advisory lock, en vez de `now()` en el DECLARE. ¿Sigue siendo
   equivalente a la semántica del doble en memoria? ¿Rompe la tabla de casos o
   la monotonía de `ultimo`? (el gate pg real pasó 15/15, audítalo).
3. `dashboard/app.py::despachar` — origen+CSRF ahora van ANTES de la
   revalidación de sello. ¿El reorden cambia QUÉ se acepta (no solo cuál
   rechazo gana)? ¿Algún camino en que un POST se procese sin revalidar sello,
   o un GET se salte origen? Mira el flujo entero: pública → sesión → (POST:
   origen+CSRF) → (no-/salir: sello) → manejador.

**Los otros cinco cierres** (prosa de runbook/app.py, workflow trigger,
declaración del cap forzable en runbook, autocontrol SQL que acepta '1 day'):
verifica que dicen la verdad contra el código, pero el peso está en los tres
de código.

**Verificación del autor** (audítala): gate pg REAL 15/15 con la 019 nueva;
las dos puertas nuevas (sonda ante httpx → RuntimeError; POST sin CSRF no llama
a `backend.sello`) pasan; suite completa en curso al escribir esto.

**Fuera de alcance**: el diseño v9, el cableado base (ya con veredicto FIEL),
el deploy real, la medición XFF.
