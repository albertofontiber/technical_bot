#!/usr/bin/env python3
"""enunciados_pass.py — el PASE corpus de enunciados por tramos (T0-4, plan s94b v2).

Por doc del store (agent_anthropic-sonnet-45) × página × item-de-datos:
  R2: enunciados LLM (PROMPT v1 CONGELADO — el del piloto DEC-086, con regla de
      discriminador de variante) por item.   R3: resumen 1-2 frases por item-tabla.
QA gate: `enunciados_qa.qa_statement` (fidelidad + anti-mispairing fila-nivel,
calibrado: caza 2/2 alucinaciones del piloto). Solo QA-OK se inserta.

Contrato de fila (migración 007 + dúo s94b):
  id            = uuid5(ancla) → estable DENTRO de una generación; la idempotencia
                  OPERATIVA la da el delete por-DOC previo al insert (dúo H4/H7 — una
                  re-generación LLM produce otros textos/ids; temperature=0 pineada)
  parent_id     = chunk del mismo source_file/página con máx. solape de tokens-valor
                  (tie → chunk_index menor). Sin padre resoluble → item FUERA (declarado).
  extraction_sha256 = el del DOC REAL (semántica intacta: re-proceso del manual borra
                  por sha → arrastra surrogates; + ON DELETE CASCADE por parent_id)
  ingest_batch  = 'enunciados-v1:<tranche>:p1' → rollback selectivo + vintage visible
  context       = blurb-B7 del padre · embedding = embed(context+"\\n\\n"+texto) (receta corpus)

Idempotencia de tramo: DELETE por ingest_batch ANTES de insertar. Cobertura por doc +
muestreo estratificado (marca × isPerfectTable) a evals/enunciados_sample_<tranche>.md.

Uso:
  python scripts/enunciados_pass.py --tranche T1 --docs <fichero con source_files> [--dry]
  python scripts/enunciados_pass.py --rollback enunciados-v1:T1
"""
import argparse
import glob
from concurrent.futures import ThreadPoolExecutor
import json
import os
import re
import sys
import uuid
from collections import defaultdict

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
import anthropic
import httpx

from enunciados_qa import cobertura_pagina, qa_statement, tokens_valor
from s94_f1_generate import item_text, store_pages
from src.config import LLM_MODEL, SUPABASE_SERVICE_KEY, SUPABASE_URL

NAMESPACE = uuid.UUID("6d0c6f2a-94b4-4e10-9c1e-a1b2c3d4e5f6")   # fijo: ids idempotentes uuid5(ancla)
STORE = "data/extraction/agent_anthropic-sonnet-45"
_H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
      "Content-Type": "application/json"}

def _msg_text(msg) -> str:
    """Texto robusto: la familia Claude 5 emite ThinkingBlock antes del TextBlock —
    content[0].text peta (cazado en el brazo p2). Concatena solo bloques text."""
    return "".join(getattr(b, "text", "") for b in msg.content
                   if getattr(b, "type", "") == "text")


def _temp_kw() -> dict:
    """temperature=0 solo donde el modelo lo acepta: la familia Claude 5 lo DEPRECÓ
    (400 explícito, cazado en el brazo p2). Vintage declarado: p1 pineado a 0;
    p2 con el default del modelo.
    (s104 F3 dúo) El predicado `"-5" in model` era FALSO-POSITIVO para claude-haiku-4-5
    (modelo 4.x, SÍ acepta temperature) → el brazo Haiku del G0 habría corrido a
    temperatura default = confound del side-by-side. Familia 5 real = fable/mythos/
    sonnet-5/opus-5 (los ids 4-5 no son familia 5)."""
    dep = re.search(r"fable|mythos|sonnet-5|opus-5", str(LLM_MODEL))
    return {} if dep else {"temperature": 0}


