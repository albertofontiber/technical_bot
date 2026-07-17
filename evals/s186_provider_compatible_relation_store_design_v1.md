# S186 — provider-compatible execution of the frozen S171 relation-store gate

S171 did not execute a model call: Anthropic's structured-output preflight
rejected `maxItems` in the provider JSON schema. S186 changes only that
transport representation. The prompt still declares at most 30 relations and
the application still rejects zero, more than 30, duplicate, overlong,
over-assigned or provenance-invalid relations before sealing the store.

The source packet, S147 development cohort, relation ontology, Haiku model,
one-call-per-chunk isolation, selector, semantic thresholds, output budgets and
no-retry policy are unchanged. The cohort therefore remains unexposed to this
mechanism. S186 is the first semantic measurement of the frozen S171 design,
not a prompt-tuning iteration.

If construction or semantic gates fail, the relation-store line stops. If they
pass, only a fresh document-independent promotion/fidelity audit is allowed;
targets, production and KPI credit remain forbidden.
