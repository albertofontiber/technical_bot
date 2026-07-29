# s286 — Limpieza tachados v1.1 CONSOLIDADA (post-dúo: Sol 9 + sub-agente 12; 0 blockers)

Base = brief v1 + enmienda §E (retiro del duplicado). TODO lo siguiente entra al applier:

## ALCANCE AMPLIADO (Sol F5 + sub H2, censado en vivo)
- `content`: 840 chunks (tokenizador §A del brief).
- `section_title`: 244 filas · `section_path`: 267 filas · `context`: 1 fila
  (`9d8d344e-bf44…`, blurb que cita título tachado) — mismo tokenizador, mismo manifest.
- P2: retiro lifecycle de `2113ac69` + patch 2 etiquetas en `18691365` (r.t→r.I, LA→t.A).
- Gemelos EN del P2 (sub H12): `7a9022bd`/`866cd4eb` (misma corrupción en inglés) — SE AUDITAN
  en el applier con la misma técnica (par bueno/malo) y entran al MISMO paquete si procede.

## TOKENIZADOR ENDURECIDO (Sol F8 + sub H3/H5/H6)
- run-4 = cierre+apertura SOLO flanqueado por no-espacio a ambos lados; run-4 standalone →
  LITERAL + flag en manifest.
- Huérfanos y «0 residuales» se computan CON el tokenizador por-línea (no `count('~~')`);
  número re-declarado por el applier.
- Manifest lista el SPAN de cada par retirado + flag de eyeball para spans >80 chars o con
  puntuación de frase (anti falso-par) → revisión en el pase de entrega.
- Censo de TODOS los run-4 del corpus en el manifest (eyeball, se esperan <10).

## RE-EMBED Y ATOMICIDAD (Sol F3/F6 + sub H4/H10 + nota anti-trampa)
- Input = `context + "\n\n" + content` con `input_type="document"` replicando
  `src/reingest/embed.py:52-59`. **NO usar scripts/re_embed.py** (legacy chunks/OpenAI).
- El chunk `9d8d344e` re-embebe con context LIMPIO (H2). El patch de etiquetas `18691365`:
  auditar su blurb B7 por r.t/LA antes de re-embed (Sol F3); si contaminado → regenerar blurb.
- **Backup incluye content + context + section_title + section_path + EMBEDDING** (rollback
  restaura texto+vector juntos — Voyage no es bit-reproducible).
- Ceremonia atómica-por-staging: (1) yo escribo tabla scratch `_s286_tachados_staging`
  (id, new_content/new_context/new_title/new_path + NEW_EMBEDDING pre-computado) — scratch, no
  toca serving; (2) el paste de Alberto hace el UPDATE-join content+embedding EN LA MISMA
  transacción (ventana cero, cierra Sol F6/sub H10); (3) `search_vector` se auto-regenera por
  trigger (verificado por el sub-agente, migrations/006:181-186).
- Paste multi-MB inviable (sub H8) → el UPDATE-join desde staging deja el paste de Alberto
  PEQUEÑO (solo el join + guards); los datos pesados viajan por staging.

## DERIVADOS Y SEALS (Sol F4 + sub H1/H7)
- 985 enunciados + 2.446 hyq de padres marcados: 0 con `~~` propio (verificado) — intactos.
- **3 hyq de `2113ac69`** (listadas en el applier): se RETIRAN con su padre (y verificación de
  que el canal hyq no sirve hijos de padres no-active — si sirve, fix en el mismo paquete).
- `corpus_fingerprint_v1()` (content+search_vector+embedding) SE INVALIDA por diseño →
  re-captura post-apply + re-anclaje declarado en DECISIONS (cadena C1/s107 que lo pinee).
  Los preregs s282 (aa13e792 = counts+timestamps) NO se invalidan (anti-eco del sub-agente).
- struck_ocr (sub H11): tras la limpieza, la superficie `~~` superviviente = LITERALES que
  `~~(.*?)~~` maneja mal — DECLARADO como restricción conocida (fix fuera de scope, TECH_DEBT).

## VERIFICACIÓN PROPORCIONADA (Sol F7 + sub H9)
0-residuales-por-tokenizador · idempotencia · hp011 re-traza K=3 · smokes hp002/cat018 ·
LQAS post-apply n=12 · **factlevel_assessment smoke** (Protocolo 4) · re-baseline v4 completa
= siguiente paso del arco (ya programada) — la no-regresión total vive ahí.

## CORRECCIONES DE FRAMING (Sol F1/F2/F9 + sub H12)
- Evidencia sellada: packet s285 con marcas de Alberto EN el repo (verificado, 3 [X]) +
  `evals/s286_tachados_lqas_c3_v1.json` escrito (antes solo existía en conversación).
- LQAS re-enunciado honesto: acota tasa, no certifica filas; la autoridad de la clase 3 es el
  ARRASTRE adjudicado por Alberto; el draw es la verificación pactada.
- Cardinalidades exactas (Sol F9): 840 strips + 1 patch-etiquetas (18691365, sin ~~) + 1 retiro
  (2113ac69) = 842 filas tocadas; re-embeds = 841 (el retirado no); + metadata-only rows aparte
  (las 244/267/1 que no estén ya entre las 840 — conteo exacto del applier).
- Nota §E.5: el texto del applier será VERBATIM del render (la paráfrasis queda marcada).
