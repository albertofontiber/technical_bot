# s320c — Mis 7 recomendaciones de marca para la sentada B2 · propuesta para el dúo

> **Encargo.** Alberto va a sentarse a marcar el packet `evals/s312_goldreview_b2_packet_v3.md`.
> Estas son las marcas que YO le recomiendo. Cada una **escribe en el ruler**
> (`evals/gold_answers_v1.yaml`) vía `scripts/gold_store.py`, y por tanto mueve el denominador de
> la medición fact-level y/o la exigencia de PASS.
>
> **El fallo que debes perseguir es CIRCULARIDAD.** Hoy, en este mismo packet, retiramos el ítem 2
> porque su evidencia era un número que nunca salió del juez — y yo, al retirarlo, cometí el error
> simétrico: argumenté «el gold está bien porque el bot SÍ transmite el hecho», que es decidir el
> alcance de un gold por el comportamiento de un modelo. Eso es exactamente lo que DEC-025 y
> `RULER_DESIGN §2` prohíben. **Ataca cada una de mis 7 recomendaciones buscando esa forma**: ¿la
> justifico desde la FUENTE y el criterio PCI, o desde cómo se comportó el bot / cómo puntuó el
> juez / cómo queda el marcador?

## Contexto imprescindible

- El ítem 2 (`hp011#2`) ya está retirado del packet: su evidencia era `evals/s305_techo_modelo_ab_v1.json`,
  cuyo `oracle_yes` era la constante 2 (bug de lectura del juez, `TECH_DEBT.md` #75).
- Quedan **7 ítems vivos**: 3, 4, 5, 6, 7, 8, 9.
- Las respuestas congeladas que se citan son del FULL v3.2 (`sha 91a4c185e664`, `claude-sonnet-4-6`);
  producción corre Opus 5 desde s308. **Ninguna marca toca un guard de producción** (el ruler es
  eval-only; `grep gold_answers_v1` en `src/` = 0 hits).

---

## Mis 7 recomendaciones

### 9 · CAD-171 (gold NUEVO) → **✅ crear así**: core = ruta `AJUSTES > AVANZADO`, suppl = candado+2222
Es el único fallo ORGÁNICO de producción documentado (DEC-185) y hoy no lo mide nada. El
no-duplicado con `hp001` está verificado contra el fichero: los 6 hechos de hp001 son
candado/2222/1111/pantalla-admin/lista-menú/aviso (`gold_answers_v1.yaml:22-56`); la RUTA solo vive
en su prosa congelada, y la prosa **no entra en el denominador** (`factlevel_assessment.py:816`
itera `core_facts()`). El valor no dispara `_is_meta_ref` ⇒ se mide.

### 4 · `cat018#2` → **✅ partir en dos, AMBAS CORE** (rechazo explícito del demote)
El split es correcto por instrumento gane quien gane el debate de alcance: el compuesto puntúa
máx **0.545** con `fact_match_score` sobre los chunks servidos, por debajo de `SCORE_FLOOR=0.55`, y
solo entra por el slack del guard L1 ⇒ el `partial 4/5` es artefacto del compuesto. Partido: 0.80 y
0.571. **Rechazo el demote** porque su premisa no aguanta (el carrier de «tipo-SW SND» SÍ se sirvió
vía lane de coverage) y porque Alberto ya rechazó un demote de SND en este mismo gold en s269.

### 8 · `hp002` → **❌ no tocar la redacción todavía**
`TECH_DEBT.md:2268-2279` asignó a esta sentada DOS cosas: adjudicar la **conducta** esperada y «de
paso» la redacción. El packet solo ofrece la redacción, presentándola como coherencia sin impacto.
Hoy el gold lleva `conducta_esperada: answer` mientras producción rechaza por la ruta `mismatch`.
Armonizar retira el artefacto que hace visible esa contradicción **sin firmarla**.

### 3 · `hp017#2` → **✏️ partir + reformular** con el operando p43 (rechazo «ambas reglas»)
La opción ✅ del packet re-ancla la mitad (b) de p43 a p45. p45 es (i) casi literal lo que la
respuesta congelada ya escribe, (ii) lo que un apéndice must-preserve determinista vuelca solo, y
(iii) los marcadores exactos de una obligación ya cableada (`answer_planner.py:1157-1182`). El gold
pasaría a medir **si disparó un renderer**. Además el matiz que motivó esa opción es media verdad:
p43 —citada en el `citations` del propio gold— dice, singular, «Es fundamental borrar la regla 1…».

### 6 · `cat020#2` → **✏️ cambiar el `valor` Y recortar el `texto`**
El `valor` de hoy es un puntero que duplica el campo `cita`, y por eso `_is_meta_ref` lo esconde del
nivel-hecho mientras el eje PASS ya lo exige y ya lo penaliza: incoherencia entre ejes, no
protección. El recorte del texto es obligatorio, no cosmético: con el texto largo el score es
**0.294 < 0.40** y el hecho puede aterrizar como **retrieval-miss FALSO**.

### 7 · `hp001#2` → **✏️ quitar «completa», CONSERVAR la negación sobre 1111**
La ✅ del packet hace dos cosas en direcciones opuestas: quita el hedge sin cita (aprieta) y
sustituye la negación explícita sobre 1111 por «requiere otra clave/nivel» (afloja) — justo el
discriminador del error real medido.

### 5 · `hp006#2` → **✏️ demote + reescribir la prosa del `gold_answer`**
**Leí la fuente**: `15088SP p70` dice «El ISO-X **vee este corto** y desconecta la rama fallante…».
El mecanismo descrito es CORTOCIRCUITO, no derivación a tierra. Recomiendo demote, pero **con la
prosa reescrita en el mismo upsert** (`gold_answer:686` y `:688`), porque si no el gold afirma ante
el juez de PASS lo que el label niega. Y el demote a secas repetiría la forma del ítem 2: encoge la
cola de etapa 3 de 9 a 8 sin que el bot mejore.

---

## Debilidades que declaro de entrada

1. **Uniformidad sospechosa**: las 7 fichas que sustentan esto volvieron con
   `requiere_criterio_pci: true` y confianza `media` — las siete. Yo escribí el encargo con esa
   salida autorizada. Gastando dos consultas al corpus, el ítem 5 dejó de ser «criterio de
   Alberto». **Sospecho que quedan más así y no he agotado esa vía.**
2. **Ítem 5, tensión en la fuente**: `50253SP p89` describe el ISO-X genéricamente («si un circuito
   falla») y el índice lo llama «Módulo aislador de **Falla de Lazo**». El texto del mecanismo dice
   «corto». No he resuelto esa tensión, solo la declaro.
3. **Ítem 6 sin verificar**: no encontré la sección del DXc en el corpus; la afirmación de que se
   titula «específica para protocolo Morley-IAS» viene de un agente, no de mi lectura.
4. **Ítem 3, premisa nunca sondada**: el carrier de la p43 NO figura en `served_ids` de ninguna de
   las 3 reps de s293 ⇒ al modelo jamás se le puso delante esa evidencia. Es candidato a APLAZAR.
5. **No he re-medido nada** para los ítems 3-9. Todas las cifras son de recibos congelados con
   sonnet-4-6.
6. Las proyecciones de %OK mezclan denominadores (131 clasificados vs 133 cores).

## Preguntas concretas

1. **¿Alguna de las 7 es CIRCULAR** — justificada por comportamiento del bot, puntuación del juez o
   efecto en el marcador, en vez de por fuente/PCI?
2. **Las 4 trampas que declaro** (demote del 4 mejora el marcador sin tocar el bot · «ambas reglas»
   del 3 mediría un renderer · demote del 5 repite la forma del ítem 2 · «expectativa de CITA» del 6
   no escribe nada porque no existe el campo): ¿son reales? **¿Falta alguna?**
3. **¿Es sólida mi lectura de la fuente del ítem 5**, y licencia el demote — o la tensión
   genérico-vs-mecanismo obliga a dejarlo en manos de Alberto sin recomendación?
4. **¿He clasificado mal qué decide Alberto y qué decido yo?** Busca ítems donde digo «es suyo» y
   en realidad la fuente lo responde, y al revés: donde recomiendo y debería callarme.
5. **¿Alguna recomendación escribe en el ruler algo que no he declarado** (denominador, PASS,
   renumeración de índices, rotura de join de series)?
6. **¿Debe el ítem 3 aplazarse** dado que su premisa nunca se sondó?

Si alguna recomendación te parece sólida, dilo. `SÓLIDO` es respuesta válida por ítem.
