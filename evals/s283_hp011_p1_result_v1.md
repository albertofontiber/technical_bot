# s283 — hp011 P1 RESULTADO: normalizar el TACHADO-OCR en el contexto servido al generador (`STRUCK_OCR_CONTEXT`)

**Lane:** hp011-P1 (s283). **Rama:** claude/s282-h0t2-qa @ 148f059 (SIN commits; HEAD intacto). **DB:** SELECT-only.
**Contrato:** `evals/s283_hp011_diag_v1.md` §5 P1. **Coste real:** ~$0.55 (A/B 3 gen ~$0.3 + bvg dirigido 1 gen+juez ~$0.25; (e) generación FAKE = $0).

## TL;DR — RECOMENDACIÓN: **NO-GO para el flip automático en Railway; surface a Alberto.**

El lever **funciona sobre su diana** (elimina la propagación de `t.Fi`; baseline **FALLO → PARCIAL** en la pasada del juez canónico) y está **byte-inerte con flag off** (suite completa 3228/0). **PERO** la medición (e) destapa un **colateral material**: la política adjudicada del EC (`apply_struck_ocr` = «el primer tachado-con-letras corta el display **hasta fin de línea**») es correcta para un **span de valor-display corto**, pero aplicada a **líneas arbitrarias de contexto** trunca **prosa válida** que sigue a un tachado a mitad de línea. Dispara en **2/3 QIDs de control** (hp002 pierde la cláusula de medición de flujo; hp014 pierde un encabezado). El corazón ESTABLE del FALLO de hp011 (el duplicado corrupto `ri/Resumen/4.1.2` de la Guía Rápida) **NO lo toca P1** — es P2/Alberto por diseño. Ship = decisión de Alberto; **recomiendo no auto-flip** y, si se persigue, **adjudicar una variante que preserve el post-tachado** (nueva regla → nueva adjudicación + dúo Protocolo 3).

**Alineación de MÉTRICA (Protocolo 2/4):** objetivo de HOY = conducta hp011 en GENERACIÓN single-turn (bvg **FALLO**). Ningún «settled» lo zanja. La métrica de P1 se mide en **conveyed-fact-level (t.Fi) + no-regresión de superficie** — es lo reportado abajo.

---

## §1 — Qué se implementó (diseño)

| Pieza | Archivo | Nota |
|---|---|---|
| **Módulo LEAF** (sólo `re`) | `src/rag/struck_ocr.py` (NUEVO) | `apply_struck_ocr` movida **VERBATIM** del EC (cero cambio de conducta) + `apply_struck_ocr_context` (aplica POR LÍNEA física). |
| **Reuso en el EC** | `src/rag/evidence_contract.py` | Sustituye la def local por `from .struck_ocr import _STRUCK_RX, apply_struck_ocr as _apply_struck_ocr`. `ec._apply_struck_ocr IS struck_ocr.apply_struck_ocr` (identidad) → los tests del EC siguen ejerciendo la MISMA política. |
| **Seam del generador** | `src/rag/generator.py` | Flag `STRUCK_OCR_CONTEXT` (default off). Import PEREZOSO del módulo sólo con flag on. Aplica en `source_content` justo tras `coverage_context_content(chunk)`. |
| **Tests** | `tests/test_s283_struck_ocr_context.py` (NUEVO, 13 tests) | (a) del contrato. |

**Punto de aplicación (ÚNICO seam) — por qué:** `generator.py` línea ~618, `source_content = coverage_context_content(chunk)`. Es el **único** punto por el que pasa TODO el contexto servido al writer: ambas ramas de abajo (`_include_context()` on/off) consumen `source_content` para construir `[Fragmento N]`. `coverage_context_content` es el derivador de la vista servida (recorta excerpts por-lane); normalizar su salida cubre coverage-append y reranked por igual. **Granularidad POR LÍNEA** (no blob): el EC aplica `apply_struck_ocr` a un span/línea de obligación, nunca a un chunk multilínea. Al blob entero, el primer tachado-con-letras de CUALQUIER línea truncaría todo el resto del chunk (catastrófico). Por línea, el corte queda contenido en la línea del artefacto. Test `test_context_normalizes_per_line_not_whole_blob` fija el contraste.

**Byte-invarianza (flag off) + patrón de flag:** `_strict_on_off("STRUCK_OCR_CONTEXT")` (estricto on|off, fail-fast, releído en runtime). NO es perfil-owned (env puro; lever en medición, no shipeado). Import perezoso ⇒ con flag off el módulo NI SE IMPORTA.

