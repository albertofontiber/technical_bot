#!/usr/bin/env python3
"""s83_full_extract_batch.py - FULL RUN: extraccion duo (Opus 4.8 + GPT-5.5) sobre los ~1014 docs
via BATCHES API (-50%). Nivel-1 (texto). Reusa SYS/SCHEMA v4 del piloto.

SEGURIDAD ANTI-RE-PAGO: el state file (s83_full_batch_state.json) guarda los batch IDs en cuanto se
crean. Re-correr NO re-submite si ya hay batches -> reanuda el poll/retrieve. Resumable.

Fases: A) fetch+group contenido de los 1014 (1 pasada sobre chunks_v2). B) submit 6+6 batches
(Anthropic in-memory + OpenAI file-upload), guarda state tras CADA batch. C) poll hasta ended ->
retrieve -> reconcilia (covered sets, agree/conflict) -> escribe s83_full_extraction.jsonl.
"""
from __future__ import annotations
import io
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx
from dotenv import load_dotenv

os.environ["CHUNKS_TABLE"] = "chunks_v2"
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import s83_pilot_extract_duo as P  # noqa: E402  (SYS, SCHEMA, norm_model, covered_set, MAX_CHARS, models)
from src.config import ANTHROPIC_API_KEY, OPENAI_API_KEY  # noqa: E402
from anthropic import Anthropic  # noqa: E402
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming  # noqa: E402
from anthropic.types.messages.batch_create_params import Request as AntRequest  # noqa: E402
from openai import OpenAI  # noqa: E402

STATE = ROOT / "evals" / "s83_full_batch_state.json"
OUT = ROOT / "evals" / "s83_full_extraction.jsonl"
OPUS_CACHE = ROOT / "evals" / "_s83_opus_raw.json"
GPT_CACHE = ROOT / "evals" / "_s83_gpt_raw.json"
DOCS_PER_BATCH = 200
POLL_BUDGET_S = 3000  # ~50 min por corrida (acotado, robusto al corte de sesion)
TOOL = [{"name": "registrar_modelos",
         "description": "Registra identidad estructurada, modelos cubiertos/mencionados, relaciones y metadatos.",
         "input_schema": P.SCHEMA}]


def log(m):
    print(m, flush=True)


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"submitted": False, "anthropic_batches": [], "openai_batches": [], "id_map": {}}


def save_state(s):
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def fetch_all_docs():
    """1 pasada sobre chunks_v2 -> {source_file: {content, cur_tag, cur_mfr, sha, n}}."""
    H, CH = P.H, P.CH
    groups = defaultdict(list)
    meta = {}
    off, page = 0, 1000
    while True:
        r = httpx.get(CH, headers=H, params={
            "select": "source_file,chunk_index,page_number,section_title,content,product_model,manufacturer,extraction_sha256",
            "order": "source_file.asc,chunk_index.asc.nullslast",
            "limit": str(page), "offset": str(off)}, timeout=180)
        r.raise_for_status()
        rows = r.json()
        if not rows:
            break
        for x in rows:
            sf = x.get("source_file")
            if not sf:
                continue
            groups[sf].append(x)
            m = meta.setdefault(sf, {"cur_tag": None, "cur_mfr": None, "sha": None})
            if not m["cur_tag"] and x.get("product_model"):
                m["cur_tag"] = x["product_model"]
            if not m["cur_mfr"] and x.get("manufacturer"):
                m["cur_mfr"] = x["manufacturer"]
            if not m["sha"] and x.get("extraction_sha256"):
                m["sha"] = x["extraction_sha256"]
        off += page
        log(f"  ...{off} chunks ({len(groups)} docs)")
        if len(rows) < page:
            break
    docs = {}
    for sf, rows in groups.items():
        parts = []
        for x in rows:
            pg = x.get("page_number")
            st = x.get("section_title")
            head = (f"[pag {pg}] " if pg is not None else "") + (f"## {st}\n" if st else "")
            parts.append(head + (x.get("content") or ""))
        text = "\n\n".join(parts)[:P.MAX_CHARS]
        if text.strip():
            docs[sf] = {"content": text, **meta[sf], "n": len(rows)}
    return docs


