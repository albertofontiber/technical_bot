"""src/flags.py — REGISTRO declarativo de la configuración por entorno (L2b, s311).

Qué ES: el censo ejecutable de las 86 flags que `src/` lee del entorno (100 call-sites:
getenv directo/indirecto + environ[.get] + `_strict_on_off` [ambas firmas] + `_mp_flag`), con default (como TEXTO fuente — el lector real
es quien lo resuelve), vía y lectores por flag. Generado del árbol y VERIFICADO contra
el árbol por `tests/test_s311_flags_registry.py`: un `getenv` nuevo sin registrar pone
la suite en rojo.

Qué NO es (alcance honesto, del blueprint §4-L2b tras su dúo):
  · NO migra lectores — los sellados siguen leyendo como leen (0 regen de sellos); la
    migración al accessor es oportunista, cuando otro lote toque su fichero.
  · La completitud es NOMINAL: garantiza que no hay call-site TEXTUAL sin registrar,
    no equivalencia semántica de parsing entre lectores no migrados.
  · El pin de `DEMO_FLAGS` detecta NOMBRES no registrados (pins fantasma), no valores.
  · Una DIVERGENCIA de defaults entre lectores se declara VISIBLE en su entrada, no se
    corrige a ciegas (hoy exactamente DOS, ambas con lados falsy y adjudicación
    pendiente no-urgente: `IDENTITY_RESOLVE_POLICY` ("" vs None) y
    `ANTHROPIC_API_KEY` ("" en config vs None en otro lector).

`snapshot()` sirve el estado ACTUAL sin secretos: las flags `sensible` reportan solo
presente/ausente. Es el insumo para comparar harness↔Railway sin exponer credenciales.
"""
from __future__ import annotations

import os

