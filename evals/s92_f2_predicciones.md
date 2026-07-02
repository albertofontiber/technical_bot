# S2 · Tabla de predicciones PRE-REGISTRADA (v2.1c) — escrita ANTES de correr la famtie

> Disciplina s69/C3 (predicción-vs-resultado). Baseline control REPRODUCIDO hoy sobre
> `s85_retrieval_miss_DEF.yaml`: **retrieval-miss FAMILY = 14/132**. Los brazos regeneran SOLO
> `pool_pin` (retrieve_chunks top_k=50 con `IDENTITY_RESOLVE=on`) reutilizando los labels GPT ya
> pagados; `top5_ids` NO se recomputa (sin re-pagar reranker) → los buckets RERANK/TOP5 de los
> brazos no son comparables, la métrica es SOLO `retrieval_miss_family` (in_pool) + per-gold.
> Limitación declarada: un chunk NUEVO que soporte un hecho pero nunca juzgado no cuenta
> (conservador — el delta medido es cota INFERIOR del efecto real).

| hecho (baseline RETRIEVAL) | predicción brazo ADD | brazo REPLACE | mecanismo esperado |
|---|---|---|---|
| hp018 × 5 ('4 circuitos','6K8','diodo','Sirenas A,B,C,D','1 A') | **GANAN in_pool (5/5)** | GANAN (5/5) | 'zxe'→[ZX1e,ZX2e,ZX5e] (seam 1) mete MIE-MI-530 (pm='ZX2e/ZX5e') al pool; seam 2 los protege del veto |
| hp011 '05 a 295 seg' | **GANA in_pool** | GANA | 'rp1r'→prefer RP1r-Supra (seam 1) — el soporte same-family existe fuera del pool (regalo no contado en la palanca ~4) |
| cat016 'autobusqueda' | posible (media) | posible | 'cad-150'→variantes; el sup es pm='CAD-150-8' — depende de que keyword/vector lo traiga |
| cat013 'CLIP' · hp006 ×3 · hp012 · hp013 'PWR-R' · hp014 '35' | SIN cambio | SIN cambio | sin mecanismo nuevo (exact ya presente o familia no cubierta) — el lever NO es esto |
| **hp009 (todos sus hechos)** | **SIN regresión** | ⚠ riesgo (LEVER2-replace lo regresó) | add conserva el token 'ZXE' → docs family-level siguen matcheando |
| resto de golds | sin movimiento neto; retrieval-miss total **14 → ~8±1 (add)** | 14 → ~8±1 salvo regresión hp009 | — |

**Criterio de decisión pre-registrado:** gana el brazo con hp018 5/5 ganados Y hp009 sin
regresión Y total ≤ baseline. Si ambos cumplen → ADD (menos invasivo). Si replace regresa
hp009 (como LEVER2) → ADD queda confirmado como el fix de la regresión histórica. Si NINGUNO
mueve hp018 → diagnóstico per-gold (¿el doc ni entra al pool → escalera v2.1d fetch-acotado?).
Config estampada: catálogo-commit + flag + policy en el YAML de cada brazo.

---

## RESULTADO (mismo día, predicción-vs-resultado — regla del pre-registro)

| pin | retrieval-miss FAMILY |
|---|---|
| baseline DEF (pin viejo, s85) | 14 |
| **OFF-control (re-retrieve hoy, flag off)** | **15** — el drift/jitter de re-retrieval existe (±1-2): hp001 '2222' cae TAMBIÉN sin flag (jitter puro, el caso documentado); hp018 sigue 5/5 miss ✓ |
| **ON + ADD** | **12** — **hp018 gana 4/5** ('4 circuitos','6K8','diodo','Sirenas A,B,C,D' entran al pool; '1 A' queda) · hp009 **SIN regresión** · hp012 '99+99' cae (desplazamiento por la unión en algún cap downstream — la forma DEC-069 en pequeño, net sigue positivo) |
| **ON + REPLACE** | **14** — hp018 gana 4/5 igual, **PERO hp009 REGRESA ×2** ('Retorno','aisladores internos': quitar el token ZXE veta los docs ZXAE/ZXEE que hp009 necesita) — **la regresión histórica de LEVER2, reproducida CON mecanismo visible** |

**Contra las predicciones:** hp018 5/5 → REAL 4/5 (parcial); hp009-sin-regresión-en-ADD ✓ CONFIRMADA;
riesgo-replace-regresa-hp009 ✓ CONFIRMADA (el porqué del brazo add queda demostrado, no intuido);
hp011-gana → **FALSADA** (sigue miss en ambos brazos — la expansión prefer-Supra no basta para
meter su chunk-soporte en el pool-50; pendiente diagnóstico); total ~8±1 → REAL 12 vs control 15
(dirección ✓, magnitud menor).

