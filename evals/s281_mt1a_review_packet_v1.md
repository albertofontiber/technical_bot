# s281 MT-1a — packet de revisión adversarial FOCAL (zona gates S99)

**Qué se revisa:** la lane MT-1a de la Fase 1 multi-turn — el clasificador conversacional
determinista + rewriter gateado, último commit de la rama `claude/s281-mt0`. Es la zona que
hundió el S99 v2 (rewrites que corrompían códigos técnicos; carry-forward heurístico tumbado
2× por el dúo). El dúo focal es OBLIGATORIO por diseño antes de cerrar la lane.

## Archivos del diff
- `src/orchestrator/conversation_policy_impl.py` — DeterministicConversationPolicy: cascada
  A-I (docstring), FAMILY_REGISTRY/BRAND_TOKENS seeds, composición resolve_conversational_turn
  + advance_working_state, flag runtime CONVERSATION_POLICY.
- `src/orchestrator/rewriter.py` — prompts fontiber/condense-LC, make_rewriter, validate_rewrite
  (post-validación determinista fail-closed).
- `src/orchestrator/conversation_policy.py` — SOLO default_policy() cambiado (flag-gated).
- `tests/test_conversation_policy_impl.py` — 26 tests.
- Su vara (NO tocada por la lane, verificado): `evals/multiturn_golds_v1.yaml` +
  `scripts/test_multiturn_vs_gold.py` + `tests/test_multiturn_golds_contract.py`.

## Claims a tumbar
1. La cascada honra los invariantes duros del contrato (conversation_policy.py docstring):
   $0-guarantee, carry byte-verbatim con hint APENDIZADO, producto-explícito-gana, corrección
   REEMPLAZA, NON_PRODUCT_CODES no disparan cambio de producto.
2. Clarify SOLO con divergencia real (s79/s80): eje divergente + guarda negativa de invariantes;
   cero clarify-indebido en producción real (no solo en los 31 turnos del gold).
3. La post-validación del rewriter es fail-closed de verdad (ningún rewrite corrupto puede
   llegar a retrieval; el fallback carry_forward es seguro).
4. El flag-gating (default stub) no debilita la vara ni rompe ningún consumidor.
5. Las regexes españolas (_DEPENDENCY_RE, _CONTENT_ANAPHOR_RE, brand tokens) funcionan sobre
   ESPAÑOL REAL de técnicos — piensa en preguntas cotidianas fuera de los 31 golds.
6. advance_working_state es correcto (CLARIFY/DECLINE no fijan modelo; el excerpt se
   backfillea post-generación).

## Contexto canónico
`evals/s280_multiturn_design_v2.md` §1.5 · `evals/s281_mt1b_vara_preregistro.md` ·
`evals/multiturn_golds_v1.yaml` · memoria del S99 (el rewrite v2 se hundió por códigos
mutados + carry heurístico) · s79/s80 clarify-solo-si-diverge.

## Qué pedimos
Ataca las 6 claims con ancla fichero:línea y escenario CONCRETO (una pregunta española real
que rompa la cascada vale más que diez abstracciones). Severidad por hallazgo + veredicto
global (SÓLIDO | SÓLIDO-CON-CAMBIOS | RECHAZAR).
