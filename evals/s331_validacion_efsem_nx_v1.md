# s331 — Validación online de `morley:efs-em-8` y `notifier:nx2-r-r-y-nx5-r-r`

**Encargo de Alberto (20-ago, cierre)**: «¿Puedes buscar info online para validar los modelos
`morley:efs-em-8` y `notifier:nx2-r-r-y-nx5-r-r`? Puedes apoyarte en los manuales que tengamos
guardados también.» Son las dos filas de §1.B que él había dejado en «pending.» y con la anotación
vacía. **Nada aplicado**: ambas son de clase **P4** (nombre real CON barra) y un «sí» acuña un id
INMUTABLE — la decisión sigue siendo suya, pero ya con la grafía del fabricante delante (**R8**).

---

## 1. `EFS/EM 8` — **producto REAL, y el mismo manual va bajo DOS marcas**

**En nuestro corpus** (evidencia primaria): **111 menciones de «EFS/EM» + 24 de «EFS/EM 8»** en dos
documentos, `MS8` (75 chunks) y `FS8` (73 chunks). Y el hallazgo que resuelve la fila:

> **`MS8` y `FS8` son EL MISMO MANUAL.** Misma portada («Panel de control de incendios de 8 zonas
> EFS/EM 8 — Manual de instalación, puesta en marcha y funcionamiento»), **mismo código
> `997-201-103`, misma edición** (Edición 1, septiembre 1999). En el bucket están archivados en
> carpetas distintas: `manuales/**Morley**/MS8.pdf` y `manuales/**Notifier**/FS8.pdf`.

Eso explica el motivo por el que la fila cayó — «ambigüedad: mismo término propuesto a dos
fabricantes» — y lo convierte en un caso de libro de **R3 (OEM)**: no hay que elegir marca, se
atesta bajo ambas.

**Online** (confirmación independiente):
- Notifier publica el manual: `notifier.es/documentacion/notifier/manualesobs/FS8.pdf` — nótese la
  carpeta **`manualesobs`** = *manuales obsoletos*. **El producto está descatalogado.**
- Existe además una versión que **NO tenemos en el corpus**: `MNDT012P.pdf`, indexada como «EFS/EM 8»
  (la `P` final es el patrón de las versiones portuguesas, como `MNDT730P` o `MIEMU520P`).

**Grafía canónica (R8)**: el fabricante titula **«EFS/EM 8»** — coincide con la del corpus, así que
no hay conflicto como lo hubo con DOA.

**Recomendación**: **alta `EFS/EM 8`** con cita de portada verificada, `vendido_bajo: [Morley, Notifier]`
por R3, y doc_map a **los dos** documentos (`MS8` y `FS8`).
⚠️ **La decisión que queda es tuya y es el namespace**: los ids llevan namespace de marca y este
producto tiene dos. El precedente del catálogo (FAAST) es acuñar bajo **una** marca y declarar la
otra en `vendido_bajo` — p. ej. `notifier:fl2011ei-hs` con `vendido_bajo: [Notifier, Morley-IAS]`.
**¿`notifier:efs-em-8` o `morley:efs-em-8`?** El packet propuso Morley; el manual lo publica hoy
Notifier.

## 2. `NX2/R/R` y `NX5/R/R` — **DOS productos reales, y hay que partir el id**

**En nuestro corpus**: el documento `EMA24RS2R_NX2y5-R-R` tiene **1 chunk**, y al bajar el PDF
original se ve por qué — **1 página con 17 caracteres de texto**: literalmente «NX2/R/R y NX5/R/R».
Todo lo demás son diagramas (474 KB de imagen): un despiece de montaje y una tabla de 4 bornes. La
ingesta no perdió nada; **el documento es un dibujo esquemático** cuyo único texto es su título.

**Online** — la ficha del fabricante los identifica como productos con página propia:
- **`NX2/R/R`**: flash estroboscópico rectangular rojo de **2 W**, destello cada 1,5 s, 24 Vcc 120 mA.
- **`NX5/R/R`**: sirena/estrobo de **14 tonos** con montaje en pared, caja y lente rojas, flash de **5 W**.
- Y el propio documento que tenemos es el que Notifier publica como «**Dibujo esquemático de las
  sirenas NX2/R/R y NX5/R/R**» (`EMA24RS2R_NX2y5-R-R.pdf`).

**Grafía canónica (R8)**: el fabricante escribe exactamente **`NX2/R/R`** y **`NX5/R/R`** — las
barras son parte del nombre, no un artefacto de extracción.

**Recomendación**: **R7** — el id concatenado `notifier:nx2-r-r-y-nx5-r-r` **no se crea**; se dan de
alta **dos** productos, `notifier:nx2-r-r` y `notifier:nx5-r-r`, y el documento los atesta a ambos.
Son dispositivos de aviso óptico-acústico, no centrales.

**Gap declarado**: la cita es **una sola mención por modelo**, y es el título de un documento sin
cuerpo de texto. Es la evidencia más floja de las dos filas — **pero la ficha del fabricante la
respalda**, que es justo lo que R8 pide para acuñar.

---

## Lo que cambia respecto a como estaban las filas

| | Antes | Ahora |
|---|---|---|
| `EFS/EM 8` | «pending.» · caída por *dos fabricantes* | producto real y obsoleto; **el conflicto de marcas ERA la respuesta** (R3) |
| `NX2/R/R` + `NX5/R/R` | anotación vacía · 1 mención en tabla | **dos** productos con ficha del fabricante; el id concatenado no se crea (R7) |

**Fuentes**: [manual FS8 (Notifier, obsoletos)](https://www.notifier.es/documentacion/notifier/manualesobs/FS8.pdf) ·
[EFS/EM 8 — MNDT012P](https://www.notifier.es/documentacion/notifier/manualesobs/MNDT012P.pdf) ·
[dibujo esquemático NX2/R/R y NX5/R/R](https://www.notifier.es/documentacion/notifier/manuales/EMA24RS2R_NX2y5-R-R.pdf) ·
[ficha NX2/R/R](https://www.notifier.es/index.php/producto/category/nx2-r-r) ·
[ficha NX5/R/R](https://www.notifier.es/index.php/component/zoo/category/nx5-r-r) ·
[tabla de obsolescencia INDT035](https://www.notifier.es/documentacion/notifier/obsolescencia/INDT035.pdf)
