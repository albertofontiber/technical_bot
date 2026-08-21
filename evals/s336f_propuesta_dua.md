# s336f — Promover candidates con cita verificada sobre el PDF original

> **Corregido tras el dúo (Sol xhigh + Fable, 9 hallazgos, 9 verificados, 0 falsos).**
> La versión que revisaron proponía **3** y decía cosas que su propio recibo desmentía. Lo
> corregido va marcado abajo; el veredicto de Fable fue «defendible y bien gated, NO SÓLIDO en su
> prosa», y tenía razón en las dos.

## La recomendación

Promover **2** candidates (`notifier:sdx-751-tem`, `notifier:lpx-751`) vía `products_confirmar`.
Des-huerfaniza 2 manuales: **84 → 82**.

`notifier:am-lcd` estaba en la propuesta y **sale**: ver «lo que cazó el dúo».

## Cómo llegué a 3 desde 84 (y por qué el camino importa más que el número)

Alberto ofreció una clave de Gemini para «rascar» los manuales huérfanos. Monté una sonda
multimodal y **medía otra cosa**: leía las páginas de `document_visual_assets`, que son una
selección (mediana 2 páginas por huérfano, en manuales de 30). Miré dos a mano: la portada del
FAD-902 dice «GUIDE MANUAL / Power Supplies» y no nombra el modelo; su página 8 es «Descripción
de los leds». Los lectores acertaban. Aquel `6/37` medía qué páginas habíamos guardado.

Los PDF originales están en Storage (83 de 84). Leyéndolos:

| bucket | n | herramienta |
|---:|---|---|
| redirect `unresolved:` pendiente | 29 | adjudicación (R21) |
| **PROMOVIBLE** | 20 | cita en PDF **y** en `chunks_v2` |
| sólo nº de referencia | 15 | adjudicación R4 |
| no nombra su producto | 13 | ningún lector lo cambia |
| canónico digit-only | 4 | irreducible (el detector los excluye a propósito) |
| PDF escaneado | 2 | lector multimodal |
| sin PDF | 1 | — |

Dos números míos frenados antes de proponerlos: «75 lo tienen en el PDF» cae con **R19**
(`NAS`, `TG`, `RHistorico.exe`, «modelo antideflagrante» pasan la cita sin identificar nada) →
contra el CANÓNICO son 49; y «lo perdimos al extraer» es **falso en 48 de 49** (ya está en
`chunks_v2`; falta promover).

Los 20 PROMOVIBLE pasan por `s336e` → **17 paran**. El desglose REAL, contra el recibo
(`evals/s336e_filtro_promovibles.json`, `"por_regla": {"R21": 11, "R19": 6}`):
- **R19 (6)**: `EEV(2)` (paréntesis: el detector no lo ve), `RHistorico.exe` (el ejecutable no es
  el software — R10 dice que el producto es el programa), `Serie 800` (familia), `NAS` ×3 (sigla
  de 3 letras, mismo mecanismo que `notifier:eia-485`).
- **R21 (11)**: `APIC`, `NFS8REL`×2, `MCX-55M`×2, `MMX-10M`×2, `TG-1020`, `ID-3000`,
  `Notifier INSPIRE E10`×2 — colisión de marca, o gemelo ya consumible por alias.
- **SUJETO: 0.** El filtro de página **no decidió ni un solo caso**. `ID-3000` (páginas 32 y 38)
  lo paró **R21**, que va antes en la cadena `elif`. En la versión revisada dije «SUJETO (1)» y
  usé ID-3000 como su ejemplo: falso, y lo cazaron los dos revisores. El umbral
  `PAGINA_SUJETO = 5` sigue en el código y sigue sin ejercitarse — es mecanismo NO probado.
- Y `notifier:notifier-inspire-e15` sale por **R4**: el manual cita E10 y **no** cita E15.

## Lo que cazó el dúo (y que cambió el lote)

1. **`AM-LCD` fuera** *(Fable, materialmente correcto)*. El censo del gate lo flagea
   `["sin_digitos", "acronimo_corto"]` —la clase con la que R19 mata `NAS`, con el precedente
   DEC-272 (231→11 documentos)— y yo escribí «LPX-751 es el más débil de los tres» omitiéndolo.
   Medí la huella en corpus (`s336g`) esperando limpiar el flag y lo **confirmó**: de sus 6
   documentos, uno es un falso positivo real —«**Pantalla FM/AM LCD**» de un manual de radio—
   porque el core `am[-\s/.+]*lcd` admite el espacio. El lado de CONSULTA está limpio (0/36
   negativos, 0/137 reales), así que no es una baja del producto: arreglarlo bien es una pregunta
   de **normalización del detector** (¿un término letters-only debe exigir el separador?) más
   grande que este lote y con su propia medida.
2. **«Dos vías independientes» era sobre-afirmar** *(los dos)*. `chunks_v2` se deriva del MISMO
   PDF: acredita que la extracción no lo perdió, no una segunda fuente. Corregido en la
   `provenance_add`, que es permanente.
3. **`sdx-751-tem` estrecha y no lo declaré** *(Sol)*. Verificado: fue
   `DESBLOQUEA_PERO_ESTRECHA`, y **s334f ya lo adjudicó `PRECISION`** — sus 2 pérdidas
   (`MNDT120`, `MNDT150`) son `DOC_DE_HERMANO`, manuales de otros modelos. Se arrastra esa
   adjudicación en vez de repetir G4; pero omitirlo y resumir «+3/−0» era un fallo de framing.
