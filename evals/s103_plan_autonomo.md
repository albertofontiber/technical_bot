# s103 — Plan de acción (arranque en sesión limpia) · sucede a s102_plan_autonomo.md

**Mandato vivo (Alberto):** OK>95% bajando buckets, upstream-first; GO de un mecanismo =
reducción del bucket (no OK/PASS); BP+estructural+escalable-30+; **flag de overfitting**
explícito si una iteración apunta a golds ya medidos; decisiones inequívocas = tomar y
comunicar; ambiguas → `evals/s101_decisiones_alberto.md` con recomendación; nunca auto-ship.

## Estado de arranque (post-s102, 9 jul — todo committeado y verificado)
- **Demo completa shippeada**: fidelity (DEC-098) + canal hyq (DEC-099, tabla 70.134 preguntas,
  mecánica v2, `HYQ_TABLE=on`, flip cat016 verificado en query_logs prod d355867).
- **Scoreboard v2.2** (dev-39, 126 hechos): OK 91 (72%) · synth 8 · retrieval 12 · rerank 13 ·
  corpus-real 0. Matriz de transición vs v3: +12/−10 (fila 2026-07-09 de FACTLEVEL_ASSESSMENT).
- Factura del canal TRAZADA: cat022×3 + hp018×3 desplazados — mecanismo verificado con probe
  (el presupuesto REDUCIDO del diversify por el carve-out aprieta a TODOS los canales, incl.
  keyword sim-0.85; la fusión de vector_search ya paga la cuota con su propia cola = hay un
  **doble descuento** y el segundo cae donde no debe).

## Cola de ejecución (en orden)

### 1. Lever «displacement-landing» — que la cuota hyq desplace la cola del canal VECTOR, no keyword
- **Diagnóstico ya hecho (no re-derivar):** el doble descuento. Descuento 1 (correcto, medido
  en piloto): `results[:top_k-quota]+quota` dentro de vector_search — la cuota compra la cola
  del PROPIO canal vectorial. Descuento 2 (el bug conceptual): el carve-out reduce el top_k del
  diversify → el interleave per-source recorta colas de TODOS los canales → salen chunks
  keyword-0.85 load-bearing (cat022: MNDT723 p58/p10, MNDT722 p14; hp018: MIE-MI-530 p21).
- **Diseño candidato (validar con dúo ANTES de cablear):** diversify corre a top_k COMPLETO
  (sin reducción); el sitio para el aside se hace quitando específicamente los peores chunks
  de `_channel=='VECTOR'` sin stamps (menor sim) del merged post-diversify — el mismo trade
  del descuento 1, aplicado consistentemente. Si no hay suficientes VECTOR → cola global
  (fallback declarado).
- **Gate (métrica declarada):** los 6 hechos perdidos recuperan `in_pool` SIN perder los 12
  ganados (comparar per-fact vs `s100_factlevel_full.yaml`) + negcontrol re-run (esperado:
  EXCESS-HIGH baja) + famtie amplio como control anti-overfit. bvg solo si el gate pasa.
- **⚠ ANTI-OVERFIT FLAG (obligatorio declararlo a Alberto en el resultado):** esta iteración
  apunta a los MISMOS golds dev que ya midieron el canal — el contrapeso es el control amplio
  (negcontrol 39 + famtie), no solo los 6 hechos diana.
- Coste: probes judge-free + full parcial de ~6 golds ≈ barato. Piezas: retrieve_chunks Step 5
  (retriever.py ~1590-1615), tests en `tests/test_hyq_channel.py` (actualizar carve-out).

### 2. Synth residual (8) — mapear ANTES de proponer lever
- Leer los 8 del yaml (per_gold → clase=synthesis-miss): ¿cuántos post-transición son estables
  vs ruido de rerank (DEC-096b)? ¿queda algo del patrón cat021-variantes en otras familias
  (la regla s79/s80 enumerar-si-diverge)? El fork de cat021 (DEC-097) solo se reabre si el
  cluster re-aparece. Tarea tracker #6 sigue in_progress para esto.

