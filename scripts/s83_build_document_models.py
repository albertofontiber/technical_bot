#!/usr/bin/env python3
"""s83_build_document_models.py - PASO 2: construir las tablas normalizadas (BORRADOR para el duo).

Transform DETERMINISTA ($0, re-ejecutable) del JSONL crudo reconciliado -> dos tablas:
  - document_models   (1 fila = 1 producto fisico distinto por doc; arrastra TODOS sus identificadores)
  - document_identity (1 fila = 1 doc: marca/OEM/distribuidor/familia/idiomas/...)

Aplica la REGLA DE GRANULARIDAD (validada con Alberto, s83):
  R1. 1 registro = 1 producto fisico distinto.
  R2. canonical_model = nombre comercial limpio; aliases[] = SKU/part-number/descriptivo/base-sin-sufijo.
  R3. cadenas COMPUESTAS ("DS 5 / DS 10 - TAS", "MPS-24A/MPS-24AE") NUNCA se guardan -> se PARTEN.
      Split EVIDENCE-GATED: solo si las piezas estan atestiguadas por separado (en la otra extraccion o
      como alias-atestiguado). Asi NO se parte "DS 10 -3G/3D" (un solo modelo ATEX).
  R4. SKU + nombre comercial = UN registro (canonical=nombre, SKU en aliases).
  R5. variantes pedibles reales (DS 5 vs DS 10; -TF) -> registros SEPARADOS, role=secondary (enlazables).
  R6. reconciliacion: agree -> conjunto; superset -> UNION; granular-vs-comprimido -> el GRANULAR (split).
      Secundario hallado por UN solo modelo -> candidate=True (guardarrail precision>velocidad, no auto-acepta).

Solo procesa class_canon in {agree, superset} (985). Los 29 conflict quedan PENDIENTES de adjudicacion.
Read-only sobre el JSONL; escribe a evals/. NO toca la DB.
"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "evals" / "s83_full_extraction_merged.jsonl"
OUT_MODELS = ROOT / "evals" / "s83_document_models.jsonl"
OUT_IDENTITY = ROOT / "evals" / "s83_document_identity.jsonl"
OUT_SAMPLE = ROOT / "evals" / "s83_build_sample.md"

SEP_RE = re.compile(r"\s*[/+]\s*|\s+y\s+|\s+and\s+|\s+&\s+", re.IGNORECASE)
DIGITS_RE = re.compile(r"^[\d\-\s\.]+$")


def norm(m: str) -> str:
    s = (m or "").upper().strip()
    for sym in ("™", "®", "©", "�"):
        s = s.replace(sym, "")
    s = re.sub(r"\s*-\s*", "-", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def keyset(m: dict) -> set:
    ks = set()
    for v in (m.get("model"), m.get("canonical_model")):
        if v and norm(v):
            ks.add(norm(v))
    for a in (m.get("aliases") or []):
        if a and norm(a):
            ks.add(norm(a))
    return ks


def mkey(m: dict) -> set:
    """MERGE-key (Fix 1, dúo s83): SOLO {model, canonical} normalizados. Los aliases NUNCA son
    merge-key → no puentean hermanos distintos (DS 5≠DS 10, VSN-RP1r≠RP1r-Supra). Bajo precisión:
    sub-merge por formato es más seguro que over-merge cross-brand (ambos quedan findable)."""
    ks = set()
    for v in (m.get("model"), m.get("canonical_model")):
        if v and norm(v):
            ks.add(norm(v))
    return ks


def covered(res):
    if not isinstance(res, dict) or res.get("_error"):
        return []
    return res.get("covered_models", []) or []


# ---------- R3: split de compuestos, evidence-gated ----------
def attested_standalone(doc_objs):
    """Conjunto de norm(model)/norm(canonical) que aparecen como modelo STANDALONE (no-compuesto)."""
    att = set()
    for m in doc_objs:
        for v in (m.get("model"), m.get("canonical_model")):
            if v and not SEP_RE.search(v or ""):
                att.add(norm(v))
    return att


def split_compounds(o_objs, g_objs):
    """Devuelve la lista combinada de covered-objs con los COMPUESTOS partidos cuando las piezas
    estan atestiguadas por separado. Cada obj lleva _src (opus|gpt)."""
    all_objs = [dict(m, _src="opus") for m in o_objs] + [dict(m, _src="gpt") for m in g_objs]
    attested = attested_standalone(all_objs)
    out = []
    for m in all_objs:
        model = m.get("model") or ""
        if SEP_RE.search(model):
            # piezas candidatas: aliases cuyo norm esta atestiguado standalone y != norm(model)
            pieces = []
            for a in (m.get("aliases") or []):
                na = norm(a)
                if na and na != norm(model) and na in attested and not SEP_RE.search(a):
                    pieces.append(a)
            # dedup piezas por norm
            seen = set(); uniq = []
            for p in pieces:
                if norm(p) not in seen:
                    seen.add(norm(p)); uniq.append(p)
            if len(uniq) >= 2:
                for p in uniq:
                    out.append({**m, "model": p, "canonical_model": p,
                                "aliases": [model], "_split_from": model})
                continue
        out.append(m)
    return out


# ---------- agrupar por interseccion de keyset (union-find) ----------
def group_products(objs):
    n = len(objs)
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb
    keys = [mkey(m) for m in objs]
    for i in range(n):
        for j in range(i + 1, n):
            if keys[i] & keys[j]:
                union(i, j)
    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    return [[objs[i] for i in idxs] for idxs in groups.values()]


def is_clean_commercial(s: str) -> bool:
    if not s: return False
    if DIGITS_RE.match(s): return False           # SKU puro -> no canonical
    if SEP_RE.search(s): return False             # compuesto
    if len(s.split()) > 4 or len(s) > 34: return False  # frase descriptiva
    return True


def pick_canonical(group):
    cands = []
    for m in group:
        for v in (m.get("canonical_model"), m.get("model")):
            if v: cands.append(v)
    # 1) consenso: canonical que ambos src dieron como canonical_model
    canon_by_src = defaultdict(set)
    for m in group:
        if m.get("canonical_model"):
            canon_by_src[norm(m["canonical_model"])].add(m["_src"])
    consensus = [c for c, srcs in canon_by_src.items() if len(srcs) >= 2]
    if consensus:
        # devuelve la forma original (no-norm) de ese consenso
        for m in group:
            if m.get("canonical_model") and norm(m["canonical_model"]) in consensus:
                return m["canonical_model"]
    # 2) el comercial limpio mas corto
    clean = sorted({c for c in cands if is_clean_commercial(c)}, key=lambda x: (len(x), x))
    if clean: return clean[0]
    # 3) fallback: el model mas corto no-vacio
    return sorted(cands, key=lambda x: (len(x or ""), x or ""))[0] if cands else ""


def build_models(o_objs, g_objs):
    objs = split_compounds(o_objs, g_objs)
    out = []
    for group in group_products(objs):
        canonical = pick_canonical(group)
        ncanon = norm(canonical)
        aliases, seen = [], {ncanon}
        for m in group:
            for v in [m.get("model"), m.get("canonical_model"), *(m.get("aliases") or [])]:
                if v and norm(v) and norm(v) not in seen:
                    seen.add(norm(v)); aliases.append(v)
        srcs = {m["_src"] for m in group}
        roles = {m.get("role") for m in group}
        role = "primary" if "primary" in roles else "secondary"
        found_by = "both" if srcs == {"opus", "gpt"} else srcs.pop()
        candidate = (found_by != "both") and (role == "secondary")
        # categoria: la de un primary si hay, si no la mas larga
        cats = [m.get("category") for m in group if m.get("category")]
        prim_cats = [m.get("category") for m in group if m.get("role") == "primary" and m.get("category")]
        category = (prim_cats or sorted(cats, key=len, reverse=True) or [""])[0]
        certs = []
        for m in group:
            for c in (m.get("cert") or []):
                if c not in certs: certs.append(c)
        conf_rank = {"high": 3, "medium": 2, "low": 1}
        confidence = max((m.get("confidence") for m in group),
                         key=lambda c: conf_rank.get(c, 0), default="")
        prov = "body" if any(m.get("provenance") == "body" for m in group) else \
               (group[0].get("provenance") or "")
        ev = next((m.get("evidence") for m in group if m.get("role") == "primary" and m.get("evidence")),
                  next((m.get("evidence") for m in group if m.get("evidence")), None))
        split_from = next((m.get("_split_from") for m in group if m.get("_split_from")), None)
        rec = {"canonical_model": canonical, "aliases": aliases, "role": role,
               "candidate": candidate, "found_by": found_by, "category": category,
               "provenance": prov, "cert": certs, "confidence": confidence, "evidence": ev}
        if split_from: rec["split_from"] = split_from
        out.append(rec)
    # HIGIENE DE ALIASES (dúo s83): si un alias de un registro es el CANONICAL de OTRO registro del
    # mismo doc, quítalo de los aliases (residuo de contaminación cross-brand: VSN-RP1r+ deja de ser
    # alias de RP1r-Supra cuando VSN-RP1r+ es su propio registro). Preserva findability (ya hay registro).
    canon_norms = {norm(r["canonical_model"]) for r in out if r["canonical_model"]}

    def bridging_compound(a, own):
        # alias COMPUESTO ("AM2020/AFP1010") cuya(s) parte(s) son canonical de OTRO registro del doc:
        # es ambiguo (apunta a 2 productos) → no debe ser alias de ninguno.
        if not re.search(r"[A-Za-z0-9]\s*[/+]\s*[A-Za-z0-9]", a):
            return False
        parts = {norm(p) for p in re.split(r"[/+]", a) if norm(p)}
        return bool(parts & (canon_norms - {own}))

    for r in out:
        own = norm(r["canonical_model"])
        r["aliases"] = [a for a in r["aliases"]
                        if norm(a) not in (canon_norms - {own}) and not bridging_compound(a, own)]
    # primary primero, luego por canonical
    out.sort(key=lambda r: (r["role"] != "primary", r["candidate"], r["canonical_model"]))
    return out


# ---------- document_identity: reconciliar campos doc-level ----------
SQ_RANK = {"ok": 0, "partial": 1, "ocr_poor": 2, "scan": 3}


def reconcile_field(o, g, key, prefer_nonempty=True):
    ov, gv = (o or {}).get(key), (g or {}).get(key)
    ov = (ov or "").strip() if isinstance(ov, str) else ov
    gv = (gv or "").strip() if isinstance(gv, str) else gv
    low = {"", "unknown", None}
    if (str(ov).lower() in low) and (str(gv).lower() not in low): return gv, False
    if (str(gv).lower() in low) and (str(ov).lower() not in low): return ov, False
    if str(ov).lower() == str(gv).lower(): return ov, False
    return ov, True  # ambos no-vacios y difieren -> conflicto de campo (flag)


def build_identity(r):
    o, g = r.get("opus") or {}, r.get("gpt") or {}
    oid, gid = o.get("identity") or {}, g.get("identity") or {}
    # JC2 (dúo s83): solo flaggear los campos de identidad CONSECUENTES (brand/oem/distributor).
    # family_scope/doc_type/protocol se reconcilian pero NO se flaggean (ruido de sinónimos).
    conflicts = []
    brand, c = reconcile_field(oid, gid, "brand_on_doc");   conflicts += ["brand_on_doc"] if c else []
    oem, c_oem = reconcile_field(oid, gid, "oem_manufacturer"); conflicts += ["oem_manufacturer"] if c_oem else []
    dist, c = reconcile_field(oid, gid, "distributor");    conflicts += ["distributor"] if c else []
    fam, _ = reconcile_field(o, g, "family_scope")
    dtype, _ = reconcile_field(o, g, "doc_type")
    proto, _ = reconcile_field(o, g, "protocol")
    langs = sorted(set(o.get("languages") or []) | set(g.get("languages") or []))
    sq = max([o.get("source_quality") or "ok", g.get("source_quality") or "ok"],
             key=lambda x: SQ_RANK.get(x, 0))
    conf_rank = {"high": 3, "medium": 2, "low": 1}
    conf = min([o.get("confidence") or "low", g.get("confidence") or "low"],
               key=lambda c: conf_rank.get(c, 0))
    out = {"brand_on_doc": brand, "oem_manufacturer": oem, "distributor": dist,
           "family_scope": fam, "doc_type": dtype, "protocol": proto,
           "languages": langs, "source_quality": sq, "confidence": conf,
           "field_conflicts": conflicts}
    # OEM-AMBOS (dúo s83, hallazgo C): si los OEM difieren no-trivialmente, NO descartar el de GPT
    # (puede ser empresa genuinamente distinta: KAC vs Pittway) → guardar ambos para adjudicar.
    if c_oem:
        out["oem_manufacturer_alt"] = (gid.get("oem_manufacturer") or "").strip()
    return out


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    rows = [json.loads(l) for l in IN.read_text(encoding="utf-8").splitlines() if l.strip()]
    reconciled = [r for r in rows if r.get("class_canon") in ("agree", "superset")]

    n_models = 0; n_cand = 0; n_split = 0; docs_with_split = 0
    fm = OUT_MODELS.open("w", encoding="utf-8")
    fi = OUT_IDENTITY.open("w", encoding="utf-8")
    sample_docs = []
    for r in reconciled:
        models = build_models(covered(r.get("opus")), covered(r.get("gpt")))
        identity = build_identity(r)
        had_split = any("split_from" in m for m in models)
        n_split += sum(1 for m in models if "split_from" in m)
        docs_with_split += 1 if had_split else 0
        n_models += len(models); n_cand += sum(1 for m in models if m["candidate"])
        fm.write(json.dumps({"source_file": r["source_file"], "models": models}, ensure_ascii=False) + "\n")
        fi.write(json.dumps({"source_file": r["source_file"], **identity}, ensure_ascii=False) + "\n")
        sample_docs.append((r, models, identity, had_split))
    fm.close(); fi.close()

    print(f"docs reconciliados procesados: {len(reconciled)} (agree+superset; 29 conflict EXCLUIDOS)")
    print(f"document_models filas: {n_models}  | candidates: {n_cand} ({100*n_cand/max(n_models,1):.1f}%)")
    print(f"compuestos partidos (R3): {n_split} filas, en {docs_with_split} docs")
    print(f"-> {OUT_MODELS.name} / {OUT_IDENTITY.name}")

    # ---- muestra representativa para el duo (cubre los 5 mecanismos + edge cases) ----
    def doc_named(sub):
        return next((t for t in sample_docs if sub.lower() in t[0]["source_file"].lower()), None)
    picks = []
    for sub in ["085501821n_DS10", "15090SP", "55310008 Manual Tarjeta Modbus",
                "08895_04-multiling", "2X-LB", "MPS-24"]:
        t = doc_named(sub)
        if t and t not in picks: picks.append(t)
    # + docs con split, + docs con field_conflicts, + candidates
    for t in sample_docs:
        if t[3] and t not in picks and len([x for x in picks if x[3]]) < 6: picks.append(t)
    for t in sample_docs:
        if t[2]["field_conflicts"] and t not in picks and \
           len([x for x in picks if x[2]["field_conflicts"]]) < 5: picks.append(t)
    for t in sample_docs:
        if any(m["candidate"] for m in t[1]) and t not in picks and \
           len([x for x in picks if any(m["candidate"] for m in x[1])]) < 8: picks.append(t)

    lines = ["# Muestra de salida del transform (REGLA de granularidad) — para revisión del dúo\n",
             f"Procesados {len(reconciled)} docs reconciliados → {n_models} filas de modelo "
             f"({n_cand} candidates, {n_split} de split de compuestos).\n",
             "Cada doc: identidad reconciliada + lista de productos (canonical + aliases). "
             "Verificar: ¿R3 partió bien (sin over-split 3G/3D)? ¿canonical = nombre comercial limpio, "
             "SKU en aliases? ¿candidate marca bien las sobre-inclusiones de 1 solo modelo? ¿pierde info?\n"]
    for r, models, identity, _ in picks[:22]:
        lines.append(f"\n## `{r['source_file'][:60]}`  [{r['class_canon']}]")
        idl = f"  identity: brand={identity['brand_on_doc']!r} oem={identity['oem_manufacturer']!r}"
        if identity["field_conflicts"]:
            idl += f"  ⚠ field_conflicts={identity['field_conflicts']}"
        lines.append(idl)
        for m in models:
            tag = " ⟂candidate" if m["candidate"] else ""
            sp = f" ⟵split({m['split_from']})" if "split_from" in m else ""
            al = ", ".join(m["aliases"][:5]) + ("…" if len(m["aliases"]) > 5 else "")
            lines.append(f"    [{m['role'][:4]}/{m['found_by']}{tag}{sp}] **{m['canonical_model']}**  "
                         f"⟵ aliases: {al}")
    OUT_SAMPLE.write_text("\n".join(lines), encoding="utf-8")
    print(f"-> muestra dúo: {OUT_SAMPLE.name} ({len(picks[:22])} docs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
