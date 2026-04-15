"""Run the Telegram bot."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot.telegram_bot import run_bot

if __name__ == "__main__":
    run_bot()