**Hallazgo de clausura sellada (s277 P1):** un import de `struck_ocr` a NIVEL DE MÓDULO en `generator.py` (que SÍ está en la clausura sellada) mete `struck_ocr.py` en la `implementation_dependency_closure` → 94 tests de `test_s277_c1_p1_runner.py` fallan `HOLD_IMPLEMENTATION_DRIFT: unsealed=['src/rag/struck_ocr.py']`. **Fix (dentro de territorio):** import PEREZOSO en cuerpo de función (mismo patrón que `EVIDENCE_CONTRACT`), que la clausura estática no sigue → 0 cambios a `scripts/s277_c1_p1.py` ni a la gobernanza del baseline inmutable. (El import a nivel de módulo en `evidence_contract.py` es invisible a la clausura: el EC no está sellado, sólo se importa perezosamente.)

## §2 — Mediciones (a)–(e)

### (a) Tests unitarios — **13/13 PASS**
Incluye el CASO REAL del chunk `475a8f18` (F13): superficie que el writer ve ON vs OFF. Asserts clave (ON): `~~` ausente, `t.Fi`/`t.A`/`0 seg.` ausentes, `r.i` y `4.12.2` presentes, `- -` (tachado de sólo-símbolos) conservado, y **COLATERAL medido**: `Rearme permitido en cualquier momento` / `De 01 a 30` (alternativas 00/De01a30 de la MISMA línea física) **caen** (van tras el corte). Paridad EC: `ec._apply_struck_ocr is struck_ocr.apply_struck_ocr`. Seam del generador: off = `~~t.Fi~~` verbatim; on = sin `~~`/`t.Fi`; fail-fast en valor no reconocido.

### (b) Suite completa foreground — **3228 passed, 5 skipped, 0 failed** (flag off por default)
Byte-invarianza confirmada. (Los 94 fallos del sellado s277 quedaron resueltos con el import perezoso, ver §1.)

### (c) A/B judge-free hp011 — 3 ON vs los 3 OFF del diag (`_s283_hp011_ans_*`). Sumas sobre 3 runs (runs-con-señal):

| señal | OFF | ON | lectura |
|---|---|---|---|
| **t.Fi** (DIANA de P1) | 1 (1/3) | **0 (0/3)** | **ELIMINADO** — el token se elimina del contexto; el writer no puede citar lo que no ve (mecanismo determinista). |
| r.i/r.I (correcto) | 16 (3/3) | 14 (3/3) | preservado |
| ABORT enclavado | 4 (3/3) | 4 (3/3) | preservado |
| 4.12.2 (apartado correcto) | 0 (0/3) | 3 (3/3) | ↑ (entrelazado con varianza del served-set; no atribución limpia a P1) |
| ri/Resumen (corrupto, F3) | 7 (3/3) | 3 (1/3) | **no empeora**; direccionalmente baja pero es P2/Alberto (N=3 no concluyente) |
| 4.1.2 (apartado corrupto) | 3 (3/3) | 1 (1/3) | tracks con ri |
| t.A limpio | 1 (1/3) | 0 (0/3) | **COLATERAL** (gap ii): F13 tacha t.A; F11 no lo recompensó en estas pasadas |
| 00 Rearme permitido | 1 (1/3) | 0 (0/3) | **COLATERAL**: alternativa 00 de F13 cae con el corte |
| De 01 a 30 | 6 (3/3) | 2 (2/3) | **COLATERAL parcial** (sobrevive vía F3) |

**Lectura:** (c) MEJORA en la diana (t.Fi 1/3→0/3) sin dañar el contenido nuclear (r.i, ABORT) → autoriza (d). Coste declarado: cae parte del tail legítimo de F13 (t.A/00/De01a30).

### (d) bvg dirigido `ONLY_QIDS=hp011` + paridad + `STRUCK_OCR_CONTEXT=on` — juez canónico GPT-5.5 (single-pass):
**PARCIAL** (baseline = **FALLO**). Diagnóstico del juez: *«Acierta al señalar ABORT enclavado, averías enclavadas, Flow Press y el procedimiento general de rearme. Pero interpreta mal el parámetro r.I … además omite comprobar explícitamente t.A y el estado de zonas/detectores».* El juez **ya NO marca** el `ri`/`F.1` alucinado que motivaba el FALLO; el residual es interpretación de r.I + **omisión de t.A** (= gap ii materializado). **Single-pass, no K-mayoría** (DEC-023): no concluyente por sí solo; consistente con la predicción del diag (P1 sola NO devuelve hp011 a PASS — falta P2/Alberto para la mitad estable `ri`).