REGISTRO: dict[str, dict] = {
    "ANSWER_OBLIGATION_PLANNER": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/rag/answer_planner.py',),
    },
    "ANTHROPIC_API_KEY": {
        "default_fuente": '""',
        "via": ['environ.get', 'getenv'],
        "lectores": ('src/config.py', 'src/rag/must_preserve.py'),
        "sensible": True,
        "divergencia": ['""', 'None'],  # VISIBLE a propósito (L2b: el pin detecta, no corrige a ciegas)
    },
    "ANTI_DIAGRAM_INVENTION": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/rag/generator.py',),
    },
    "BOT_ERROR_LOGGING": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/bot/telegram_bot.py',),
    },
    "BOT_VERSION": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/version.py',),
    },
    "CANONICAL_HYQ_COVERAGE": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "CHUNKS_TABLE": {
        "default_fuente": '"chunks_v2"',
        "via": ['getenv'],
        "lectores": ('src/config.py', 'src/rag/catalog_resolver.py'),
    },
    "COMPATIBILITY_BUNDLE_COVERAGE": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "CONVERSATION_POLICY": {
        "default_fuente": '"stub"',
        "via": ['getenv'],
        "lectores": ('src/orchestrator/conversation_policy_impl.py',),
    },
    "CONVO_MAINTENANCE": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "COVERAGE_RELEASE_PROFILE": {
        # leída vía `env.get(PROFILE_ENV, LEGACY_PROFILE)` con el entorno pasado como
        # mapping — la indirección que el censo v3 no veía (el pin fantasma la destapó)
        "default_fuente": 'LEGACY_PROFILE',
        "via": ['mapping.get-indirecto'],
        "lectores": ('src/release_profiles.py',),
    },
    "CONVO_SHADOW": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "COVERAGE_MANDATORY_CALLOUT": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/rag/post_rerank_coverage.py',),
    },
    "DEDUP_REFERENCE_NAVIGATION": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "DOCUMENT_LOCAL_SELECTION_V2": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/rag/document_local_coverage.py', 'src/rag/post_rerank_coverage.py'),
    },
    "EMBED_CACHE_PATH": {
        "default_fuente": 'None',
        "via": ['getenv'],
        "lectores": ('src/ingestion/embedder.py',),
    },
    "EMBED_MODEL": {
        "default_fuente": '"voyage-4-large"',
        "via": ['getenv'],
        "lectores": ('src/reingest/embed.py',),
    },
    "EMBED_PROVIDER": {
        "default_fuente": '"voyage"',
        "via": ['getenv'],
        "lectores": ('src/reingest/embed.py',),
    },
    "ENUNCIADOS_MULTIVECTOR": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "ENUNCIADOS_QUOTA_FUSION": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "EVIDENCE_CONTRACT": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/rag/generator.py',),
    },
    "EVIDENCE_DERIVATION_OVERLAY": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "FACET_COMPLEMENT_FALLBACK": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/rag/post_rerank_coverage.py',),
    },
    "GENERATOR_DIRECT_FIRST": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/rag/generator.py',),
    },
    "GENERATOR_FOLLOWUPS": {
        "default_fuente": '"on"',
        "via": ['getenv'],
        "lectores": ('src/rag/generator.py',),
    },
    "GENERATOR_INCLUDE_CONTEXT": {
        "default_fuente": 'None',
        "via": ['getenv'],
        "lectores": ('src/rag/generator.py',),
    },
    "GENERATOR_PROMPT_VARIANT": {
        "default_fuente": '"base"',
        "via": ['getenv'],
        "lectores": ('src/rag/generator.py',),
    },
    "GENERATOR_SELECTION_BLOCK": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/rag/generator.py',),
    },
    "HYDE_ENABLED": {
        "default_fuente": '"false"',
        "via": ['getenv'],
        "lectores": ('src/rag/hyde.py',),
    },
    "HYDE_MODEL": {
        "default_fuente": '"claude-haiku-4-5"',
        "via": ['getenv'],
        "lectores": ('src/rag/hyde.py',),
    },
    "HYQ_PILOT_FILE": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "HYQ_PILOT_MIN_COS": {
        "default_fuente": '"0.45"',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "HYQ_PILOT_QUOTA": {
        "default_fuente": '"10"',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "HYQ_TABLE": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "IDENTITY_FETCH": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/rag/catalog_resolver.py',),
    },
    "IDENTITY_MAP": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "IDENTITY_RESOLVE": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/rag/catalog_resolver.py',),
    },
    "IDENTITY_RESOLVE_POLICY": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/config.py', 'src/rag/catalog_resolver.py'),
        "divergencia": ['""', 'None'],  # VISIBLE a propósito (L2b: el pin detecta, no corrige a ciegas)
    },
    "IMAGES_DIR": {
        "default_fuente": 'PROJECT_DIR / "extracted_images"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "LEVER1_KEYWORD_ORDER": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "LEVER2_IDENTITY": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "LEVER2_PM_RESCUE": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "LLM_MAX_TOKENS": {
        "default_fuente": '"2048"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "LLM_MODEL": {
        "default_fuente": '"claude-sonnet-4-6"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "LOGICAL_RECORD_COVERAGE": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "MANUALS_DIR": {
        "default_fuente": 'PROJECT_DIR / "Manuales_ES"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "MERGE_STRATEGY": {
        "default_fuente": '"stamps"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "MP_DEFLINE_EQ": {
        "default_fuente": '"off"',
        "via": ['mp_flag'],
        "lectores": ('src/rag/must_preserve.py',),
    },
    "MP_DISTINCTIVE_TOKEN": {
        "default_fuente": '"off"',
        "via": ['mp_flag'],
        "lectores": ('src/rag/must_preserve.py',),
    },
    "MP_HYBRID_DETECT": {
        "default_fuente": '"off"',
        "via": ['mp_flag'],
        "lectores": ('src/rag/must_preserve.py',),
    },
    "MP_MANDATORY_VERB_TRIGGER": {
        "default_fuente": '"off"',
        "via": ['mp_flag'],
        "lectores": ('src/rag/must_preserve.py',),
    },
    "MP_SERVED_BINDING": {
        "default_fuente": '"off"',
        "via": ['mp_flag'],
        "lectores": ('src/rag/must_preserve.py',),
    },
    "MP_STEM_BINDING": {
        "default_fuente": '"off"',
        "via": ['mp_flag'],
        "lectores": ('src/rag/must_preserve.py',),
    },
    "MUST_PRESERVE_CONTRACT": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py', 'src/rag/must_preserve.py'),
    },
    "NEIGHBOR_MODELS_ONLY": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "NEIGHBOR_WINDOW": {
        "default_fuente": '"0"',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "OBLIGATION_RESERVE_ORDERED": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/rag/rerank_pool_coverage.py', 'src/release_profiles.py'),
    },
    "OBLIGATION_WARNING_APPENDIX": {
        "default_fuente": '"off"',
        "via": ['mp_flag', 'strict_on_off'],
        "lectores": ('src/rag/must_preserve.py', 'src/release_profiles.py'),
    },
    "OPENAI_API_KEY": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
        "sensible": True,
    },
    "ORCHESTRATOR_PATH": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "PROSE_SOURCE_CARD": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/rag/document_local_coverage.py', 'src/rag/post_rerank_coverage.py'),
    },
    "R2_REPAIR_NAVIGATION": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "RAILWAY_GIT_COMMIT_SHA": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/version.py',),
    },
    "RERANKER_BACKEND": {
        "default_fuente": '"llm"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "RERANK_POOL_COVERAGE": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "RERANK_PREVIEW_CHARS": {
        "default_fuente": '"800"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "RERANK_TOP_K": {
        "default_fuente": '"5"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "REWRITER_MODEL": {
        "default_fuente": '"claude-sonnet-4-6"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "SERIES_REGISTRY_ENABLED": {
        "default_fuente": '"true"',
        "via": ['getenv'],
        "lectores": ('src/rag/series_registry.py',),
    },
    "SOURCE_LEGEND": {
        "default_fuente": '"off"',
        "via": ['getenv', 'strict_on_off'],
        "lectores": ('src/rag/generator.py', 'src/rag/source_legend.py'),
    },
    "STRUCK_OCR_CONTEXT": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/rag/generator.py',),
    },
    "STRUCTURAL_CASCADE_COVERAGE": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "STRUCTURAL_NEIGHBOR_SHADOW": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
        "sensible": True,
    },
    "STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY_VERSION": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
        "sensible": True,
    },
    "SUPABASE_KEY": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
        "sensible": True,
    },
    "SUPABASE_SERVICE_KEY": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
        "sensible": True,
    },
    "SUPABASE_URL": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
        "sensible": True,
    },
    "TABLE_PREAMBLE_CLOSURE": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "TELEGRAM_BOT_TOKEN": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
        "sensible": True,
    },
    "TELEGRAM_FEEDBACK": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/bot/telegram_bot.py',),
    },
    "TELEGRAM_FEEDBACK_REASON": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/bot/telegram_bot.py',),
    },
    "VISUAL_ASSETS_LISTING_GATE": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/rag/generator.py',),
    },
    "VISUAL_ASSETS_REGISTRY": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "VOICE_TRANSCRIPTION_MODEL": {
        "default_fuente": '"whisper-1"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "VOYAGE_API_KEY": {
        "default_fuente": 'None',
        "via": ['getenv'],
        "lectores": ('src/rag/reranker.py', 'src/reingest/embed.py'),
        "sensible": True,
    },
    "WIRING_TOPOLOGY_GUARD": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/rag/generator.py',),
    },
}


def snapshot() -> dict[str, str]:
    """Estado actual del entorno según el registro, SIN secretos."""
    salida: dict[str, str] = {}
    for nombre, spec in REGISTRO.items():
        crudo = os.getenv(nombre)
        if spec.get("sensible"):
            salida[nombre] = "(presente)" if crudo is not None else "(ausente)"
        elif crudo is None:
            salida[nombre] = "(default: " + spec["default_fuente"] + ")"
        else:
            salida[nombre] = crudo
    return salida
