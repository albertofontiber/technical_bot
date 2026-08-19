# s325h-d (r2) — Corrección de registro: la doc oficial CONTRADICE mi hipótesis de rutas y desplaza la sospecha fuera del repo (sin cerrarla)

**Impacto: MEDIO** (solo documentación/registro; ningún cambio de código). Modifica el gap principal
de una decisión ya registrada (DEC-242) y retira una vía de diseño que había declarado natural.

## 1. Qué motivó esto

DEC-242 (mergeada en #300) dejó como hipótesis principal: «el snapshot no cubre `/usr/local`».
Alberto preguntó dónde estaba el dashboard del environment; al verificarlo en la doc oficial
—en vez de responder de memoria— resultó que **no existe tal página**, y que la doc contradice
la hipótesis.

## 2. Los hechos nuevos, con cita verbatim de <https://code.claude.com/docs/en/cloud-environments>

1. *«The cache is a filesystem snapshot, so it keeps what the setup script writes to disk.
   Packages you install, Docker images you pull, and files you write all carry over.»*
   → **No hay exclusión de rutas documentada.** La hipótesis de purelib cae.
2. *«The setup script runs first, before Claude Code launches, and only when no cached environment
   exists»*; tabla: *«skipped when a cached environment exists»*.
   → En nuestra VM el setup script **corrió** (marcador a boot+99 s; el hook posterior se saltó la
   instalación por encontrarlo) ⇒ **esa VM no encontró caché**. El problema no es un snapshot que
   llega sin deps: es que **no hay snapshot**.
3. *«The setup script runs again to rebuild the cache when you change the environment's setup script
   or allowed network hosts, and when the cache reaches its expiry after roughly seven days.»*
   → **Alberto confirma no haber tocado ni el script ni los dominios desde que lo pegó**, y las
   cuatro VMs son del mismo día. Ninguna de las tres causas aplica.
4. *«keep the script's total runtime under roughly five minutes so the environment cache can
   build»* → comprobado y descartado: repo de 128 MiB de pack / 488 MB de árbol, `clone --depth 1`
   + instalación ≈ 2-3 min. Margen real pero no enorme.

## 3. Qué se cambia (solo documentación)

- **DEC-242 addendum**: retira la hipótesis de rutas con la cita; reubica la causa fuera del repo;
  retira también la vía «venv bajo un prefijo que sí viaje» (era la salida SI la causa eran las
  rutas); sustituye el gap (iv) «mirar el dashboard» por el experimento de coste cero.
- **ENTORNO_CLOUD.md**: navegación real del campo Setup script (selector de nube encima del cuadro
  de mensaje; no hay página ni URL) + la causa corregida.
- **PLAN**: arregla una frase que yo mismo dejé rota en #300 («La\ndeps no estaban…») y actualiza
  el pendiente.

## 4. El experimento que cierra, coste CERO

El merge de #300 movió la huella a `1ead8d63`; el snapshot —si existe— llevaría `663fae88`. Luego
la próxima VM nueva discrimina sola en la primera línea del hook: «marcador previo 663fae88 …
huella caduca» ⇒ la caché SÍ persiste y mi diagnóstico era erróneo; «no traía NINGÚN marcador» ⇒
confirma lo medido. Basta abrir una sesión y leer una línea.

## 5. Gaps y riesgos declarados

1. **«Ninguna causa documentada aplica» descansa en dos cosas que no puedo verificar yo**: el
   testimonio de Alberto (no tocó nada) y que la doc esté completa. Una condición no documentada
   —o una invalidación por algo que no sé— explicaría todo sin que haya bug.
2. **No he visto el estado real de la caché en ninguna parte.** Concluyo por implicación desde
   «el setup script corrió», no por observación directa del snapshot.
3. La inferencia de (2) supone que el marcador de boot+99 s lo puso el setup script y no otra cosa.
   El soporte: el hook posterior lo encontró y se saltó la instalación, y los 163/164 paquetes
   post-boot excluyen que vinieran de un snapshot. No hay logs del setup script para confirmarlo
   directamente. **Ésta es la objeción que más quiero que ataques.**
4. Riesgo de framing: paso de «el repo tiene un problema» a «esto es de Anthropic». Es la
   dirección cómoda para mí y por eso merece escrutinio extra.


## 6. Ronda 1 (Fable) — **NO SÓLIDO en framing, sólido en sustancia**; los 5 aplicados

Diagnóstico del revisor, aceptado entero: *«el registro canónico endurece a hecho lo que el recibo
marca ambiguo y adelanta la conclusión al experimento»*.

| # | Hallazgo | Adjudicación |
|---|---|---|
| 1 | **[medio]** DECISIONS y PLAN registraban «el setup script sí corrió / que corriera PRUEBA que no había caché» como hecho, perdiendo el hedge que el recibo sí tiene | **ACEPTADO**: reescrito como inferencia, con su soporte explícito (el hook se saltó; `session-start.sh` es el ÚNICO invocador en sesión — verificado por grep; 163/164 post-boot) **y su límite** (no hay log del setup script; si el instalador fue otro, la cadena cae y la hipótesis de rutas resucita) |
| 2 | **[medio]** el experimento no es binario ni se lee «en la primera línea»: con caché reconstruida post-merge el hook diría «ya instaladas», idéntico al caso sin caché | **ACEPTADO — era un error técnico real**: reescrito con los TRES desenlaces; el ambiguo se resuelve con `cloud_smoke.py` → `deps_cache`, que lee el registro sellado con `boot_id` («instalada» ⇒ se pagó; «solo saltada» ⇒ la caché funcionó). Verificado en `scripts/cloud_smoke.py:317-326` |
| 3 | **[medio]** «La causa raíz NO es del repo» en negrita, registrado ANTES de correr el discriminador que el propio addendum propone | **ACEPTADO**: degradado a «desplaza la sospecha, sin cerrarla», en DECISIONS, PLAN y ENTORNO_CLOUD |
| 4 | **[menor]** la 4.ª condición se declaraba «comprobada» con «~2-3 min», que es estimación y choca con el «~50 s» de ENTORNO_CLOUD | **ACEPTADO**: ahora dice lo medido (56,3 s de pip; 16 s de clone LOCAL) y declara que el clone por red **no se ha medido**; se explica por qué el «~50 s» no es la misma cifra |
| 5 | **[menor]** «no hay exclusión documentada ≠ no hay exclusión»; «TUMBA»/«es falso» tratan prosa externa como falsación | **ACEPTADO**: «contradicha por la doc, que no es lo mismo que refutada por medición: prosa externa, mutable y no versionada aquí»; la hipótesis se retira por falta de apoyo, no por refutación |