def user_msg(sf, content):
    return f"source_file: {sf}\n\n===== CONTENIDO COMPLETO DEL DOCUMENTO =====\n{content}"


def chunked(items, n):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def submit(docs, a_client, o_client, state):
    sfs = sorted(docs.keys())
    id_map = {f"doc-{i:05d}": sf for i, sf in enumerate(sfs)}
    state["id_map"] = id_map
    cid_of = {sf: cid for cid, sf in id_map.items()}
    items = [(cid_of[sf], sf, docs[sf]["content"]) for sf in sfs]
    save_state(state)

    # --- Anthropic batches (in-memory requests) ---
    for bi, group in enumerate(chunked(items, DOCS_PER_BATCH)):
        reqs = [AntRequest(
            custom_id=cid,
            params=MessageCreateParamsNonStreaming(
                model=P.OPUS_MODEL, max_tokens=12000, system=P.SYS,
                tools=TOOL, tool_choice={"type": "tool", "name": "registrar_modelos"},
                messages=[{"role": "user", "content": user_msg(sf, content)}],
            )) for (cid, sf, content) in group]
        b = a_client.messages.batches.create(requests=reqs)
        state["anthropic_batches"].append(b.id)
        save_state(state)
        log(f"  Anthropic batch {bi} -> {b.id} ({len(reqs)} reqs, status={b.processing_status})")

    # --- OpenAI batches (file upload) ---
    for bi, group in enumerate(chunked(items, DOCS_PER_BATCH)):
        lines = []
        for (cid, sf, content) in group:
            lines.append(json.dumps({
                "custom_id": cid, "method": "POST", "url": "/v1/chat/completions",
                "body": {
                    "model": P.GPT_MODEL,
                    "messages": [{"role": "system", "content": P.SYS},
                                 {"role": "user", "content": user_msg(sf, content)}],
                    "response_format": {"type": "json_schema", "json_schema": {
                        "name": "registrar_modelos", "schema": P.SCHEMA, "strict": True}},
                }}, ensure_ascii=False))
        buf = io.BytesIO(("\n".join(lines)).encode("utf-8"))
        f = o_client.files.create(file=("batch.jsonl", buf), purpose="batch")
        b = o_client.batches.create(input_file_id=f.id, endpoint="/v1/chat/completions",
                                    completion_window="24h")
        state["openai_batches"].append(b.id)
        save_state(state)
        log(f"  OpenAI batch {bi} -> {b.id} ({len(lines)} reqs, status={b.status})")

    state["submitted"] = True
    save_state(state)
    log(f"SUBMITTED: {len(state['anthropic_batches'])} Anthropic + {len(state['openai_batches'])} OpenAI batches.")


