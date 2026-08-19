# s325h-e (r4) — La caché PUEDE persistir (no siempre): cross-check hecho; el AHORRO sigue sin medir

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


## 8. El cross-check que faltaba, HECHO (r3)

Fable r1 #3 bloqueaba el cierre: «viajó en el snapshot» exigía excluir que la VM de las 20:05 fuera
la VM-A viva 6 h, y yo no había registrado su uptime. Lo cierra el registro de s325h, que sella el
uptime en cada línea:

```
instalada 1ead8d63 3ed69f66-… 40.89 2026-08-19T20:06:56Z   ← el arranque
saltada   1ead8d63 c6a2be29-… 14.30 2026-08-19T20:28:51Z   ← resume 1
saltada   1ead8d63 26d13e00-… 15.81 2026-08-19T20:54:36Z   ← resume 2
saltada   1ead8d63 5b85241a-… 22.26 2026-08-19T21:18:50Z   ← boot actual
```

**Uptime 40,89 s en el momento de instalar.** En 41 segundos de vida esa VM no pudo escribir un
fichero con mtime `14:09:35Z`. El marcador viajó en el snapshot ⇒ la caché persiste `site-packages`.
No es la aritmética mtime-vs-uptime que s325h declaró no fiable: es el uptime **sellado en la línea
del propio evento**, que es exactamente para lo que se diseñó ese registro.

**Dos hechos nuevos, más valiosos que el veredicto:**

1. **El snapshot trae `purelib` pero NO el `/tmp` del build** — el marcador viajó, el registro del
   build no (empieza en el arranque de la VM). Confirma **empíricamente** la decisión de s325g de
   mudar el centinela de `/tmp` a site-packages, que se tomó por razonamiento.
2. **Cada `resume` re-provisiona el contenedor y resetea el uptime** (4 `boot_id` en una sesión).
   Invalida toda medida por `/proc/uptime` entre turnos — **incluida la derivación de boot de
   DEC-242**, lo que da una segunda razón, independiente, para desconfiar de aquel diagnóstico.

**Lo que sigue sin probarse, y no se disfraza**: el AHORRO. Que el snapshot porte `purelib` no es
que el mecanismo ahorre; eso exige una VM que arranque y se salte la instalación, y no hay ninguna
medida — las de ese día llevan todas la huella movida. Se medirá sola en cuanto pase un día sin
tocar `install-deps.sh`.


## 9. Ronda 2 (Fable) — **NO SÓLIDO**; los 4 aplicados

| # | Hallazgo | Adjudicación |
|---|---|---|
| 1 | **[medio]** la inversión documental dejó una **contradicción viva**: `ENTORNO_CLOUD` §3.1 conservaba el AVISO de s325h-c («el snapshot no trajo nada») mientras §2 y §4 decían lo contrario, en el mismo fichero. Y yo declaré «§2/§4 y PLAN invertidos» — alcance sobre-afirmado | **ACEPTADO, verificado**: §3.1 reescrito; ya no hay dos veredictos en el doc |
| 2 | **[medio]** «SÍ persiste — PROBADO» compra **uniformidad** que mis propios datos niegan: una VM la recibió y otra no. Lo probado es «puede persistir / al menos a veces». Y «el snapshot trae `purelib`» extiende a 164 entradas lo observado en **un** fichero | **ACEPTADO**: titulares reescritos en DECISIONS, ENTORNO_CLOUD y PLAN; el punto del `purelib` dice ahora «UN fichero; las 164 no se comprobaron» |
| 3 | **[menor]** «el uptime sellado en la línea del propio evento» estira: el sello está en la línea `instalada`, el `mtime` lo ve la traza del hook, que no lleva `boot_id`; se emparejan por identidad de sesión | **ACEPTADO**: matiz escrito — sólido, pero no un sello único |
| 4 | **[menor, especulativo]** «viajó en el snapshot» atribuye **mecanismo**; un volumen persistente daría la misma observación | **ACEPTADO**: se dice «sobrevivió a un arranque anterior»; el mecanismo se declara indistinguible desde dentro |

Es la tercera vez en esta línea de trabajo que el revisor caza la misma clase de error —comprar
uniformidad desde una observación—, dos veces hacia la conclusión pesimista y una hacia la optimista.
Queda anotado como el sesgo a vigilar en este expediente.
