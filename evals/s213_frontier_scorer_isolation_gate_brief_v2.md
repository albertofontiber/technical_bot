# S213 compact scorer-isolation correction gate

Decision: does the S213 scorer adapter preserve the v1 dual-PASS execution design while restoring
historical S210-S212 artifact immutability, without introducing a path to false GO?

The v1 S213 design gate received PASS from GPT-5.6 Sol xhigh and Fable 5 with zero blockers. Before
PR, the full test suite exposed one implementation-isolation defect: S213 had parameterized the
hard-coded `calls == 202` check inside the historical S210 scorer. Although scoring semantics were
unchanged, that modified a byte-frozen file and correctly broke six S210-S212 seal tests. No S213
paid execution occurred.

The correction restores `scripts/s210_score_query_evidence_compiler.py` byte-for-byte to portable
SHA-256 `b9a524a35223491b14f4d76afdd0848121a53a48876e6e6d0f56b693b0a2767c`, the exact hash frozen by
S210, S211 and S212. Their 26 relevant contract tests now pass.

S213 uses a local adapter instead. Before scoring it:

1. loads the original S213 receipt and recomputes its canonical seal;
2. requires `status == COMPLETE` and `calls == 260`;
3. creates an ephemeral proxy with exactly one semantic-field delta, `calls: 260 -> 202`, and
   recomputes the proxy seal;
4. points the unchanged S210 scorer at that proxy, so every answer row, selected-evidence receipt,
   source overlap, baseline prefix, contradiction, guardrail, precision, length, cost and two-replica
   check runs unchanged;
5. replaces the proxy receipt hash in the published score with the portable SHA-256 of the untouched
   original 260-call S213 receipt and records the one-field compatibility delta in lineage.

The adapter never changes, drops or synthesizes an answer, receipt, selection, cost, preflight row,
replica, or gate. A contract test constructs a sealed 260-call artifact and proves the proxy equals
the original body with only `calls: 202` plus its necessarily recomputed seal; it also proves the
original remains 260. Invalid seals or incomplete/wrong-call matrices fail before the historical
scorer runs.

All other reviewed S213 mechanisms, models, prompts, population, 260-call geometry, budget, gates,
no-retry rule, default-off status and chunks/Railway invariants are unchanged. The refreshed
zero-call preflight remains GO with 12/12 deterministic source coverage and portable SHA-256:
`7776d5a42a31a12e735b9d0b151b2a19c3e1bd9a10565ab7365c088fd05332d1`.

PASS only if this isolated compatibility adapter cannot falsely produce GO and historical scorer
immutability is restored. FAIL only for a concrete remaining blocker. Do not reopen the already
dual-PASS S213 mechanism, request another cohort, or require another review round.
