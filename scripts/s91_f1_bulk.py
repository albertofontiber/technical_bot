#!/usr/bin/env python3
"""s91_f1_bulk.py — F1 BULK: carga de las 31 marcas al catálogo canónico (contrato F0/DEC-079).

Generaliza el pipeline endurecido del slice F1a (s90: match delimitado, filtros a canonical Y
aliases, candidate-por-blast-radius, reconciliación de colisiones, dedupe por document_id) a la
semilla COMPLETA (1014 docs / ~2761 menciones), con:

1. **brand_map** (catalog_gt.BRAND_MAP): 96 formas → ~31 namespaces; los GRUPO_BRANDS
   (Honeywell/HLSI/unknown/vacío, ~215 docs) se resuelven por CONTEXTO en 2ª pasada — si la
   mayoría de los tokens del doc ya viven bajo UN namespace real → ese; si no → 'unresolved'
   (todo candidate = no consumible). NUNCA se fabrica marca.
2. **gt nivel-1** (catalog_gt): Morley (s78+QA s90) + FAAST (s80/D3) + CAD-150 (Detnov) —
   transcripción fiel, reserva de tokens, gana siempre.
3. **docrel language-variant**: pares ES/EN/PT/FR por heurística de stem conservadora
   (nadie los consume en v0; habilitan prefer-ES/dedup en F2).
4. **QA-RIESGO pre-filtrado** para Alberto (~30-60): tokens multi-namespace REALES tras
   normalizar marcas (¿rebrand/OEM?), brands candidate, docs unresolved.

Salida: data/catalog/*.jsonl + evals/s91_f1_qa_riesgo.md. NADA fuera de branch.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import httpx
import catalog_store as cs
import catalog_gt as gt
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

SEED_IDENT = ROOT / "evals" / "s83_document_identity_final.jsonl"
SEED_MODELS = ROOT / "evals" / "s83_document_models_final.jsonl"
QA_OUT = ROOT / "evals" / "s91_f1_qa_riesgo.md"
H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}

NOT_A_PRODUCT_RX = re.compile(r"(/| y | e | and | or )", re.IGNORECASE)
GENERIC_LABELS = {"zx", "dx", "vsn", "zxe", "zxse", "dxc", "morley", "morleyias", "vision",
                  "dimension", "connexion", "lite", "plus", "max", "agile", "eco2000",
                  "notifier", "honeywell", "kidde", "aritech", "vesda", "faast", "detnov",
                  "series", "serie", "range", "system", "sistema"}
GENERIC_WORDS_RX = re.compile(
    r"^(impresora|placa( de lazo)?|gateway|pasarela|tarjeta|central(es)?|detector(es)?|sirena|"
    r"panel(es)?|repetidor|modulo|módulo|fuente|llave( opcional)?|base|zocalo|zócalo|rs-?232|"
    r"rs-?485|printer|loop card|key|power supply|module|sounder|beacon|strobe|manual|kit|"
    r"accesorio|accessory|software|cable|bater[ií]a|battery)\b", re.IGNORECASE)


def slug(model: str) -> str:
    s = model.strip().lower()
    s = re.sub(r"[\s/]+", "-", s)
    s = re.sub(r"[^a-z0-9._+-]", "", s)
    return s.strip("-.")


def not_a_product(label: str) -> str | None:
    if NOT_A_PRODUCT_RX.search(label):
        return "combinada/familia"
    if cs.norm_token(label) in GENERIC_LABELS:
        return "término-familia/marca"
    if GENERIC_WORDS_RX.match(label.strip()):
        return "sustantivo/estándar"
    return None


LANG_SUFFIX_RX = re.compile(r"[\s_-]*(ES|EN|PT|FR|IT|DE|I|P)$", re.IGNORECASE)


def lang_stem(src: str) -> str:
    """Stem sin marcador de idioma (heurística CONSERVADORA: solo sufijo final corto)."""
    return LANG_SUFFIX_RX.sub("", src.strip())


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ident = [json.loads(l) for l in SEED_IDENT.read_text(encoding="utf-8").splitlines() if l.strip()]
    models_by_src = {r["source_file"]: r for r in
                     (json.loads(l) for l in SEED_MODELS.read_text(encoding="utf-8").splitlines() if l.strip())}
    print(f"[semilla] docs: {len(ident)}")

    # ── document_id (match por stem normalizado, delimitado) ──
    with httpx.Client(timeout=60) as c:
        rows, offset = [], 0
        while True:
            page = c.get(f"{SUPABASE_URL}/rest/v1/documents", headers=H,
                         params={"select": "id,source_pdf_filename,language", "limit": "1000",
                                 "offset": str(offset)}).json()
            assert isinstance(page, list), f"documents SELECT falló: {page}"
            rows.extend(page)
            if len(page) < 1000:
                break
            offset += 1000
    _stem = lambda fn: re.sub(r"\.pdf$", "", fn or "", flags=re.IGNORECASE)
    docid_by_norm = {cs.norm_token(_stem(r["source_pdf_filename"])): (r["id"], _stem(r["source_pdf_filename"]))
                     for r in rows if r.get("source_pdf_filename")}
    doclang_by_id = {r["id"]: (r.get("language") or "") for r in rows}
    docid_by_src = {}
    for doc in ident:
        hit = docid_by_norm.get(cs.norm_token(doc["source_file"]))
        if hit:
            docid_by_src[doc["source_file"]] = hit[0]

    def find_docids(prefix: str) -> list[tuple[str, str]]:
        p = cs.norm_token(prefix)
        return [(did, src) for norm, (did, src) in docid_by_norm.items()
                if norm.startswith(p) and not (len(norm) > len(p) and norm[len(p)].isdigit())]

    print(f"[DB] documents: {len(rows)} | semilla matcheada: {len(docid_by_src)}/{len(ident)}")

    qa: dict[str, list[str]] = defaultdict(list)

    # ── namespace por doc: brand_map directo; GRUPO → contextual (2ª pasada) ──
    def brand_ns(doc) -> tuple[str | None, str]:
        b = (doc.get("brand_on_doc") or "(vacio)").strip()
        if b in gt.GRUPO_BRANDS:
            return None, "grupo"
        if b in gt.BRAND_MAP:
            return gt.BRAND_MAP[b]
        qa["brand SIN mapear (añadir a BRAND_MAP)"].append(f"`{b}` (doc {doc['source_file'][:45]})")
        return "unresolved", "candidate"

    ns_by_src: dict[str, tuple[str, str]] = {}
    grupo_docs = []
    for doc in ident:
        ns, tier = brand_ns(doc)
        if ns is None:
            grupo_docs.append(doc)
        else:
            ns_by_src[doc["source_file"]] = (ns, tier)

    # pasada 1: índice token→namespaces de docs con marca clara
    tok_ns: dict[str, Counter] = defaultdict(Counter)
    for doc in ident:
        if doc["source_file"] not in ns_by_src:
            continue
        ns = ns_by_src[doc["source_file"]][0]
        for m in (models_by_src.get(doc["source_file"], {}).get("models") or []):
            cm = (m.get("canonical_model") or "").strip()
            if cm:
                tok_ns[cs.norm_token(cm)][ns] += 1
    # pasada 2: docs de grupo → namespace por mayoría de sus tokens
    n_ctx = n_unres = 0
    for doc in grupo_docs:
        votes: Counter = Counter()
        for m in (models_by_src.get(doc["source_file"], {}).get("models") or []):
            cm = (m.get("canonical_model") or "").strip()
            for ns, cnt in tok_ns.get(cs.norm_token(cm), {}).items():
                if ns != "unresolved":
                    votes[ns] += cnt
        if votes and votes.most_common(1)[0][1] >= 2:
            ns_by_src[doc["source_file"]] = (votes.most_common(1)[0][0], "contextual")
            n_ctx += 1
        else:
            ns_by_src[doc["source_file"]] = ("unresolved", "candidate")
            n_unres += 1
    print(f"[brands] claras={len(ident)-len(grupo_docs)} | grupo→contextual={n_ctx} | unresolved={n_unres}")

    # ── gt (reserva) ──
    products = {p["id"]: p for p in gt.gt_products()}
    aliases = {cs.norm_token(a["alias"]): a for a in gt.gt_aliases()}
    reserved = {cs.norm_token(p["canonical_model"]) for p in products.values()}
    reserved |= {cs.norm_token(u["termino"]) for u in gt.gt_umbrellas()}
    reserved |= {cs.norm_token(h["termino"]) for h in gt.gt_homonyms()}
    reserved |= set(aliases)

    # ── semilla → productos/aliases ──
    n_prod = n_alias = 0
    for doc in ident:
        src = doc["source_file"]
        if any(cs.norm_token(src).startswith(cs.norm_token(ig)) for ig in gt.GT90_IGNORED_DOCS):
            continue
        ns, tier = ns_by_src[src]
        forced_cand = tier in ("candidate",) or ns == "unresolved"
        for m in (models_by_src.get(src, {}).get("models") or []):
            cm = (m.get("canonical_model") or "").strip()
            if not cm:
                continue
            key = cs.norm_token(cm)
            if key in reserved or key in gt.GT90_BLOCKED:
                continue
            why = not_a_product(cm)
            if why:
                continue  # masivo — no ensucia la cola QA del bulk; queda en el reporte agregado
            pid = f"{ns}:{slug(cm)}"
            if pid in products:
                if m.get("found_by") == "both" and products[pid].get("candidate") and not forced_cand:
                    products[pid]["candidate"] = False
                    products[pid]["provenance"] += " | promoted:both"
                continue
            products[pid] = {
                "id": pid, "canonical_model": cm,
                "vendido_bajo": [(doc.get("brand_on_doc") or ns).strip() or ns],
                "estado": "activo",
                "candidate": forced_cand or m.get("found_by") != "both",
                "provenance": f"s83:{src[:55]} (brand-tier={tier})", "added_by": "f1-bulk",
            }
            n_prod += 1
            for al in (m.get("aliases") or []):
                akey = cs.norm_token(al)
                if not akey or akey in reserved or akey in gt.GT90_BLOCKED or akey in aliases:
                    continue
                if not_a_product(al):
                    continue
                tipo = "numero-de-parte" if re.search(r"\d{4,}", al) else "nombre-largo"
                aliases[akey] = {"alias": al, "id": pid, "tipo": tipo,
                                 "provenance": f"s83:{src[:55]}", "added_by": "f1-bulk"}
                n_alias += 1
    # promociones P7 (QA s90)
    for pid, note in gt.GT90_PROMOTE.items():
        if pid in products:
            products[pid]["candidate"] = False
            products[pid]["categoria"] = note.split(" (")[0]
            products[pid]["provenance"] += f" | {gt.GT90} P7"
    print(f"[semilla] productos: {n_prod} | aliases: {n_alias}")

    # ── MERGE TIPOGRÁFICO same-namespace (la metadata-inconsistency #49: AFP-400≡AFP400) ──
    # Mismo namespace + mismo token normalizado = MISMO producto → fusión mecánica segura.
    # Superviviente por prioridad: (1) gt, (2) id referenciado por gt (umbrellas/homonyms/
    # relations/doc_map — sus ids son constantes), (3) orden estable. id_remap GLOBAL después.
    gt_referenced: set[str] = set()
    for u in gt.gt_umbrellas():
        gt_referenced.update(u["ids"])
    for h in gt.gt_homonyms():
        gt_referenced.update(h["ids"])
    for r in gt.gt_relations():
        gt_referenced.update((r["origen"], r["destino"]))
    for _, entries in gt.gt_doc_map():
        gt_referenced.update(i for i, _ in entries)

    by_ns_tok: dict[tuple, list[str]] = defaultdict(list)
    for pid, p in products.items():
        by_ns_tok[(pid.split(":")[0], cs.norm_token(p["canonical_model"]))].append(pid)
    id_remap: dict[str, str] = {}
    n_typo = 0
    for (ns, tok), pids in by_ns_tok.items():
        if len(pids) < 2:
            continue
        pids = sorted(pids, key=lambda x: (products[x].get("added_by") != "f1-gt",
                                           x not in gt_referenced, x))
        keep = pids[0]
        for other in pids[1:]:
            o = products.pop(other)
            id_remap[other] = keep
            if not o.get("candidate"):
                products[keep]["candidate"] = False
            products[keep]["provenance"] += f" | typo-merge:{o['canonical_model']}"
            ak = cs.norm_token(o["canonical_model"])
            if ak not in aliases and ak != cs.norm_token(products[keep]["canonical_model"]):
                aliases[ak] = {"alias": o["canonical_model"], "id": keep,
                               "tipo": "variante-tipografica",
                               "provenance": "f1-bulk typo-merge (#49)", "added_by": "f1-bulk"}
            n_typo += 1

    def remap(pid: str) -> str:
        while pid in id_remap:
            pid = id_remap[pid]
        return pid

    for a in aliases.values():
        a["id"] = remap(a["id"])
    print(f"[typo-merge] {n_typo} fusiones same-namespace (#49); remap global aplicado")

    # ── CROSS-NAMESPACE (posible rebrand/OEM): jamás merge auto → todos candidate +
    #    homónimo candidate (bloquea exact → fail-open) + QA-riesgo ──
    tok_all: dict[str, list[str]] = defaultdict(list)
    for pid, p in products.items():
        tok_all[cs.norm_token(p["canonical_model"])].append(pid)
    auto_homonyms = []
    for tok, pids in tok_all.items():
        nss = {x.split(":")[0] for x in pids} - {"unresolved"}   # unresolved = ausencia de marca,
        if len(nss) < 2:                                         # NO cuenta como colisión (fix DXc)
            continue
        pids = [x for x in pids if not x.startswith("unresolved:")]
        gt_pids = [x for x in pids if products[x].get("added_by") == "f1-gt"]
        if gt_pids:   # el gt manda: los demás candidate; sin homónimo auto (el gt ya resuelve)
            for x in pids:
                if x not in gt_pids:
                    products[x]["candidate"] = True
                    products[x]["provenance"] += " | x-brand-vs-gt→candidate"
            continue
        for x in pids:
            products[x]["candidate"] = True
            products[x]["provenance"] += " | x-brand→candidate"
        auto_homonyms.append({"termino": products[pids[0]]["canonical_model"], "ids": sorted(pids),
                              "politica": "fail-open", "candidate": True,
                              "provenance": "f1-bulk auto: token multi-namespace (¿rebrand/OEM?) → QA",
                              "added_by": "f1-bulk"})
        qa["token en VARIOS namespaces (¿rebrand/OEM?) → candidate+homónimo, adjudicar"].append(
            f"`{tok}` → {sorted(pids)}")
    print(f"[x-brand] {len(auto_homonyms)} homónimos-candidate auto")

    # reconciliación alias↔canonical (la clase ZXr-A/DX2)
    canon_norms = {cs.norm_token(p["canonical_model"]): p["id"] for p in products.values()}
    n_recon = 0
    for akey in list(aliases):
        owner = canon_norms.get(akey)
        if owner and owner != aliases[akey]["id"]:
            a = aliases.pop(akey)
            qa["colisión alias↔canonical (¿mismo producto? adjudicar)"].append(
                f"alias `{a['alias']}`→{a['id']} vs canonical de `{owner}`")
            n_recon += 1

    # ── doc_map (gt delimitado + semilla, dedupe por document_id) ──
    doc_map_by_id: dict[str, dict] = {}
    for prefix, entries in gt.gt_doc_map():
        for did, src in find_docids(prefix):
            if did not in doc_map_by_id:
                doc_map_by_id[did] = {"document_id": did, "source_file": src,
                                      "entries": [{"id": i, "role": r, "scope": "doc",
                                                   "provenance": "gt (catalog_gt.gt_doc_map)"}
                                                  for i, r in entries]}
    pid_by_norm = {cs.norm_token(p["canonical_model"]): p["id"] for p in products.values()}
    pid_by_norm.update({k: a["id"] for k, a in aliases.items()})
    n_unmapped = 0
    for doc in ident:
        src = doc["source_file"]
        did = docid_by_src.get(src)
        if not did or did in doc_map_by_id:
            continue
        entries = []
        for m in (models_by_src.get(src, {}).get("models") or []):
            cm = (m.get("canonical_model") or "").strip()
            pid = pid_by_norm.get(cs.norm_token(cm))
            if pid and not not_a_product(cm):
                entries.append({"id": pid, "role": m.get("role") or "secondary", "scope": "doc",
                                "provenance": f"s83 found_by={m.get('found_by')}"})
        if entries:
            doc_map_by_id[did] = {"document_id": did, "source_file": src, "entries": entries}
        else:
            n_unmapped += 1

    # ── docrel language-variant (heurística de stem conservadora) ──
    by_stem: dict[str, list[str]] = defaultdict(list)
    for src, did in docid_by_src.items():
        st = cs.norm_token(lang_stem(src))
        if st:
            by_stem[st].append(did)
    docrel = []
    for st, dids in by_stem.items():
        dids = sorted(set(dids))
        if 2 <= len(dids) <= 4:                       # pares/tríos plausibles; >4 = stem genérico
            langs = {doclang_by_id.get(d, "") for d in dids}
            if len(langs) > 1:                         # idiomas DISTINTOS en DB = señal fuerte
                for i in range(len(dids) - 1):
                    docrel.append({"doc_a": dids[i], "doc_b": dids[i + 1],
                                   "tipo": "language-variant-of",
                                   "provenance": f"f1-bulk stem-heurística ({st[:30]}) + language DB"})
    print(f"[doc_map] {len(doc_map_by_id)} docs | sin-entries: {n_unmapped} | docrel lang-pairs: {len(docrel)}")

    # ── escribir + validar (remap aplicado a TODAS las colecciones) ──
    umbrellas_out = []
    for u in gt.gt_umbrellas():
        u = dict(u); u["ids"] = [remap(i) for i in u["ids"]]
        umbrellas_out.append(u)
    homonyms_out = []
    for h in gt.gt_homonyms() + sorted(auto_homonyms, key=lambda x: x["termino"]):
        h = dict(h); h["ids"] = [remap(i) for i in h["ids"]]
        if h.get("politica", "").startswith("prefer:"):
            h["politica"] = "prefer:" + remap(h["politica"].split(":", 1)[1])
        homonyms_out.append(h)
    relations_out = []
    for r in gt.gt_relations():
        r = dict(r); r["origen"] = remap(r["origen"]); r["destino"] = remap(r["destino"])
        relations_out.append(r)
    for dm in doc_map_by_id.values():
        for e in dm["entries"]:
            e["id"] = remap(e["id"])
    cs.write_jsonl("products", sorted(products.values(), key=lambda r: r["id"]), validate_after=False)
    cs.write_jsonl("aliases", sorted(aliases.values(), key=lambda r: cs.norm_token(r["alias"])), validate_after=False)
    cs.write_jsonl("umbrellas", umbrellas_out, validate_after=False)
    cs.write_jsonl("homonyms", homonyms_out, validate_after=False)
    cs.write_jsonl("relations", relations_out, validate_after=False)
    cs.write_jsonl("doc_map", sorted(doc_map_by_id.values(), key=lambda r: r["source_file"]), validate_after=False)
    cs.write_jsonl("docrel", docrel, validate_after=False)
    errs = cs.validate()
    print(f"[validate] {len(errs)} error(es)")
    for e in errs[:15]:
        print("  [ERROR]", e)

    n_cand = sum(1 for p in products.values() if p.get("candidate"))
    ns_counts = Counter(p["id"].split(":")[0] for p in products.values())
    lines = ["# s91 · F1 bulk — QA de RIESGO (pre-filtrado para Alberto)\n",
             f"products: {len(products)} ({n_cand} candidate) · aliases: {len(aliases)} · "
             f"umbrellas: {len(gt.gt_umbrellas())} · homonyms: {len(gt.gt_homonyms())} · "
             f"doc_map: {len(doc_map_by_id)} · docrel: {len(docrel)}\n",
             "## Namespaces (top): " + ", ".join(f"{k}:{v}" for k, v in ns_counts.most_common(15))]
    for reason, items in qa.items():
        lines.append(f"\n## {reason} ({len(items)})")
        lines.extend(f"- {i}" for i in items[:30])
        if len(items) > 30:
            lines.append(f"- … (+{len(items)-30})")
    QA_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[written] {QA_OUT.name}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
