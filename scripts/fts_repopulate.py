#!/usr/bin/env python3
"""Call repopulate_search_vector_batch RPC with concurrent workers.

Assumes:
- Column `fts_v2 BOOLEAN DEFAULT FALSE` exists on `chunks`
- RPC `repopulate_search_vector_batch(INT)` uses FOR UPDATE SKIP LOCKED (concurrency-safe)
- Text search config `public.spanish_unaccent` exists
"""
import io
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from src.ingestion.supabase_client import get_supabase


BATCH_SIZE = 300
WORKERS = 4
CONSECUTIVE_EMPTY_TO_STOP = 3


counter_lock = threading.Lock()
counters = {"total_updated": 0, "batches": 0, "empty_streak": 0, "errors": 0}


def call_rpc(sb, worker_id: int) -> int:
    url = f"{sb.url}/rest/v1/rpc/repopulate_search_vector_batch"
    headers = {
        "apikey": sb.service_key,
        "Authorization": f"Bearer {sb.service_key}",
        "Content-Type": "application/json",
    }
    try:
        r = sb.client.post(url, headers=headers, json={"batch_size": BATCH_SIZE}, timeout=300)
        if r.status_code != 200:
            with counter_lock:
                counters["errors"] += 1
            print(f"[w{worker_id}] ERROR {r.status_code}: {r.text[:200]}", flush=True)
            time.sleep(2)
            return -1
        return int(r.json())
    except Exception as e:
        with counter_lock:
            counters["errors"] += 1
        print(f"[w{worker_id}] EXCEPTION: {type(e).__name__}: {e}", flush=True)
        time.sleep(2)
        return -1


def worker(worker_id: int, start_time: float):
    sb = get_supabase()
    while True:
        with counter_lock:
            if counters["empty_streak"] >= CONSECUTIVE_EMPTY_TO_STOP:
                return
        t0 = time.time()
        updated = call_rpc(sb, worker_id)
        dt = time.time() - t0
        if updated < 0:
            continue
        with counter_lock:
            counters["batches"] += 1
            if updated == 0:
                counters["empty_streak"] += 1
                if counters["empty_streak"] >= CONSECUTIVE_EMPTY_TO_STOP:
                    print(f"[w{worker_id}] empty — stopping", flush=True)
                    return
                print(f"[w{worker_id}] empty batch #{counters['empty_streak']}", flush=True)
            else:
                counters["empty_streak"] = 0
                counters["total_updated"] += updated
            batch_num = counters["batches"]
            total = counters["total_updated"]
        if updated > 0:
            elapsed = time.time() - start_time
            print(
                f"[w{worker_id} b{batch_num:3d}] +{updated:>4} in {dt:5.1f}s "
                f"| total {total:>7,} | elapsed {elapsed:5.0f}s",
                flush=True,
            )


def main():
    start = time.time()
    print(f"[start] {WORKERS} workers × batch={BATCH_SIZE}", flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(worker, i + 1, start) for i in range(WORKERS)]
        for f in futures:
            f.result()
    total_t = time.time() - start
    print(
        f"[DONE] total updated: {counters['total_updated']:,} in {total_t:.0f}s "
        f"(errors: {counters['errors']})",
        flush=True,
    )


if __name__ == "__main__":
    main()
