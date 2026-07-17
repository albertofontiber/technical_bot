# CLAUDE.md — Technical Bot PCI

Bot RAG de Telegram para técnicos de PCI (protección contra incendios): Claude API
(Sonnet genera) + Supabase pgvector. Responde SOLO desde manuales oficiales, cita
fuente, y admite cuando no sabe. Contexto M&A (Fontiber); escala a 30+ fabricantes.

- Arquitectura: `docs/ARCHITECTURE.md` (el banner del inicio = estado actual).
- Plan / roadmap: `docs/PLAN_RAG_2026.md`.
- Deuda técnica: `TECH_DEBT.md`.

## Comandos
- Tests: `python -m pytest -q`
- Eval bot vs gold: `python scripts/test_bot_vs_gold.py` (fuerza chunks_v2)
- Correr con el corpus nuevo en local: `CHUNKS_TABLE=chunks_v2 python ...`

## Deploy (Railway — auto-deploy desde `main`)
- Railway despliega `origin/main` automáticamente al hacer push. Las variables de
  entorno viven en Railway (dashboard), NO en el `.env` local.
- El SWAP de corpus es la variable `CHUNKS_TABLE` (`chunks` viejo OpenAI-1536 /
  `chunks_v2` Voyage-1024). `chunks_v2` requiere también `VOYAGE_API_KEY` en
  Railway. Es reversible (cambiar/quitar la variable).
- Cuando vayas a desplegar → tests verdes → smoke del bot completo → **PR (no push
  directo a `main`)** → merge → verificar en producción → rollback documentado.

## Protocolo 1 — Verificar antes de declarar
Cuando vayas a escribir "hecho / confirmado / en producción / desplegado /
funciona / listo / pasa" sobre un cambio → ejecuta la verificación EN EL MISMO
TURNO y cita el resultado:
- "en producción / desplegado" → `git log origin/main..HEAD` (¿pusheado?) + de qué
  rama despliega Railway.
- "tests pasan" → corre la suite.
- "funciona / listo" → smoke del path real (no solo tests unitarios).

Cuando NO puedas verificar ahora → usa lenguaje condicional ("creo que",
"pendiente verificar"). NUNCA afirmación de éxito sin verificación.

