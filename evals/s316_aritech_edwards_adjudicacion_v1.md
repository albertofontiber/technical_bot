# s316 — Adjudicación Aritech / Edwards: el frente se cierra casi entero contra el corpus

> ## ⚠ CORRECCIÓN DE ALCANCE (Alberto, mismo día — leer ANTES que el resto)
>
> Este documento respondía a la pregunta **equivocada**. Alberto la reformuló:
> *«no quiero añadir productos de Aritech/Edwards que no estén ya; quiero añadir los
> MANUALES que faltan de los productos que YA están en el corpus, como el caso de Kidde
> (NC-PF2)»*.
>
> Consecuencia directa: **«AS250 es el único hueco real» NO es accionable** — AS250 es un
> producto nuevo, justo lo que NO se quiere. Lo que sigue en pie de este documento es la
> parte negativa (Aritech ya es la 5ª marca del corpus; Casmar no distribuye Edwards).
>
> El barrido que SÍ responde a la pregunta correcta está en
> `evals/s316_casmar_gap_sweep_v1.json` (19 candidatos Aritech, 0 Edwards) y su método,
> corregido, en `scripts/s316_casmar_gap_sweep.py`. Criterio durable en memoria.

**Pregunta abierta desde s315** (quedó sin respuesta porque casmarglobal.com estaba
bloqueado por la política de egress del entorno cloud): *¿Casmar distribuye Aritech y
Edwards? ¿Hay que abrir esas marcas como lote de adquisición?*

**Cómo se cerró.** El recon (`scripts/s315_casmar_recon.py`) ya se había corrido en la
máquina local el 9-ago 23:31, dejando `recon_search.json` suelto en la raíz **sin
registrar en ningún doc**. Esta sesión lo recupera y lo cruza contra la DB de producción.

## Lo que dijo el recon (Casmar)

| Marca | SKUs en Casmar | URLs |
|---|---|---|
| aritech | **5** | AS250 · AS2363 · AS2364 · ASW2366 · ASW2367 (`casmarglobal.com/es/<sku>.html`) |
| edwards | **0** | — |

## El cruce contra el corpus (fuente: DB de producción, hoy)

**Aritech NO es una marca nueva: es la 5ª del corpus** — 55 documentos, 34 modelos, por
delante de System Sensor y Xtralis. La premisa implícita del frente («abrir Aritech») era
falsa.

| SKU de Casmar | ¿En corpus? |
|---|---|
| ASW2367 | ✅ 2 docs |
| ASW2366 | ✅ 1 doc |
| AS2364 | ✅ 2 docs |
| AS2363 | ✅ 1 doc |
| **AS250** | ❌ **ausente** — 0 en `documents` y 0 menciones en el texto de `chunks_v2` |

**Edwards**: 0 SKUs en Casmar (confirmado) y ya hay 3 docs / 2 modelos en corpus
(FHSD8310, FHSD8330). La fuente para ampliar Edwards **no es Casmar** sino
`firesecurityproducts.com` (portal del grupo), como anticipaba el propio docstring del
recon y `docs/CORPUS_FIRESECURITYPRODUCTS.md`.

## Veredicto

- **Aritech vía Casmar: NO-GO como lote.** 4 de 5 SKUs ya están. El único hueco real es
  **AS250** — un documento, no un lote. No justifica una campaña de adquisición ni un
  canal nuevo en `portal.yaml`.
- **Edwards vía Casmar: NO-GO por inexistencia.** Casmar no lo distribuye. Si se quiere
  ampliar Edwards, la vía es firesecurityproducts.com, y eso es un frente propio con su
  propio harvest — no un subproducto de este.
- **Quinta instancia de `feedback_corpus_gap`** (precedentes: los 44→7 documentos de s302,
  la Guía Avanzada de la CAD-171 que ya teníamos, el gap orgánico NC-PFx que era
  findability, el barrido pm-de-familia de s315). El patrón se repite con la misma forma:
  **un hueco aparente de corpus que se disuelve al verificarlo contra la DB en vez de
  contra el nombre del fichero o el catálogo del distribuidor.** El coste de NO verificar
  habría sido un lote de ingesta entero.

## Gaps declarados

- El recon casa por **término de búsqueda** en el buscador Magento de Casmar; un producto
  Aritech catalogado sin la palabra «aritech» en su ficha no aparecería. El recuento de 5
  es un suelo, no un techo. Atenuante: la evidencia s314 independiente (la familia 2X es
  Aritech-OEM vendida como Kidde y ya está en corpus) apunta en la misma dirección.
- `total_declared` salió `null` para ambas marcas: el script no pudo leer el total
  declarado por el portal, así que no hay control de paginación. Con 5 y 0 resultados el
  riesgo de truncamiento es bajo, pero no es cero.
- **AS250 no se ha adquirido** en esta sesión: queda como el único ítem accionable del
  frente, de tamaño 1 documento.
