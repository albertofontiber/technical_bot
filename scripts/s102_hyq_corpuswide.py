#!/usr/bin/env python3
"""s102_hyq_corpuswide.py — generación hyq CORPUS-WIDE por TRAMOS (ship-path D2, GO Alberto s101).

Reusa el pipeline del generador s99 (mismo PROMPT/few-shot no-circular/parser) sobre TODOS los docs
del corpus, por tramos gateados (lección DEC-088: nunca pase ciego). Append al MISMO jsonl (resumible
por chunk_id). QA muestral por tramo ANTES del siguiente (gate de sanidad ≥70%, patrón prereg).

Uso: python scripts/s102_hyq_corpuswide.py tranche 3000   # genera hasta N chunks nuevos y para
Coste: ~$0.004/chunk (Sonnet). Total restante ≈ 22.4k chunks ≈ $90 en ~8 tramos.
"""
import os, sys, json
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
for k, v in {"CHUNKS_TABLE": "chunks_v2"}.items():
    os.environ.setdefault(k, v)
from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)
import requests, anthropic
from src.config import ANTHROPIC_API_KEY, LLM_MODEL, SUPABASE_URL, SUPABASE_SERVICE_KEY
from s99_hyq_generate import OUT, PROMPT, _docs_and_fewshot   # mismo prompt + few-shot congelados

_HDR = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}


def all_chunks_paged(offset, page=1000):
    hdr = {**_HDR, "Range-Unit": "items", "Range": f"{offset}-{offset+page-1}"}
    r = requests.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=hdr,
                     params={"select": "id,content,product_model,manufacturer,source_file,page_number",
                             "order": "source_file.asc,page_number.asc"}, timeout=60)
    r.raise_for_status()
    return r.json()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    done = set()
    if OUT.exists():
        for ln in OUT.open(encoding="utf-8"):
            try:
                done.add(json.loads(ln)["chunk_id"])
            except Exception:
                pass
    print(f"tramo: hasta {limit} chunks nuevos · ya generados {len(done)} · modelo {LLM_MODEL}")
    _, fewshot = _docs_and_fewshot()
    fewshot_txt = "\n".join(f"- {q}" for q in fewshot)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    kw = {} if ("-5" in LLM_MODEL or "fable" in LLM_MODEL) else {"temperature": 0}
    n = 0; offset = 0
    with OUT.open("a", encoding="utf-8") as f:
        while n < limit:
            rows = all_chunks_paged(offset)
            if not rows:
                break
            offset += len(rows)
            for c in rows:
                if n >= limit:
                    break
                cid = c.get("id")
                if cid in done:
                    continue
                content = (c.get("content") or "")[:2000]
                if len(content.strip()) < 40:
                    done.add(cid)
                    continue
                prod = c.get("product_model") or "el equipo del manual"
                try:
                    msg = client.messages.create(model=LLM_MODEL, max_tokens=300, **kw,
                        messages=[{"role": "user", "content": PROMPT.format(
                            producto=prod, fewshot=fewshot_txt, content=content)}])
                    raw = msg.content[0].text.strip()
                except Exception as e:
                    raw = f"ERROR: {type(e).__name__}"
                qs = [q.strip("-• ").strip() for q in raw.splitlines() if q.strip()
                      and "NONE" not in q and not q.startswith("ERROR")]
                f.write(json.dumps({"chunk_id": cid, "source_file": c.get("source_file"),
                                    "page_number": c.get("page_number"), "product_model": prod,
                                    "manufacturer": c.get("manufacturer"), "questions": qs,
                                    "origin": "synthetic"}, ensure_ascii=False) + "\n")
                f.flush()
                done.add(cid)
                n += 1
                if n % 200 == 0:
                    print(f"  {n}/{limit}…", flush=True)
    print(f"tramo OK: +{n} chunks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