def _insert_rows(rows: list, poison_log: list) -> int:
    """Insert con BISECCIÓN de filas venenosas (un 500 de PostgREST suele ser UNA fila
    que revienta un trigger — cazado en 15088SP): si un batch falla se parte en dos
    hasta aislar la(s) fila(s), que se loguean y SALTAN (drop medido, no crash)."""
    if not rows:
        return 0
    r = httpx.post(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                   headers={**_H, "Prefer": "return=minimal"},
                   json=rows, timeout=120)
    if r.status_code < 300:
        return len(rows)
    if len(rows) == 1:
        poison_log.append({"id": rows[0]["id"], "source_file": rows[0].get("source_file"),
                           "status": r.status_code, "err": r.text[:200],
                           "content_head": (rows[0].get("content") or "")[:120]})
        return 0
    mid = len(rows) // 2
    return _insert_rows(rows[:mid], poison_log) + _insert_rows(rows[mid:], poison_log)


# PROMPTS v1 CONGELADOS (= piloto DEC-086; NO editar — un cambio es p2 y se declara)
R2_PROMPT_V1 = """Convierte el siguiente fragmento de un manual técnico PCI en ENUNCIADOS autónomos, uno por línea.
Reglas ESTRICTAS: cada enunciado expresa UN dato como frase completa en español técnico; incluye SIEMPRE el modelo/producto EXACTO ({producto}) y el contexto de sección; si el dato pertenece a una VARIANTE concreta (nº de lazos, versión, canal), el enunciado DEBE nombrarla; conserva los valores LITERALES (números, unidades, códigos, referencias) sin redondear ni convertir; NADA que no esté en el fragmento; sin comentarios, sin numeración, sin markdown."""
R3_PROMPT_V1 = """Describe la siguiente tabla de un manual técnico PCI en 1-2 frases en español técnico: su PROPÓSITO (qué pregunta responde), el producto/modelo EXACTO ({producto}) y qué magnitudes/columnas lista. NO enumeres los valores. Sin markdown."""


def doc_chunks(source_file: str) -> list[dict]:
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_H, params={
        "select": "id,content,context,product_model,manufacturer,source_file,page_number,"
                  "language,document_id,section_title,doc_type,content_type,chunk_index,"
                  "extraction_sha256",
        "source_file": f"eq.{source_file}", "parent_id": "is.null",
        "duplicate_of": "is.null", "limit": "2000"}, timeout=30)
    r.raise_for_status()
    return r.json()


def resolve_parent(item_txt: str, page_1b: int, chunks: list[dict]) -> dict | None:
    """Padre = chunk de la página con máx. solape de tokens-valor (tie → chunk_index)."""
    # Fallback ACOTADO a ±1 página (cross-model T0 + dúo H6: el fallback a doc-entero
    # amplificaba mispairing que nadie caza; el drift real store↔DB es de ±1). Más allá
    # → sin_padre (declarado).
    cand = [c for c in chunks if c.get("page_number") == page_1b]
    if not cand:
        cand = [c for c in chunks if c.get("page_number") in (page_1b - 1, page_1b + 1)]
    if not cand:
        return None
    vals = tokens_valor(item_txt)

    def score(c):
        return len(vals & tokens_valor(c.get("content") or ""))

    best = min(cand, key=lambda c: (-score(c), c.get("chunk_index") or 0))
    if vals and score(best) == 0:          # el item no vive en ningún chunk → sin padre
        return None
    return best


_SHA_MAP: dict | None = None


def _build_sha_map() -> dict:
    """(s104 F6 dúo) Mapa doc→[shas] EXACTO (basename normalizado, sin extensión). El
    substring first-match anterior colisionaba a ~1000 docs (nombre-contenido-en-nombre →
    items de OTRO manual con fidelidad-QA en verde = la clase más venenosa). El store REAL
    tiene ~5 claves con >1 sha (revisiones/variantes con igual nombre — verificado en el
    micro-smoke): la desambiguación es contra el `extraction_sha256` de la DB (la DB sabe
    qué vintage está vivo); sin match → None (declarado, no adivinado)."""
    m: dict[str, set] = {}
    for p in glob.glob(f"{STORE}/*.json"):
        head = open(p, encoding="utf-8").read(600)
        mm = re.search(r'"source_path":\s*"([^"]+)"', head)
        ms = re.search(r'"sha256":\s*"([0-9a-f]{16,})"', head)
        if not (mm and ms):
            continue
        base = re.sub(r"\.(pdf|json)$", "", os.path.basename(mm.group(1)), flags=re.I)
        key = re.sub(r"[^a-z0-9]", "", base.lower())
        m.setdefault(key, set()).add(ms.group(1))
    return m