### 3. Estructural grande — entity-linking / identidad (DEC-074)
- El lever de 4-7 sesiones: F1 (índice inverso producto→docs) está CONSTRUIDO y sin consumir
  (s83/s84, branch-local). cat013 y la clase identidad no se mueven con retrieval genérico.
  Arrancar por: releer DEC-074 + s83_identity_asset (memoria) + decidir el primer consumo
  medible (candidato: resolver de sinónimos/series en el family-filter de hyq — TECH_DEBT
  #52.1 series-window — mata dos pájaros).

### 4. Menores / gateados
- Enunciados R2 corpus-wide ($160-270): decisión de presupuesto de Alberto, gateada a que el
  scoreboard lo pida.
- TECH_DEBT #52.2 (family-pattern server-side en `match_hyq`, migración futura): al gatillo de
  duplicar corpus o perder flips con fabricante nuevo.
- Flake orden-dependiente `test_enunciados_multivector:212` (pre-existente, benigno).

## Reglas de ORQUESTACIÓN (Alberto s102 — `feedback_model_tiering`; aplicar DESDE EL ARRANQUE)
| Trabajo | Quién | Cómo |
|---|---|---|
| Diseño, diagnóstico causa-raíz, decisiones de medición, síntesis final, lectura de veredictos | **Fable 5 (main loop)** | no delegar |
| Dúo Protocolo 3 | **sub-agente pin `fable` (INTOCABLE, decisión Alberto s88) + cross-model GPT-5.5** | agente FRESCO por ronda |
| Verificación-por-lectura (DEC-092b), spot-checks regla-C, matrices de transición, QA muestral | **sub-agente `model: opus`** | Agent tool con model override; prompt autocontenido, salida CORTA |
| Exploración amplia de repo / búsquedas | **Explore agent (`model: opus` o menor)** | conclusión, no dumps |
| Fan-outs paralelos (verificar N regresiones, sweep de N golds) | **Workflow** con `opts.model='opus'`/`effort` bajo en etapas mecánicas; verify/judge en tier alto | ultracode activo |
| Runs pesados (fulls, gates, loaders) | **scripts en background (0 LLM)** | siempre primera opción |
- Principio: delegar paquetes AUTOCONTENIDOS con salida corta (el gasto dominante es el
  contexto del main loop); nunca degradar el tier de revisión/diseño para ahorrar.
- **⚠ CUIDADO (Alberto s102): mismo-árbol ≠ independencia.** Opus 4.8 y Fable 5 son el MISMO
  árbol Claude que el líder: un sub-agente Claude (cualquier tier) ahorra tokens pero NO compra
  independencia — comparte los blind spots conceptuales del autor (feedback_my_bias; la razón
  de ser del cross-model). Regla: el tiering aplica a EJECUCIÓN; toda verificación cuyo valor
  ES la independencia (anti-bias, challenge a claims conceptuales/framing del autor, review
  adversarial en ALTO/zona-de-dolor) exige **GPT-5.5 además del sub-agente Claude** — como el
  dúo. Caso especial que SÍ funciona mismo-árbol: verificar el veredicto de un juez GPT
  leyendo respuestas (patrón DEC-092b/hp020) es cross-model EN ESA DIRECCIÓN (Claude revisa a
  GPT — modos de fallo distintos).

## Cómo retomar
1. Leer este fichero + `docs/PLAN_RAG_2026.md` (Estado actual s102) + `git log --oneline -10`.
2. La fila v2.2 del scoreboard + su yaml (`evals/s100_factlevel_full.yaml`) son la base de
   TODO: cualquier claim sobre buckets se verifica ahí (per_gold → facts → clase).
3. Los probes de desplazamiento son reproducibles: patrón OFF-vs-ON con `R.HYQ_TABLE_ON`
   (ver `scripts/s102_hyq_negcontrol_table.py:_pool`).
4. Digest de levers inyectado al arranque: la fila hyq dice SHIPPEADO — no re-litigar el canal;
   el lever nuevo es el LANDING del desplazamiento (§1), que es OTRO mecanismo.
