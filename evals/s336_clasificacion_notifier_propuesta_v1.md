# s336 · Lote de clasificación por categoría del catálogo — Notifier primero (GO Alberto 21-ago)

## 0 · Objetivo y MÉTRICA (el lever de HOY)

La fila real `a9ba756a` (21-ago 15:53Z, voz): «¿Qué centrales de Notifier tienes?» →
«ninguno de los **3** productos clasificados casa con "central"» — el inventario FILTRADO
es inservible para Notifier: **480 consumibles sin `clasificacion` (478 con docs)**; los 3
clasificados son software (TG). Global: 1.019 sin clasificar de 1.187 (15% cubierto).

Métrica del lote (pre-registrada):
- **Gate de MÉTODO**: precisión de la alta-confianza vs mini-GT NUEVA ≥95% en categoría
  (sin contradicción en tecnología/lazos donde el GT los tenga), n≥10 — la MISMA barra
  del gate s322-76 que pasó 19/19. Población nueva ⇒ **GT nueva congelada** (el análogo
  del DEC-126: sin herencias).
- **Gate de EFECTO (G6)**: la query real de producción re-jugada sirve listado gobernado
  de centrales Notifier NO vacío; before/after de clasificados/ciegos estampado.
- **No-regresión**: las 168 filas clasificadas existentes byte-idénticas (el writer solo
  AÑADE donde falta); inventario sin-filtro byte-igual; suite + MT.

## 1 · Recomendación: EXTENDER el método s322-76, sin cambiar ninguna pieza

El método ya existe, está MEDIDO y adjudicado (provenance de las 168: «s322-76 población
fable-5, gate GT 19/19 PASS; §0 adjudicado por Alberto 14-ago»; dúo r27 aplicado en
`evals/s322_76_propuesta_v1.md`). El lote s336 es el mismo método sobre población nueva:

1. **Censo diana Notifier**: 478 sin clasificar CON docs en doc_map (267 con 1 doc, 211
   con 2+); los 2 sin docs → packet «sin evidencia» (jamás inventar). **EXCLUIDOS los
   `unresolved:*` (45)**: sin marca resuelta el inventario por marca no los sirve —
   clasificarlos no paga nada hasta que Alberto resuelva el namespace (cola declarada).
2. **Población fable-5**: MISMO prompt/esquema/degradación de s322_76_poblacion.py
   (muestra real de SUS docs vía doc_map, 3 chunks×3 docs; veredicto {categoria∈enum
   CERRADO, tecnologia?, lazos?} con CITA VERBATIM POR CAMPO; cita verificada contra la
   muestra o la confianza se degrada sola; divergencia multi-doc → ambas entradas, jamás
   fusión). Script parametrizado por censo — reuso, no re-diseño.
3. **Mini-GT nueva**: 30 productos Notifier estratificados (familias aparentes:
   centrales NFS/ID · detectores · sirenas/AV · módulos · fuentes · software · accesorios;
   y 1-doc vs multi-doc), etiquetados A MANO leyendo los docs ANTES de la pasada
   (disciplina s322 §6). Congelada con SHA antes de correr la población.
4. **Escritura**: SOLO alta+cita-verificada, por la puerta del catálogo
   (validate/backup/swap), `provenance: "s336 método s322-76 …"` por fila; media/baja/
   sin-cita → packet §1 (una a una); fuera-de-enum → packet con propuesta (el enum es
   CERRADO: central|detector|pulsador|sirena|modulo|fuente|repetidor|aspiracion|barrera|
   retenedor|pasarela|software|accesorio — ampliarlo es adjudicación del owner, no mía).
   La excepción «alta se escribe sin preguntar fila a fila» NO se presupone: viene
   ADJUDICADA del mandato 13-ago (r27 Fable M3 → §0) y este lote la hereda declarándola.
