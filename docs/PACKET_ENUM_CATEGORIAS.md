# Packet de adjudicación — el enum de categorías y su ancla normativa

> Nace de la pregunta de Alberto (22-ago): *«¿esas categorías que faltan están definidas en
> alguna norma, tipo la EN 54, o de dónde las sacas?»*. Respuesta honesta: **el enum vigente es
> EMPÍRICO**, sembrado en s322 (DEC-216) con lo que el corpus y las preguntas reales pedían; el
> propio código lo declara adjudicable (`catalog_store.py:61`, «la semilla de CATEGORIAS es
> adjudicable»). Este packet propone **anclarlo en norma donde la norma existe**, y pone tamaño
> medido a cada decisión.
>
> **Nada está aplicado.** Marca `[X]` lo que apruebes y escribe al lado si quieres otra cosa.
> Una fila = una decisión.

---

## 0 · Lo primero: ¿hay que re-clasificar lo ya escrito? **NO** (medido)

La pregunta obligada antes de tocar el enum: las **411 filas** que el lote ya escribió, ¿están
mal por haberse clasificado con un enum sin ancla normativa? Auditoría sobre el catálogo vivo,
buscando las filas cuya cita contiene las palabras de los seis huecos:

| clase sonda | filas tocadas | dónde cayeron | veredicto de la auditoría |
|---|---|---|---|
| anunciador | 18 | 7 `accesorio` · 7 `repetidor` · 4 `modulo` | **correcto**: las cajas, revestimientos y llaves (ABF-1/2/4, ADP-4, AKS-1) son accesorios **DE** un anunciador; los anunciadores propiamente (ABM-32A, RPT-485W/WF «repetidores anunciador de lazo») fueron a `repetidor`; las placas MIB-F/WF que interconectan central↔display son `modulo` |
| barrera-IS | 1 real | `detector` | **correcto**: IDX-751AE es «INTRINSICALLY SAFE INTELLIGENT PHOTO ELECTRONIC SMOKE SENSOR» — un detector con protección IS, no una barrera Zener |
| audio/EVAC | 4 reales | 2 `sirena` · 2 `accesorio` | **correcto**: PAN-AVD1 y AVD EVJ son señalización óptico-acústica (EN 54-3/23 → `sirena`); RPJ-1 y VRAM-1 son accesorios |

**Conclusión medida**: el clasificador clasifica por la **función del sujeto**, no por las palabras
de la cita, y el enum de 13 absorbió bien estos casos. Los huecos de enum no produjeron filas
mal escritas: produjeron **filas NO escritas** (el sistema mandó la duda al packet en vez de
forzarla — que es lo que debe hacer). **Ninguna decisión de este packet obliga a re-clasificar.**

---

## 1 · El enum de HOY, mapeado a norma (lo que ya está alocado)

Trece categorías vigentes. Diez tienen ancla normativa directa; tres son funcionales sin norma
—y deben seguir existiendo, porque el técnico pregunta por ellas:

| categoría | ancla normativa | nota |
|---|---|---|
| `central` | **EN 54-2** (ECI) · equivalente UL 864 | el corpus tiene manuales de régimen US (AFP1010 cita UL 864) |
| `fuente` | **EN 54-4** (alimentación) | |
| `detector` | **EN 54-5** (calor) · **-7** (humo) · **-10** (llama) · **-26** (CO) | cinco partes → UNA categoría: la tecnología ya es atributo, no categoría |
| `pulsador` | **EN 54-11** | |
| `sirena` | **EN 54-3** (acústicos) · **-23** (VAD ópticos) | |
| `barrera` | **EN 54-12** (haz óptico lineal) | ⚠️ colisión de palabra con la barrera Zener — ver §2.5 |
| `modulo` | **EN 54-17** (aislador) · **-18** (E/S) | |
| `aspiracion` | **EN 54-20** (ASD) | |
| `pasarela` | **EN 54-21** (transmisión de alarmas) | |
| `repetidor` | sin parte propia: EN 54-2 lo trata como **equipo auxiliar del ECI** | ver §2.3 |
| `retenedor` | EN 1155 / EN 14637 (retenedores electromagnéticos) | fuera de EN 54 pero normalizado |
| `software` | — | funcional; R10 lo declara producto consultable |
| `accesorio` | — | funcional; cajón declarado |