### (e) No-regresión judge-free — controles hp002 / cat001 / hp014 (served-set FIJO, contexto OFF vs ON, generador FAKE $0):

| QID | chunks con `~~` | contexto OFF==ON | efecto |
|---|---|---|---|
| **cat001** | 0 | **True** | byte-idéntico. Limpio. |
| **hp002** | 1 | False | `~~y con el conducto de aspiración intacto~~` va A MITAD DE LÍNEA → el corte **trunca prosa válida** que sigue: «se registrarán los valores de la medición del flujo de aire…». **Pérdida de contenido relevante** (reset/baseline de flujo, pertinente a un diagnóstico de flujo bajo). |
| **hp014** | 1 | False | `**~~Hardware de la tarjeta de lazo~~**` → cae el encabezado, deja `**` colgante. Bajo impacto pero superficie alterada. |

**Conclusión (e):** el diff **NO es «~0 fuera de tachados»**. Se localiza en las líneas que CONTIENEN tachados, pero **dentro de esas líneas trunca contenido no-tachado** que va detrás. Dispara en **2/3 controles**. Este es el riesgo (i) que el propio diag declaró («byte-afectante → exige gate de no-regresión»), ahora **medido y positivo**.

## §3 — Recomendación de ship + alternativas + gaps

**Recomendación: NO-GO para poner `STRUCK_OCR_CONTEXT=on` en Railway sin adjudicación de Alberto.**

- **A favor:** ataca el layer correcto (contexto servido, no el prompt — coherente con DEC-097/098); genérico/estructural (artefacto de extracción en cualquiera de 31 fabricantes); reutiliza máquina adjudicada; byte-inerte off; elimina la diana t.Fi (FALLO→PARCIAL single-pass).
- **En contra (decisivo):** la semántica «cortar-hasta-fin-de-línea» de la política adjudicada del EC —correcta para un span de valor-display— **sobre-alcanza** en líneas de contexto arbitrarias: trunca prosa válida tras un tachado a mitad de línea (2/3 controles + el tail de F13). Y **no** resuelve la mitad ESTABLE del FALLO de hp011 (`ri/Resumen/4.1.2`, que es corrupción de corpus → P2/Alberto).

**Alternativas consideradas:**
1. **Ship as-is (flip):** descartada — colateral en controles no es aceptable sin visto de Alberto.
2. **Variante que preserve el post-tachado** (quitar SÓLO el span `~~…~~` y su contenido, continuando la línea): **la mejor candidata técnica**, PERO es una **regla NUEVA** de limpieza distinta de la adjudicada → viola la regla (4) del contrato («no inventes reglas nuevas de limpieza») sin adjudicación previa. Requiere adjudicación de Alberto + dúo Protocolo 3 (zona-de-dolor: OCR/idiomas/serving). NO implementada aquí a propósito.
3. **Stripping en INGESTA:** descartada (diag) — más cara, irreversible, pierde la traza.

**Gaps / riesgos declarados:**
- (i) **[MEDIDO, materializado]** colateral de truncado de prosa post-tachado a mitad de línea (2/3 controles).
- (ii) **[MEDIDO, materializado]** F13 tacha t.A; F11 no lo recompensó → el juez marca «omite t.A». La red no captó el t.A limpio.
- (iii) P1 no toca la mitad estable `ri` (P2/Alberto) → hp011 no llega a PASS con P1 sola.
- Single-pass en (d): no es K-mayoría (DEC-023); veredicto indicativo, no sello.

**Estado de código:** flag OFF por default, suite 3228/0, HEAD 148f059 intacto (sin commits). El lever queda **construido y medido, apagado**; el flip (Railway) y/o la adjudicación de la variante-que-preserva-post-tachado son decisión de Alberto. **Antes de cualquier ship: dúo Protocolo 3** (MEDIO-en-zona-de-dolor).

## §4 — Artefactos
Repo: `src/rag/struck_ocr.py`, `src/rag/evidence_contract.py`, `src/rag/generator.py`, `tests/test_s283_struck_ocr_context.py`, este doc.
Scratchpad (no versionado): `s283_hp011_ab_struck.py`, `s283_hp011_noregress.py`, `_s283_hp011_ans_ON_run{1,2,3}.md`, `_s283_hp011_ans_run{1,2,3}.md` (OFF, del diag).
