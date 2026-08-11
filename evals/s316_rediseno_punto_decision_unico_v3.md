# s316d v3 — Punto de decisión conversacional: contratos precisos (DISEÑO VIGENTE)

**Qué es.** La versión adjudicable del rediseño. La ARQUITECTURA es la del v2 —contrato de
hechos + un solo escritor— que ambos revisores declararon sostenida en la ronda 7 («ninguno
[de los hallazgos] exige re-arquitectura», Fable). Este v3 corrige los contratos que la
ronda tumbó, con trazabilidad hallazgo→resolución. Convergencia notable: Sol y Fable
llegaron por separado al enmascaramiento de la guardia en fase A y a la infidelidad del
rollback — los dos ejes donde el v2 volvía a sobre-afirmar.

## Correcciones de contrato (cada una responde a un hallazgo verificado)

1. **Firma completa con metadata** (Sol C1 · Fable es_reply):
   `plan_turn_hechos(texto, estado, meta, lexico)` y `plan_turn(texto, estado, meta,
   hechos)`, con `meta = {es_reply: bool, fuente: texto|voz}` inmutable. La exclusión de
   replies (restricción PAGADA de s316b: un feedback en reply jamás invalida) y la
   restricción de rutas en voz viven en el CONTRATO, no en el orden de llamadas. Cubre
   también los replies no-capturados que siguen el camino normal.

2. **El léxico de marcas es un HECHO A DEMANDA con necesidad computada PURAMENTE**
   (§enmendado en ronda 8 — el build lo implementó así y Sol confirmó que el «SIEMPRE»
   de la versión anterior de este punto era un sobre-claim que CHOCABA con la
   restricción pagada de s316c: cero httpx síncrono en el camino caliente — 0,54 s en
   frío por mensaje; el test `test_guardia_no_paga_db_en_el_camino_caliente` la fija).
   La primera pasada DETERMINA con regexes puros si la resolución dinámica hará falta
   (`_necesita_lexico_para_invalidar` + la condición del 5-bis) y solo entonces pide
   `lexico_marcas`; el matching texto↔léxico ocurre EN el plan. La caché de proceso y
   su semántica (fallo NO cacheado) son las de hoy. Los demás hechos a demanda:
   `marca_de_modelo(M)`, `marca_servida(X)`.

3. **Flujo de datos fijado: la política resuelve DESDE el estado post-plan** (Sol C3 — el
   más peligroso): el despachador aplica `plan.transicion` ANTES de invocar la resolución
   conversacional; la política/legacy reciben `estado'` como argumento, no leen
   `user_data`. Sin esto, un carry-forward calculado sobre el estado viejo sobrescribiría
   la invalidación y #70 revive por construcción. (Es el orden que hoy garantiza
   implícitamente grupo−1→lectura; el v3 lo convierte en contrato con test.)

4. **`log` se desdobla** (Sol M5): `log_consulta: bool` gobierna SOLO `query_logs`
   (cortesía y feedback: no — promesa del aviso v7). La persistencia PROPIA de cada ruta
   (`log_feedback`, tabla `feedback`) pertenece a su handler y NO está gobernada por ese
   campo — conflarlos podía borrar telemetría de feedback o falsear la auditoría.

5. **Fase A, dicho como es** (Sol m6 · Fable enmascaramiento — convergente): con la
   guardia −1 viva, el plan NUNCA emite INVALIDAR en vivo (ve el estado ya limpio:
   su predicado exige `estado_modelos` no-vacío). No es «redundante»: es ENMASCARADA.
   Consecuencia de diseño: (a) la lógica portada se testea en fase A como FUNCIÓN PURA
   contra snapshots PRE-guardia (mismos casos del instrumento + batería FUEGO/vamos/
   Xtralis de s316b-c); (b) la fase B es el PRIMER momento en que corre en integración, y
   por eso su gate incluye los testigos e2e + smoke de producción; (c) en voz, fase A
   mantiene la llamada explícita actual y el plan NO invalida (lo hace la llamada) — una
   sola fuente activa por fase, nunca dos.

