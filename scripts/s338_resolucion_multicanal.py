#!/usr/bin/env python
"""s338 — resolver un manual huérfano por VARIOS canales independientes.

Nace de un pushback de Alberto con tres ejemplos que mi censo había mandado al
suelo y que son resolubles:

  · `55320002 Manual Programador PGD-200 ES FR GB IT` — el modelo está LITERAL
    en el nombre del fichero, y yo lo clasifiqué «el manual no nombra su
    producto» porque el TEXTO del PDF no lo cita.
  · `Manual-de-Usuario-S3-T2-y-S2-T2` — `S/3-T2` y `S/2-T2`, deducibles del
    nombre y legibles en la portada.
  · `55350005 Manual Central Monoxido CMD-500` — la referencia del fabricante,
    buscada en la web, devuelve **el propio PDF publicado por Detnov**:
    `detnov.com/…/55350005-Manual-Central-Monoxido-CMD-500-ES-FR-GB-IT.pdf`.

**Dónde me equivoqué**: leía R8 («el fichero miente») como «el fichero no vale».
R8 protege de INVENTARSE un producto que el catálogo no tiene; no dice que un
nombre de fichero no pueda CONFIRMAR un producto que el `doc_map` ya enlaza.
Medido sobre los 84: el canal del fichero rescata **30**.

Canales, todos independientes entre sí:
  1. `FICHERO`      — el nombre del documento cita el canónico (hipótesis fuerte)
  2. `PDF`          — la capa de texto del PDF lo cita (s336b)
  3. `CHUNKS`       — sobrevivió a la extracción (integridad, no fuente aparte)
  4. `URL_FABRICANTE` — el FABRICANTE publica ese documento y el modelo está en
     su URL o su título. Es atestación de la fuente primaria, no la opinión de
     un modelo, y por eso vale más que cualquier lectura.
  5. `VISION`       — Anthropic sobre la página renderizada (s336d), para escaneados

**Contrato**: un manual queda `RESUELTO` con **≥2 canales independientes** de
acuerdo. `FICHERO` solo NO basta (sería confiar en R8 al revés); `FICHERO`+`URL`
o `FICHERO`+`PDF` sí.

El canal 4 necesita búsqueda web. Este script NO la hace: emite las consultas
(`--consultas`) y consume sus resultados (`--web fichero.json`), porque la
búsqueda vive en la sesión. Cuando la clave de Gemini tenga grounding activo,
`--gemini` lo hace end-to-end sin intermediario.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))
from src.rag import catalog_store as cs                        # noqa: E402

import importlib.util                                          # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "s336b", ROOT / "scripts/s336b_censo_pdf_huerfanos.py")
_s336b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s336b)
cita = _s336b.cita

DIAG = ROOT / "evals/s336c_diagnostico_huerfanos.json"
SALIDA = ROOT / "evals/s338_resolucion_multicanal.json"
CONSULTAS = ROOT / "evals/s338_consultas_web.json"

#: Dominio oficial por fabricante. Sin esto la búsqueda devuelve reventas y
#: foros; con esto, el PDF del propio fabricante. Se amplía a medida que haga
#: falta — no hay nada específico de marca en el mecanismo, sólo en esta tabla.
DOMINIO = {
    "Detnov": "detnov.com",
    "Notifier": "notifier.es",
    "Morley": "morley-ias.es",
    "Aritech": "firesecurityproducts.com",
    "Xtralis": "xtralis.com",
    "Kilsen": "aritech.es",
    "Sensitron": "sensitron.it",
    "Kidde": "kidde.com",
}


def referencia_del_fichero(sf: str) -> str | None:
    """La referencia del fabricante suele abrir el nombre del fichero
    (`55350005 Manual Central Monoxido CMD-500 …`). ≥6 dígitos para no confundir
    con un número de modelo."""
    m = re.match(r"^\s*(\d{6,})\b", sf)
    return m.group(1) if m else None


def canal_fichero(sf: str, canonicos: list[str]) -> list[str]:
    """R8 al derecho: el fichero no puede INVENTAR un producto, pero sí
    CONFIRMAR uno que el `doc_map` ya enlaza."""
    return [c for c in canonicos if cita(sf, c)]


#: Tokens con forma de modelo: letras + dígitos con separadores opcionales
#: (`MAD-491`, `S/3-T2`, `CMD-500`). Deliberadamente NO captura palabras sueltas.
_FORMA_MODELO = re.compile(r"\b[A-Z]{1,6}[/\-]?\d{1,4}[A-Z0-9/\-]{0,8}\b")


def canal_url(web: dict, sf: str, canonicos: list[str]) -> tuple[list[str], str | None]:
    """¿El FABRICANTE publica este documento, y su URL/título nombra el modelo?"""
    for hit in (web.get(sf) or []):
        texto = f"{hit.get('url','')} {hit.get('titulo','')}"
        vistos = [c for c in canonicos if cita(texto, c)]
        if vistos:
            return vistos, hit.get("url")
    return [], None


def nombres_nuevos(web: dict, sf: str, conocidos: list[str]) -> list[str]:
    """Lo que el fabricante llama al producto y NOSOTROS no tenemos.

    Nace del ejemplo de Alberto: `Manual-de-Usuario-S3-T2-y-S2-T2` tiene en el
    catálogo los canónicos `00051`/`00052` —números de referencia— mientras
    Fidegas lo llama **S/3-T2** y **S/2-T2**. El canal web no sólo CONFIRMA
    nombres: descubre los que faltan. Se propone, no se aplica: bautizar un
    producto es adjudicación (R21)."""
    out: list[str] = []
    for hit in (web.get(sf) or []):
        texto = f"{hit.get('url','')} {hit.get('titulo','')}"
        for tok in _FORMA_MODELO.findall(texto):
            if len(re.sub(r"[^A-Za-z0-9]", "", tok)) < 4:
                continue
            # R19 aplicado al descubrimiento: no todo lo que tiene forma de
            # modelo lo es. `MI-635` es el código de DOCUMENTO de Detnov
            # («Manual de Instalación»), no un producto; y un token cortado por
            # el separador (`MI-635-`) es un artefacto de mi propia regex.
            if tok.endswith(("-", "/", ".")):
                continue
            if re.match(r"^(MI|MU|DS|TP|GA|MN|MA)[-/]?\d{2,4}$", tok, re.I):
                continue
            if any(cita(tok, c) or cita(c, tok) for c in conocidos):
                continue
            if tok not in out:
                out.append(tok)
    return out


def main() -> int:
    cat = cs.load()
    diag = json.loads(DIAG.read_text("utf-8"))
    web, catalogo = {}, {}
    if "--web" in sys.argv:
        web = json.loads(Path(sys.argv[sys.argv.index("--web") + 1]).read_text("utf-8"))
    if "--catalogo" in sys.argv:
        catalogo = json.loads(Path(sys.argv[sys.argv.index("--catalogo") + 1]).read_text("utf-8"))

    # huérfanos VIVOS + el fabricante de cada documento
    huer = {}
    for f in cat.doc_map:
        ids = [e["id"] for e in f.get("entries", []) if e["id"] in cat.products]
        if ids and not any(cat._consumable(i) for i in ids):
            huer[str(f.get("source_file") or "")] = ids
    fabricante = {}
    with httpx.Client(timeout=180) as c:
        from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
        sb = SUPABASE_URL.rstrip("/") + "/rest/v1"
        h = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
        r = c.get(f"{sb}/documents", headers=h,
                  params={"select": "source_pdf_filename,manufacturer", "limit": "2000"})
        for d in (r.json() if r.status_code in (200, 206) else []):
            fabricante[str(d.get("source_pdf_filename") or "")] = str(d.get("manufacturer") or "")

    bucket = {f["source_file"]: f for f in diag["filas"]}

    if "--consultas" in sys.argv:
        # sólo hace falta el canal web donde los otros NO alcanzan
        pendientes = []
        for sf, ids in sorted(huer.items()):
            canon = [cat.products[i]["canonical_model"] for i in ids if i in cat.products]
            b = (bucket.get(sf) or {}).get("bucket", "?")
            if b in ("REDIRECT_PENDIENTE_R21", "PROMOVIBLE"):
                continue
            ref = referencia_del_fichero(sf)
            fab = fabricante.get(sf) or ""
            dom = DOMINIO.get(fab)
            pendientes.append({
                "source_file": sf, "canonicos": canon, "referencia": ref,
                "fabricante": fab, "dominio": dom, "bucket": b,
                "consulta": (f'"{ref}" {fab}'.strip() if ref
                             else f'{Path(sf).stem[:70]} {fab} manual'.strip()),
            })
        CONSULTAS.write_text(json.dumps(
            {"que_es": "s338 · consultas web a lanzar para el canal URL_FABRICANTE. Una por "
                       "manual. Rellenar `resultados` como {source_file: [{url,titulo}]} y "
                       "pasarlo con `--web`.",
             "n": len(pendientes), "consultas": pendientes}, ensure_ascii=False, indent=1), "utf-8")
        print(f"{len(pendientes)} consultas → {CONSULTAS}")
        for p in pendientes[:10]:
            print(f"   {p['consulta'][:64]:66s} ({p['fabricante'] or '?'})")
        return 0

    filas, cuenta = [], Counter()
    for sf, ids in sorted(huer.items()):
        canon = [cat.products[i]["canonical_model"] for i in ids if i in cat.products]
        b = bucket.get(sf) or {}
        canales = {}
        c_fich = canal_fichero(sf, canon)
        if c_fich:
            canales["FICHERO"] = c_fich
        c_pdf = [c for c in canon if c in (b.get("tokens_citados") or [])]
        if c_pdf:
            canales["PDF"] = c_pdf
        if b.get("en_chunks"):
            canales["CHUNKS"] = c_pdf or canon[:1]
        c_url, url = canal_url(web, sf, canon)
        if c_url:
            canales["URL_FABRICANTE"] = c_url
        # El catálogo del fabricante es canal PROPIO: una sola descarga cubre la
        # gama entera y trae la descripción impresa junto al código. Es más
        # barato y más completo que buscar referencia a referencia.
        c_cat, url_cat = canal_url(catalogo, sf, canon)
        if c_cat:
            canales["CATALOGO_FABRICANTE"] = c_cat
            url = url or url_cat
        # nombres que el fabricante usa y el catálogo no tiene (ni canónico ni alias)
        conocidos = canon + [a["alias"] for a in cat.aliases if a.get("id") in ids]
        propuestos = nombres_nuevos({**web, **{k: (web.get(k, []) + v)
                                               for k, v in catalogo.items()
                                               if not k.startswith("_")}},
                                    sf, conocidos)
        # el acuerdo se mide sobre canales INDEPENDIENTES: chunks se deriva del
        # PDF, así que los dos juntos NO son dos.
        indep = {k for k in canales if k != "CHUNKS"}
        modelos = sorted({m for v in canales.values() for m in v})
        v = ("RESUELTO" if len(indep) >= 2 else
             "UN_SOLO_CANAL" if indep else "SIN_CANAL")
        cuenta[v] += 1
        filas.append({"source_file": sf, "ids": ids, "canonicos": canon,
                      "canales": canales, "url_fabricante": url,
                      "modelos": modelos, "veredicto": v,
                      "nombres_que_no_tenemos": propuestos,
                      "bucket_anterior": b.get("bucket")})

    print(f"=== RESOLUCIÓN MULTICANAL · {len(filas)} huérfanos ===")
    for k, n in cuenta.most_common():
        print(f"  {k:16s} {n}")
    nuevos = [f for f in filas if f["veredicto"] == "RESUELTO"
              and f["bucket_anterior"] not in ("PROMOVIBLE",)]
    print(f"\n  RESUELTOS que antes no lo estaban: {len(nuevos)}")
    for f in nuevos[:24]:
        print(f"    {f['source_file'][:44]:46s} {list(f['canales'])} → {f['modelos'][:2]}")
    faltan = [f for f in filas if f["nombres_que_no_tenemos"]]
    if faltan:
        print(f"\n  NOMBRES QUE EL FABRICANTE USA Y NOSOTROS NO TENEMOS ({len(faltan)}):")
        for f in faltan:
            print(f"    {f['source_file'][:42]:44s} catálogo={str(f['canonicos'][:2]):26s} "
                  f"fabricante={f['nombres_que_no_tenemos'][:3]}")
        print("    → se PROPONEN, no se aplican: bautizar un producto es adjudicación (R21)")

    SALIDA.write_text(json.dumps(
        {"que_es": "s338 · resolución por canales independientes (fichero, PDF, chunks, URL del "
                   "fabricante, visión). RESUELTO exige ≥2 canales INDEPENDIENTES: `CHUNKS` se "
                   "deriva del PDF, así que no cuenta como segundo. NADA aplicado.",
         "n": len(filas), "veredictos": dict(cuenta), "filas": filas},
        ensure_ascii=False, indent=1), "utf-8")
    print(f"\n→ {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
