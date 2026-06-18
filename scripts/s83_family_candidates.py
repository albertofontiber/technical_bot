#!/usr/bin/env python3
"""s83_family_candidates.py — AUTO-GENERA candidatos de familia desde el corpus (escalable a 30+).

Rumbo BP (dúo #12 + decisión de Alberto s83): declarar familias a mano NO escala, pero la parte
que no escala es IRREDUCIBLE. Este script genera los CANDIDATOS automáticos; el humano (Alberto)
solo CONFIRMA/VETA lo irreducible (shared_docs que cruzan, paraguas→variantes, OEM/marca).

Señal manufacturer-agnóstica y corpus-driven (crece con el corpus, no con horas-de-Alberto):
dos modelos pertenecen a la misma familia si co-ocurren en el mismo `source_file` (un manual cubre
la familia) o aparecen juntos en un `product_model` COMPUESTO ('ZX2e/ZX5e' = MULTI-LABEL nativo,
imprescindible — Alberto s83). Componentes conexos del grafo de co-ocurrencia = familias candidatas.

Read-only (cero mutación). Output: evals/s83_family_candidates.yaml para la review primera-pasada.
"""
from __future__ import annotations
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

os.environ["CHUNKS_TABLE"] = "chunks_v2"
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402

H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
CH = f"{SUPABASE_URL}/rest/v1/chunks_v2"
# separadores de pm compuesto (multi-label literal en el tag)
_SPLIT = re.compile(r"\s*[/+&]\s*|\s*,\s*|\s+y\s+", re.IGNORECASE)


def split_models(pm: str) -> list[str]:
    """MULTI-LABEL: 'ZX2e/ZX5e' → ['ZX2e','ZX5e']; 'ID3000' → ['ID3000']."""
    parts = [p.strip() for p in _SPLIT.split(pm or "") if p.strip()]
    return parts or ([pm.strip()] if pm and pm.strip() else [])


def fetch_doc_identity() -> dict:
    """source_file → {models:set, manufacturers:set}. Pagina sobre chunks_v2."""
    docs: dict = defaultdict(lambda: {"models": set(), "manufacturers": set()})
    offset, page = 0, 1000
    while True:
        r = httpx.get(CH, headers=H, params={
            "select": "product_model,source_file,manufacturer",
            "limit": str(page), "offset": str(offset)}, timeout=90)
        r.raise_for_status()
        rows = r.json()
        if not rows:
            break
        for row in rows:
            sf, pm, mfr = row.get("source_file"), row.get("product_model"), row.get("manufacturer")
            if not sf or not pm or pm == "unknown":
                continue
            for m in split_models(pm):
                docs[sf]["models"].add(m)
            if mfr:
                docs[sf]["manufacturers"].add(mfr)
        offset += page
        if len(rows) < page:
            break
    return docs


class UF:
    """Union-Find para componentes conexos."""
    def __init__(self) -> None:
        self.p: dict = {}

    def find(self, x: str) -> str:
        self.p.setdefault(x, x)
        root = x
        while self.p[root] != root:
            root = self.p[root]
        while self.p[x] != root:
            self.p[x], x = root, self.p[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    docs = fetch_doc_identity()
    uf = UF()
    model_docs: dict = defaultdict(set)
    model_mfr: dict = defaultdict(set)
    for sf, d in docs.items():
        models = sorted(d["models"])
        for m in models:
            model_docs[m].add(sf)
            model_mfr[m] |= d["manufacturers"]
            uf.find(m)
        for i in range(len(models)):
            for j in range(i + 1, len(models)):
                uf.union(models[i], models[j])
    fams: dict = defaultdict(set)
    for m in model_docs:
        fams[uf.find(m)].add(m)

    candidates = []
    for members_set in fams.values():
        members = sorted(members_set)
        mfrs = sorted(set().union(*[model_mfr[m] for m in members]))
        sf_members: dict = defaultdict(set)
        for m in members:
            for sf in model_docs[m]:
                sf_members[sf].add(m)
        shared = sorted(sf for sf, ms in sf_members.items() if len(ms) >= 2)
        multilabel = sorted(sf for sf in sf_members
                            if len(docs[sf]["models"]) >= 2)
        all_docs = set().union(*[model_docs[m] for m in members])
        conf = "high" if (len(members) >= 2 and shared) else (
            "medium" if len(members) >= 2 else "low")
        candidates.append({
            "members": members,
            "manufacturers": mfrs,
            "n_docs": len(all_docs),
            "shared_docs": shared[:12],
            "multilabel_docs": multilabel[:12],
            "confidence": conf,
            "cross_manufacturer": len(mfrs) > 1,
        })
    candidates.sort(key=lambda c: (-len(c["members"]), c["members"][0]))
    multi = [c for c in candidates if len(c["members"]) >= 2]
    out = {
        "_meta": "auto-candidatos de familia (s83); REVIEW humano confirma/veta lo irreducible",
        "n_families": len(candidates),
        "n_multi_member": len(multi),
        "n_cross_manufacturer": sum(1 for c in candidates if c["cross_manufacturer"]),
        "n_high_conf": sum(1 for c in candidates if c["confidence"] == "high"),
        "families": candidates,
    }
    OUT = ROOT / "evals" / "s83_family_candidates.yaml"
    OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False), encoding="utf-8")

    print(f"docs con identidad: {len(docs)} | modelos distintos: {len(model_docs)}")
    print(f"familias candidatas: {len(candidates)} ({len(multi)} con ≥2 members)")
    print(f"  alta confianza (≥2 members + shared_docs): {out['n_high_conf']}")
    print(f"  cross-manufacturer (OEM/colisión → REVISAR a mano): {out['n_cross_manufacturer']}")
    print("\nTop familias multi-member (para la review):")
    for c in multi[:20]:
        xm = " ⚠XMFR" if c["cross_manufacturer"] else ""
        print(f"  [{c['confidence']:6}] {'/'.join(c['manufacturers'])[:22]:22} "
              f"{c['members']} | docs={c['n_docs']} shared={len(c['shared_docs'])}{xm}")
    print(f"\n→ {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