6. **`transicion_basica` reproduce el QUIRK legacy, con el quirk documentado** (Fable
   rollback): hoy el régimen legacy refresca `last_query_time` en TODO turno RAG (con o
   sin modelos, `:1494`), así que un contexto expirado puede RESUCITAR si un turno sin
   modelos cae dentro de la ventana; F1 arregló eso a conciencia. «Rollback = mismo
   carry-forward de hoy» significa MISMO, quirk incluido — importar el fix de F1 al
   régimen stub sería un cambio de conducta silencioso justo donde se promete fidelidad.
   Firma: `transicion_basica(estado, modelos, query, respuesta, ts)`; test dedicado del
   quirk + test de ventana (`SESSION_TIMEOUT == WINDOW_SECONDS == 3600`; el literal LOCAL
   de `_process_query:1256` queda fijado por test compartido).

7. **El clúster de feedback tiene dueño declarado** (Fable sin-dueño):
   `last_query`/`last_answer_excerpt` MIGRAN a `WorkingState` (los campos ya existen) y
   los puebla la transición de cada régimen; `last_query_log_id` es TELEMETRÍA (FK para
   anclar feedback), NO estado conversacional: queda fuera del invariante, escrito por el
   despachador tras el log, declarado como tal. El invariante de un-escritor cubre
   `mt_working_state`; el scoping deja de ser tácito.

8. **El alcance de fase B lista los DOS writes de F1 que el invariante AST condena**
   (Fable): el write mid-handler de CLARIFY/DECLINE (`:1388`) y el backfill
   post-generación (`:1506`) se IZAN al despachador como transiciones producidas por la
   política. El contrato de la política (enum, golds, gate MT) queda intacto; su GLUE de
   serving se mueve — decirlo así, no «la cascada intacta debajo» a secas.

9. **El gate de consentimiento entra al censo** (Fable): es un return terminal con
   respuesta sobre estado persistido. Queda como PRE-PASO DECLARADO (como la captura de
   reply), fuera del plan — el censo re-congelado lo lista con su justificación.

10. **El test del shell se endurece tipando el vocabulario** (Fable vacuidad): los args
    de los hechos son TOKENS tipados (marca del léxico, modelo detectado), nunca texto
    libre — el vector real (colar texto como arg de hecho) muere por tipo, no por un AST
    que no puede verlo.

## Lo que NO cambia respecto al v2

La arquitectura (dos pasadas puras + shell mecánico + despachador único escritor + F1
congelada debajo + retirada de guardia y clave legacy en fase B), la migración en dos
fases con la voz sin expandir, la reversibilidad (git revert, sin DDL), los gaps
declarados (ES-only, fall-through XFAIL, superficie de regresión, ~1 sesión de coste) y
la eliminación del seam Haiku anticipatorio.

## Estado de adjudicación

- Rondas 6 y 7 del dúo completas (Sol + Fable 5, pin restaurado). Veredicto de ronda 7:
  arquitectura sostenida; hallazgos = precisión de claims y alcance → este v3.
- **Fase A CONSTRUIDA y adjudicada (ronda 8)**: GO de Alberto 11-ago → build → dúo sobre
  el diff. **Fable: SÓLIDO con la equivalencia MEDIDA** (batería diferencial de 32 casos
  contra HEAD en un worktree: 0 divergencias de conducta; 72 combinaciones del predicado
  perezoso exactas; templates byte-idénticos). Sol: NO-SÓLIDO de contratos, los 2 críticos
  aplicados (campos del plan load-bearing; léxico enmendado §2 — el build tenía razón).
  Los 2 medios de Fable aplicados: short-circuit de `marca_servida` como dependencia
  DECLARADA del resolver (la versión fase-A de la lección FUEGO: el sobre-fetch añadía
  roundtrip y superficie de fallo al camino más caliente) y el test de mecanicidad AST
  construido (mordió dos veces al nacer). Nota para el checklist de fase B (Fable m6):
  la guardia resuelve la lista FRESCA por turno y el léxico del plan usa la caché de
  proceso — al retirar la guardia, la invalidación pasaría a caché-estancada; decidir
  la disciplina de caché ANTES de retirar.
- **Fase B: PENDIENTE** (retirar guardia −1 y `last_detected_models`, `transicion_basica`,
  izar los 2 writes F1, actualizar los tests pineados del instrumento).