def sha_of(source_file: str, db_sha: str | None = None) -> str | None:
    """sha del store para el doc; ambigüedad (varias revisiones con igual nombre) se
    resuelve con el sha de la DB (`db_sha`), nunca por orden de glob."""
    global _SHA_MAP
    if _SHA_MAP is None:
        _SHA_MAP = _build_sha_map()
    base = re.sub(r"\.(pdf|json)$", "", source_file, flags=re.I)
    key = re.sub(r"[^a-z0-9]", "", base.lower())
    shas = _SHA_MAP.get(key) or set()
    if len(shas) == 1:
        return next(iter(shas))
    if db_sha and db_sha in shas:
        return db_sha
    return None      # ambiguo sin ancla DB → sin store (declarado)


# (s104 F8 dúo) Clase CHAFF: enunciados de historial-de-revisiones/nº-documento — pasan el
# QA (fieles) pero no responden preguntas de técnico y a ~260K filas compiten por los ~120
# slots del fetch. Se CUENTAN por doc y se marcan en el dump (decisión de filtro duro =
# post-G0 con el conteo; el G0 los EXCLUYE de sus numeradores para que un generador verboso
# no gane la banda con chaff).
_CHAFF_RE = re.compile(
    r"n[uú]mero de (documento|parte)|revisi[oó]n [A-Z0-9]|documento .{0,40}(corresponde|tiene)"
    r"|hist[oó]rico de revisiones|PN \d|edici[oó]n \d", re.IGNORECASE)


def _is_chaff(text: str) -> bool:
    return bool(_CHAFF_RE.search(text or ""))


# (s104 G0 panel) META-LINEAS del generador (conversacionales, sin contenido): pasan el QA
# por no tener tokens-valor (clase ciega F2/X2) — cazado EN SONNET en el panel del G0
# ("Por favor, comparte el texto completo del fragmento..."). Filtro duro + contador.
_META_RE = None


def _is_meta(text: str) -> bool:
    global _META_RE
    if _META_RE is None:
        _META_RE = re.compile(
            r"^(por favor|lo siento|no puedo|aqu[ií] (est[aá]n|tienes)|claro[,:]|"
            r"entendido|de acuerdo)|proceder[ée] a|comparte el (texto|fragmento)|"
            r"no hay (datos|enunciados|informaci[oó]n) (que|para) (convertir|extraer)",
            re.IGNORECASE)
    return bool(_META_RE.search((text or "").strip()))


# tarifas $/Mtok para el tope de gasto (F10); default conservador = Sonnet
_RATES = {"haiku-4-5": (1.0, 5.0), "haiku": (1.0, 5.0), "sonnet": (3.0, 15.0)}


def _rate() -> tuple:
    m = str(LLM_MODEL)
    for k, v in _RATES.items():
        if k in m:
            return v
    return (3.0, 15.0)


