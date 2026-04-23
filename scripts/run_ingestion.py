#!/usr/bin/env python3
"""
Script to run the ingestion pipeline.
Usage:
    python scripts/run_ingestion.py                              # Full ingestion (default MANUALS_DIR)
    python scripts/run_ingestion.py --dry-run                    # Parse and chunk only, no upload
    python scripts/run_ingestion.py --use-vision                 # Enable Claude Vision for unextracted content
    python scripts/run_ingestion.py --single <path>              # Process a single PDF
    python scripts/run_ingestion.py --base-dir <path>            # Override the default Manuales_ES directory
                                                                  # (NOTE: config.py calls load_dotenv(override=True)
                                                                  # so the MANUALS_DIR env var alone doesn't win —
                                                                  # this flag is the way to point at another folder.)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ingestion.ingest import ingest_all, ingest_single_pdf
from src.ingestion.supabase_client import get_supabase


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    use_vision = "--use-vision" in args

    base_dir = None
    if "--base-dir" in args:
        idx = args.index("--base-dir")
        if idx + 1 >= len(args):
            print("Error: --base-dir requires a directory path argument")
            sys.exit(1)
        base_dir = Path(args[idx + 1]).resolve()
        if not base_dir.exists():
            print(f"Error: base-dir {base_dir} does not exist")
            sys.exit(1)
        print(f"Using base_dir: {base_dir}")

    if "--single" in args:
        idx = args.index("--single")
        if idx + 1 >= len(args):
            print("Error: --single requires a PDF path argument")
            sys.exit(1)
        pdf_path = args[idx + 1]
        supabase = None if dry_run else get_supabase()
        ingest_single_pdf(
            pdf_path, supabase=supabase, dry_run=dry_run, use_vision=use_vision
        )
    else:
        if base_dir is not None:
            ingest_all(base_dir=base_dir, dry_run=dry_run, use_vision=use_vision)
        else:
            ingest_all(dry_run=dry_run, use_vision=use_vision)


if __name__ == "__main__":
    main()
