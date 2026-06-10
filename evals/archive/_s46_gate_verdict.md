# Gate s46 — ¿Fase 2 (lever de calidad) o Fase 3 (escala)?

## Contexto
Bot RAG técnico de protección contra incendios (PCI). Eval "gold" de 21 preguntas; cada
respuesta del bot tiene veredicto PASS/PARCIAL/FALLO y "hechos atómicos core" verificados
contra el manual. Universo no-PASS ≈ 16 (13 PARCIAL + 3 FALLO).

**Decisión de rumbo:** ¿hay un LEVER de calidad que valga la pena (Fase 2: mejorar
retrieval — contextual-retrieval / BM25-híbrido — o generación), o NO lo hay y se pasa a
Fase 3 (escalar a más fabricantes: contrato identidad-producto, catálogo)?

**Historial (decidido por MEDICIÓN en sesiones previas, no opinión):**
- El cuello NO es generación/síntesis (3 levers de generación medidos y fracasados, DEC-001/005/006).
- retrieve-wide (top_k 15→50) cerró los FALLO peligrosos (s44, FALLO ~6→1).
- Caveat fuerte "recall no convierte": mejorar recall históricamente NO movió veredictos.
- Prior honesto declarado: **Fase 3**.

## Lo que hice esta sesión (s46)
Arreglé un matcher (frontera-dígito: "99" ya no casa dentro de "990") y corrí un audit del
funnel de retrieval + un cruce source-anchored: por cada hecho FUERTE (número ≥2 díg / código
de modelo), ¿está en el top-5 que vio el bot?, y ¿el bot lo usó en su respuesta?

## Mi conclusión preliminar (PROBABLEMENTE SESGADA) fue: **Fase 2 (lever retrieval)**
El cruce mostró: síntesis-genuina FUERTE ~0 (el bot usa lo que ve), y el cuello = "retrieval-
residual" (el dato fuerte está en el manual objetivo pero no sube al pool@50), en ~4 casos
(cat001, hp002, hp008, hp011). hp008 tenía 4 códigos de modelo no recuperados → lo leí como
señal de BM25-híbrido / contextual-retrieval.

## Un revisor adversarial (sub-agente, MISMO modelo que yo = Claude) lo REFUTÓ → **Fase 3:**
1. Síntesis-genuina no es 0 sino ~2 dispersos (hp005, hp010), de PROSA, no rentable (y el eje
   síntesis/retrieval para prosa es ruidoso: un FP de quote-overlap metió un retrieval-miss en
   el bucket SÍNTESIS en hp014).
2. **12 de 16 no-PASS tienen CERO hechos fuerte-retrieval.** El retrieval no es el cuello del grueso.
3. **hp008 = 36% (4/11) de todo el fuerte-retrieval en UN solo caso "catálogo"** (pregunta:
   "¿qué detectores son compatibles?"); el bot ya listó 6 modelos correctos, faltan otros de
   una lista larga → eso es Fase 3 (contrato identidad-producto / matriz), no un lever de retrieval.
4. **"Recall no convierte" aplica** — cada PARCIAL/FALLO arrastra un componente de
   PRECISIÓN/RAZONAMIENTO que el retrieval no toca (verificado en los diagnósticos del juez):
   - hp011 (FALLO): describe MAL el parámetro `ri` (nombre/valores/default incorrectos) = generación.
   - hp002 (PARCIAL): mezcla "rotura de tubo" como flujo-bajo cuando produciría flujo-alto = razonamiento.
   - cat001 (PARCIAL): ya respondió lo principal (318/512/autoconfig); faltan valores CLIP
     secundarios de una pregunta multi-parte enorme.

## Veredicto actual: **Fase 3** (el prior se sostiene; mi Fase 2 era mi sesgo conocido de pre-suponer un lever).

## Tu encargo (cross-model — ROMPES el echo-chamber: yo y el sub-agente somos AMBOS Claude)
NO confirmes por consenso. Tu trabajo es REFUTAR Fase 3 / cazar un blind spot compartido por dos instancias del mismo modelo:
1. ¿Hay un lever que descartamos PREMATURAMENTE — incluido uno barato, no-binario, que el marco rígido F2/F3 esconde?
2. ¿El argumento "recall no convierte" es sólido, o es una RACIONALIZACIÓN para no hacer el experimento F2 (que sería el test honesto)?
3. ¿hp008 (catálogo) pertenece realmente a F3, o es una señal de retrieval generalizable que estamos descartando porque es incómoda?
4. Si Fase 3 es correcto, ¿qué es lo de MÁS señal y MÁS barato que F3 debería atacar primero, dado que no hay técnicos reales aún (fase due-diligence M&A)?
