# Non-production and gated SQL proposals

Files in this directory are deliberately excluded from `supabase db push`.
They preserve reviewed SQL contracts that are not part of the production
migration history.

- `20260714102428_chunks_v3_provenance_shadow.sql` and
  `20260716120000_chunks_v3_shadow_binding_v2.sql` are disposable-environment
  contracts. Their recorded release status is `NO_GO_FOR_DB`/`HOLD`; neither
  has ever been materialized in production.
- `20260720095702_add_query_logs_rag_trace.sql` is a gated C1 deployment
  proposal. It has not been applied. After a fresh P1 PASS, it must be reviewed
  again and copied to `supabase/migrations` under a fresh timestamp before a
  normal dry-run and production apply.

Do not mark any of these historical versions as applied with
`migration repair`.
