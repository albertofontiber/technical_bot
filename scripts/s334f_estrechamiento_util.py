#!/usr/bin/env python3
"""s334f — ¿el ESTRECHAMIENTO es DAÑO o es PRECISIÓN?

LA PREGUNTA QUE NO ME HICE. Cuando Fable cazó en r43 que promover puede quitarle
fuentes a la consulta, cablée el veredicto `DESBLOQUEA_PERO_ESTRECHA` y **excluí
en bloque** a todos los que lo disparaban. Eso presupone que perder una fuente es
siempre malo. No lo es: si el documento perdido **no habla de este producto**,
perderlo es el filtro de modelo haciendo su trabajo — precisión, no daño.

La verificación de citas (s334d) lo dejó a la vista y yo no lo leí así:
`systemsensor:8100e-faast` perdía 14 documentos y **ninguno de los 14 lo nombra**.
Eran manuales de OTROS modelos FAAST que el paraguas arrastraba. Perderlos es
exactamente lo que queremos.

PERO NO TODO LO PERDIDO ES IGUAL, y aquí está la distinción que decide:

  · **DOC DE HERMANO** — no nombra a nuestro producto pero SÍ nombra a otro
    producto consumible. Es un manual de un modelo concreto distinto. Perderlo
    es PRECISIÓN: el técnico que pregunte por ese otro modelo lo seguirá
    encontrando.
  · **DOC GENÉRICO DE FAMILIA** — no nombra a NINGÚN producto consumible en
    concreto. Es el «Manual de usuario del TG» que responde las preguntas de
    todos los TG-xxxx. Perderlo SÍ es daño: el técnico que pregunte por nuestro
    producto se queda sin el documento que probablemente le contesta.

Así que el veredicto por id es:
  · **PRECISIÓN** — todo lo que pierde son docs de hermano → se puede promover.
  · **DAÑO** — pierde al menos un genérico de familia → sigue fuera (y su arreglo
    es una relación de catálogo, que es adjudicación de Alberto).

NO escribe. Produce el veredicto por id para que el plan se regenere.

Uso:  python scripts/s334f_estrechamiento_util.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ["IDENTITY_RESOLVE"] = "on"
os.environ["IDENTITY_RESOLVE_POLICY"] = "replace"          # el brazo de producción

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402
from src.rag import catalog_store as cs                    # noqa: E402
from src.rag import catalog_resolver as R                  # noqa: E402
from src.rag.catalog_store import CATALOG_DIR, FILES       # noqa: E402

H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
VERIF = ROOT / "evals/s334_huerfanos_verificacion_v1.json"
SALIDA = ROOT / "evals/s334f_estrechamiento_util.json"


def _pag(c: httpx.Client, tabla: str, params: dict) -> list[dict]:
    out, off = [], 0
    while True:
        p = dict(params)
        p.update({"limit": "1000", "offset": str(off)})
        r = c.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=H, params=p)
        if r.status_code != 200:
            return out
        pag = r.json()
        out += pag
        if len(pag) < 1000:
            return out
        off += 1000


def _n_chunks(c: httpx.Client, sf: str) -> int | None:
    """Cuántos chunks tiene el documento — o None si la LECTURA falló.

    La distinción no es cosmética: `_pag` devuelve `[]` tanto cuando el documento
    está vacío como cuando la petición se cayó, y tratar las dos igual convierte
    un fallo de red en un dato. (Es la misma clase de fail-open-disfrazado-de-dato
    que G2 nombra.) Con el `count=exact` de PostgREST la diferencia es explícita:
    un 200 con 0 es un hecho; cualquier otra cosa es «no lo sé»."""
    r = c.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers={**H, "Prefer": "count=exact"},
              params={"select": "id", "source_file": f"eq.{sf}", "limit": "1"})
    # 200 **y 206**: PostgREST devuelve `206 Partial Content` cuando el `limit`
    # trunca, o sea en TODO documento que tenga contenido. Comprobar `!= 200`
    # marcaba como «lectura fallida» exactamente los que sí se leyeron — y el
    # veredicto salía invertido. Se ve en el desglose por clase, no en el titular.
    if r.status_code not in (200, 206):
        return None
    return int((r.headers.get("content-range") or "0/0").split("/")[-1] or 0)


def _cita(texto: str, tok: str) -> bool:
    return bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(tok)}(?![A-Za-z0-9])", texto, re.I))


def _copia(promover: set[str]) -> Path:
    d = Path(tempfile.mkdtemp())
    for _, fn in FILES.items():
        if (CATALOG_DIR / fn).exists():
            shutil.copy(CATALOG_DIR / fn, d / fn)
    ruta = d / FILES["products"]
    filas = [json.loads(l) for l in ruta.read_text("utf-8").splitlines() if l.strip()]
    for p in filas:
        if p["id"] in promover:
            p["candidate"] = False
    ruta.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in filas), "utf-8")
    return d


def _fuentes(catalog_dir: Path, q: str) -> set[str]:
    orig = cs.load
    try:
        cs.load = lambda *a, **k: orig(catalog_dir)
        R._loaded = False
        R._pattern = None
        R._build()
        return set(R.resolve_query(q)["allowed_sources"])
    finally:
        cs.load = orig
        R._loaded = False
        R._pattern = None


def main() -> int:
    cat = cs.load()
    verif = json.loads(VERIF.read_text("utf-8"))
    estrechan = {}
    for d in verif["detalle"]:
        if d["veredicto"] == "DESBLOQUEA_PERO_ESTRECHA":
            estrechan[d["id"]] = d["canonico"]
    # sólo los que siguen en cuarentena (los ya promovidos no aplican)
    estrechan = {i: c for i, c in estrechan.items()
                 if i in cat.products and cat.products[i].get("candidate")}
    print(f"ids que estrechan y siguen en cuarentena: {len(estrechan)}")

    # (1) qué pierde cada uno, medido AISLADO
    perdidas: dict[str, list[str]] = {}
    antes: dict[str, set[str]] = {}
    for i, (pid, canon) in enumerate(sorted(estrechan.items()), 1):
        if canon not in antes:
            antes[canon] = _fuentes(CATALOG_DIR, canon)
        d = _copia({pid})
        try:
            perdidas[pid] = sorted(antes[canon] - _fuentes(d, canon))
        finally:
            shutil.rmtree(d, ignore_errors=True)
        if i % 5 == 0:
            print(f"  …{i}/{len(estrechan)}", flush=True)

    # (2) el texto de cada documento perdido, UNA vez
    docs = sorted({s for v in perdidas.values() for s in v})
    print(f"documentos perdidos distintos a leer: {len(docs)}")
    texto: dict[str, str] = {}
    n_chunks: dict[str, int | None] = {}
    with httpx.Client(timeout=120) as c:
        for i, sf in enumerate(docs, 1):
            n_chunks[sf] = _n_chunks(c, sf)
            filas = _pag(c, "chunks_v2", {"select": "content", "source_file": f"eq.{sf}"})
            texto[sf] = " ".join(str(f.get("content") or "") for f in filas)
            if i % 10 == 0:
                print(f"  …{i}/{len(docs)}", flush=True)
    vacios = [s for s, n in n_chunks.items() if n == 0]
    if vacios:
        print(f"  documentos con 0 chunks VERIFICADOS (perderlos es inocuo): {vacios}")

    # (3) tokens de los productos CONSUMIBLES, para saber si un doc nombra a un hermano
    alias_de = defaultdict(list)
    for a in cat.aliases:
        alias_de[a["id"]].append(a["alias"])
    consumibles = [(pid, [p["canonical_model"]] + alias_de.get(pid, []))
                   for pid, p in cat.products.items() if cat._consumable(pid)]

    filas_out, veredicto = [], {}
    for pid, perd in sorted(perdidas.items()):
        canon = estrechan[pid]
        toks_mios = [canon] + alias_de.get(pid, [])
        detalle = []
        hay_generico = False
        for sf in perd:
            cuerpo = texto.get(sf, "")
            n = n_chunks.get(sf)
            if n == 0:
                # 0 chunks VERIFICADO: el documento no puede responderle a nadie,
                # así que quitarlo de `allowed_sources` no le resta nada al técnico.
                # Es NEUTRO, no daño — contarlo como daño estaba bloqueando 5 ids
                # por un PDF sin contenido.
                clase = "SIN_CHUNKS_INOCUO"
            elif n is None:
                clase = "LECTURA_FALLIDA"          # no lo sé → conservador: daño
            elif any(_cita(cuerpo, t) for t in toks_mios):
                clase = "NOMBRA_A_NUESTRO_PRODUCTO"     # perderlo es DAÑO claro
            else:
                hermanos = [q for q, ts in consumibles
                            if q != pid and any(_cita(cuerpo, t) for t in ts)]
                clase = "DOC_DE_HERMANO" if hermanos else "GENERICO_DE_FAMILIA"
            if clase in ("NOMBRA_A_NUESTRO_PRODUCTO", "GENERICO_DE_FAMILIA", "LECTURA_FALLIDA"):
                hay_generico = True
            detalle.append({"source_file": sf, "clase": clase})
        v = "DAÑO" if hay_generico else "PRECISION"
        veredicto[pid] = v
        filas_out.append({"id": pid, "canonico": canon, "veredicto": v,
                          "n_perdidas": len(perd), "perdidas": detalle})

    from collections import Counter
    print("\n=== ¿EL ESTRECHAMIENTO ES DAÑO O PRECISIÓN? ===")
    print(" ", dict(Counter(veredicto.values())))
    for f in sorted(filas_out, key=lambda x: (x["veredicto"], -x["n_perdidas"])):
        cl = Counter(d["clase"] for d in f["perdidas"])
        print(f"  {f['veredicto']:9s} {f['id']:30s} pierde {f['n_perdidas']:2d}  {dict(cl)}")

    SALIDA.write_text(json.dumps(
        {"que_es": "Distingue si el estrechamiento que provoca promover un candidate es DAÑO "
                   "(pierde un documento que le sirve) o PRECISIÓN (pierde documentos de OTROS "
                   "modelos que el paraguas arrastraba). NADA aplicado.",
         "criterio": {"DOC_DE_HERMANO": "no nos nombra pero nombra a otro producto consumible → "
                                        "perderlo es precisión",
                      "GENERICO_DE_FAMILIA": "no nombra a ningún producto consumible → es el "
                                             "manual de la familia y perderlo es daño",
                      "NOMBRA_A_NUESTRO_PRODUCTO": "daño claro",
                      "SIN_CHUNKS_INOCUO": "0 chunks verificado con count=exact: no puede "
                                           "responderle a nadie, perderlo es neutro",
                      "LECTURA_FALLIDA": "no se pudo leer: se cuenta como daño, conservador"},
         "resumen": dict(Counter(veredicto.values())), "filas": filas_out}, ensure_ascii=False,
        indent=1), "utf-8")
    print(f"\n→ {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
