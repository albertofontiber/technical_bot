# -*- coding: utf-8 -*-
"""s322 #76 fase 2 — PASADA DE POBLACIÓN (fable-5) sobre la diana (160:
Detnov 28 + Kidde 132). NADA se escribe al catálogo: recibo + gate-vs-GT +
packet §0/§1 (r27 Fable M3: el sí de Alberto manda).

Por producto: muestra de contenido de SUS docs (doc_map) → veredicto
estructurado {categoria∈enum, tecnologia?, lazos?} con CITA VERBATIM POR CAMPO
(r27 Sol C1: multi-fuente; si dos docs divergen en lazos, el modelo debe
devolver ambos) → citas verificadas contra la muestra (alta sin cita
verificada se degrada).

Convención DECLARADA en el prompt: analogica ≈ direccionable/inteligente
(addressable) — uso PCI estándar ES; nota de enum-semántica al packet.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

import anthropic  # noqa: E402

from src.http_pool import abierto  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
MODELO = "claude-fable-5"

PROMPT = """Eres el clasificador de productos de un catálogo de protección contra incendios (PCI).

PRODUCTO: {canonical} (id {pid})
DOCUMENTOS de este producto y MUESTRAS de su contenido real:
---
{muestra}
---
Pista legacy (texto libre del seed, puede estar mal): {pista}

Clasifícalo. Responde SOLO este JSON:
{{"categoria": "central|detector|pulsador|sirena|modulo|fuente|repetidor|aspiracion|barrera|retenedor|pasarela|software|accesorio",
 "categoria_cita": "fragmento VERBATIM del contenido que lo fundamenta",
 "tecnologia": "analogica|convencional|algoritmica|aspiracion|via_radio|null",
 "tecnologia_cita": "fragmento VERBATIM o null",
 "lazos": [{{"base": N, "max": N, "cita": "fragmento VERBATIM"}}] o null,
 "confianza": "alta|media|baja",
 "razon": "una frase"}}

Reglas: analogica INCLUYE direccionable/inteligente/addressable (uso PCI-ES estándar). Los sounder/VAD/beacon de notificación → sirena. LHD/sensor cable → detector. PAK/llaves/repuestos → accesorio. Si el doc cubre VARIAS variantes y los lazos difieren POR VARIANTE, devuelve los lazos DE ESTE producto (por su sufijo si el doc lo ancla) — si no puedes anclarlo, lazos=null. Si dos DOCS divergen (p.ej. mercados), devuelve AMBAS entradas de lazos con su cita. Sin cita verbatim → confianza baja."""


def main() -> int:
    censo = json.loads((ROOT / "evals" / "s322_76_censo_diana_v1.json")
                       .read_text(encoding="utf-8"))["detalle"]
    cliente = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"],
                                  timeout=120.0, max_retries=1)
    filas = []
    with abierto(timeout=30.0) as c:
        for i, d in enumerate(censo):
            trozos = []
            for sf in d["docs"][:3]:
                r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                          params={"select": "content",
                                  "source_file": f"eq.{sf}",
                                  "order": "chunk_index.asc", "limit": "3"})
                r.raise_for_status()
                trozos.append(f"[DOC: {sf}]\n" + "\n···\n".join(
                    (x.get("content") or "")[:900] for x in r.json()))
            muestra = "\n\n".join(trozos)[:7000]
            msg = cliente.messages.create(
                model=MODELO, max_tokens=500,
                messages=[{"role": "user", "content": PROMPT.format(
                    canonical=d["canonical_model"], pid=d["id"],
                    muestra=muestra, pista=d.get("pista_legacy"))}])
            texto = "".join(b.text for b in msg.content
                            if getattr(b, "type", "") == "text").strip()
            try:
                v = json.loads(texto[texto.index("{"):texto.rindex("}") + 1])
            except Exception:                     # noqa: BLE001
                v = {"categoria": None, "confianza": "baja",
                     "razon": "parse-fail", "raw": texto[:200]}
            # verificación de citas contra la muestra (por campo)
            ml = muestra.lower()

            def _ok(cita):
                return bool(cita) and cita[:50].lower() in ml

            citas_ok = _ok(v.get("categoria_cita"))
            if v.get("tecnologia") and v.get("tecnologia") != "null":
                citas_ok = citas_ok and _ok(v.get("tecnologia_cita"))
            for lz in (v.get("lazos") or []):
                citas_ok = citas_ok and _ok(lz.get("cita"))
            if v.get("confianza") == "alta" and not citas_ok:
                v["confianza"] = "media"
                v["nota"] = "cita no verificada → degradada"
            filas.append({"id": d["id"], "canonical": d["canonical_model"],
                          "marca": d["marca"], "docs": d["docs"][:3],
                          "llm": v, "citas_verificadas": citas_ok})
            if (i + 1) % 20 == 0:
                print(f"  {i+1}/{len(censo)}…", flush=True)
            time.sleep(0.2)

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    resumen: dict = {}
    for f in filas:
        k = f"{f['llm'].get('categoria')}:{f['llm'].get('confianza')}"
        resumen[k] = resumen.get(k, 0) + 1
    recibo = {"que_es": ("Población #76 (fable-5, citas por campo verificadas). "
                         "NADA escrito: gate-vs-GT y packet deciden."),
              "utc": utc, "modelo": MODELO, "total": len(filas),
              "resumen": resumen, "detalle": filas}
    destino = ROOT / "evals" / "s322_76_poblacion_v1.json"
    destino.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"total {len(filas)}")
    print(f"recibo -> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
