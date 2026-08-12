# -*- coding: utf-8 -*-
"""s320 E1 — Generador de PACKETS de adjudicación (todo lo que NO se escribe).

Desde los recibos versionados produce:
- evals/s320_e1_packet_adjudicacion_v1.md — el packet para la sentada:
  §1 colisiones (49: id viejo VIVO = posibles documents duplicados)
  §2 tier B (67: paraguas/homónimo/split-parcial/OEM, con trazas)
  §3 tier C (162: propuestas de producto candidate, por marca)
  §4 no-producto (4: revisión humana de pm sucio)
- evals/s320_e1_candidates_draft.jsonl — el draft de productos candidate de
  tier C (FUERA de data/catalog/: solo entra tras la aprobación por lotes).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import re  # noqa: E402
import unicodedata  # noqa: E402


def _normkey(s: str) -> str:
    plano = unicodedata.normalize("NFKD", s or "")
    plano = "".join(c for c in plano if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]", "", plano)


def _slug(s: str) -> str:
    plano = unicodedata.normalize("NFKD", s or "")
    plano = "".join(c for c in plano if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", plano).strip("-")


detalle = json.loads((ROOT / "evals" / "s320_e1_docmap_derivacion_v2_detalle.json")
                     .read_text(encoding="utf-8"))
censo = json.loads((ROOT / "evals" / "s320_e1_reconciliacion_censo_v1.json")
                   .read_text(encoding="utf-8"))

colisiones = censo["detalle"]["colision"]
alta_sources = {r["source_file"] for r in censo["detalle"]["alta"]}
tier_b = detalle["tier_b"]
tier_c = [c for c in detalle["tier_c"] if c["source_file"] in alta_sources]
tier_c_colision = [c for c in detalle["tier_c"]
                   if c["source_file"] not in alta_sources]
no_producto = detalle["no_producto"]

# draft de candidates tier-C (por marca, id derivado marca:slug(pm))
draft = []
por_marca = defaultdict(list)
for c in tier_c:
    marca = _slug(c.get("manufacturer") or "desconocida")
    pid = f"{marca}:{_slug(c['pm'])}"
    fila = {"id": pid, "canonical_model": c["pm"], "candidate": True,
            "estado": "propuesto-s320-e1",
            "added_by": "s320-e1 derivacion (doc sin producto en catalogo)",
            "provenance": f"documents.pm de {c['source_file']}"}
    draft.append(fila)
    por_marca[c.get("manufacturer") or "?"].append(c)

(ROOT / "evals" / "s320_e1_candidates_draft.jsonl").write_text(
    "\n".join(json.dumps(f, ensure_ascii=False, sort_keys=True) for f in draft)
    + "\n", encoding="utf-8")

utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
lineas = [
    "# s320 E1 — Packet de ADJUDICACIÓN (sentada; generado " + utc + ")",
    "",
    "Lo escrito sin ti (con recibos): 26 altas tier-A + 11 reconciliaciones de",
    "id stale — sonda PRE/POST PASS (26/26 flips esperados), catálogo válido,",
    "109 tests verdes. TODO lo de este packet requiere tu ojo; nada entra solo.",
    "",
    f"## §1 — COLISIONES de identidad ({len(colisiones)}) — posibles docs DUPLICADOS",
    "",
    "El doc_map apunta a un document_id que SIGUE VIVO en documents, pero el",
    "documento activo actual con ese filename tiene OTRO id → dos filas activas",
    "para el mismo manual (clase nueva; puede exigir supersede o borrado).",
    "Decisión por fila: [mantener ambos / marcar viejo superseded / investigar].",
    "",
]
for r in sorted(colisiones, key=lambda x: x["source_file"]):
    vivos = ", ".join((r.get("filenames_de_vivos") or ["?"]))
    lineas.append(f"- [ ] `{r['source_file']}` — id mapa {r['ids_en_mapa'][0][:8]}… "
                  f"(vivo como: {vivos[:70]}) vs id actual "
                  f"{r['document_id_actual'][:8]}… · tier {r['tier'][5:]}")

lineas += [
    "",
    f"## §2 — Tier B: resolución ambigua ({len(tier_b)})",
    "",
    "Paraguas/homónimo/split-parcial/OEM — la traza de resolve por token está",
    "en `evals/s320_e1_docmap_derivacion_v2_detalle.json`. Decisión por fila:",
    "[ids correctos → entrada doc_map / otra cosa].",
    "",
]
for c in sorted(tier_b, key=lambda x: x["source_file"]):
    vias = "+".join(sorted({t["via"] or "none" for t in c["trazas"]}))
    ids = sorted({i for t in c["trazas"] for i in t["ids"]})[:4]
    lineas.append(f"- [ ] `{c['source_file'][:60]}` · pm `{c['pm'][:40]}` · "
                  f"vías {vias} · ids {', '.join(ids) if ids else '—'}")

lineas += [
    "",
    f"## §3 — Tier C: productos NUEVOS propuestos como candidate ({len(tier_c)})",
    "",
    "Draft en `evals/s320_e1_candidates_draft.jsonl` (FUERA del catálogo hasta",
    "tu OK por lotes). candidate=true = no-consumible aunque entren. Por marca:",
    "",
]
for marca in sorted(por_marca, key=lambda m: -len(por_marca[m])):
    casos = por_marca[marca]
    lineas.append(f"### {marca} ({len(casos)})")
    for c in sorted(casos, key=lambda x: x["pm"]):
        lineas.append(f"- [ ] `{c['pm'][:50]}` ← `{c['source_file'][:60]}`")
    lineas.append("")

lineas += [
    f"## §3b — Tier C bloqueado por colisión ({len(tier_c_colision)})",
    "",
    "Resuelve primero su fila de §1 (mismo doc).",
    "",
    f"## §4 — Revisión humana de pm sucio ({len(no_producto)})",
    "",
    "El filtro léxico los apartó como no-producto, pero un pm-norma sucio puede",
    "tapar un producto real (caso EMA1224B4R con pm «EN-54-3»):",
    "",
]
for c in no_producto:
    lineas.append(f"- [ ] `{c['source_file'][:60]}` · pm `{c['pm']}` · "
                  f"marca {c.get('manufacturer')}")

destino = ROOT / "evals" / "s320_e1_packet_adjudicacion_v1.md"
destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
print(f"packet -> {destino}")
print(f"draft candidates -> evals/s320_e1_candidates_draft.jsonl ({len(draft)})")
print(f"secciones: colisiones {len(colisiones)} · B {len(tier_b)} · "
      f"C {len(tier_c)} (+{len(tier_c_colision)} bloqueados) · "
      f"no-producto {len(no_producto)}")
