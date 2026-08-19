# s325h-c — Propuesta (r2): instrumentar por qué las deps no estaban en disco, y corregir el registro de DEC-238

**Impacto: MEDIO** (tooling de arranque cloud; no toca retrieval, corpus, esquema ni producción).

## 1. El hecho medido (esta VM)

- Boot derivado `ahora − /proc/uptime` = **2026-08-19T14:12:33Z**; doble lectura de uptime
  (119,39 s → 174,81 s, +55,4 s vs +55 s de reloj): monótona, sin reinicio a mitad de sesión.
- Marcador `…/dist-packages/.technical_bot_deps_663fae88…` mtime **14:14:12,565Z** = 99 s DESPUÉS
  del boot. `install-deps.sh` no re-estampa cuando la caché sirve (`exit 0` sin tocarlo), así que
  ese mtime implica rama de instalación real.
- **163 de 164** entradas de `/usr/local/lib/python3.11/dist-packages` escritas después del boot;
  única excepción `uno.pth` (31-mar, imagen base). Ventana 14:13:16,28 → 14:14:12,57 = **56,3 s**.
- El hook imprimió «deps: ya instaladas (663fae88) — se salta la instalación»: cierto, y no prueba
  persistencia — el setup script dejó el marcador ~90 s antes, en esta misma VM.

**Alcance exacto de la conclusión**: lo PROBADO es que *las deps no estaban en disco al arrancar*.
«La caché no persiste purelib» es la lectura más probable, **no** una propiedad probada. En
cualquier caso, la premisa central de DEC-238 («las sesiones siguientes arrancan con las deps en
disco, ~7 días») no se sostiene: el ahorro esperado (~77 s → ~30 s) no existe hoy.

## 2. Qué se cambia

**(a) `.claude/hooks/install-deps.sh`** — traza de diagnóstico justo tras el bloque centinela y
ANTES del primer `pip`, es decir antes del `rm -f` de huérfanos que borraba la evidencia. Declara
cuál de tres causas se dio: (a) sin marcador; (b) marcador de huella caduca ⇒ el snapshot SÍ
persistió; (c) huella vigente + sondeo de imports fallido ⇒ persiste y hay corrupción. Va en
**subshell con `|| true`**: es diagnóstico, y bajo `set -e` no puede tumbar el arranque.

**(b) Registro**: addendum de premisa-falsada in-place a DEC-238 (traza, no borrado), **DEC-241**
nueva con la adjudicación, y reconciliación de `ENTORNO_CLOUD.md` (§2, §3.1, arranque en frío, §4)
y del bloque «Estado actual» del PLAN.

**(c) Recibo** `evals/s325h_setup_script_verificacion_v2.json` ampliado con los mtimes.

## 3. Por qué así (BP + estructural + escalable)

- **Estructural**: el `rm -f` destruía la evidencia justo antes de estamparla. Se informa antes de
  tocar nada, y también si `pip` revienta después.
- **Discriminador parcial, declarado como tal**: el cambio mueve la huella (`663fae88` →
  `58aa661d`, porque el script entra en la suya por DEC-238 r2). Si la próxima VM dice «marcador
  previo 663fae88 — huella caduca», el snapshot SÍ persiste (causa b). El converso NO aísla: «no
  traía NINGÚN marcador» ⇒ **(a) ∨ (c)** — un build que nunca corrió tampoco deja marcador.
- **Coste cero en la ruta feliz**: verificado que el control no imprime traza cuando la caché sirve.
- **Verificado en dry-run hermético** (`TB_MARCA_DIR`/`TB_PIP_CMD`), CINCO ramas: (a), (b), (c),
  control, y `MARCA_DIR` ilegible → `exit=0`, el script sobrevive.
- Suite: **4517 passed, 62 skipped, 2 xfailed**.

## 4. Alternativas descartadas

- **Revertir DEC-238 / borrar el setup script**: no hace daño activo (de facto = pre-s325g) y si la
  caché llegara a funcionar el beneficio vuelve gratis; tirarlo es limpieza estética.
- **Wheelhouse versionado en el repo**: cientos de MB binarios en git, no escala, rompe el
  determinismo de `requirements`; el problema es de infra del environment, no del repo.
- **Venv bajo un prefijo que sí viaje**: salida natural SI la causa es (a), pero diseñarla ahora es
  construir sobre una causa no probada (bias #20).
- **No tocar el registro**: dejar una premisa no verificada escrita como hecho en DECISIONS.md es
  exactamente el fallo que este proyecto persigue.

## 5. Gaps y riesgos declarados

1. **La causa raíz NO está determinada.** Se cablea el instrumento, no el arreglo.
2. El `rm -f` de ESTA VM ya borró la evidencia que separaría (a) de (b): sirve para la siguiente.
3. **El instrumento vale menos de lo que sugería la r1**: los mtimes ya hacen (b) poco probable —
   si el snapshot hubiera traído purelib, `pip` sobre requirements satisfechos no reescribiría
   163/164 entradas en 56 s (solo `PyJWT`/`cryptography` llevan `--ignore-installed`). Paga porque
   cuesta cero, pero la pieza que cierra el caso es el dashboard, no esto.
4. La atribución por `/proc/uptime` asume procfs namespaced (verificado s325g, re-contrastado hoy).
5. Lo que está en juego son ~90 s/sesión: no es el cuello de botella del proyecto. El valor
   declarado es corregir el registro y no gastar otra sesión adivinando.

## 6. Ronda 1 del revisor (Fable, 2026-08-19T14:37:32 — **NO SÓLIDO**) y qué se hizo

| # | Hallazgo | Adjudicación |
|---|---|---|
| 1 | **[crítico]** el script no era auditable: no estaba commiteado, el claim «cableado» no tenía evidencia revisable | **ACEPTADO**: se commitea ANTES de esta ronda; el script está en el árbol que el revisor lee |
| 2 | **[medio]** colisión de ID: ya existía un `DEC-240` (panel Vercel, s324j) | **ACEPTADO, verificado** (`DECISIONS.md:7998`): renumerado a **DEC-241** |
| 3 | **[medio]** el discriminador sobre-afirmaba: sin marcador ⇒ (a)∨(c), no (a) | **ACEPTADO**: corregido en el script, en DEC-241 y en el recibo |
| 4 | **[medio]** el dry-run no ejercita el riesgo de `set -e` que yo mismo señalé | **ACEPTADO**: traza en subshell `|| true` + rama de prueba con `MARCA_DIR` ilegible |
| 5 | **[medio, especulativo]** los mtimes ya casi excluyen (b) → el instrumento discrimina algo casi resuelto | **ACEPTADO como límite declarado** (§5.3); no se retira el instrumento: coste cero |
| 6 | **[menor]** los titulares afirmaban propiedad («no persiste») donde lo medido es «no estaban al boot» | **ACEPTADO**: titulares de DEC-241/§4/PLAN reescritos al alcance real |
