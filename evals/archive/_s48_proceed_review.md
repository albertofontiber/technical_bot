# s48 — ¿Cómo proceder con el lever context→generator, dado el smoke-débil Y que vamos a ampliar el eval? REFUTA

## Estado verificado de s48 (todo con datos, no teoría)
- **Contextual-retrieval YA activo al 100%** en `chunks_v2` (22.849/22.849 con blurb B7). La premisa de DEC-020 "F2 = medir el cimiento OMITIDO" era falsa. PLAN:381 desalineado.
- **El generador NO usa el blurb** (`generator.py:411` solo `content`); el reranker tampoco. El blurb vive solo en el retrieval (embedding+FTS).
- **Audit 8/8 FALLO (DEC-017): 0 léxico-recuperable.** hp008 (candidato léxico del dúo s48-ronda1) = corpus-gap de extracción, no léxico. Residual = síntesis/razonamiento (6: hp001/05/09/13/19/20) + extracción (2: hp008 tabla-imagen, hp011 7-seg). Material "servable" en casi todos.
- El dúo (ronda 1) cazó mi over-frame pro-F3; lo corregí con el audit (miré el léxico, no lo descarté a ciegas).

## El smoke del lever context→generator (Alberto eligió probarlo)
Cambio: `GENERATOR_INCLUDE_CONTEXT` (default OFF) mete el blurb al prompt, marcado "orientativo, no citable". Smoke con context hidratado completo (5/5) sobre hp005/hp013 (síntesis):
- **A (off) ≈ B (on) en SUSTANCIA.** El blurb situacional NO aparece en la respuesta de B ni mejora la integración — el bot ya sitúa con el `header` (manual/sección/producto) que recibe. El bot **ignora** el blurb.
- **0 fabricación** en B (el marcado + la regla CERO-INVENCIÓN del system prompt lo contuvieron).
- **El generador es NO-determinista**: hp013 con context=0 ya daba A≠B → las diferencias visibles son sampling, no el lever. Un A/B single-run NO separa señal de ruido.
- Señal: lever DÉBIL. NO concluyente (3 casos single-run).

## La pregunta de Alberto (el núcleo)
Vamos a ampliar el eval a ~60-100 (Track B, DEC-021 §C, breadth + split dev/held-out). **¿Eso permite un test más concluyente del lever** (más casos de síntesis → más poder), de modo que convenga DIFERIR el A/B del lever al eval grande en vez de cerrarlo ahora con el smoke?

## Mis dos lecturas (sesgo declarado: me cazaron pro-F3/declarar-techo; ahora riesgo de cerrar-prematuro O de usar "eval grande" como excusa para diferir)
- **(a) Cerrar ahora:** el lever es DÉBIL POR DISEÑO — el blurb es retrieval-oriented, el header ya da contexto estructural, Anthropic deliberadamente lo mantiene fuera del output, y el smoke muestra que el bot lo IGNORA. Si no aporta en 3 casos por mecanismo, más N no lo rescata. El eval grande no cambia el mecanismo.
- **(b) Diferir al eval grande:** el smoke es single-run ruidoso; con N mayor + K-mayoría podría emerger un efecto pequeño-real; y el montaje del A/B se amortiza sobre el eval que se construye igual.

## ENCARGO — REFUTA (no confirmes), y opina sobre el PROCEDER
1. ¿El smoke (A≈B, **blurb ignorado por el bot**) basta para concluir lever-débil, o es débil-single-run y el eval grande daría un test genuinamente más concluyente para ESTE lever?
2. ¿El lever es débil-por-DISEÑO (mecanismo) → más casos no lo rescatan? ¿O hay un mecanismo por el que con más N/diversidad emergería señal que el smoke de 3 no ve?
3. ¿"Diferir el A/B al eval grande" es proceder sensato o procrastinación disfrazada (lección s27: aparato para algo ya decidible)?
4. **Freeze-contract** (§F): si el A/B del lever se corre sobre el eval grande con held-out embargado (§C), ¿hay riesgo de contaminar el embargo o el A/B de contextual-retrieval (que se mide sobre los 22 congelados, §C.2)?
5. Dado TODO (contextual activo, léxico 0/8, síntesis muerta, smoke débil): ¿cuál es el proceder correcto de s48 — cerrar lever + F3 + Track B; o Track B primero y A/B del lever diferido; o A/B acotado ahora? ¿Algún over-claim de framing mío?
