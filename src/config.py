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
