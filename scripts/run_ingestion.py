#!/usr/bin/env python3
"""
Script to run the ingestion pipeline.
Usage:
    python scripts/run_ingestion.py                    # Full ingestion (requires Supabase + OpenAI keys)
    python scripts/run_ingestion.py --dry-run          # Parse and chunk only, no upload
    python scripts/run_ingestion.py --use-vision       # Enable Claude Vision for unextracted content
    python scripts/run_ingestion.py --single <path>    # Process a single PDF
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ingestion.ingest import ingest_all, ingest_single_pdf


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    use_vision = "--use-vision" in args

    if "--single" in args:
        idx = args.index("--single")
        if idx + 1 >= len(args):
            print("Error: --single requires a PDF path argument")
            sys.exit(1)
        pdf_path = args[idx + 1]
        ingest_single_pdf(pdf_path, dry_run=dry_run, use_vision=use_vision)
    else:
        ingest_all(dry_run=dry_run, use_vision=use_vision)


if __name__ == "__main__":
    main()