4. **«Sólo QUITA, así que sólo puede ser estricto» confunde monotonicidad con corrección**
   *(Sol)*. Un filtro monótono también deja pasar falsos — y `AM-LCD` lo demostró en la misma
   sesión.
5. **Heurísticas no declaradas** *(Fable)*: el umbral «≤3 letras» de R19 (por el que `AM-LCD`,
   5 letras, pasó) y el acoplamiento a `cat._consumable`, API privada de `catalog_store`.

### Bug sistémico encontrado al verificar el hallazgo 1

Dos pases idénticos de `s336g` dieron `AM-LCD=2` y `AM-LCD=6`, y el corpus salía con **954**
documentos cuando tiene **1.080**: mis paginadores no pasaban `order`, y **PostgREST no garantiza
orden estable entre rangos**, así que la paginación saltaba y duplicaba filas. Arreglado en
`s336b`/`s336c`/`s336g` con `order` explícito + verificación contra `count=exact`. Los dos censos
se re-corrieron: **salen idénticos** (75/6/2/1 y la tabla de buckets), ahí no mordía.

**El gate cazó un fallo de mi filtro** y lo dejo declarado: mi R21 sólo cruzaba
canónico↔canónico. `notifier:notifier-inspire-e10` pasó, y su canónico ya es **alias
`variante-tipografica` de `notifier:inspire-e10`, que sí es consumible** — el validador lo paró
(«COLISIONA con canonical_model … exact pisaría el alias»). Cableé R21(b) para no depender de eso.

## Medido

- Gate dry-run **PASS** · detector 2032 → 2034 (**+2/−0**) · **APLICADO**, censo post PASS
- **0 gold perdidas** · 0 disparos en negativos sintéticos · 0 detecciones nuevas en 137 reales
- resolver: 0 gold que pierden, 0 que ganan
- **Seam 1** (`models` bajo `IDENTITY_RESOLVE_POLICY=replace`, el punto ciego del gate):
  162 consultas únicas, **0 pierden**, 0 ganan
- **Huella en corpus** (`s336g`, tras arreglar la paginación): `SDX-751-TEM` 14 documentos,
  `LPX-751` 13 — todas sus apariciones ajenas son tablas de compatibilidad y listas de sensores
  VIEW que nombran el producto correctamente
- **Estrechamiento de `sdx-751-tem`**: 2 fuentes, adjudicadas `PRECISION` en s334f
  (`DOC_DE_HERMANO`), no re-medido — se arrastra la adjudicación
- **NO medido**: retrieval/generación end-to-end. El gate mide detección y fuentes, no respuesta.

## Alternativas consideradas y por qué se descartan

1. **Seguir puliendo la sonda multimodal** (más lectores, mejor prompt, más páginas). Mejora un
   instrumento que responde a una pregunta que no es la nuestra: el multimodal decide 2 de 84,
   la lectura de texto decide el bucket de los 84 y cuesta ~0.
2. **Promover los 20 tal cual.** Es lo que pedía el número. Mete 6 no-productos (R19) y
   pre-empta 10 adjudicaciones de Alberto (R21) — exactamente lo que R21 prohíbe.
3. **Aflojar el filtro de sujeto** para recuperar `ID-3000` (citado en páginas 32 y 38 de un
   manual de TG). Es una referencia cruzada; atestarla repetiría el mecanismo que dejó 32 de 43
   atestaciones sin cita en s334d.
4. **Redirects mecánicos** para los gemelos (`notifier-inspire-e10`→`inspire-e10`,
   `id-3000`→`id3000`). Es lo que R21 llama adjudicación, y ya me lo cazó el dúo en r43.

## Gaps y riesgos, declarados de entrada

- **El filtro `s336e` es NUEVO.** Ya revisado por el dúo, que corrigió dos cosas: que sea
  monótono (sólo QUITA) **no** implica que no deje pasar falsos —`AM-LCD` lo demostró—, y su
  umbral de R19 («≤3 letras», sin dígitos, una palabra) es una heurística sin medir que dejó
  pasar precisamente el término problemático.
- **`PAGINA_SUJETO = 5` sigue SIN EJERCITARSE**: 0 casos decididos por él en esta corrida.
- **`cat._consumable` es API privada** de `catalog_store`: acoplamiento frágil si cambia.
- **84 → 82 no llega a los «10 como máximo» que pidió Alberto.** La medida dice por qué: **53 de
  84 están gated en sus adjudicaciones** (29 redirects + 10 colisiones R21 + 15 nº de
  referencia, con solape). No hay camino autónomo a 10 sin saltarse R21.
- `LPX-751` se cita por primera vez en la **página 3**, no en la 1. Pasa el umbral, pero es el
  más débil de los tres.
- No he verificado que los 3 manuales sean *sobre* esos productos más allá de la cita; el filtro
  de sujeto es posicional, no semántico.

## Por qué es BP + estructural + escalable

- **Raíz, no parche**: la pregunta «¿qué herramienta paga este huérfano?» se contesta con un
  censo reproducible sobre la fuente (el PDF), no con intuición por fabricante.
- **Escala a 30+**: `s336b/c/e` no tienen nada específico de marca; el coste es una descarga de
  PDF y una regex por documento.
- **La puerta sigue siendo la puerta**: nada se aplica sin el gate, y el gate acaba de demostrar
  que atrapa lo que mi filtro no vio.
