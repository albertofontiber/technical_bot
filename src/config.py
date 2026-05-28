import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
PROJECT_DIR = Path(__file__).parent.parent

load_dotenv(PROJECT_DIR / ".env", override=True)
MANUALS_DIR = Path(os.getenv("MANUALS_DIR", PROJECT_DIR / "Manuales_ES"))
IMAGES_DIR = Path(os.getenv("IMAGES_DIR", PROJECT_DIR / "extracted_images"))

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Tabla de chunks activa (sesión 27). Permite probar/SWAP a chunks_v2 sin tocar
# código ni hacer RENAME destructivo: basta cambiar CHUNKS_TABLE en el entorno.
#   chunks    → corpus viejo (OpenAI text-embedding-3-small, 1536 dims)
#   chunks_v2 → corpus re-ingestado (Voyage voyage-4-large, 1024 dims)
# El sufijo de RPC y el proveedor de embedding de la query se derivan de aquí.
CHUNKS_TABLE = os.getenv("CHUNKS_TABLE", "chunks")
CHUNKS_IS_V2 = CHUNKS_TABLE.endswith("_v2")
RPC_SUFFIX = "_v2" if CHUNKS_IS_V2 else ""

# Embedding config
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# RAG config
RETRIEVAL_TOP_K = 15
RERANK_TOP_K = 5
CHUNK_MAX_TOKENS = 1500
CHUNK_OVERLAP_TOKENS = 200

# LLM config
LLM_MODEL = "claude-sonnet-4-6"
LLM_MAX_TOKENS = 2048

# Cross-model validator (sesión 13 — experimentado y REVERTIDO 23 abril 2026).
#
# Intento: Opus audita la respuesta de Sonnet post-generación y, si detecta
# afirmaciones no soportadas por los chunks, Sonnet regenera con feedback.
#
# Resultado:
#   - V1 (con fallback): 25/52 → 20/52 judge (-5). Catastrófico: fallback
#     mataba happy_path (19/19 fallbacks → FAIL).
#   - V2 (retry-only, sin fallback, corpus Morley expandido): 25/52 → 26/52
#     judge (+1 aparente, pero con churn +7/-9 — net neutral, ruido de Opus).
#
# Conclusión: Opus como validator post-generación no aporta señal consistente
# en este dominio y añade ~2-3x coste y latencia. Código del validator
# preservado en `src/rag/validator.py` + tests por si futuras iteraciones
# quieren reintentar con otra arquitectura (citation faithfulness estructural,
# Haiku-strict, validator sobre chunks en vez de respuesta, etc.). Ver
# TECH_DEBT #11i. El generator.py ya NO lo invoca.
VALIDATOR_MODEL = os.getenv("VALIDATOR_MODEL", "claude-opus-4-6")
VALIDATOR_MAX_TOKENS = 800

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