def load_cache(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_cache(p, d):
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def collect_anthropic(a_client, ids, cache):
    """1 chequeo por batch; cachea ended; deja pendientes para la proxima corrida."""
    for bid in ids:
        b = a_client.messages.batches.retrieve(bid)
        if b.processing_status != "ended":
            log(f"  Anthropic {bid}: {b.processing_status} (pendiente)")
            continue
        got = 0
        for res in a_client.messages.batches.results(bid):
            cid = res.custom_id
            if cid in cache:
                continue
            if res.result.type == "succeeded":
                inp = None
                for blk in res.result.message.content:
                    if blk.type == "tool_use":
                        inp = blk.input
                cache[cid] = inp if inp is not None else {"_error": "sin tool_use"}
            else:
                cache[cid] = {"_error": f"{res.result.type}"}
            got += 1
        if got:
            save_cache(OPUS_CACHE, cache)
        log(f"  Anthropic {bid}: ended (+{got}, total {len(cache)})")
    return cache


def collect_openai(o_client, ids, cache):
    for bid in ids:
        b = o_client.batches.retrieve(bid)
        if b.status != "completed":
            log(f"  OpenAI {bid}: {b.status} (pendiente)")
            continue
        if not b.output_file_id:
            log(f"  !! OpenAI {bid} completed sin output_file_id")
            continue
        txt = o_client.files.content(b.output_file_id).text
        got = 0
        for line in txt.splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            cid = r["custom_id"]
            if cid in cache:
                continue
            try:
                content = r["response"]["body"]["choices"][0]["message"]["content"]
                cache[cid] = json.loads(content)
            except Exception as e:
                cache[cid] = {"_error": str(e)[:120]}
            got += 1
        if got:
            save_cache(GPT_CACHE, cache)
        log(f"  OpenAI {bid}: completed (+{got}, total {len(cache)})")
    return cache


def classify(o, g):
    if o is None or g is None:
        return "error"
    if o == g:
        return "agree"
    if o <= g or g <= o:
        return "superset"
    return "conflict"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if not ANTHROPIC_API_KEY or not OPENAI_API_KEY:
        sys.exit("Faltan claves")
    a_client = Anthropic(api_key=ANTHROPIC_API_KEY)
    o_client = OpenAI(api_key=OPENAI_API_KEY)
    state = load_state()

    if not state["submitted"]:
        log("== FASE A: fetch contenido de los docs ==")
        docs = fetch_all_docs()
        tot_chars = sum(len(d["content"]) for d in docs.values())
        log(f"docs: {len(docs)} | total chars: {tot_chars} (~{tot_chars/1e6:.0f}MB) | "
            f"batches: {-(-len(docs)//DOCS_PER_BATCH)}/proveedor")
        log("== FASE B: submit batches (paga aqui) ==")
        submit(docs, a_client, o_client, state)
    else:
        log(f"== state ya SUBMITTED: {len(state['anthropic_batches'])}A + "
            f"{len(state['openai_batches'])}O batches -> reanudo collect ==")

    id_map = state["id_map"]
    need = len(id_map)
    log(f"== FASE C: poll + retrieve (cacheado, budget {POLL_BUDGET_S}s) ==")
    t0 = time.monotonic()
    while True:
        opus = collect_anthropic(a_client, state["anthropic_batches"], load_cache(OPUS_CACHE))
        gpt = collect_openai(o_client, state["openai_batches"], load_cache(GPT_CACHE))
        log(f"  -> opus {len(opus)}/{need} | gpt {len(gpt)}/{need}")
        if len(opus) >= need and len(gpt) >= need:
            break
        if time.monotonic() - t0 > POLL_BUDGET_S:
            log(f"PENDIENTE (budget agotado): opus {len(opus)}/{need}, gpt {len(gpt)}/{need} "
                f"-> re-correr el script reanuda (cache a salvo, batches viven 29d).")
            return 0
        time.sleep(60)

    n = ag = sup = conf = err = 0
    with OUT.open("w", encoding="utf-8") as fh:
        for cid, sf in sorted(id_map.items()):
            o_res, g_res = opus.get(cid), gpt.get(cid)
            os_set = P.covered_set(o_res) if o_res else None
            gs_set = P.covered_set(g_res) if g_res else None
            cls = classify(os_set, gs_set)
            rec = {
                "source_file": sf, "custom_id": cid,
                "opus": o_res, "gpt": g_res,
                "opus_covered": sorted(os_set) if os_set is not None else None,
                "gpt_covered": sorted(gs_set) if gs_set is not None else None,
                "class": cls,
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
            cls == "agree" and (ag := ag + 1)
            cls == "superset" and (sup := sup + 1)
            cls == "conflict" and (conf := conf + 1)
            cls == "error" and (err := err + 1)
    log("\n===== FULL RUN COMPLETO =====")
    log(f"docs: {n} | agree {ag} ({100*ag/max(n,1):.0f}%) | superset {sup} ({100*sup/max(n,1):.0f}%) "
        f"| conflict {conf} ({100*conf/max(n,1):.0f}%) | error {err}")
    log(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