## Protocolo 2 — Propuestas de rumbo (arquitectura, método, plan, deploy)
Cuando propongas un rumbo de alto impacto → ANTES de presentarlo, ejecuta
auto-pushback adversarial en thinking (simula: "¿es BP? ¿estrictamente? ¿escala a
30+ fabricantes? ¿es necesario dado lo que ya está decidido?") e itera hasta que
no quede auto-corrección. NO presentes la primera versión razonable.

Cuando presentes la propuesta → incluye SIEMPRE, visible en el texto:
1. la recomendación;
2. alternativas consideradas y por qué se descartan;
3. gaps / riesgos conocidos (declarados de entrada, sin esperar pushback);
4. por qué es BP + estructural + escalable;
5. **si toca un lever YA medido:** declara visible la MÉTRICA del objetivo de HOY + la métrica de
   cada «settled/NO-GO» citado + si coinciden (un settled-en-PASS NO zanja un lever medido en
   retrieval-miss). La visibilidad ES el control.

La ausencia de (2) y (3) en una propuesta es la señal de que no hiciste el
análisis. La visibilidad ES el control — no una auto-pregunta privada.

## Protocolo 3 — Revisión adversarial antes de build/commit (medio/alto impacto)
ANTES de cablear/commitear una decisión de impacto MEDIO o ALTO → lanza el revisor
adversarial (spec: `docs/ADVERSARIAL_REVIEWER.md`). Es para no depender de Alberto como
anti-bias (feedback_my_bias). Tiering: Fable 5 (lee código mediante
`scripts/adversarial_review_fable.py`) siempre; y si es
ALTO **o** MEDIO-en-zona-de-dolor (corpus/idiomas/legacy/retrieval/esquema), TAMBIÉN el
revisor principal GPT-5.6 Sol con `reasoning_effort=xhigh`
(`scripts/adversarial_review.py`) — una sola familia comparte blind
spots conceptuales. Reglas: **(C)** verifica sus claims fuertes contra el código antes de
actuar (Protocolo 1 aplica a su output); **(F)** aumenta, no reemplaza — yo decido y soy
responsable. Guardarraíl anti-ritual: precisión/recall en casos congelados con fallos conocidos
y controles limpios, más coste; una propuesta sólida puede devolver `SÓLIDO`. NO es un `/propose` 2.0:
debe producir bite concreto anclado en evidencia (validado: cazó 5 fallos del localizador).
**s56→s73→s88→actual:** el segundo revisor frontera corre de forma independiente con pin
`model: fable` / proveedor `claude-fable-5` (Fable 5; Alberto, s88; s73→s88 fue `opus`)
y el revisor principal es
GPT-5.6 Sol xhigh; en
ALTO/zona-de-dolor el dúo es INNEGOCIABLE (no "recomendado"). **s88 (Alberto): Sol también
LEE el repo** — `adversarial_review.py` corre
un loop agéntico sobre Responses API (`store=False`) con tools read-only sobre el repo versionado
(`read_file`/`grep_repo`/`list_dir`; sandbox + deny `.env*`/tally;
cap 30 calls; `--no-tools` escape) → acceso autónomo al repo versionado (memoria externa material
se adjunta como snapshot autorizado; cierra TECH_DEBT #36; smoke: cazó 2 claims falsas plantadas
con ancla fichero:línea). Ronda nueva de review =
agente FRESCO siempre. (Histórico s73: el dúo-Opus cazó 4 issues que el dúo-sonnet previo NO vio →
el modelo top del momento como sub-agente es materialmente más fuerte en verificación de código.)

## Protocolo 4 — Registro de procedimientos canónicos (gatillo → acción)
**Regla rectora (extiende el Protocolo 1):** antes de declarar que seguiste un procedimiento o
que algo está "hecho/completo/verificado", **re-lee su checklist canónico y verifícalo punto por
punto EN EL MISMO TURNO**. La ausencia de verificación punto-por-punto ES la señal de que no lo
hiciste. (Nace s49b: declaré 2× "procedimiento seguido" sin completarlo + arrastré 3 sesiones la
premisa no verificada de contextual-retrieval — `feedback_my_bias`: el sistema no depende de Alberto como anti-bias.)

| GATILLO | ACCIÓN OBLIGATORIA | Canónico |
|---|---|---|
| Autorar/editar un gold | **ANTES (selección, s50):** revisa las preguntas YA existentes → **no-duplicado**; elige por **DIMENSIÓN DE FALLO desde la FUENTE** — `chunks_v2` JAMÁS criterio **ni en la SELECCIÓN** (artefactos content-pobre/fragmento = causa post-hoc, no eje de autoría). **DESPUÉS:** checklist completo de localización + verificación; ancla en la FUENTE; escribe vía `gold_store` (la puerta valida) | `RULER_DESIGN §2`; `DEC-025` |
| Tocar retrieval/generación/una premisa/un "cimiento" | Verifica el **código y el estado real PRIMERO**; no teorices sobre premisas no verificadas (Protocolo 1 aplicado a premisas) | `DEC-022`; bias #20 |
| Correr eval / medir un lever | Held-out **embargado**; juez GPT-5.5 + **K-mayoría** (no single-pass); 2 ejes (completitud↑ sin invención↑); freeze-contract (corpus+índice+embeddings+juez+seeds+config) | `DEC-023/015/001/021§F` |
| Proponer/elegir/opinar/**NEGAR** sobre un lever o un hecho estructural (¿existe X? ¿ya probamos Y?) | **NUNCA de memoria:** revisa el digest de levers (inyectado al inicio · `docs/LEVER_DIGEST.md`) + grep `DECISIONS.md`/`TECH_DEBT.md` ANTES de responder. **Gate/audit primero** (no pre-suponer — Protocolo 2); mide **delta en eval**, no proxies. **El "settled" tiene MÉTRICA:** cita la métrica del veredicto y verifica que coincide con el objetivo de HOY (settled-en-PASS ≠ settled-en-retrieval-miss) | `DEC-019/005`; `LEVER_DIGEST`; bias #51/#52 |
| Re-medir dónde caen los hechos (tras cambio de pipeline/golds) · saber "qué tal funciona el bot" a nivel-hecho | Correr el **assessment estandarizado** `scripts/factlevel_assessment.py {smoke\|full}` (smoke SIEMPRE antes del full — coste). **Estampar la fila en el scoreboard** (`docs/FACTLEVEL_ASSESSMENT.md`) + **verificar a mano CADA corpus-gap** (`feedback_corpus_gap`: son FN hasta probar). Mide ruta HARNESS con flags-demo, NO el bot Telegram. Sub-motivo de síntesis contaminado por scope/gold → no zanja lever sin gold-review | `docs/FACTLEVEL_ASSESSMENT.md`; `DEC-094` |

**Criterio de inclusión** (que el registro no crezca arbitrario): solo procedimientos/contratos
RECURRENTES (se aplican en un gatillo repetido), no decisiones puntuales. Extender al cerrar sesión
si una decisión med/alto establece un procedimiento nuevo. El detalle vive en el doc canónico (no se
duplica aquí); esta tabla solo gatilla + apunta.

## Convenciones de trabajo
- **Contrato de toda propuesta: BP + estructural (raíz, no parche) + escalable.**
  Declara el resultado; si algo falla, declara el gap honestamente.
- **Pregunta cero (antes del contrato)**: ¿este trabajo cambia una decisión real, o
  es rigor mal dirigido? No construir un aparato para algo que ya está decidido
  (lección sesión 27: el pre-registro estadístico de un SWAP ya decidido).
- **Eval-driven**: ningún cambio de calidad se da por bueno sin medir delta en eval.
- **NO usar `/propose`** — se volvió ritual vacío (sesión 21). Internalizar el
  contrato directamente.
- Precisión > velocidad. Arreglos de raíz. Sin sobre-ingeniería.

## Cierre de sesión
Antes del commit final, actualizar (en orden de canonicidad):
1. **`docs/PLAN_RAG_2026.md`** — doc CANÓNICO del roadmap + estado + qué sigue. Reconciliar su
   bloque "Estado actual" + "Qué sigue" con lo avanzado — **manteniéndolo COMPACTO** (s56/DEC-036:
   el PLAN se relee cada arranque; llegó a 123KB y se partió). El **RESULTADO narrado de la sesión
   se APENDIZA a `docs/HISTORY.md`** (log append-only), NUNCA se apila en el PLAN. NO dejar que un
   sub-doc (RULER_DESIGN §4, el banner de ARCHITECTURE, o la memoria) sea la única fuente del
   estado: PLAN manda (lección s35 — el desalineamiento §9.14 vs RULER_DESIGN §4 costó una sesión).
2. **`docs/DECISIONS.md`** — apendizar toda decisión de impacto MEDIO/ALTO de la sesión
   (decisión · motivo · alternativas descartadas · ref al `adversarial_review_log.jsonl`). Es
   la traza para no re-litigar el rumbo en el futuro. **Si la sesión cambió el veredicto de un
   lever** (o estableció uno nuevo), SOBRESCRIBE su fila en `docs/LEVER_DIGEST.md` in-place (el
   digest que el hook `SessionStart` inyecta; una fila por lever, con su MÉTRICA — nunca apilar).
3. **`docs/ARCHITECTURE.md`** (cifras, estado del sistema) + la **memoria del proyecto**. El detalle
   de sesión va al **topic file** (`memory/*.md`) + `docs/DECISIONS.md`; el índice **`MEMORY.md` es UNA
   línea por memoria (puntero estable, NO log)** — nunca apilar el resultado de la sesión en la línea
   del índice (s54: reventó el límite de 24KB por acumular s44→s52b ahí; la traza canónica vive en
   DECISIONS.md/PLAN, no en el índice).

Working tree limpio.
