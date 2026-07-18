import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Base paths
PROJECT_DIR = Path(__file__).parent.parent

# Process/deployment/launcher environment is authoritative; .env fills only missing values.
# This is required for the isolated evaluation launcher to target a sealed branch without
# editing or replacing the production .env file.
load_dotenv(PROJECT_DIR / ".env", override=False)
MANUALS_DIR = Path(os.getenv("MANUALS_DIR", PROJECT_DIR / "Manuales_ES"))
IMAGES_DIR = Path(os.getenv("IMAGES_DIR", PROJECT_DIR / "extracted_images"))

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Voice transcription stays on the measured historical provider by default.
# The two current OpenAI candidates are exposed only as explicit, reversible
# experiment arms; selecting one does not by itself constitute a quality GO.
_VOICE_TRANSCRIPTION_MODELS = {
    "whisper-1",
    "gpt-4o-mini-transcribe-2025-12-15",
    "gpt-4o-transcribe",
}
VOICE_TRANSCRIPTION_MODEL = os.getenv(
    "VOICE_TRANSCRIPTION_MODEL", "whisper-1"
).strip()
if VOICE_TRANSCRIPTION_MODEL not in _VOICE_TRANSCRIPTION_MODELS:
    raise RuntimeError(
        "VOICE_TRANSCRIPTION_MODEL must be one of: "
        + ", ".join(sorted(_VOICE_TRANSCRIPTION_MODELS))
    )

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Tabla de chunks activa (sesión 27). Permite probar/SWAP a chunks_v2 sin tocar
# código ni hacer RENAME destructivo: basta cambiar CHUNKS_TABLE en el entorno.
#   chunks    → corpus viejo (OpenAI text-embedding-3-small, 1536 dims)
#   chunks_v2 → corpus re-ingestado (Voyage voyage-4-large, 1024 dims)
# El sufijo de RPC y el proveedor de embedding de la query se derivan de aquí.
CHUNKS_TABLE = os.getenv("CHUNKS_TABLE", "chunks_v2").strip()
if CHUNKS_TABLE != "chunks_v2":
    raise RuntimeError(
        "production retrieval requires CHUNKS_TABLE=chunks_v2; "
        "use dedicated offline diagnostics for legacy corpora"
    )
CHUNKS_IS_V2 = True
RPC_SUFFIX = "_v2"

# Embedding config
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# RAG config
# s44 (DEC-018): retrieve WIDE (15→50), generate narrow — TECH_DEBT #16. El reranker
# (por contenido, reranker.py) elige top-5 de un pool ancho; evita el burial del CORTE
# merged[:15], que enterraba chunks de coseno real bajo keyword-stamps planos (0.80-0.85).
# Medido A/B K=3 HyDE-off (test_bot_vs_gold): FALLO ~6→1 estable (3 réplicas idénticas),
# 7 mejoras / 1 regresión (hp013, completitud). RERANK_TOP_K (generador) se queda en 5.
RETRIEVAL_TOP_K = 50
# s98/s99: ancho de la ventana SERVIDA al generador (rerank top-N). Default 5 = prod histórico
# (DEC-018 "generate narrow"). SWAP reversible por entorno (patrón CHUNKS_TABLE/RERANKER_BACKEND).
# s99: gate de NO-REGRESIÓN PASADO (K=5 juez K-mayoría; las 3 "regresiones" verificadas = artefactos
# del juez, el bot sirve MÁS info correcta con fuente, 0 invención) + GO de Alberto → SHIPPEABLE.
# En Railway se pone RERANK_TOP_K=10 (con LLM_MAX_TOKENS=3500, ver abajo). DEC-092. Rollback = quitar.
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "5"))
CHUNK_MAX_TOKENS = 1500
CHUNK_OVERLAP_TOKENS = 200

# s74 Lever 1 / sub-fix 2c (DEC-052): cuántos chars de cada chunk VE el reranker LLM
# (`reranker.py`, `chunk.get("content")[:RERANK_PREVIEW_CHARS]`). El hecho decisivo a veces
# cae más allá del char 800 (offset fuera de ventana) → el reranker no puede juzgar relevancia
# y no sube el chunk al top-5 (hp003). SWAP reversible por entorno, mismo patrón que
# CHUNKS_TABLE/RERANKER_BACKEND/MERGE_STRATEGY:
#   800 (default)  → comportamiento histórico EXACTO (prod inerte; paridad de prompt).
#   2400 / 4000    → ventana ancha; el valor se ELIGE por dato en el gate-0 modal (no tuneado).
# Solo afecta el path LLM-rerank; el cross-encoder Voyage ya lee VOYAGE_RERANK_DOC_CHARS=4000.
RERANK_PREVIEW_CHARS = int(os.getenv("RERANK_PREVIEW_CHARS", "800"))

