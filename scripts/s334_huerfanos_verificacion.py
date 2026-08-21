#!/usr/bin/env python3
"""s334 — VERIFICACIÓN DE LA PREMISA del ataque a huérfanos, ANTES de escribir nada.

POR QUÉ EXISTE ESTE SCRIPT. La sesión pasada presenté tres veces una medida como
decisiva y las tres veces medía algo más estrecho que lo que yo decía, siempre
sesgado hacia mi propia conclusión. De ahí salieron las guardas G1–G5 de
`reglas_clasificacion.json`. Dos de ellas muerden justo aquí, y ninguna es
retórica:

  **G3 — antes de estratificar, comprueba qué cuenta la variable.** «Manual
  huérfano» lo cuento yo sobre filas de `doc_map`. Una fila de `doc_map` NO es un
  manual: es una fila. Si el documento está inactivo, o no tiene chunks, no hay
  ningún técnico perdiendo nada y «desbloquearlo» es contabilidad creativa.

  **G4 — control negativo o no has arreglado nada.** Toda la propuesta descansa
  en una premisa que NO he verificado: que promover el candidate hace que el bot
  ALCANCE el manual. Se comprueba con el resolver de verdad, en los dos sentidos:
     · ANTES la consulta por el modelo NO debe traer ese `source_file`
       (si ya lo trae, el manual nunca estuvo perdido y promover no paga nada);
     · DESPUÉS SÍ debe traerlo (si no, promover no arregla el problema y lo único
       que deja es un término más en el detector, o sea riesgo léxico gratis).

LO QUE ESTE SCRIPT **NO** DICE. «Huérfano» no significa invisible: significa **no
alcanzable POR NOMBRE DE MODELO**. Sin producto detectado el retriever busca en
todo el corpus, así que el manual puede salir igualmente por semántica. Lo que se
pierde es la consulta que un técnico hace de verdad —«¿cómo cableo el MAD-491?»—
y el `allowed_sources` que la ancla. Es un problema real y acotado; decirlo de
otra forma sería vender de más.

NO escribe en el catálogo. Sólo mide, sobre una COPIA temporal.

Uso:  python scripts/s334_huerfanos_verificacion.py [--marca morley] [--limite N]
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY      # noqa: E402
from src.rag import catalog_store as cs                        # noqa: E402
from src.rag import catalog_resolver as R                      # noqa: E402
from src.rag.catalog_store import CATALOG_DIR, FILES           # noqa: E402

H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
EVIDENCIA = ROOT / "evals/s334_huerfanos_evidencia_v1.json"
SALIDA = ROOT / "evals/s334_huerfanos_verificacion_v1.json"


def _paginado(c: httpx.Client, tabla: str, params: dict) -> list[dict]:
    out, off = [], 0
    while True:
        p = dict(params)
        p.update({"limit": "1000", "offset": str(off)})
        r = c.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=H, params=p)
        r.raise_for_status()
        pag = r.json()
        out += pag
        if len(pag) < 1000:
            return out
        off += 1000


def resolver_sobre(catalog_dir: Path, consultas: list[str]) -> dict[str, dict]:
    """`resolve_query` REAL con el catálogo de `catalog_dir` (mismo monkeypatch que el gate)."""
    orig = cs.load
    try:
        cs.load = lambda *a, **k: orig(catalog_dir)
        R._loaded = False
        R._pattern = None
        R._build()
        return {q: {"detected": R.resolve_query(q)["detected"],
                    "allowed_sources": sorted(R.resolve_query(q)["allowed_sources"])}
                for q in consultas}
    finally:
        cs.load = orig
        R._loaded = False
        R._pattern = None


def promover(origen: Path, destino: Path, ids: set[str]) -> None:
    """Copia el catálogo quitando `candidate` a esos ids. Nada más: es la simulación
    MÍNIMA de lo que hará el lote, para que lo que se mida sea el efecto de la
    promoción y no el de otra cosa que se colara en la copia."""
    for nombre, fichero in FILES.items():
        if (origen / fichero).exists():
            shutil.copy(origen / fichero, destino / fichero)
    ruta = destino / FILES["products"]
    filas = [json.loads(l) for l in ruta.read_text("utf-8").splitlines() if l.strip()]
    for p in filas:
        if p["id"] in ids:
            p["candidate"] = False
    ruta.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in filas), "utf-8")


def main() -> int:
    marca = sys.argv[sys.argv.index("--marca") + 1] if "--marca" in sys.argv else None
    limite = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else 0

    ev = json.loads(EVIDENCIA.read_text("utf-8"))
    riesgos = set(ev.get("riesgos_detectados") or {})

    # las filas LIMPIAS de clase A (las que el lote autónomo se plantea promover)
    filas = []
    for m, lote in ev["lotes"].items():
        if marca and m != marca:
            continue
        for it in lote["ids"]:
            if it["id"] in riesgos:
                continue
            filas.append(it)
    # cada id, con el/los documentos que lo atestan
    doc_de: dict[str, list[str]] = defaultdict(list)
    dm = [json.loads(l) for l in (ROOT / "data/catalog/doc_map.jsonl")
          .read_text("utf-8").splitlines() if l.strip()]
    for fila in dm:
        for e in fila.get("entries", []):
            doc_de[e["id"]].append(str(fila.get("source_file") or ""))
    docid_de: dict[str, str] = {}
    for fila in dm:
        for e in fila.get("entries", []):
            docid_de.setdefault(e["id"], str(fila.get("document_id") or ""))

    if limite:
        filas = filas[:limite]
    print(f"filas limpias de clase A a verificar: {len(filas)}"
          + (f"  (marca={marca})" if marca else ""))

    # ── G3: ¿qué cuenta «manual huérfano»? ──────────────────────────────────
    docids = sorted({docid_de.get(f["id"], "") for f in filas} - {""})
    print(f"\n=== G3 — ¿son manuales de verdad? ({len(docids)} documentos) ===")
    estado: dict[str, dict] = {}
    with httpx.Client(timeout=90) as c:
        for i in range(0, len(docids), 40):
            trozo = docids[i:i + 40]
            docs = _paginado(c, "documents",
                             {"select": "id,status,product_model,source_pdf_filename",
                              "id": f"in.({','.join(trozo)})"})
            for d in docs:
                estado[str(d["id"])] = d
        # ¿tienen chunks? (un documento sin chunks no lo alcanza NADIE, ni por
        # catálogo ni por semántica: desbloquearlo sería contabilidad vacía)
        con_chunks: dict[str, int] = {}
        for i, did in enumerate(docids, 1):
            r = c.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers={**H, "Prefer": "count=exact"},
                      params={"select": "id", "document_id": f"eq.{did}", "limit": "1"})
            r.raise_for_status()
            con_chunks[did] = int((r.headers.get("content-range") or "0/0").split("/")[-1] or 0)
            if i % 25 == 0:
                print(f"  …{i}/{len(docids)}", flush=True)

    faltan = [d for d in docids if d not in estado]
    inactivos = [d for d, v in estado.items() if v.get("status") != "active"]
    sin_chunks = [d for d, n in con_chunks.items() if n == 0]
    print(f"  no existen en `documents` ....... {len(faltan)}")
    print(f"  existen pero NO están `active` .. {len(inactivos)}")
    print(f"  activos pero SIN chunks ........ {len(sin_chunks)}")
    print(f"  manuales REALES (active+chunks)  "
          f"{len([d for d in docids if d in estado and d not in inactivos and d not in sin_chunks])}"
          f" / {len(docids)}")

    # ── G4: control negativo — ¿la promoción alcanza el manual? ─────────────
    print(f"\n=== G4 — ¿promover ALCANZA el manual? (resolver real, antes/después) ===")
    consultas = [f["canonico"] for f in filas]
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        promover(CATALOG_DIR, d, {f["id"] for f in filas})
        antes = resolver_sobre(CATALOG_DIR, consultas)
        despues = resolver_sobre(d, consultas)

    veredictos = defaultdict(list)
    detalle = []
    for f in filas:
        q = f["canonico"]
        srcs = set(doc_de.get(f["id"], []))
        a = set(antes[q]["allowed_sources"])
        b = set(despues[q]["allowed_sources"])
        ya = bool(srcs & a)
        gana = bool(srcs & b)
        if ya:
            v = "YA_ALCANZABLE"       # promover no paga: otro id ya lo trae
        elif gana:
            v = "DESBLOQUEA"          # es lo que decimos que hace
        elif despues[q]["detected"]:
            v = "DETECTA_SIN_FUENTE"  # el término entra pero el manual no llega
        else:
            v = "NI_DETECTA"          # promover no cambia nada: término inerte
        veredictos[v].append(f["id"])
        detalle.append({"id": f["id"], "canonico": q, "veredicto": v,
                        "detected_despues": despues[q]["detected"],
                        "fuentes_del_id": sorted(srcs)[:4],
                        "allowed_sources_antes": len(a), "allowed_sources_despues": len(b),
                        "document_id": docid_de.get(f["id"], ""),
                        "doc_status": (estado.get(docid_de.get(f["id"], "")) or {}).get("status"),
                        "doc_chunks": con_chunks.get(docid_de.get(f["id"], ""))})
    etiquetas = {
        "DESBLOQUEA": "la consulta por el modelo NO traía su manual y ahora SÍ  ← lo que pagamos",
        "YA_ALCANZABLE": "su manual ya salía por otra vía: promover no lo desbloquea",
        "DETECTA_SIN_FUENTE": "el término entra en el detector pero el manual no llega",
        "NI_DETECTA": "promover no cambia nada: término inerte (riesgo sin beneficio)",
    }
    for k in ("DESBLOQUEA", "YA_ALCANZABLE", "DETECTA_SIN_FUENTE", "NI_DETECTA"):
        if veredictos.get(k):
            print(f"  {k:20s} {len(veredictos[k]):4d}  {etiquetas[k]}")
            for pid in veredictos[k][:4]:
                print(f"      · {pid}")

    salida = {
        "que_es": "Verificación de la PREMISA del ataque a huérfanos: G3 (qué cuenta la "
                  "variable) y G4 (control negativo con el resolver real). NADA aplicado.",
        "aviso_de_alcance": "«Huérfano» = no alcanzable POR NOMBRE DE MODELO. Sin producto "
                            "detectado el retriever sigue buscando en todo el corpus; lo que "
                            "se pierde es la consulta por modelo y su `allowed_sources`.",
        "marca": marca, "n": len(filas),
        "G3_documentos": {"total": len(docids), "no_existen": faltan,
                          "no_active": inactivos, "sin_chunks": sin_chunks},
        "G4_veredictos": {k: len(v) for k, v in veredictos.items()},
        "G4_etiquetas": etiquetas,
        "detalle": detalle,
    }
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1), "utf-8")
    print(f"\n→ {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
