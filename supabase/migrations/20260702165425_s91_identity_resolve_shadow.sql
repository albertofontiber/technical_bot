-- s91 F2-S1 (plan v2.2 + hallazgo dúo build: el shadow necesita artefacto AUDITABLE,
-- no degradación silenciosa a log local — Railway FS es efímero)
CREATE TABLE IF NOT EXISTS identity_resolve_shadow (
    id bigserial PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    query text,
    mode text,
    policy text,
    detected jsonb,
    records text,
    models_before jsonb,
    models_after jsonb,
    allowed_sources_n integer,
    catalog_commit text
);
CREATE INDEX IF NOT EXISTS idx_identity_shadow_created ON identity_resolve_shadow (created_at DESC);
ALTER TABLE identity_resolve_shadow ENABLE ROW LEVEL SECURITY;
-- sin policies: solo la service key (el bot) escribe/lee, igual que query_logs