# Backend del reranker (s61, diseño _s61_lever_design.md §4). SWAP reversible por
# entorno, como CHUNKS_TABLE:
#   llm    → rerank_chunks (Claude Sonnet listwise; prod histórico)
#   voyage → rerank_chunks_voyage (cross-encoder rerank-2.5) SOLO para llamadas
#            sin target_models — el path con target_models conserva el LLM
#            (dispatch condicional Y1: se shipea exactamente lo que el A/B mide;
#            el harness de eval nunca pasa target_models).
# voyage requiere VOYAGE_API_KEY (ya requerida por chunks_v2 / embed_query).
RERANKER_BACKEND = os.getenv("RERANKER_BACKEND", "llm")


def _strict_on_off(name: str, default: str = "off") -> bool:
    raw = os.getenv(name, default).strip().lower()
    if raw == "on":
        return True
    if raw == "off":
        return False
    raise RuntimeError(f"{name}={raw!r} no reconocido (on|off) — fail-fast")


# S107 candidate, default inert.  When enabled, independently validated coverage
# candidates bypass the mono-intent reranker only after its top-k is frozen.
POST_RERANK_COVERAGE = _strict_on_off("POST_RERANK_COVERAGE")

# S109 release lane for same-blob structural neighbours.  The master switch
# above and this lane-specific switch must both be on before a candidate can
# reach the generator.  It is intentionally separate from the observer: the
# observer can be sampled without changing answers, while this flag is a
# serving decision.
STRUCTURAL_NEIGHBOR_COVERAGE = _strict_on_off(
    "STRUCTURAL_NEIGHBOR_COVERAGE"
)

# S161 exact table-boundary repair.  A reranked table whose heading/preamble
# was split into its immutable predecessor may recover only that exact source
# span.  The independent lane remains inert unless both this switch and the
# post-rerank master switch are enabled.
TABLE_PREAMBLE_CLOSURE = _strict_on_off("TABLE_PREAMBLE_CLOSURE")

# S183 content-addressed, exact live-chunk-bound typographic evidence view. It does not
# affect retrieval/rerank scores and stays inert unless explicitly released.
EVIDENCE_DERIVATION_OVERLAY = _strict_on_off("EVIDENCE_DERIVATION_OVERLAY")

# S107 v4 candidate, default inert. This lane flag and the S109 master switch
# enable canonical-document HYQ independently of the other coverage lanes.
CANONICAL_HYQ_COVERAGE = _strict_on_off("CANONICAL_HYQ_COVERAGE")

# S126 relational three-facet compatibility bundle.  This is deliberately
# separate from the generic HYQ lane: when on for an applicable two-entity
# compatibility query, an incomplete bundle serves nothing.
COMPATIBILITY_BUNDLE_COVERAGE = _strict_on_off(
    "COMPATIBILITY_BUNDLE_COVERAGE"
)

# S110 deterministic complement over the already-retrieved pool.  It never
# re-runs retrieval or calls a model; the frozen reranker top-k remains an
# immutable prefix and at most two query-aligned exact-source rows may append.
RERANK_POOL_COVERAGE = _strict_on_off("RERANK_POOL_COVERAGE")

# S111 bounded second hop: a query-aligned pool complement may expose that its
# decisive explanation lives in an adjacent chunk of the exact same extraction
# blob.  The cascade is separately reversible and remains GET-only/fail-open.
STRUCTURAL_CASCADE_COVERAGE = _strict_on_off("STRUCTURAL_CASCADE_COVERAGE")

# S111 serving-boundary repair for evidence cards clipped inside a Markdown
# table row.  It is independent from every retrieval lane so deploying the
# code cannot alter an already-enabled lane unless this flag is also enabled.
LOGICAL_RECORD_COVERAGE = _strict_on_off("LOGICAL_RECORD_COVERAGE")