def process_doc(client, source_file: str, tranche: str, dry: bool,
                vintage: str = "p1", to_dump: str | None = None) -> dict:
    from src.reingest.embed import embed
    chunks = doc_chunks(source_file)
    if not chunks:
        return {"doc": source_file, "error": "sin chunks en DB"}
    # (s104 F6) el sha del store se ancla al de la DB cuando el nombre es ambiguo
    db_sha = next((c.get("extraction_sha256") for c in chunks
                   if c.get("extraction_sha256")), None)
    sha = sha_of(source_file, db_sha)
    if not sha:
        return {"doc": source_file, "error": "sin store (o ambiguo sin ancla DB)"}
    marca = chunks[0].get("manufacturer") or "?"
    batch = f"enunciados-v1:{tranche}:{vintage}"
    rows, sample, stats = [], [], {"items": 0, "gen": 0, "qa_fail": 0, "sin_padre": 0,
                                   "chaff": 0}
    usage = [0, 0]   # [input_tokens, output_tokens] del doc — para el tope de gasto (F10)
    cov_by_page = []
    for pidx, page in enumerate(store_pages(sha)):
        items = page.get("items", []) if isinstance(page, dict) else []
        data_items = [(j, it) for j, it in enumerate(items)
                      if it.get("rows") or len(tokens_valor(item_text(it))) >= 3]
        page_stmts: list[str] = []
        def _gen_item(par):
            """Fase LLM de un item (paralela: el SDK es thread-safe y reintenta 429)."""
            j, it, parent = par
            # (s104 F1 dúo) pm "unknown"/vacío NO se inyecta como {producto}: frase sin
            # atribución > atribución falsa (el QA no puede verificar nombres de modelo)
            _pm = (parent.get("product_model") or "").strip()
            producto = _pm if _pm and _pm.lower() not in ("unknown", "n/a", "generic")                 else "el equipo del manual"
            outs = []
            msg = client.messages.create(model=LLM_MODEL, max_tokens=1500, **_temp_kw(),
                                         system=R2_PROMPT_V1.format(producto=producto),
                                         messages=[{"role": "user",
                                                    "content": item_text(it)[:8000]}])
            outs += [("R2", ln.strip()) for ln in _msg_text(msg).splitlines() if ln.strip()]
            usage[0] += getattr(msg.usage, "input_tokens", 0)
            usage[1] += getattr(msg.usage, "output_tokens", 0)
            if it.get("rows"):
                msg = client.messages.create(model=LLM_MODEL, max_tokens=300, **_temp_kw(),
                                             system=R3_PROMPT_V1.format(producto=producto),
                                             messages=[{"role": "user",
                                                        "content": item_text(it)[:6000]}])
                outs.append(("R3", _msg_text(msg).strip()))
                usage[0] += getattr(msg.usage, "input_tokens", 0)
                usage[1] += getattr(msg.usage, "output_tokens", 0)
            return j, it, parent, outs

        pend = []
        for j, it in enumerate(items):
            if (j, it) not in data_items:
                continue
            stats["items"] += 1
            parent = resolve_parent(item_text(it), pidx + 1, chunks)
            if parent is None:
                stats["sin_padre"] += 1
                continue
            pend.append((j, it, parent))
        with ThreadPoolExecutor(max_workers=4) as ex:
            resultados = list(ex.map(_gen_item, pend))
        for j, it, parent, outs in resultados:
            wl = " ".join(str(parent.get(k) or "") for k in
                          ("product_model", "manufacturer", "source_file"))
            n_item = 0
            for arm, text in outs:
                stats["gen"] += 1
                if _is_meta(text):
                    stats["meta_drop"] = stats.get("meta_drop", 0) + 1
                    continue
                ok, motivo = qa_statement(text, [it], wl)
                if not ok:
                    stats["qa_fail"] += 1
                    continue
                page_stmts.append(text)
                is_chaff = _is_chaff(text)
                if is_chaff:
                    stats["chaff"] += 1
                # contador POR-ITEM (MENOR del cross-model: len(rows) global dependía de
                # omisiones previas → ids no estables entre reruns)
                ancla = f"{sha}:{pidx}:{j}:{arm}:{n_item}"
                n_item += 1
                rows.append({
                    "id": str(uuid.uuid5(NAMESPACE, ancla)),
                    "content": text.replace(chr(0), "")[:8000],
                    "context": parent.get("context"),
                    "parent_id": parent["id"], "ingest_batch": batch,
                    "extraction_sha256": parent.get("extraction_sha256") or sha,
                    **{k: parent.get(k) for k in
                       ("product_model", "manufacturer", "source_file", "language",
                        "document_id", "section_title", "doc_type", "content_type",
                        "chunk_index")},
                    "page_number": pidx + 1,
                    "chaff": is_chaff,   # solo en el DUMP (el loader la descarta; F8)
                })
                if it.get("rows") is not None and len(sample) < 3:
                    sample.append({"marca": marca, "isPerfect": bool(it.get("isPerfectTable")),
                                   "text": text[:160]})
        cov = cobertura_pagina(items, page_stmts)
        if cov is not None:
            cov_by_page.append(cov)
            if cov < 1.0:
                stats.setdefault("uncovered_pages", []).append(pidx + 1)
    if to_dump and rows:
        # (s104 X1 CRÍTICO dúo) El pase corpus-wide JAMÁS inserta en chunks_v2 (el índice
        # compartido del NO-GO DEC-088): generación+QA → DUMP; la carga la hace SOLO el
        # loader A3 (tabla separada). Dump-before-anything = el activo caro queda a salvo.
        with open(to_dump, "a", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    if not dry and not to_dump:
        raise SystemExit(
            "insert directo a chunks_v2 RETIRADO (DEC-088/s104): usa --to-dump y el loader "
            "A3 (scripts/s104_a3_load.py). --dry sigue disponible.")
    if False:
        # (legacy T1, conservado como referencia histórica — inalcanzable)
        # idempotencia POR-DOC (dúo H4: el rollback global re-pagaba el tramo entero
        # tras un crash en el doc N): borrar SOLO lo previo de este doc+batch.
        httpx.delete(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                     headers={**_H, "Prefer": "return=minimal"},
                     params={"ingest_batch": f"eq.{batch}",
                             "source_file": f"eq.{source_file}"},
                     timeout=60).raise_for_status()
    if False and rows:
        from src.reingest.embed import embed as _embed
        texts = [(f"{r['context']}\n\n{r['content']}" if r.get("context") else r["content"])
                 for r in rows]
        embs = []
        for i in range(0, len(texts), 100):
            embs.extend(_embed(texts[i:i + 100], "document"))
        for r, e in zip(rows, embs):
            r["embedding"] = e
        poison: list = []
        for i in range(0, len(rows), 50):
            _insert_rows(rows[i:i + 50], poison)
        if poison:
            stats["filas_venenosas"] = len(poison)
            with open(f"evals/enunciados_poison_{tranche}.jsonl", "a", encoding="utf-8") as fh:
                for x in poison:
                    fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    cov_doc = sum(cov_by_page) / len(cov_by_page) if cov_by_page else None
    ci, co = _rate()
    stats["cost_usd"] = round(usage[0] / 1e6 * ci + usage[1] / 1e6 * co, 4)
    stats["tokens_in"], stats["tokens_out"] = usage
    return {"doc": source_file, "marca": marca, "insertables": len(rows),
            "cobertura": round(cov_doc, 3) if cov_doc is not None else None,
            "sample": sample, **stats}


def rollback(batch_prefix: str) -> int:
    r = httpx.delete(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                     headers={**_H, "Prefer": "return=minimal"},
                     params={"ingest_batch": f"like.{batch_prefix}*"}, timeout=120)
    r.raise_for_status()
    chk = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_H,
                    params={"select": "id", "ingest_batch": f"like.{batch_prefix}*",
                            "limit": "1"}, timeout=30)
    n = len(chk.json())
    print(f"[rollback {batch_prefix}] restantes: {n}")
    return 0 if n == 0 else 1


