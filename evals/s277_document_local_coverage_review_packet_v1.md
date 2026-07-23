# S277 document-local coverage — adversarial review packet v1

## Objective and decision metric

Decide whether the default-off mechanism is safe enough to commit as an
**unreleased candidate** and advance to a separately preregistered release
profile/evaluation. It is not a production GO and it cannot change the current
146/154 fact KPI.

The mechanism passes this stage only if it:

1. recovers the missing authoritative HP011 source record from the sealed S113
   prefix without a target/QID/page rule;
2. preserves every protected prefix byte-for-byte and appends at most one row
   from this lane;
3. uses only bounded GETs inside an exact active document/extraction scope;
4. fails closed on ambiguous lifecycle, duplicate, cross-blob, overflow,
   timeout and receipt tamper;
5. serves the complete exact logical record rather than a clipped selector
   window; and
6. leaves `coverage_c1_v1` import-isolated and rejects the new flag under that
   historical profile.

## Implemented architecture

`validated structural neighbour → reciprocal lifecycle resolution → active
document + exact extraction binding → bounded document-local FTS → existing
retrieval-pool semantic selector → one exact-source append`.

- `DOCUMENT_LOCAL_COVERAGE` is strict `on|off`, defaults off and is outside C1.
- The lane starts only from a structural row that actually survives the append
  seam. It does not search globally or infer a revision by date/name.
- Each structural source scope is adjudicated independently. An incomplete
  legacy scope is rejected and never queried; it cannot suppress a separate
  fully governed scope.
- FTS is constrained by `document_id`, `extraction_sha256`, `source_file` and
  `duplicate_of IS NULL`, with a 64+1 sentinel, a shared two-second deadline,
  no retries and at most three lane GETs.
- Query terms come from the versioned generic facet planner. The existing
  selector ranks the bounded candidates; the lane does not know the target ID.
- The normal serving view uses the already revalidated bounded logical-record
  receipt for this lane, even while the independent legacy logical-row flag is
  off.
- The implementation is imported lazily only when its flag is active, so the
  sealed C1 v1 static and loaded dependency closure remains unchanged.

## Evidence available

- `evals/s277_document_local_coverage_probe_v1.json`: `GO_MECHANISM` over all
  13 preregistered P1 QIDs, 85 GETs, zero model calls, zero database writes.
- HP011: selected v.07 p63, one document-local append, exact 1,107-character
  served record containing the reset-inhibition record, `t.A`, `00` and
  `01–30`; target ID absent from every request.
- In the 12 controls the new lane appended nothing. HP017 overflowed its bounded
  candidate cap and failed closed.
- Negative controls reject two active revisions, broken reciprocal pointers,
  SHA mismatch, duplicate, cross-blob candidate, tampered receipt and cap+1.
- Focused implementation tests: 78 passed. The sealed C1 runner/contract suite:
  170 passed after import isolation.

## Deliberate limitations / non-claims

- The probe replays sealed reranker prefixes; it does not rerun live retrieval,
  reranking, generation or fact judging.
- Only sources with complete governed lifecycle metadata are eligible. A chain
  not completely visible in the bounded lifecycle read is rejected.
- The 13-QID observation is a control cohort, not proof of organic
  generalisation or zero regression.
- No new release profile, deployment, Railway mutation or P1 execution is part
  of this change. A future release must use a new versioned profile rather than
  silently changing `coverage_c1_v1`.

## Review focus

Look specifically for authority bypass, unsafe partial-lineage acceptance,
cross-document leakage, FTS vocabulary/ES–EN problems, false semantic receipts,
served-view clipping, hidden writes/model calls, target leakage, C1 closure
contamination, and over-engineering relative to the measured HP011 miss.
