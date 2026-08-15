# -*- coding: utf-8 -*-
"""s322e — Split ZXr-A/ZXr-P ≠ ZXR50A/ZXR50P (adjudicado por Alberto, 14-ago).

Su veredicto con el MIE-MI-440 en la mano: «ZXR50A/P son los repetidores de la
central ZX50, mientras que los ZXrA/P lo son de [DXc/DX/ZXe/ZXSe], así que son
productos diferentes». Deshace el colapso antiguo (una sesión pasada tagueó el
manual ZXr-A/ZXr-P MIE-MI-431rv2 como ZXR50A/ZXR50P):

1. products: nacen `morley:zxr-a` y `morley:zxr-p` (adjudicación directa —
   el candidate-birth lo cubre el sí de Alberto).
2. doc_map: MIE-MI-431rv2 → [zxr-a, zxr-p]; la FAQ de puesta en marcha →
   zxr-a (su secundaria idr6a se conserva). MIE-MI-440 NO se toca (ZXR50A/P
   reales, panel ZX50).
3. chunks (mecánica T3: backup + CAS por-chunk + conteo): MIE-MI-431rv2
   «ZXR50A/ZXR50P»→«ZXr-A/ZXr-P»; FAQ «ZXrA»→«ZXr-A». POR DOCUMENTO — los
   chunks de MIE-MI-440 conservan su pm ZXR50A/ZXR50P.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl, write_jsonl  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}",
      "Content-Type": "application/json"}
PROV = ("adjudicado por Alberto 14-ago-2026 (s322e): ZXr-A/ZXr-P son los "
        "repetidores de DXc/DX/ZXe/ZXSe y ZXR50A/ZXR50P los del panel ZX50 — "
        "productos DIFERENTES (manuales separados MIE-MI-431 vs MIE-MI-440; "
        "tablas de compatibilidad DXc/MIE-MP-520/MIE-MI-530/MIE-MI-600)")
FAQ = "Puesta-en-marcha-repetidor-ZXrA-en-central-CONNEXION"
MANUAL = "MIE-MI-431rv2"

# 1) products
products = _read_jsonl(CATALOG_DIR / "products.jsonl")
ids = {r["id"] for r in products}
nuevos = []
for pid, canonical, hint in (("morley:zxr-a", "ZXr-A", "repetidor (con teclado)"),
                             ("morley:zxr-p", "ZXr-P", "repetidor (sin teclado)")):
    if pid in ids:
        continue
    fila = {"id": pid, "canonical_model": canonical, "estado": "activo",
            "vendido_bajo": ["Morley-IAS"], "categoria": hint,
            "added_by": "s322e-adjudicacion", "provenance": PROV}
    products.append(fila)
    nuevos.append(pid)

# 1-bis) aliases: el colapso de s78 declaraba ZXr-A/ZXr-P como «variante
# tipográfica» de ZXR50A/P — la adjudicación de hoy lo REVOCA (la puerta del
# catálogo cazó la colisión). Se retiran; los nombres pasan a ser canónicos
# de los productos nuevos.
aliases = _read_jsonl(CATALOG_DIR / "aliases.jsonl")
alias_retirados = [a for a in aliases if a.get("alias") in ("ZXr-A", "ZXr-P")]
aliases = [a for a in aliases if a.get("alias") not in ("ZXr-A", "ZXr-P")]

# 2) doc_map
doc_map = _read_jsonl(CATALOG_DIR / "doc_map.jsonl")
remapeos = []
for r in doc_map:
    sf = r.get("source_file")
    if sf == MANUAL:
        antes = [e["id"] for e in r["entries"]]
        assert sorted(antes) == ["morley:zxr50a", "morley:zxr50p"], antes
        r["entries"] = [
            {"id": "morley:zxr-a", "role": "primary", "scope": "doc",
             "provenance": PROV},
            {"id": "morley:zxr-p", "role": "primary", "scope": "doc",
             "provenance": PROV}]
        remapeos.append({"doc": sf, "antes": antes,
                         "despues": ["morley:zxr-a", "morley:zxr-p"]})
    elif sf == FAQ:
        antes = [e["id"] for e in r["entries"]]
        for e in r["entries"]:
            if e["id"] == "morley:zxr50a":
                e["id"] = "morley:zxr-a"
                e["provenance"] = PROV
        remapeos.append({"doc": sf, "antes": antes,
                         "despues": [e["id"] for e in r["entries"]]})
assert len(remapeos) == 2, remapeos

write_jsonl("aliases", aliases)
write_jsonl("products", products)
write_jsonl("doc_map", doc_map)

# 3) chunks (T3 por documento)
RETAGS = [(MANUAL, "ZXR50A/ZXR50P", "ZXr-A/ZXr-P"),
          (FAQ, "ZXrA", "ZXr-A")]
backup, ops = [], []
with abierto(timeout=30.0) as c:
    for sf, pm_prev, pm_nuevo in RETAGS:
        r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                  params={"select": "id,product_model",
                          "source_file": f"eq.{sf}",
                          "product_model": f"eq.{pm_prev}",
                          "order": "id.asc", "limit": "1000"})
        r.raise_for_status()
        objetivo = r.json()
        for ch in objetivo:
            backup.append({"id": ch["id"], "source_file": sf,
                           "product_model_prev": ch["product_model"]})
        afectadas = 0
        for ch in objetivo:
            rr = c.patch(f"{SB}/rest/v1/chunks_v2",
                         headers={**HS, "Prefer": "return=representation"},
                         params={"id": f"eq.{ch['id']}",
                                 "product_model": f"eq.{pm_prev}"},
                         json={"product_model": pm_nuevo})
            rr.raise_for_status()
            afectadas += len(rr.json())
        assert afectadas == len(objetivo), (sf, afectadas, len(objetivo))
        ops.append({"doc": sf, "pm_prev": pm_prev, "pm_nuevo": pm_nuevo,
                    "chunks": afectadas})
        # verificación: MIE-MI-440 intacto
    r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
              params={"select": "product_model", "source_file": "eq.MIE-MI-440",
                      "limit": "100"})
    pms_440 = sorted({x.get("product_model") for x in r.json()})

utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
(ROOT / "evals" / "s322_e3_zxra_split_v1.json").write_text(
    json.dumps({"que_es": PROV, "utc": utc, "products_nuevos": nuevos,
                "aliases_retirados": alias_retirados,
                "remapeos": remapeos, "retags": ops,
                "mie_mi_440_pms_intactos": pms_440,
                "backup": backup,
                "reversible": "restaurar pms del backup + deshacer remapeos + "
                              "retirar productos nuevos"},
               ensure_ascii=False, indent=1), encoding="utf-8")
print(f"products nuevos: {nuevos}")
for m in remapeos:
    print(f"doc_map: {m['doc']}: {m['antes']} → {m['despues']}")
for o in ops:
    print(f"retag: {o['doc']}: {o['pm_prev']!r} → {o['pm_nuevo']!r} "
          f"({o['chunks']} chunks)")
print(f"MIE-MI-440 pms (deben seguir ZXR50A/ZXR50P): {pms_440}")
