# S150 one-pass coverage verifier probe

S149 proves that a minimum single-pass selector under-covers broad diagnostic and
procedural questions. S150 reuses those four frozen selections and adds exactly
one bounded coverage-verification pass. The verifier compares selected IDs with
all already-served immutable evidence units and may add at most six new IDs. It
does not retrieve, answer, use gold, or iterate. Sonnet 4.6 is used only for this
planning/verification step; no frontier judge is needed. All 13 local relations
must be covered before a fresh broad independent cohort is allowed.