**Criterio de diseño que propongo** (y su descarte): taxonomía **funcional-primero, anclada en
norma donde exista** — NO «una parte EN 54 = una categoría». Descartado el mapeo 1:1 con la
norma porque (a) cinco partes distintas son todas `detector` y el técnico pregunta «¿qué
detectores tienes?», no «¿qué EN 54-7 tienes?»; (b) categorías reales del negocio no tienen
norma (`software`, `accesorio`); (c) medio corpus es régimen UL, no EN. El beneficio del ancla
no es mandar sobre la taxonomía: es dar al clasificador una **señal verificable** (la cita de
certificación del propio manual) y darnos a nosotros un criterio no-arbitrario para decidir
altas futuras.

---

## 2 · Las seis decisiones (con tamaño medido)

Tamaño = filas de la vista Notifier que quedaron **sin clasificar** (86 no-alta) tocadas por cada
hueco. Es el dato duro que tenemos; el proxy por nombre sobre el catálogo entero **no sirve**
(los modelos son códigos tipo `AFP-1010`, no llevan la palabra) y lo declaro como no-medida en
vez de darte un número inventado.

### 2.1 — `audio` (megafonía / EVAC) · **12 filas** · ancla: **EN 54-16** (VACIE) + **EN 54-24** (altavoces)

Ejemplos parados: `AA-120E`, `AA-30E` (amplificadores), `TCC-1`, `VCC-1`.

- **Recomendación: SÍ, categoría nueva `audio`.** Es el hueco más grande, tiene norma propia y
  clara, y es un sistema entero (VACIE) que el técnico distingue perfectamente de una sirena.
- **Alternativa descartada**: meterlo en `sirena`. Rompe la distinción que hace la propia norma
  (EN 54-3 señalización vs EN 54-16 sistema de voz) y mezcla amplificadores con campanas.

  - [ ] OK  ·  [ ] otra cosa: ______

### 2.2 — `extincion` · **1 fila** (`UDS-2N`) · ancla: **EN 12094-1** (dispositivo eléctrico de control) — *no es EN 54*

- **Recomendación: SÍ, categoría nueva `extincion`.** Aunque hoy pese 1 fila en Notifier, la
  norma es inequívoca y **Kidde es fuerte en extinción**: la siguiente marca la llena. Crear la
  categoría ANTES de correr Kidde evita una re-pasada.
- **Alternativa descartada**: `central`. Una central de extinción sí es un ECI-adyacente, pero
  fundirlas haría que «¿qué centrales tienes?» devuelva unidades de extinción — precisamente el
  tipo de mezcla que el lote vino a arreglar.

  - [ ] OK  ·  [ ] otra cosa: ______

### 2.3 — `anunciador` · **6 filas** (`ACM-16AT`, `AFM-16ATF`, `INA`, `NRT-NET`) · ancla: **ninguna propia** (EN 54-2 = auxiliar del ECI)

- **Recomendación: NO crear categoría — usar `repetidor`, que ya existe.** La auditoría del §0
  muestra que el clasificador YA manda ahí los anunciadores de lazo (RPT-485W: «repetidores
  anunciador») y funciona. Bastaría una línea en el prompt: «anunciador/annunciator ⇒ repetidor».
- **Alternativa descartada**: categoría propia. Sin norma que la respalde y con `repetidor`
  cubriendo la función (mostrar remotamente el estado del ECI), sería fragmentar por vocabulario
  comercial, no por función.
- **Gap declarado**: si tú distingues en obra «repetidor» (repite el panel entero) de
  «anunciador» (solo señaliza zonas), la fusión pierde ese matiz. Tú lo sabes mejor que yo.

  - [ ] fusionar en `repetidor`  ·  [ ] categoría propia `anunciador`  ·  [ ] otra cosa: ______