**ERRATA (cazada por el cross-model s93, bias de framing #51-clase): el criterio LOCAL de esta
tabla (hp018 5/5) NO se cumplió — se cumplió el criterio del CONTRATO (hp018 4/4, DEC-074b), que
es el gate oficial de F2. Mi texto original los fundió presentando 4/5 como cumplimiento del
pre-registro local; ambos criterios y ambos resultados quedan ahora visibles.** Con esa
corrección: ADD gana el brazo (contrato cumplido, hp009 intacto, −3 neto vs control); pendientes
hp018 '1 A' + hp011 + hp012 '99+99'.

---

## S3-FETCH · Predicciones PRE-REGISTRADAS del brazo fetch-acotado (ANTES de medir)

Config: IDENTITY_RESOLVE=on + POLICY=add + IDENTITY_FETCH=on. Baseline de comparación:
ON+add = 12 · OFF-control = 15.

| hecho (miss en ON+add) | predicción | mecanismo |
|---|---|---|
| hp011 '05 a 295 seg' | **GANA** | HLSI-MN-103 (ALLOW, ausente del pool) → fetch trae sus chunks; el soporte está ahí |
| hp006 ×3 | **GANAN** (alta) | 50253SP/MIDT170 ALLOW ausentes → fetch |
| hp013 'PWR-R' · hp014 '35' · cat016 | GANAN (media) | docs ALLOW ausentes; depende de que el score léxico elija el chunk-soporte entre ≤3 |
| hp001 '2222' · hp012 ×2 | GANAN (media) | ALLOW ausentes; '99+99' además recupera el −1 del desplazamiento |
| hp018 '1 A' | GANA (media) | MIE-MI-530rv001 ALLOW ausente |
| cat013 'CLIP' | GANA (media) | MIDT190 ahora en doc_map (fix s93) vía SDX-751 secondary — exige que 'sdx-751' se detecte y el léxico encuentre el chunk CLIP |
| **total** | **12 → 2-5** | si >8 → el score léxico es el cuello (diagnóstico per-doc) |

**Correcciones del dúo s93 ANTES de medir:**
- **Todas las filas "GANA" son HIPÓTESIS CONDICIONADAS** a que el score léxico elija, entre ≤3
  de hasta 300, exactamente los chunk-ids YA JUZGADOS (la famtie no re-juzga: un chunk nuevo
  del doc correcto sin votos sigue midiendo MISS — cota inferior, igual que en S2).
- **El gate de SHIP no es la famtie sola**: el contrato del workstream exige cero-regresión
  PASS (±2, freeze per-eval) en cada fase → encender IDENTITY_FETCH en demo requiere famtie OK
  **+ bvg PASS-control ±2** (cuesta juez GPT — decisión de Alberto cuándo). "≤5 → ship-candidate"
  queda RETIRADO como criterio.
- **Por qué esto NO re-litiga DEC-069** (delimitación explícita): el aditivo muerto era unión
  CIEGA del índice dentro del pool capado (desplazaba soporte). Este fetch: (a) fuente =
  SOLO docs adjudicados por humano vía doc_map (whitelist), (b) APPEND tras el corte [:top_k]
  — extensión acotada ≤12, desplaza a NADIE (el bug de truncado que lo convertía en no-op
  silencioso fue cazado por el dúo y movido tras el corte), (c) entra como BRAZO MEDIDO nuevo,
  la autorización explícita de la fila del LEVER_DIGEST.

### RESULTADO S3-FETCH (predicción-vs-resultado)
**retrieval-miss = 12 — IDÉNTICO a ON+add sin fetch. Predicción (2-5) FALSADA.**
El mecanismo FUNCIONA (pools >50 prueban los appends: hp018=57) pero el selector léxico NO
encuentra los chunk-ids juzgados entre cientos por doc — exactamente el criterio pre-escrito
">8 → el score léxico es el cuello". Lectura estructural: los 12 residuales son la clase
FINE-GRAINED de s86 (aguja-en-chunk-grande: el soporte vive en tablas/celdas que ni el vector
ni el léxico superficial puntúan) → pertenecen al workstream foundational de ingesta
(multi-granularidad + extracción-tablas + BM25), YA mapeado como futuro. **Veredicto del brazo:
NO-SHIP (sin beneficio medido, +latencia); el código queda tras flag default-off con este
veredicto. El lever identidad-en-retrieval queda EXHAUSTO con −3 neto (la expansión ADD).**
