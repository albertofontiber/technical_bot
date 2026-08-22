# Propuesta — enum ampliado (adjudicado) + GT v2 re-congelado + re-pasada de las no-alta

## Contexto y autorización
Alberto revisó `docs/PACKET_ENUM_CATEGORIAS.md` y dio luz verde a lo recomendado:
crear `audio`, `extincion` y `barrera_is`; NO crear `anunciador` (va a `repetidor`),
ni `impresora` (va a `accesorio`), ni `kit` (no es un tipo de producto). El §3 del
packet —cablear el ancla normativa en el esquema— queda como documentación, «a
futuro revisamos si merece la pena».

## Qué cambia
1. `catalog_store.CATEGORIAS`: 13 → 16 valores, cada alta con su ancla en comentario.
2. Prompt de clasificación v3 (sha c59d81d092fbb3b5): define las tres categorías nuevas
   y las tres negativas explícitas. Incluye la trampa que ya vimos en producción: un
   detector con protección IS («intrinsically safe smoke sensor») sigue siendo
   `detector` — la protección no cambia lo que el producto ES.
3. **GT v2 re-congelado ENTERO** (`evals/s336_gt_v2.yaml`, sha 3be2ca54e402aa76):
   sin-duda 22 → 27. Cinco dudas del v1 eran huecos de enum y se resuelven:
   - por ADJUDICACIÓN (la duda era «¿existe categoría propia?»): `firelite:led-10`
     → `repetidor`, `notifier:prn-4` → `accesorio`.
   - por EVIDENCIA re-leída en la fuente: `pepperl-fuchs:z978` → `barrera_is`
     («BARRERA ZENER — Barrera Zener para detectores analógicos…», TIDT089 #2),
     `notifier:uds-2n` → `extincion` («Unidad de extinción Modelo UDS-2N» +
     «la central de extinción UDS-2N», MNDT112), `notifier:atg-2` → `audio`
     («Generador de Tono de Audio ATG-2», MFDT170 / 50253SP #28).
   - `notifier:be-xp` SIGUE en duda, y ahora por evidencia y no por hueco: el kit
     agrupa XPP-1, CHS-4, chasis y fuente — no hay sujeto único que clasificar.
   El v1 se conserva porque DEC-279 lo cita por sha (c8bb02620b4ade74).
4. `lib_lote_marca.ruta_gt_vigente()`: el gate usa la versión MÁS ALTA del gold y
   estampa cuál usó. Quién juzgó una corrida no puede quedar implícito.
5. `s336_poblacion.py --solo-no-alta`: re-corre sólo las filas cuya confianza no es
   alta (86 en Notifier) y fusiona sobre el recibo.

## Por qué el GT se re-congela ENTERO y no sólo las filas que cambian
DEC-126 (anti-gate-shopping). Tocar únicamente las filas que convienen convierte el
gold en una función del resultado que se busca. Cambia el fichero, cambia su sha, y
la decisión declara qué se movió y por qué.

## Verificación previa hecha
- Las tres etiquetas por evidencia se leyeron en `chunks_v2` con la cita verbatim
  delante (no de memoria, no por el nombre del producto).
- El enum carga: 16 categorías, `barrera` (EN 54-12) intacta junto a `barrera_is`.

## Gaps declarados
- **El gate cambia de listón al cambiar el gold**: n sube de 17 a ~22 elegibles y las
  categorías nuevas por fin quedan juzgadas — pero el PASS de hoy y el de ayer NO son
  la misma medida. Se declara en el recibo, no se compara con el anterior como si lo
  fuera.
- **Las tres filas nuevas del GT las etiqueté yo leyendo la fuente**, con la misma
  mano que escribió el prompt v3. Es el sesgo estructural del gold de autor: lo mitiga
  que la cita es verbatim y verificable, no que yo sea imparcial.
- `barrera` y `barrera_is` conviven y comparten palabra. Renombrar `barrera` a
  `barrera_haz` sería más limpio y rompería las 12 filas ya escritas; se prefirió la
  convivencia y el prompt lleva el aviso explícito.
- Coste de la re-pasada: ~$1, 86 filas. Si el enum nuevo no las desbloquea, el lote
  simplemente no escribe y se declara.
