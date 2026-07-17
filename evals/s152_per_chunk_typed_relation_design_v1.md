# S152 per-chunk typed-relation pilot

S151 showed that multi-chunk structured extraction can silently omit a chunk.
S152 preserves the source-first typed-relation architecture but isolates every
chunk in one Haiku call and checkpoints the provider receipt before validation.
Thus a malformed call is attributable and cannot contaminate any other chunk.

This topology is intended for an offline/asynchronous ingestion job, where work
is paid once per immutable chunk and can later use a discounted provider batch
API. The query path remains four cheap claim-ID selections. The 51 source chunks
and 13-relation local oracle are development data only; passing still requires a
fresh independent cohort before answer generation or integration.