### 2.4 — `kit` / paquete · **3 filas** (`BE-5000AA`, `ID3004-001`, `ID3008-001`) · ancla: **ninguna** (empaquetado comercial)

- **Recomendación: NO crear categoría.** Un kit no es un tipo de producto: es una forma de
  venderlo. Encaja mejor como **umbrella** (`familia`/`rango`, mecanismo que ya existe) apuntando
  a sus componentes, o como `accesorio` si es un pack menor.
- **Alternativa descartada**: `categoria: kit`. Un técnico que pregunta «¿qué centrales tienes?»
  querría ver el ID3004-001 si el kit contiene una central — y una categoría `kit` lo escondería.

  - [ ] NO crear (umbrella/accesorio)  ·  [ ] crear `kit`  ·  [ ] otra cosa: ______

### 2.5 — `barrera-IS` (Zener) · **2 filas** (`Z978`, `AIS-GALS1`) · ancla: **EN 60079-11** (seguridad intrínseca / ATEX) — *ni siquiera es normativa de incendios*

- **Recomendación: SÍ, pero renombrando el eje.** Dos normas distintas comparten la palabra
  «barrera»: EN 54-12 (haz óptico, detección) y EN 60079-11 (barrera Zener, protección ATEX).
  Propongo `barrera_is` como categoría separada y dejar `barrera` = haz. Renombrar `barrera` a
  `barrera_haz` sería más limpio pero **rompería las 12 filas ya escritas** — no lo compensa.
- **Alternativa descartada**: `accesorio`. Perdería una distinción que en obra ATEX es crítica.

  - [ ] crear `barrera_is`  ·  [ ] dejarlo en `accesorio`  ·  [ ] otra cosa: ______

### 2.6 — `impresora` · **1 fila** (`HOP-136-412`) · ancla: **ninguna**

- **Recomendación: NO crear categoría — `accesorio`.** Sin norma, una sola fila, y función
  claramente periférica. La auditoría del §0 ya muestra 5 impresoras/periféricos escritos como
  `accesorio` sin que chirríe.
- **Alternativa descartada**: categoría propia. Sería la definición de sobre-ingeniería.

  - [ ] `accesorio`  ·  [ ] crear `impresora`  ·  [ ] otra cosa: ______

---

## 3 · Y una pregunta de rumbo, no de fila

¿Quieres que el **ancla normativa se cablee** — es decir, que cada categoría lleve su norma en el
esquema y que el clasificador pueda usar la cita de certificación del manual («certificado según
EN 54-16») como señal de apoyo?

- **A favor**: señal verificable y objetiva, escalable a 30+ fabricantes, y criterio no-arbitrario
  para futuras altas de categoría.
- **En contra / riesgo declarado**: medio corpus es régimen **UL**, no EN; si el clasificador se
  apoya de más en la cita normativa, los manuales americanos quedan en desventaja. Se mitiga
  tratándola como señal **de apoyo**, nunca como requisito.
- **R14 sigue intacta**: una norma JAMÁS es un producto. Aquí ancla una **categoría**, que es un
  rol distinto y no toca la regla.

  - [ ] cablear el ancla (norma en el esquema + señal de apoyo)  ·  [ ] dejarlo como documentación  ·  [ ] otra cosa: ______

---

## 4 · Qué pasa cuando firmes

1. Enum ampliado en `catalog_store.CATEGORIAS` + reglas al prompt (v3) — cambio pequeño, con test.
2. **Re-pasada quirúrgica** solo de las filas afectadas (86 no-alta), NO del lote entero: el §0
   demuestra que lo escrito no se toca.
3. Gate re-corrido contra el GT congelado, que **no se modifica** (si el enum nuevo lo contradijera
   en alguna fila, eso sería una señal a mirar, no algo a silenciar).
4. Entonces —y solo entonces— la siguiente marca (Morley o Kidde, tu orden).
