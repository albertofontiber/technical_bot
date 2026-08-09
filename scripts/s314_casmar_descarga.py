# -*- coding: utf-8 -*-
"""Descarga los gaps del cruce a staging + sha-dedup vs corpus + paginas + sidecar propuesto."""
import hashlib
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, r"C:\dev\technical_bot")
sys.stdout.reconfigure(line_buffering=True)
from dotenv import load_dotenv
load_dotenv(r"C:\dev\technical_bot\.env")
import httpx
import fitz

SCRATCH = os.environ.get("S314_WORKDIR", os.getcwd())  # artefactos del harvest (JSONs/staging)
STAGING = os.path.join(SCRATCH, "casmar_batch")
os.makedirs(STAGING, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

cruce = json.loads(io.open(os.path.join(SCRATCH, "casmar_kidde_cruce.json"), encoding="utf-8").read())
gaps = cruce["gaps"]

# shas ya en DB (documents) y en el store
U = os.environ["SUPABASE_URL"].rstrip("/")
K = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
H = {"apikey": K, "Authorization": f"Bearer {K}"}
shas_db = set()
offset = 0
while True:
    r = httpx.get(f"{U}/rest/v1/documents", params={"select": "source_pdf_sha256",
                  "order": "id.asc", "limit": "1000", "offset": str(offset)}, headers=H, timeout=60)
    lote = r.json()
    shas_db |= {d["source_pdf_sha256"] for d in lote if d.get("source_pdf_sha256")}
    if len(lote) < 1000:
        break
    offset += 1000
STORE = r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\data\extraction\agent_anthropic-sonnet-45"
shas_store = {f[:-5] for f in os.listdir(STORE) if f.endswith(".json")}
print(f"shas en DB: {len(shas_db)} | en store: {len(shas_store)}")


def sanea(nombre):
    nombre = re.sub(r'[<>:"/\\|?*]', "_", nombre)
    return nombre


resultados = []
vistos_sha = {}
with httpx.Client(headers=UA, timeout=120, follow_redirects=True) as c:
    for n, g in enumerate(sorted(gaps, key=lambda x: x["nombre"]), 1):
        nombre = sanea(g["nombre"])
        destino = os.path.join(STAGING, nombre)
        try:
            if not os.path.exists(destino):
                r = c.get(g["url"])
                if r.status_code in (403, 429):
                    raise SystemExit(f"WAF ({r.status_code}) — ABORTO educado en {n}/{len(gaps)}")
                r.raise_for_status()
                with open(destino + ".tmp", "wb") as f:
                    f.write(r.content)
                os.replace(destino + ".tmp", destino)
                time.sleep(1.2)
        except SystemExit:
            raise
        except Exception as e:
            resultados.append({**g, "estado": f"FALLO-descarga: {type(e).__name__}: {e}"})
            print(f"[{n}/{len(gaps)}] FALLO {nombre}: {e}")
            continue

        h = hashlib.sha256(open(destino, "rb").read()).hexdigest()
        try:
            with fitz.open(destino) as doc:
                paginas = doc.page_count
        except Exception:
            paginas = None
        if h in shas_db or h in shas_store:
            estado = "DUP-corpus (mismo sha ya ingestado/extraido)"
        elif h in vistos_sha:
            estado = f"DUP-lote (identico a {vistos_sha[h]})"
        elif paginas is None:
            estado = "ILEGIBLE"
        else:
            estado = "NUEVO"
            vistos_sha[h] = nombre
        resultados.append({**g, "local": nombre, "sha256": h, "paginas": paginas, "estado": estado})
        print(f"[{n}/{len(gaps)}] {estado:<12} {nombre} ({paginas} pag)")

io.open(os.path.join(SCRATCH, "casmar_batch_report.json"), "w", encoding="utf-8").write(
    json.dumps(resultados, ensure_ascii=False, indent=1))

nuevos = [r for r in resultados if r["estado"] == "NUEVO"]
dup_corpus = [r for r in resultados if r["estado"].startswith("DUP-corpus")]
dup_lote = [r for r in resultados if r["estado"].startswith("DUP-lote")]
pag = sum(r["paginas"] or 0 for r in nuevos)
print(f"\nRESUMEN: {len(resultados)} bajados | NUEVOS {len(nuevos)} ({pag} paginas) | "
      f"dup-corpus {len(dup_corpus)} | dup-lote {len(dup_lote)}")
print(f"Coste extraccion estimado de los NUEVOS: ~{pag*45} creditos (~${pag*45*1.25/1000:.2f})")
