# s325h-e (r2) — «La caché no persiste» queda RETIRADO; la contraria NO está probada

**Impacto: MEDIO.** Corrige un hecho FALSO ya mergeado en el registro canónico + el mensaje de un
instrumento. Es una autocorrección: el diagnóstico que sostuve toda la tarde estaba equivocado.

## 1. El dato que invierte

La sesión de las ~20:05 imprimió en su hook:
`deps: marcador previo 663fae88 mtime=2026-08-19T14:09:35Z — huella caduca`

Un marcador de **seis horas antes**, y anterior al boot (14:12:33) de la VM que motivó DEC-242.
Viajó en el snapshot ⇒ la caché conserva `site-packages`.

## 2. Cronología: por qué las dos medidas son compatibles

| hora | VM | qué pasó |
|---|---|---|
| ~14:09:35 | A | construyó la caché, estampó `663fae88` |
| **14:12:33** | la de DEC-242 | arrancó 3 min después y NO la recibió → instaló 163/164 entradas |
| ~20:05 | la de #307 | sí la recibió, pero reinstaló porque #300 movió la huella a `1ead8d63` |

Mi medición era correcta **como observación de una VM**. El error fue generalizar a «el mecanismo».

## 3. Por qué falló mi razonamiento (nombrado para no repetirlo)

- Generalicé de N=1 al mecanismo.
- La cadena «el setup script corrió ⇒ no había caché» era válida para ESA VM; la extendí a todas.
- Las otras tres VMs de s325h apuntaban igual, pero **todas caían en la misma ventana temprana**:
  muestra correlacionada, no confirmación independiente. La conté como refuerzo.
- El instrumento me lo dijo al oído y no lo oí: `deps_cache` afirmaba «la caché del environment no
  las traía» en un caso donde SÍ las traía (con la receta anterior).

## 4. Qué se cambia

- **Código (la raíz)**: `cloud_smoke.py` deja de deducir el CONTENIDO de la caché a partir del coste
  pagado. «se PAGÓ la instalación en este arranque — no dice qué traía la caché: si la huella
  cambió, pudo traer la receta anterior». Contrato fijado en `tests/test_cloud_smoke.py` con un
  assert **negativo** (`"no las traía" not in detalle`) para que la afirmación no pueda volver.
- **DEC-242**: se conserva ÍNTEGRA con marca de conclusión falsa. **DEC-245** con la inversión.
- **ENTORNO_CLOUD §2/§4 y PLAN**: invertidos.
- **DEC-238 vindicada**: se retira la degradación a «redundancia inocua».

## 5. Lo que sobrevive de la sesión equivocada

La traza de diagnóstico de DEC-242 en `install-deps.sh` es **lo que cazó este error**: imprime el
`mtime` del marcador previo en vez de afirmar su origen. Esa calibración la forzó el propio revisor
en la r3 («el mensaje NO asevera persistencia; quien decide es el mtime»).

## 6. Gaps y riesgos declarados

1. **La latencia de publicación del snapshot es hipótesis, NO medida.** Explica el hueco de la VM de
   las 14:12:33, pero no se ha comprobado. No cambia ninguna decisión, por eso no se persigue.
2. **Sigo con N pequeño, ahora en la otra dirección.** Un marcador viejo en una VM prueba que la
   caché PUEDE persistir; no prueba que persista siempre ni cuánto ahorra en la práctica. No he
   medido ningún arranque que se salte la instalación de verdad (todos los de hoy tienen la huella
   movida). **Ésta es la objeción que más quiero que ataques**: ¿estoy repitiendo el error de
   generalizar desde una observación, solo que ahora hacia la conclusión cómoda?
3. El nuevo mensaje del check es más largo y menos tajante; se acepta a cambio de que no mienta.


## 7. Ronda 1 (Fable) — **NO SÓLIDO**; los 5 aplicados, y me cazó repitiendo el error

Respuesta directa a mi propia pregunta del gap 2 — *«¿estoy generalizando otra vez, ahora hacia la
conclusión cómoda?»*—: **sí**. El revisor: *«el salto a "puede persistir" es legítimo con N=1 si el
dato es sólido — pero el dato no lleva el cross-check registrado, y tras una inversión de
diagnóstico el listón es más alto»*.

| # | Hallazgo | Adjudicación |
|---|---|---|
| 1 | **[medio]** la hipótesis de latencia se mergeaba como hecho («**era** una VM que arrancó 3 min antes», «**verificado**: lo consigue») | **ACEPTADO**: ENTORNO_CLOUD y PLAN reescritos; lo verificado es que UN marcador viajó, nada más |
| 2 | **[medio]** «DEC-238 VINDICADA / compra lo que prometía» sobre-afirma: cero arranques con ahorro medido; y la vindicación DEPENDE de la hipótesis de latencia, luego «no cambia ninguna decisión» era falso **en mi propio texto** | **ACEPTADO**: se retira la degradación *por falta de fundamento*, que no es vindicar. El ahorro pasa a «predicción, no medida» |
| 3 | **[medio]** «viajó en el snapshot» es una inferencia mtime→origen — la misma clase que s325h declaró NO fiable — y no registré `boot_id`/uptime de la VM de las 20:05, así que no está excluido que fuera la VM-A viva 6 h | **ACEPTADO, es el hallazgo central**: queda como cross-check pendiente y bloquea el cierre |
| 4 | **[menor]** instancia residual del mismo pecado: la rama «solo saltada» seguía afirmando origen («la caché las trajo hechas») | **ACEPTADO**: ninguna rama afirma ya el origen; se reporta el COSTE |
| 5 | **[menor]** el assert negativo fijaba una FRASE, no la clase — otra redacción pasaría | **ACEPTADO**: ahora exige la cláusula de no-afirmación y prohíbe una lista de veredictos de origen |