# S107 upstream candidate, default inert. Follows explicit numeric section
# references inside governed documents to recover information hidden by unsafe
# historical semantic-dedup marks; candidates still compete in the reranker.
DEDUP_REFERENCE_NAVIGATION = _strict_on_off("DEDUP_REFERENCE_NAVIGATION")

# S107 R2 repair candidate, default inert. Reads only a versioned rescue batch
# and uses generated statements as navigation hints; evidence remains an exact
# substring of the hydrated source parent.
R2_REPAIR_NAVIGATION = _strict_on_off("R2_REPAIR_NAVIGATION")

# S269 Track 2 must-preserve atom contract (default inert). When enabled, the
# generator appends verbatim missing must-preserve atoms from cited, identity-
# attested fragments (src/rag/must_preserve.py). The serving-path helper
# re-reads this same strict switch at call time (house pattern
# GENERATOR_PROMPT_VARIANT) so in-process A/B toggling works; this import-time
# constant keeps the flag inventoried and fail-fast on typos at boot.
MUST_PRESERVE_CONTRACT = _strict_on_off("MUST_PRESERVE_CONTRACT")

# S107 same-blob neighbor observer. This hook is post-rerank and has no return
# path into the generator. Enabling it requires a keyed telemetry HMAC secret;
# defaults remain fully inert.
STRUCTURAL_NEIGHBOR_SHADOW = _strict_on_off("STRUCTURAL_NEIGHBOR_SHADOW")
STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY = os.getenv(
    "STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY", ""
)
STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY_VERSION = os.getenv(
    "STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY_VERSION", ""
).strip()
if STRUCTURAL_NEIGHBOR_SHADOW and len(STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY) < 32:
    raise RuntimeError(
        "STRUCTURAL_NEIGHBOR_SHADOW requires a >=32-character "
        "STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY"
    )
if STRUCTURAL_NEIGHBOR_SHADOW and not re.fullmatch(
    r"v[1-9][0-9]{0,5}", STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY_VERSION
):
    raise RuntimeError(
        "STRUCTURAL_NEIGHBOR_SHADOW requires a non-secret key version such as "
        "STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY_VERSION=v1"
    )

# Estrategia del MERGE de canales del retriever (s68, diseño _s68_merge_design.md v6.1).
# SWAP reversible por entorno, mismo patrón que RERANKER_BACKEND/CHUNKS_TABLE:
#   stamps (default) → comportamiento histórico EXACTO (keyword-first dedup + sort por
#                      similarity con stamps planos 0.65-0.85 — bit-idéntico a main).
#   quota  (V-D)     → composición: léxicos con sus límites actuales + canal vectorial
#                      SANO (sin filter_category, sin broad-5, sin 3c-i) llena hasta
#                      top_k por coseno; en duales el registro VECTOR conserva su coseno.
#   cosine (V-A′)    → score único := coseno real para TODO candidato (re-score
#                      cliente-side de los léxicos); sin boosts.
MERGE_STRATEGY = os.getenv("MERGE_STRATEGY", "stamps")

# LLM config
LLM_MODEL = "claude-sonnet-4-6"
# s99: tope de tokens de SALIDA del generador. SWAP reversible por entorno (patrón RERANK_TOP_K)
# — default 2048 = prod histórico INERTE. Se sube a 3500 en Railway JUNTO con RERANK_TOP_K=10:
# servir 10 chunks produce respuestas más completas que a veces rozaban el cap de 2048 (cat019
# truncaba, TECH_DEBT #74). Sin el bump, top-10 truncaría respuestas verbosas. DEC-092.
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))

# Validator post-generación: experimentado s13 y REVERTIDO (net-neutral, 2-3x coste/latencia);
# código borrado en s56 tras 7 semanas muerto (TECH_DEBT #11i; rationale completo y el código
# viven en git — DEC-036).

# Image config
MAX_IMAGE_WIDTH = 1200
IMAGE_QUALITY = 80


def validate_config(require_telegram: bool = False):
    """Validate that required environment variables are set.

    Args:
        require_telegram: If True, also require TELEGRAM_BOT_TOKEN (for bot mode).
    """
    required = {
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_SERVICE_KEY": SUPABASE_SERVICE_KEY,
    }
    if require_telegram:
        required["TELEGRAM_BOT_TOKEN"] = TELEGRAM_BOT_TOKEN

    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Check your .env file."
        )
