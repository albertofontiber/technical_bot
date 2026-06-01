# Log de decisiones — Technical Bot

> **Qué es.** Registro **append-only** de las decisiones de impacto **MEDIO/ALTO** del
> proyecto, con su **motivo y las alternativas descartadas**, para trazabilidad futura: si
> en una sesión futura nos cuestionamos un camino, aquí está por qué se eligió y qué se
> rechazó. Nace de la lección de la sesión 35: una decisión sin traza obliga a re-litigar
> el marco entero (y a depender de Alberto como memoria humana).
>
> **Cuándo se escribe.** En el cierre de sesión (ver `CLAUDE.md` → "Cierre de sesión"), o
> en el momento de tomar una decisión med/alto. El Protocolo 2 ya obliga a declarar
> alternativas + motivo al proponer; esto solo lo **persiste**.
>
> **Relación con otros docs (mapa canónico).** `PLAN_RAG_2026.md` = roadmap + estado
> (canónico). `RULER_DESIGN.md` = diseño del ruler + sus decisiones D1-D11. `TECH_DEBT.md`
> = deuda con triggers. `ARCHITECTURE.md` = cómo funciona. **Este log** = el *por qué* de
> las decisiones de rumbo. Las decisiones de diseño del ruler viven como D1-D11 en
> `RULER_DESIGN §5`; aquí van las de rumbo/proceso/producción.
>
> **Formato de entrada.** `DEC-NNN — título` · fecha · impacto · decisión · contexto ·
> alternativas descartadas + por qué · revisión adversarial (ref) · estado.

---

## DEC-001 — Revertir change-1 (lever de generación anti-falso-rechazo)
- **Fecha**: 1 jun 2026 (sesión 34). **Impacto**: ALTO (producción).
- **Decisión**: revertir change-1 (bloque "DOS ERRORES SIMÉTRICOS" del SYSTEM_PROMPT) de `main`.
- **Contexto**: re-validado contra el ruler 19/19 (A/B HyDE-off, temp=0): NO rescata ningún
  falso-rechazo (los 5 FALLO son idénticos con/sin → son **retrieval**) e **induce
  sobre-respuesta** en hp015 (inferencia procedimental NO documentada sobre datos reales del
  CCD-103 — riesgo real, pero NO alucinación de datos).
- **Alternativas descartadas**: mantener change-1 → rechazada (neutral-negativo + riesgo hp015).
- **Por qué**: revertir por **PRECAUCIÓN** (riesgo hp015), NO por superioridad de la rama-B.
- **Revisión adversarial**: `adversarial_review_log.jsonl` entrada 2 (9/9 confirmados; cazó
  over-claims de framing: "no rescata ninguno" = escala gruesa; "retrieval es el cuello"
  retractado; revert = precaución, no superioridad).
- **Estado**: ✅ HECHO (PR #18, squash `8473996`, en `main`; Railway desplegado; pendiente
  smoke en Telegram de Alberto).

## DEC-002 — `PLAN_RAG_2026.md` como único doc canónico + este `DECISIONS.md`
- **Fecha**: 1 jun 2026 (sesión 35). **Impacto**: MEDIO (proceso/docs).
- **Decisión**: `PLAN_RAG_2026.md` es el **único doc canónico** de roadmap + estado + qué
  sigue. Los demás docs tienen un dueño único por tema (mapa canónico en sus cabeceras) y
  apuntan a PLAN, no duplican. Este `DECISIONS.md` registra las decisiones med/alto. El
  cierre de sesión reconcilia PLAN + apendiza aquí.
- **Contexto**: la inconsistencia `PLAN §9.14` (stale, framing s27 "no ampliar ahora") vs
  `RULER_DESIGN §4`/D1 (canónico, "crecer el ruler ahora") **descarriló una sesión entera**;
  el roadmap vivía duplicado en varios sitios y derivaron.
- **Alternativas descartadas**: (a) un doc mega-único → rechazada (ARCHITECTURE/TECH_DEBT
  sirven propósitos distintos; fusionar no es la raíz); (b) sección dentro de PLAN en vez de
  fichero separado → Alberto eligió fichero `DECISIONS.md` separado.
