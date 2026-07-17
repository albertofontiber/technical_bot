# S151 upstream typed-relation target pilot

S149 and S150 show that repeatedly asking a query-time agent to rediscover
implicit relations from long chunks is incomplete. S151 moves that work
upstream: Haiku processes each served chunk without seeing any question and
emits source-bound atomic relations with immutable IDs, typed roles and exact
quotes. A separate Haiku query planner then classifies intent and selects claims
using generic answer-role policies for diagnostics, programming and recovery.

The pilot covers all 51 unique chunks already served to the four synthesis
questions. Extraction is batched and paid once; query selection is four bounded
calls. Exact-quote validation, offsets and IDs are deterministic. All 13 target
relations must be covered before an independent cohort or answer generation.
No database schema, ingestion pipeline, runtime bot or production state changes.