5. **Efecto**: replay de `a9ba756a` + filtros central/detector/sirena de Notifier
   before/after + conteo de ciegos. Smoke de 10 productos PRIMERO (coste real medido)
   antes de la pasada completa.

**Colas declaradas del MISMO método** (cada una con su GT y su gate, no en este lote):
morley 119 · systemsensor 78 · xtralis 38 · kidde 26 · securiton 25 · kac 12 · resto.

## 2 · Alternativas consideradas y por qué se descartan

- **Clasificar por nombre/patrón de familia ($0, sin leer docs)**: viola el principio
  rector de `reglas_clasificacion.json` («el sujeto es lo que el documento dice, no el
  nombre») y R19; sin cita anclada no hay fila defendible. Descartada.
- **Clasificar desde la web del fabricante**: R18 la usa para VALIDAR dudas puntuales,
  no como fuente masiva (no versionada, no citable contra el corpus). Descartada.
- **Todo el backlog (1.019) de una tacada**: un gate por marca detecta deriva de método
  por población (docs de otro fabricante = otro estilo documental); tranche por marca.
  Descartada la tacada única.
- **LLM en el turno (clasificar al vuelo al preguntar)**: coste y latencia por consulta
  para un dato ESTÁTICO que se ancla una vez; el catálogo gobernado es el sitio. Descartada.

## 3 · Gaps y riesgos DECLARADOS

1. **GT etiquetada por mí** (leyendo docs, sin LLM) — mismo agente que configura la
   pasada: riesgo de sesgo compartido. Mitigación: es la disciplina que el dúo r27 ya
   revisó y Alberto adjudicó; los límites del GT se marcan `duda` y quedan FUERA del
   gate (como en s322); el dúo de esta ronda puede exigir muestreo extra u owner-labels.
2. **Coste/latencia**: ~478 llamadas fable-5 (~7k in / 500 out) — estimo $10-20 y
   ~1-1,5 h secuencial. El smoke de 10 calibra el coste REAL antes de comprometer la
   pasada; se estampa en el recibo.
3. **267/478 tienen UN solo doc**: sin contraste multi-fuente (divergencias imposibles
   con n=1) — declarado; la cita sigue anclando y el gate mide la precisión igual.
4. **La muestra (3 chunks×3 docs) puede no contener la sección de enumeración (R9)**:
   entonces no hay cita → el método degrada a media/baja → packet. El falso-ALTA es lo
   que el gate mide; la cobertura es informativa, jamás gate (s322 §6).
5. **R20 NO aplica y por qué**: `clasificacion`/`atributos` no tocan resolve/models/
   allowed_sources — solo la vista de inventario (mostrador). No hay pérdida posible de
   fuentes. (El riesgo de estrechar era de PROMOCIONES; aquí no se promueve nada.)
6. **Enum posiblemente insuficiente para Notifier** (¿EVAC/megafonía/audio?): lo que no
   quepa va a packet con propuesta de valor nuevo — el validador revienta claves
   desconocidas (por diseño), así que nada entra por la puerta de atrás.
7. Los 3 clasificados de Notifier (software) NO se tocan; los 2 sin docs, a packet.

## 4 · Por qué es BP + estructural + escalable

Método medido con gate reproducible, agnóstico de marca (doc_map + corpus + enum
cerrado), dato en el catálogo GOBERNADO versionado con cita+provenance por fila, y
tranches declaradas para el fabricante 31. No es un parche a la respuesta de Notifier:
es la población del dato que el mostrador (s322) ya sabe servir.

## 5 · Build (B1-B6, tras el dúo)

B1 censo diana notifier (espejo parametrizado de `s322_76_censo_diana.py`) · B2 mini-GT
30 a mano + freeze SHA · B3 smoke 10 (coste real) → pasada completa · B4 gate ≥95% +
packet §0/§1 · B5 writer alta-verificada por la puerta + efecto before/after + suite/MT ·
B6 recibos + DEC + digest/PLAN/HISTORY + PR con mergeabilidad verificada.
