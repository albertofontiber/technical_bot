# s332 · Gates GC0/GC1/GC3 — RESULTADO (21-ago-2026) · fallos=0, exit 0

> Recibo: `evals/s332_gc_v1.json` (respuestas verbatim dentro; LEÍDAS, DEC-092b).
> Corrió sobre `379f92da` (lotes E1+E2 commiteados) + B5 en working-tree — B5 es capa BOT
> (sufijo + obs de trace) y la ruta harness de los gates no la ejercita: su cobertura son los
> tests unitarios `test_s332_b5_render.py` (17 passed) y la verificación en prod post-flip.

## GC0 (flags off) — conducta de HOY, byte a byte: PASS 7/7
Los 5 turnos reales de la mañana + controles: normalizador INTACTO (BQide/ID/id-minúscula/
ID3000), death-knob sigue corrigiendo y sigue muda, y «me refería a Kidde» cae en
`new_brand_no_state` (la plantilla vacía del incidente — el statu quo exacto).

## GC1 (flags on) — la mañana re-jugada: PASS 7/7
- `02055e5d`: «¿Qué centrales BQide tienes?» → **reescrito a Kidde** + 1 asunción
  (`marca_asr`/`reescrito`, detectado=BQide).
- `2b3febb6`/`838e71a6`: texto **INTACTO** + asunción modo `aviso` (ID↔Kidde) — el usuario
  legítimo de la familia ID conserva su respuesta.
- Controles del homógrafo: «id al menú de configuración» y «la ID3000 en fallo» **sin disparo**.
- `576a7ef9`: «me refería a Kidde» → `brand_correction_rebuild`, qfr = pregunta base +
  «(el usuario corrige: la marca es Kidde)» → **respuesta e2e con contenido Kidde REAL y
  CERO cross-brand** (leída): «centrales **Kidde Commercial**: Serie NC — NC-PF2/4/8[-SC],
  32 dispositivos por zona, 2 salidas supervisadas…» con citas [F1]-[F6]. La plantilla vacía
  está MUERTA en el harness.

## GC3 (on, estabilidad) — 4/4 PASS
El par BQide→corrección repetido: `brand_correction_rebuild` y respuesta con contenido en
todas las reps (transitorios de canal Supabase recuperados por el retry — no afectan al
veredicto; las 4 respuestas guardadas y leídas, consistentes).

## GC2 (no-interferencia) — en piezas, todas verdes
- MT `test_multiturn_vs_gold`: **52/52 con flag off Y con flag on** (executor E2, exits 0).
- Casos borde: 21 tests de `test_s332_correccion_marca.py` (negación, sustancia extra,
  modelo explícito gana por A, sin last_query, fuera de ventana, EN, encadenado, léxico
  ilegible=statu-quo) + 33 de `test_s332_asr_confusiones.py` (homógrafo/boundaries/case) +
  17 de `test_s332_b5_render.py` + 6 de `test_s332_observabilidad.py`.
- Suite completa final (árbol con B5 incluido): **4823 passed, 91 skipped, 2 xfailed, 0 failed — PYTEST_EXIT=0** (leído; la foto previa E1+E2 fue 4817/0).

## Ship (pendiente de Alberto)
Railway worker: `ASR_AVISOS=on` + `F1_MARCA_CORRECCION=on` (rollback = quitarlas; off =
byte-idéntico probado por GC0). Verificación DEC-099 post-flip: repetir por VOZ la
conversación de la mañana («¿Qué centrales Kidde tienes?» dictado) y comprobar (1) si el ASR
vuelve a romper la marca, la confirmación 🎤 lleva el aviso 🏷/ℹ️; (2) «me refería a Kidde»
responde contenido Kidde con el sufijo «ℹ️ Respondo a tu pregunta anterior…»; (3) filas de
`query_logs` con `asunciones.status=on` e ítems.