LEDGER = "evals/enunciados_ledger.json"


def _ledger_load() -> dict:
    if os.path.exists(LEDGER):
        return json.load(open(LEDGER, encoding="utf-8"))
    return {"docs": {}, "seeded_t1": False}


def _ledger_save(led: dict) -> None:
    json.dump(led, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def _seed_t1(led: dict) -> None:
    """(s104 F11 dúo) Pre-seed con los docs T1 (ya en prod, vintage Sonnet-p1): un T1-doc
    colado en otro tramo duplicaría filas servidas (el DELETE es por batch+doc)."""
    if led.get("seeded_t1"):
        return
    seen: dict = {}
    for line in open("evals/t1_surrogates_dump.jsonl", encoding="utf-8"):
        row = json.loads(line)
        seen.setdefault(row["source_file"], row.get("extraction_sha256") or "")
    for doc, sha in seen.items():
        led["docs"].setdefault(doc, {"sha": sha, "tranche": "T1", "vintage": "p1",
                                     "note": "pre-seed: ya en prod (s95 A3 load)"})
    led["seeded_t1"] = True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tranche")
    ap.add_argument("--docs", help="fichero con un source_file por línea")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--to-dump", action="store_true",
                    help="(s104 X1) generación+QA → evals/enunciados_dump_<tranche>.jsonl; "
                         "NUNCA inserta (la carga la hace el loader A3)")
    ap.add_argument("--resume", action="store_true",
                    help="salta docs ya presentes en el LEDGER con dump reconciliado (F7)")
    ap.add_argument("--model", default=None,
                    help="override del modelo LLM (exige --vintage distinto de p1)")
    ap.add_argument("--vintage", default="p1",
                    help="(s104 F4) vintage del batch: p1=Sonnet piloto, h1=Haiku, ...")
    ap.add_argument("--budget-usd", type=float, default=180.0,
                    help="(s104 F10) tope DURO de gasto acumulado del ledger")
    ap.add_argument("--rollback")
    a = ap.parse_args()
    if a.rollback:
        return rollback(a.rollback)
    assert a.tranche and a.docs, "--tranche y --docs son obligatorios"
    assert not (a.model and a.vintage == "p1"), (
        "--model exige --vintage distinto de p1 (el vintage es la traza del generador)")
    docs = [ln.strip() for ln in open(a.docs, encoding="utf-8") if ln.strip()]
    batch = f"enunciados-v1:{a.tranche}:{a.vintage}"
    dump_path = f"evals/enunciados_dump_{a.tranche}.jsonl" if a.to_dump else None
    if a.model:
        globals()["LLM_MODEL"] = a.model         # override declarado (vintage distinto)
    led = _ledger_load()
    _seed_t1(led)
    spent = sum((d.get("cost_usd") or 0) for d in led["docs"].values())
    client = anthropic.Anthropic()
    results = []
    dump_docs: set = set()
    if dump_path and os.path.exists(dump_path):
        for line in open(dump_path, encoding="utf-8"):
            try:
                dump_docs.add(json.loads(line).get("source_file"))
            except Exception:
                pass
    for i, doc in enumerate(docs):
        if spent > a.budget_usd:
            print(f"TOPE DE GASTO alcanzado (${spent:.2f} > ${a.budget_usd}) — STOP (F10); "
                  f"revisar ledger y relanzar con --resume")
            break
        if a.resume and doc in led["docs"]:
            entry = led["docs"][doc]
            reconciled = (entry.get("tranche") == "T1") or (doc in dump_docs) or a.dry
            if reconciled:
                print(f"[{i+1}/{len(docs)}] {doc[:44]:46} RESUME: en ledger "
                      f"({entry.get('tranche')}:{entry.get('vintage')}), saltado")
                results.append({"doc": doc, "skipped": True})
                continue
            print(f"[{i+1}/{len(docs)}] {doc[:44]:46} ledger SIN respaldo en dump -> re-procesa (F7)")
        res = process_doc(client, doc, a.tranche, a.dry, vintage=a.vintage,
                          to_dump=dump_path)
        results.append(res)
        if not res.get("error") and not a.dry:
            led["docs"][doc] = {"sha": sha_of(doc), "tranche": a.tranche,
                                "vintage": a.vintage, "items": res.get("items"),
                                "insertables": res.get("insertables"),
                                "chaff": res.get("chaff"),
                                "cost_usd": res.get("cost_usd")}
            spent += res.get("cost_usd") or 0
            _ledger_save(led)
        print(f"[{i+1}/{len(docs)}] {doc[:44]:46} ins={res.get('insertables','-'):4} "
              f"qa_fail={res.get('qa_fail','-')} chaff={res.get('chaff','-')} "
              f"cov={res.get('cobertura','-')} ${res.get('cost_usd','-')} "
              f"{res.get('error','')}")
    out = f"evals/enunciados_pass_{a.tranche}{'_dry' if a.dry else ''}.json"
    json.dump({"tranche": a.tranche, "batch": batch, "dry": a.dry,
               "prompt_vintage": a.vintage, "model": str(LLM_MODEL),
               "budget_usd": a.budget_usd, "spent_after": round(spent, 2),
               "results": results},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"-> {out} · gasto acumulado ledger: ${spent:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