- **Revisión adversarial**: la inconsistencia la cazó el dúo (log entrada 3, F3: "obsoleto"
  era over-claim → son dos ejes compatibles → cross-pointer, no sobreescribir).
- **Estado**: ✅ HECHO (esta pasada de higiene documental).

## DEC-003 — Crecer el ruler por cobertura-diagnóstica (método y nivel)
- **Fecha**: 1 jun 2026 (sesión 35). **Impacto**: ALTO (gobierna la medición de todos los
  levers futuros, en la ventana pre-técnicos).
- **Decisión**: crecer el ruler como instrumento **DIAGNÓSTICO** (NO gate estadístico).
  **Dos capas**: (1) **breadth-baseline FIJO** con el eje del doc (fabricante/tipo/modalidad
  + idioma/ES-EN) cubriendo las 5 conductas (`RULER_DESIGN §1`) + el caso multi-marca-parcial
  + ES/EN — se re-ejecuta siempre = guarda anti-regresión; (2) golds **lever-targeted ENCIMA**
  (no en lugar de). **Criterio de parada = cobertura de TAXONOMÍA** (cada conducta + cada modo
  que el lever toca representado ≥1 vez con calidad), NO un N. Autoría **costosa** (`§6 Gap #4`)
  → crecer **modesto**. **Barrera anti-contaminación** del sintético (pregunta generada
  cross-model y/o revisión de premisa). Asimetría de ausencia + **fracción ciega** de
  localización en los golds nuevos. El "modo de fallo" es **sesgo de autoría declarado**, no
  el eje primario (sería circular).
- **Contexto**: el ruler 19/19 es fiable pero estrecho (3 fabricantes, mayoría spec-lookups);
  sin más cobertura los deltas de lever son ilegibles (lección change-1 con n=19). La ventana
  para construir el instrumento es **antes** de que haya técnicos (recurso escaso de validación).
- **Alternativas descartadas**: (a) **N fijo objetivo** → gate estadístico, anti-patrón
  `feedback_my_bias #14`; (b) **puro lever-driven sin baseline** → ciega la regresión
  multi-marca YA documentada (nd003/cm007, `TECH_DEBT:310`); (c) **estratificar solo por modo
  de fallo** → circular + revertía el eje del diseño (`RULER_DESIGN:241`); (d) **esperar a las
  preguntas reales de DD** → ventana pre-técnicos (honrado en parte: crecer modesto + diferir
  la inversión grande a #10, que aún no está disponible).
- **Revisión adversarial**: log entradas 3 y 4 (cross-model 8/8 + sub-agente Claude, 2
  críticos). Corrigió over-claims míos: G2 revertía el eje sin declararlo (#15); "autoría
  barata" contradecía Gap #4; "~5-8 golds" era gate estadístico encubierto.
- **Estado**: 🟢 APROBADO; ejecución pendiente. Orden: auditar 13 PARCIAL/5 FALLO → asegurar
  baseline (taxonomía + multi-marca) → golds lever-targeted encima → tirar del lever → medir
  sobre baseline+incremento → repetir (INTERLEAVE).

## DEC-004 — Elevar la metadata de revisión a tarea próxima
- **Fecha**: 1 jun 2026 (sesión 35). **Impacto**: MEDIO (corpus/ingesta; riesgo de corrección
  en producción).
- **Decisión**: elevar la gestión de revisiones (`TECH_DEBT #4`) de *trigger-gated* a **tarea
  próxima**.
- **Contexto**: `chunks_v2` (corpus de producción) NO tiene metadata de revisión/fecha/estado
  (verificado en `migrations/006_chunks_v2.sql`); las RPC no filtran por ella → el bot puede
  **citar una revisión obsoleta** y no puede aplicar la conducta "latest-wins" (`RULER_DESIGN §1:67-72`).
- **Alternativas descartadas**: dejarlo tras su trigger original → rechazada (riesgo de
  corrección en prod + es prerrequisito para enforce latest-wins).
- **Estado**: 🔼 ELEVADO; trabajo (revision_parser → columna en chunks_v2/`documents` → filtro
  en las RPC, ~4-6h) pendiente. Documentado en `TECH_DEBT #4`.
