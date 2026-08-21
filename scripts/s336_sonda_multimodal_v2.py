#!/usr/bin/env python3
"""s336 — SONDA MULTIMODAL v2: ¿recupera una lectura de la PÁGINA los nombres que
la extracción de texto perdió?

POR QUÉ HAY UNA v2. La v1 (s334) quedó **INCONCLUSA** y el dúo r41 dijo por qué,
con tres defectos que no eran de capacidad sino de método. Los tres van arreglados
aquí, y se declaran para que se vea que no se dan por buenos por repetirlos:

  **(1) EL ESTRATO CONTABA ASSETS, NO PÁGINAS DE PDF.** «Lectura completa» se
  medía por el nº de imágenes renderizadas, y `MAD-412` tiene `pdf_page_count: 2`
  con `renderable_pages: [1]`. De los 24 que llamé completos, **cero** eran
  verificablemente completos. → Aquí la cobertura sale de
  `s271_pdf_coverage_v1.json` (`pdf_page_count` vs `renderable_pages`) y **un
  «no está» sólo vale como tal en documentos con cobertura COMPLETA**; en los
  demás el negativo se declara como «no está en las páginas que pude leer».

  **(2) LAS n NO ERAN INDEPENDIENTES.** La misma imagen contaba como varios
  ensayos. → Aquí la unidad es el DOCUMENTO, y dentro de él se leen **todas** sus
  páginas renderizadas; un documento aporta UN dato, no uno por página.

  **(3) `_sin_fuga` ERA VACUO.** Inspeccionaba un prompt CONSTANTE que jamás
  llevaba nombres: no podía fallar nunca, y «cero fuga verificada» sobrevendía una
  propiedad que se cumplía por construcción, no por comprobación. → Aquí se
  inspecciona **el cuerpo real de la petición** (el JSON que sale por el cable,
  con la imagen recortada) buscando el token esperado, el nombre del fichero y la
  URL. Y hay un **auto-test del guardarraíl**: antes de empezar se le pasa un
  payload envenenado a propósito y se comprueba que ABORTA. Un guardarraíl que no
  se demuestra capaz de saltar no es un guardarraíl.

EL PATRÓN SIGUE SIENDO DE PLATA, no de oro: el nombre esperado viene del NOMBRE
DEL FICHERO, y **R8 dice que el nombre del fichero miente** (el caso
`D838-1_kac sounders`). Por eso hay TRES familias — un desacuerdo con el patrón en
el que las tres coinciden acusa al patrón, no a los lectores.

Uso:  python scripts/s336_sonda_multimodal_v2.py --poblacion   # sólo el censo
      python scripts/s336_sonda_multimodal_v2.py --limite 6     # censo + lectura
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
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

H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
COBERTURA = ROOT / "evals/s271_pdf_coverage_v1.json"
SALIDA = ROOT / "evals/s336_sonda_multimodal_v2.json"

PROMPT = (
    "Esta es una página de un documento técnico de protección contra incendios "
    "o detección de gas.\n\n"
    "¿Qué MODELO o MODELOS de producto identifica este documento? Fíjate en el "
    "título, en la portada, en las etiquetas de las fotos del equipo y en los "
    "rótulos de los diagramas.\n\n"
    "Responde SÓLO con un JSON, sin texto alrededor:\n"
    '{"modelos": ["..."], "confianza": "alta|media|baja", "donde": "dónde lo has visto"}\n\n'
    "Si no identificas ningún modelo, devuelve la lista vacía. NO inventes: "
    "una referencia de documento (tipo «REF: 55349102») no es un modelo."
)

#: Tres familias. Gemini es la que Alberto observó; las otras dos son el
#: cross-model que hace del acuerdo una evidencia y no una opinión.
GEMINI = "gemini-3.6-flash"          # los `pro` dan 429 con esta clave (cuota)
#: Páginas leídas por documento. ACOTADO y DECLARADO: el nombre del modelo vive en
#: la portada y las primeras páginas, así que 3 basta para el resultado POSITIVO
#: («la página recupera el nombre»). Para el NEGATIVO no basta —y por eso el
#: negativo sólo se interpreta en los documentos con cobertura completa, que aquí
#: son 3 y tienen 1-2 páginas: en ésos se leen TODAS.
TOPE_PAGINAS = 3
CLAUDE = "claude-fable-5"
GPT = "gpt-5.6-sol"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


class Fuga(SystemExit):
    pass


def sin_fuga(payload: object, esperado: str, fichero: str, url: str) -> None:
    """ABORTA si el token esperado, el nombre del fichero o la URL viajan al modelo.

    Inspecciona el CUERPO REAL de la petición, no un prompt constante. La versión
    de la v1 miraba una constante que jamás llevaba nombres: no podía fallar, y
    por eso su «cero fuga verificada» no verificaba nada."""
    crudo = json.dumps(payload, ensure_ascii=False)
    # la imagen en base64 es ruido para esta comprobación y puede casar por azar
    crudo = re.sub(r'"data"\s*:\s*"[^"]*"', '"data":"<img>"', crudo)
    n = _norm(crudo)
    for etiqueta, valor in (("token esperado", esperado), ("nombre del fichero", fichero),
                            ("url", url)):
        v = _norm(valor)
        if v and len(v) >= 4 and v in n:
            raise Fuga(f"FUGA: el {etiqueta} «{valor}» viaja en la petición — la sonda "
                       f"quedaría invalidada; se aborta.")


def _autotest_guardarrail() -> None:
    """El guardarraíl tiene que DEMOSTRAR que salta. Sin esto es decoración."""
    envenenado = {"contents": [{"parts": [{"text": "identifica el MAD-491 de la página"}]}]}
    try:
        sin_fuga(envenenado, "MAD-491", "x", "y")
    except Fuga:
        return
    raise SystemExit("el guardarraíl anti-fuga NO salta con un payload envenenado — "
                     "es vacuo, exactamente el defecto que la v1 tenía")


def _pag(c: httpx.Client, tabla: str, params: dict) -> list[dict]:
    out, off = [], 0
    while True:
        p = dict(params)
        p.update({"limit": "1000", "offset": str(off)})
        r = c.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=H, params=p)
        if r.status_code not in (200, 206):
            return out
        pag = r.json()
        out += pag
        if len(pag) < 1000:
            return out
        off += 1000


def poblacion() -> list[dict]:
    """Los manuales HUÉRFANOS cuyo bloqueo es «sin cita»: la extracción perdió el
    nombre. Es la población donde leer la página puede aportar algo — no los 601
    de la cuarentena ni los 52 de la v1."""
    cat = cs.load()
    ev = json.loads((ROOT / "evals/s334_huerfanos_evidencia_v1.json").read_text("utf-8"))
    clase = {it["id"]: it.get("clase") for l in ev["lotes"].values() for it in l["ids"]}

    huerf = []
    for f in cat.doc_map:
        ids = [e["id"] for e in f.get("entries", []) if e["id"] in cat.products]
        if not ids or any(cat._consumable(i) for i in ids):
            continue
        cands = [i for i in ids if cat.products[i].get("candidate")]
        sin_cita = [i for i in cands if clase.get(i) == "E"]
        if sin_cita:
            huerf.append({"source_file": str(f.get("source_file") or ""),
                          "document_id": str(f.get("document_id") or ""),
                          "ids_sin_cita": sin_cita,
                          "esperado": cat.products[sin_cita[0]]["canonical_model"]})

    cob = {d["document_id"]: d for d in
           json.loads(COBERTURA.read_text("utf-8"))["documents"]}
    with httpx.Client(timeout=120) as c:
        assets = _pag(c, "document_visual_assets",
                      {"select": "document_id,page_index,visual_role,storage_url,media_type"})
    por_doc = defaultdict(list)
    for a in assets:
        por_doc[str(a.get("document_id"))].append(a)
    for v in por_doc.values():
        v.sort(key=lambda a: a.get("page_index") or 0)

    out = []
    for h in huerf:
        pgs = por_doc.get(h["document_id"], [])
        if not pgs:
            continue
        cv = cob.get(h["document_id"], {})
        n_pdf = cv.get("pdf_page_count")
        rend = cv.get("renderable_pages") or []
        completa = bool(n_pdf) and len(rend) >= n_pdf
        out.append({**h, "paginas": pgs, "n_paginas_renderizadas": len(pgs),
                    "pdf_page_count": n_pdf, "n_renderable_pages": len(rend),
                    "cobertura_completa_VERIFICADA": completa})
    return out


def _json_de(t: str) -> dict:
    t = re.sub(r"^```(?:json)?|```$", "", (t or "").strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(t)
    except Exception:                                          # noqa: BLE001
        m = re.search(r"\{.*\}", t, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:                                  # noqa: BLE001
                pass
    return {"modelos": [], "confianza": "baja", "_crudo": t[:300]}


def lee_gemini(img: bytes, mime: str, esperado: str, fichero: str, url: str) -> dict:
    payload = {"contents": [{"parts": [
        {"inline_data": {"mime_type": mime, "data": base64.b64encode(img).decode()}},
        {"text": PROMPT}]}]}
    sin_fuga(payload, esperado, fichero, url)
    # 503 «high demand» y 429 son transitorios en la API de Gemini: dos reintentos
    # con espera. Un fallo de infraestructura no es un «no lo vio».
    for intento in range(3):
        r = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI}:generateContent",
            headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"],
                     "Content-Type": "application/json"}, json=payload, timeout=240)
        if r.status_code not in (429, 503) or intento == 2:
            break
        time.sleep(4 * (intento + 1))
    r.raise_for_status()
    d = r.json()
    return _json_de("".join(p.get("text", "") for c in d.get("candidates", [])
                            for p in c.get("content", {}).get("parts", [])))


def lee_claude(img: bytes, mime: str, esperado: str, fichero: str, url: str) -> dict:
    from anthropic import Anthropic
    contenido = [{"type": "image", "source": {"type": "base64", "media_type": mime,
                                              "data": base64.b64encode(img).decode()}},
                 {"type": "text", "text": PROMPT}]
    sin_fuga({"messages": [{"role": "user", "content": contenido}]}, esperado, fichero, url)
    cli = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY_SCRIPTS")
                    or os.environ["ANTHROPIC_API_KEY"])
    r = cli.messages.create(model=CLAUDE, max_tokens=600,
                            messages=[{"role": "user", "content": contenido}])
    return _json_de("".join(b.text for b in r.content if b.type == "text"))


def lee_gpt(img: bytes, mime: str, esperado: str, fichero: str, url: str) -> dict:
    from openai import OpenAI
    entrada = [{"role": "user", "content": [
        {"type": "input_text", "text": PROMPT},
        {"type": "input_image",
         "image_url": f"data:{mime};base64,{base64.b64encode(img).decode()}"}]}]
    sin_fuga({"input": entrada}, esperado, fichero, url)
    cli = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _json_de(cli.responses.create(model=GPT, store=False, input=entrada).output_text)


def acierta(resp: dict, esperado: str) -> bool:
    e = _norm(esperado)
    if not e:
        return False
    for m in resp.get("modelos") or []:
        n = _norm(str(m))
        if n and (e in n or n in e):
            return True
    return False


def main() -> int:
    _autotest_guardarrail()
    print("guardarraíl anti-fuga: AUTO-TEST OK (aborta con payload envenenado)")
    pob = poblacion()
    completos = [p for p in pob if p["cobertura_completa_VERIFICADA"]]
    print(f"\n=== POBLACIÓN v2 ===")
    print(f"  manuales huérfanos bloqueados por «sin cita», con página renderizada: {len(pob)}")
    print(f"  de ellos con COBERTURA COMPLETA verificada ....................... {len(completos)}")
    print(f"  (en el resto, un «no está» sólo significa «no está en lo que pude leer»)")
    if "--poblacion" in sys.argv:
        SALIDA.write_text(json.dumps({"que_es": "Población de la sonda v2", "poblacion": pob},
                                     ensure_ascii=False, indent=1), "utf-8")
        print(f"\n→ {SALIDA}")
        return 0

    limite = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else 0
    # SE LEEN TODOS. La cobertura NO decide qué documentos se leen: decide qué
    # NEGATIVO es interpretable. El positivo («la página recupera el nombre») vale
    # en cualquiera — si el modelo lo lee de la portada, lo recuperó y punto.
    # (Mi primera versión hacía `completos or pob` y la corrida se quedó en 3 de 37:
    #  restringir la lectura a los completos es justo confundir las dos cosas otra vez.)
    objetivo = pob[:limite] if limite else pob
    filas = []
    for i, doc in enumerate(objetivo, 1):
        esperado, fich = doc["esperado"], doc["source_file"]
        # UNA fila por DOCUMENTO: se leen TODAS sus páginas y se agrega
        por_lector = {"gemini": [], "claude": [], "gpt": []}
        paginas = (doc["paginas"] if doc["cobertura_completa_VERIFICADA"]
                   else doc["paginas"][:TOPE_PAGINAS])
        for pg in paginas:
            url = pg["storage_url"]
            try:
                im = httpx.get(url, timeout=120)
                im.raise_for_status()
            except Exception as e:                             # noqa: BLE001
                continue
            mime = im.headers.get("content-type", "image/jpeg").split(";")[0]
            for nombre, fn in (("gemini", lee_gemini), ("claude", lee_claude), ("gpt", lee_gpt)):
                try:
                    por_lector[nombre].append(fn(im.content, mime, esperado, fich, url))
                except Fuga:
                    raise
                except Exception as e:                         # noqa: BLE001
                    por_lector[nombre].append({"error": str(e)[:160]})
                time.sleep(0.4)
        fila = {"document_id": doc["document_id"], "source_file": fich, "esperado": esperado,
                "n_paginas_leidas": len(paginas),
                "n_paginas_renderizadas": doc["n_paginas_renderizadas"],
                "cobertura_completa_VERIFICADA": doc["cobertura_completa_VERIFICADA"]}
        for nombre, respuestas in por_lector.items():
            fila[nombre] = respuestas
            fila[f"{nombre}_acierta"] = any(acierta(r, esperado) for r in respuestas)
        fila["acuerdan_los_tres"] = all(fila.get(f"{n}_acierta") for n in por_lector)
        filas.append(fila)
        marca = "".join(("GCP"[j] if fila.get(f"{n}_acierta") else "·")
                        for j, n in enumerate(("gemini", "claude", "gpt")))
        print(f"  [{i}/{len(objetivo)}] {fich[:38]:40s} esp={esperado[:14]:16s} {marca}")
        SALIDA.write_text(json.dumps({"filas": filas}, ensure_ascii=False, indent=1), "utf-8")

    n = len(filas)
    res = {k: sum(1 for f in filas if f.get(f"{k}_acierta")) for k in ("gemini", "claude", "gpt")}
    print(f"\n=== RESULTADO (unidad = DOCUMENTO, n={n}) ===")
    for k, v in res.items():
        print(f"  {k:8s} {v}/{n}")
    print(f"  los tres de acuerdo: {sum(1 for f in filas if f['acuerdan_los_tres'])}/{n}")
    SALIDA.write_text(json.dumps(
        {"que_es": "Sonda multimodal v2 (s336). Arregla los 3 defectos que el dúo r41 señaló en "
                   "la v1: cobertura verificada contra pdf_page_count, unidad = DOCUMENTO (n "
                   "independientes) y guardarraíl anti-fuga con auto-test. Patrón de PLATA "
                   "(nombre de fichero, R8 dice que miente). NADA aplicado.",
         "modelos": {"gemini": GEMINI, "claude": CLAUDE, "gpt": GPT},
         "n_documentos": n, "aciertos": res,
         "acuerdan_los_tres": sum(1 for f in filas if f["acuerdan_los_tres"]),
         "filas": filas}, ensure_ascii=False, indent=1), "utf-8")
    print(f"\n→ {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
