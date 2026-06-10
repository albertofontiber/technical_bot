# s48 — ¿El spot-check cierra F2 (contextual-retrieval) → F3? REFUTA mi lectura pro-F3

## La decisión bajo revisión (ALTO impacto, zona de dolor = retrieval/corpus)
s46/DEC-020 decidió: **"F2 = medir contextual-retrieval, el cimiento BP OMITIDO"**, tras
que el cross-model GPT-5.5 rompiera el echo-chamber Claude diciendo *"`:1246` (top-k/RRF/
rerank/dense YA medidos-no-convierten) NO descarta contextual-retrieval + BM25-léxico-
término-exacto = NO medidos → descartarlos a ciegas = racionalización"*.

## HALLAZGO s48 (verificado en código + BD de producción)
La premisa **"omitido" es FALSA**: contextual-retrieval (Anthropic sept-2024) YA está
implementado y ACTIVO al 100%.
- BD `chunks_v2`: **22.849 / 22.849 chunks con blurb `context` no-vacío (100%)**, avg 320
  chars. Ejemplos reales son blurbs tipo-Anthropic de calidad ("Sección 7.2 Categorías de
  entrada del manual de programación del Panel ID3000…", "módulos direccionables MMX, CMX,
  ISO-X…").
- `src/reingest/contextualize.py` (B7, Haiku+prompt-caching, prompt = el de Anthropic) →
  `src/reingest/embed.py:55` embebe `f"{chunk.context}\n\n{body}"`. El PLAN canónico lo
  sigue listando "pendiente" (`PLAN_RAG_2026.md:381`) → doc desalineado con el código.

## Spot-check barato (lo eligió Alberto)
**(a) ¿Quién usa el blurb?** Solo el retrieval.
- `generator.py:411`: el prompt se arma con `context_parts.append(f"{header}\n{chunk['content']}")`
  — **solo `content`, NO `chunk['context']`**. El generador no ve el blurb.
- `reranker.py`: grep `context` → **0 matches**. El reranker no lee el blurb.
- → el blurb B7 vive SOLO en embedding (vector) + FTS (search_vector peso C). NO en
  generación ni rerank. (By-design Anthropic: el técnico ve la cita limpia.)
**(b) Calidad del blurb en los FALLO (BD):** los chunks-objetivo de hp005 (síntesis
ID3000-coincidencia), hp006 (AFP-400 fallo-tierra, MIDT170) EXISTEN con blurbs precisos.
hp008 (lista de sensores compatibles ID3000) **no aparece por término exacto** (CPX-551E/
SDX551) → recall/extracción-identidad, no contextual.

## Mi lectura — SESGO PRO-F3 DECLARADO (cázalo)
El contextual está implementado, es bueno, solo toca retrieval, y el retrieval ya se midió
no-convierte (gate s45/s46) + retrieve-wide ya cosechó. La ablación A/B (re-embeber slice
sin context) llevaría a F3 *en cualquiera de sus dos resultados* (ayuda→cosechado→F3; no-
ayuda→no-aporta→F3) → rigor mal dirigido (lección s27). **Recomiendo NO gastar en la
ablación; ir a F3 (escala: identidad §E + CATEGORY_TERMS) + breadth, documentando el
residual de calidad como NO-retrieval.**

## ENCARGO — REFUTA (no confirmes)
1. ¿"F3 directo sin ablación" es racionalización de mi prior, o justificado? ¿La ablación
   SÍ cambiaría una decisión — p.ej. si el blurb a veces ENTIERRA el chunk correcto
   (mete ruido al embedding) y quitarlo MEJORA veredictos?
2. **El punto que más me preocupa:** el cross-model de s46 nombró DOS cimientos no-medidos
   (contextual **+ BM25-léxico-término-exacto**). Verifico que el contextual ESTÁ. ¿Y el
   BM25/término-exacto? hp008 (modelos no recuperados por término exacto) ¿es señal de que
   el lever real no-medido es léxico (BM25/RRF sobre `search_vector`), y estoy cerrando F2
   ANTES de mirar ESE cimiento — repitiendo el pecado de s46?
3. ¿3 casos (hp005/06/08) bastan para declarar "residual NO-retrieval", o debo auditar
   hp009/11/13/19 primero?
4. El generador NO ve el blurb ni un header de sección rico. ¿Meter el `context` al
   generador (lever barato, NO medido) podría mover FALLO de síntesis/identidad, o el gate
   "síntesis-muerta" ya lo descarta?
5. ¿Over-claims de framing míos? ("ya implementado", "ya cosechado", "el spot-check cierra
   la pregunta", "F3 en cualquier resultado").
