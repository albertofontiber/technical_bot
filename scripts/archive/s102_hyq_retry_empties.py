#!/usr/bin/env python3
"""s102_hyq_retry_empties.py — pasada única sobre los registros `questions: []` del jsonl hyq.

Motivo (S4/DEC-096d): hasta el fix del tramo 4, un error de API se escribía como `questions=[]`
— indistinguible del NONE legítimo — y el chunk quedaba done-para-siempre. Esta pasada regenera
UNA vez cada registro vacío: el NONE legítimo vuelve a dar [] (se conserva) y el error histórico
se sana. Reglas: (1) SOLO corre con los tramos cerrados (reescribe el fichero completo — un solo
escritor); (2) un error de API en el retry CONSERVA el registro viejo (no pisa, reporta); (3)
escritura atómica (tmp + replace) con el fichero previo committeado en git (rollback trivial).

Uso: python scripts/s102_hyq_retry_empties.py
Coste estimado: ~1.950 chunks ≈ $6-8 (una pasada, no iterar — feedback_cost_discipline).
"""
import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import anthropic
import requests

from s102_hyq_corpuswide import LLM_MODEL, PROMPT, _docs_and_fewshot

JSONL = ROOT / "evals" / "s99_hyq_generated.jsonl"
SUPABASE_URL = os.environ["SUPABASE_URL"]
KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
HDR = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}


def fetch_contents(ids: list[str]) -> dict[str, dict]:
    out = {}
    for i in range(0, len(ids), 80):
        batch = ids[i:i + 80]
        r = requests.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=HDR,
                         params={"id": f"in.({','.join(batch)})",
                                 "select": "id,content,product_model"}, timeout=60)
        r.raise_for_status()
        for row in r.json():
            out[row["id"]] = row
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    lines = io.open(JSONL, encoding="utf-8").readlines()
    recs = [json.loads(l) for l in lines]
    empty_idx = [i for i, r in enumerate(recs) if not r.get("questions")]
    # dedup: si un chunk_id vacío aparece varias veces (dupes s99), regenerar solo la primera
    seen, targets = set(), []
    for i in empty_idx:
        cid = recs[i].get("chunk_id")
        if cid and cid not in seen:
            seen.add(cid)
            targets.append(i)
    print(f"{len(empty_idx)} registros vacíos · {len(targets)} chunks únicos a regenerar", flush=True)

    contents = fetch_contents([recs[i]["chunk_id"] for i in targets])
    _, fewshot = _docs_and_fewshot()
    fewshot_txt = "\n".join(f"- {q}" for q in fewshot)
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    kw = {} if ("-5" in LLM_MODEL or "fable" in LLM_MODEL) else {"temperature": 0}

    healed, still_none, short, errors = 0, 0, 0, 0
    for n, i in enumerate(targets):
        rec = recs[i]
        row = contents.get(rec["chunk_id"])
        content = ((row or {}).get("content") or "")[:2000]
        if len(content.strip()) < 40:
            short += 1
            continue                      # NONE estructural (página vacía/corta): [] se queda
        prod = rec.get("product_model") or (row or {}).get("product_model") or "el equipo del manual"
        try:
            msg = client.messages.create(model=LLM_MODEL, max_tokens=300, **kw,
                messages=[{"role": "user", "content": PROMPT.format(
                    producto=prod, fewshot=fewshot_txt, content=content)}])
            raw = msg.content[0].text.strip()
        except Exception as e:
            errors += 1
            print(f"  API error {rec['chunk_id']}: {type(e).__name__} — registro viejo conservado", flush=True)
            if errors >= 20:
                raise RuntimeError("20 errores — abortando (fail-fast); lo hecho se escribe igual")
            continue
        qs = [q.strip("-• ").strip() for q in raw.splitlines() if q.strip() and "NONE" not in q]
        if qs:
            rec["questions"] = qs
            rec["origin"] = "synthetic-retry"
            recs[i] = rec
            healed += 1
        else:
            still_none += 1
        if (n + 1) % 200 == 0:
            print(f"  {n+1}/{len(targets)}… (healed {healed})", flush=True)

    tmp = JSONL.with_suffix(".jsonl.tmp")
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, JSONL)
    nq = sum(len(r.get("questions") or []) for r in recs)
    print(f"\nRETRY-EMPTIES: healed={healed} · still-NONE={still_none} · cortos-skip={short} · "
          f"errores-conservados={errors} · total preguntas ahora {nq}", flush=True)


if __name__ == "__main__":
    main()
