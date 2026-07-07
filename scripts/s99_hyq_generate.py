"""s99 · Genera hypothetical QUESTIONS por chunk de los docs-diana (a FICHERO, sin DB).

Disciplina de coste: generar + spot-verificar ANTES de construir tabla/indexar. Few-shot NO-circular
(preguntas de golds FUERA del slice de medición — fix dúo/Q3 Alberto). Genera para TODOS los chunks
de los docs-diana (no solo las agujas = no cherry-pick). Salida: evals/s99_hyq_generated.jsonl.

Uso:  python scripts/s99_hyq_generate.py count   # cuenta chunks + estima coste
      python scripts/s99_hyq_generate.py gen     # genera a fichero
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for k, v in {"CHUNKS_TABLE": "chunks_v2"}.items():
    os.environ.setdefault(k, v)
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)
import yaml  # noqa: E402
import anthropic  # noqa: E402
import requests  # noqa: E402
from src.config import ANTHROPIC_API_KEY, LLM_MODEL, SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402

_HDR = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}

OUT = ROOT / "evals" / "s99_hyq_generated.jsonl"
SLICE_QIDS = ["cat001", "cat010", "hp002", "hp003", "hp005", "hp006", "hp009", "hp017",
              "cat016", "hp011", "hp012",
              # s101 (Fase 1): RECALL del deathpoint cuyos docs faltaban en la 1ª pasada
              "hp013", "hp020", "hp014"]
# few-shot NO-CIRCULAR: golds FUERA del slice (registro real de Alberto, no del instrumento medido)
# s101: hp013 SALE del few-shot (entró al slice de medición — regla anti-fuga del prereg); entra hp008.
FEWSHOT_QIDS = ["cat019", "cat024", "hp004", "hp008", "cat009", "cat011"]


def _docs_and_fewshot():
    golds = {g["qid"]: g for g in yaml.safe_load(open(ROOT / "evals" / "gold_answers_v1.yaml",
             encoding="utf-8"))}
    docs = set()
    for q in SLICE_QIDS:
        for d in (golds.get(q, {}).get("pdfs_used") or []):
            docs.add(d.rsplit(".pdf", 1)[0])  # chunks_v2.source_file va SIN .pdf
    fewshot = [golds[q]["question"] for q in FEWSHOT_QIDS if q in golds and golds[q].get("question")]
    return sorted(docs), fewshot


def _chunks(docs):
    """GET chunks de cada doc vía REST (patrón retriever.py; paginado, REST capa a 1000)."""
    rows = []
    sel = "id,content,product_model,manufacturer,source_file,page_number"
    for d in docs:
        offset = 0
        while True:
            hdr = {**_HDR, "Range-Unit": "items", "Range": f"{offset}-{offset+999}"}
            r = requests.get(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                             headers=hdr, params={"source_file": f"eq.{d}", "select": sel},
                             timeout=60)
            r.raise_for_status()
            batch = r.json()
            rows.extend(batch)
            if len(batch) < 1000:
                break
            offset += 1000
    return rows


def count():
    docs, fewshot = _docs_and_fewshot()
    rows = _chunks(docs)
    print(f"docs-diana: {len(docs)} · chunks: {len(rows)} · few-shot (no-circular): {len(fewshot)} preguntas")
    print(f"coste estimado ~{len(rows)} llamadas Sonnet cortas ≈ ${len(rows)*0.004:.1f}")
    return 0


PROMPT = """Eres un técnico de PCI (protección contra incendios) experimentado. Lee este fragmento \
de un manual del producto {producto}. Genera 2-4 PREGUNTAS que un técnico haría EN CAMPO, en \
lenguaje llano/coloquial (como se pregunta de verdad, no como está escrito el manual), y que ESTE \
fragmento responde. Incluye el modelo/producto exacto cuando aporte. Ejemplos del REGISTRO real de \
preguntas de técnicos (NO son sobre este fragmento, solo para el ESTILO):
{fewshot}

Fragmento:
{content}

Devuelve SOLO las preguntas, una por línea, sin numeración ni markdown. Si el fragmento no responde \
ninguna pregunta útil de técnico (índice, portada, legal), devuelve la línea: NONE"""


def gen():
    docs, fewshot = _docs_and_fewshot()
    fewshot_txt = "\n".join(f"- {q}" for q in fewshot)
    rows = _chunks(docs)
    done = set()
    if OUT.exists():
        for ln in OUT.open(encoding="utf-8"):
            try:
                done.add(json.loads(ln)["chunk_id"])
            except Exception:
                pass
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    kw = {} if ("-5" in LLM_MODEL or "fable" in LLM_MODEL) else {"temperature": 0}
    n = 0
    with OUT.open("a", encoding="utf-8") as f:
        for c in rows:
            cid = c.get("id")
            if cid in done:
                continue
            content = (c.get("content") or "")[:2000]
            if len(content.strip()) < 40:
                continue
            prod = c.get("product_model") or "el equipo del manual"
            try:
                msg = client.messages.create(
                    model=LLM_MODEL, max_tokens=300, **kw,
                    messages=[{"role": "user", "content": PROMPT.format(
                        producto=prod, fewshot=fewshot_txt, content=content)}])
                raw = msg.content[0].text.strip()
            except Exception as e:
                raw = f"ERROR: {type(e).__name__}"
            qs = [q.strip("-• ").strip() for q in raw.splitlines() if q.strip()
                  and "NONE" not in q and not q.startswith("ERROR")]
            rec = {"chunk_id": cid, "source_file": c.get("source_file"),
                   "page_number": c.get("page_number"), "product_model": prod,
                   "manufacturer": c.get("manufacturer"), "questions": qs, "origin": "synthetic"}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            n += 1
            if n % 50 == 0:
                print(f"  {n} chunks generados…", flush=True)
    print(f"gen OK → {OUT.name} (+{n} chunks nuevos)")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "count"
    raise SystemExit(count() if cmd == "count" else gen())
