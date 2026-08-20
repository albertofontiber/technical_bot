# Lo que espera tu decisión — cierre de s331 (20-ago-2026, noche)

> Ordenado por **coste tuyo**, no por importancia mía. Cada punto trae la medida ya hecha, para que
> decidas con el dato delante y no tengas que abrir nada. Lo que no está aquí, no te bloquea.

---

## 🟢 Cuatro frases y se desbloquean 33 filas del packet

### 1. Paraguas «2X-A» — **una frase**
¿Con los táctiles o sin ellos? (38 modelos incluyendo los 11 `2X-AT`, o 27 sin ellos — los táctiles
ya tienen su propio paraguas).
**Medido** (`evals/s331_2xa_sonda_plan_v1.json`): **0 gold perdidas**, **2 golds ganan 12 fuentes cada
una** —una es «¿El detector KE-DP3020W vale para la central 2X-A?»—, **0 disparos en 111 consultas
reales**. Lo único que salta es una sonda sintética («2 x a») que yo mismo escribí.
👉 *Con tu frase lo aplico con recibo, y de paso caen 4 documentos de la serie 2X-A que hoy están sin
`doc_map` esperando esto.*

### 2. Los 15 «P1» del packet v3 — **un sí en bloque**
Filas donde el juez propone otra grafía **y hay cita de portada verificada**. Es el patrón que ya
firmaste **nueve veces** en §1.B con tu «OK con juez».
👉 *Si me dices «P1 en bloque, sí», las aplico todas juntas con un solo gate y un solo recibo.*

### 3. Los 9 «P3» — **un sí en bloque**
Artefactos de extracción con **0 menciones estrictas** del token. No son productos.
👉 *Mismo trato: un sí y se retiran en bloque.*

### 4. Los 8 «P4» (nombres reales CON barra) — **estos sí son uno a uno**
Aquí no hay atajo: un «sí» crea un id **INMUTABLE**. La lección de hoy con DOA es la guía —
comprueba que la grafía es la del **fabricante**, no la del documento (`DOA FJ` era el modelo;
`/CPD` era el sufijo del certificado).

---

## 🟡 Dos decisiones de fondo, con la evidencia ya reunida

### 5. FAAST atribuido a un competidor — **5 documentos, y tu observación destapó la clase**
Tenías razón: `ASD Harsh Environments_SP` es de **System Sensor** (logo FAAST, foto del equipo
—«a black FAAST detection device with transparent front panel»— y «© 2015 System Sensor»), y su
ficha dice **Xtralis**, que es el fabricante de VESDA, es decir **la competencia**.

**El censo dice que no es un caso aislado.** De los 30 documentos activos que mencionan FAAST:

| marca en la ficha | documentos | ¿correcto? |
|---|---|---|
| Notifier | 19 | sí — FAAST se vende bajo Notifier |
| Morley | 5 | sí — y bajo Morley |
| **Xtralis** | **5** | **no** — Xtralis es VESDA, el competidor |
| System Sensor | 1 | sí — es el fabricante real |

Y hay incoherencia entre hermanos: la misma serie de folletos de aplicación está repartida entre tres
marcas (`ASD Cold` → Notifier, `ASD Harsh` → Xtralis, `ASD Custodial` → Xtralis).

**Por qué no lo parcheé hoy**: el dúo (Sol, crítico) señaló que un retag es efímero — la re-ingesta
re-deriva la marca. **Pero al verificarlo aparece un matiz que cambia la decisión**: este documento
es un *backfill* de abril y `_detect_brand` con su texto real devuelve **`(None, None, None)`**. O
sea, el pipeline de hoy **no produce ese «Xtralis»**: es un valor heredado. Un retag no sería
machacado con Xtralis; en el peor caso se perdería.

**Las tres vías, y lo que cuesta cada una:**
| vía | qué hace | coste | aguanta re-ingesta |
|---|---|---|---|
| **A** | retag de los 5 a su marca correcta | bajo | no (pero tampoco vuelve a Xtralis) |
| **B** | patrón de marca nuevo en `config/manufacturers/` | medio | sí |
| **C** | que la ingesta lea el `vendido_bajo` del catálogo (**arreglo de raíz de `#95`**) | alto | sí, y para todo el corpus |
👉 **Mi recomendación: A ahora + C en su sesión.** El dato lleva mal desde abril y la B no basta,
porque la marca correcta no es la misma para los cinco (depende de bajo qué marca se distribuye cada
documento). **Lo que necesito de ti**: confirmar que los 5 `Xtralis` pasan a **System Sensor**, o
decirme cuáles van a Notifier/Morley.

### 6. `morley:efs-em-8` y `notifier:nx2-r-r-y-nx5-r-r`
Los dejaste en «pending.» y con la anotación vacía. Siguen ahí, sin tocar.

---

## ⚪ Contexto: dónde estamos y qué NO te bloquea

- **El packet**: 125 de 192 filas resueltas. Las 67 vivas están en
  **`evals/s320_e1_packet_adjudicacion_v3.md`** — trabaja sobre esa versión, no sobre el v2.
- **Fuera del packet** hay una cola mayor que no vive en ningún sitio: **77 documentos activos sin
  `doc_map`** (Notifier 31, Morley 23, Kidde 13…). Si quieres, te la genero como packet.
- **E1b (474 confirmaciones) y E2 (1.361 altas)** siguen abiertos: son el grueso, más mecánicos.
- **Nada de esto bloquea el piloto.** El único bloqueante sigue siendo **enviar el paquete del
  abogado** (PLAN, punto 1).
