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
#: El progreso EN VUELO va a un fichero temporal, no al recibo versionado. Escribir
#: cada fila directamente en `evals/` deja el árbol de git sucio durante toda la
#: corrida y obliga a commitear instantáneas a medias que no son un resultado.
#: El recibo de `evals/` se escribe UNA vez, al final.
PARCIAL = Path(os.environ.get("TMPDIR", "/tmp")) / "s336_sonda_parcial.json"

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

#: PREFERENCIA DE ALBERTO (s336e): entre Anthropic y Gemini, **Anthropic**.
#: Así que el orden de lectura empieza por Claude y Gemini deja de ser un lector
#: por defecto — se pide explícitamente con `LECTORES=claude,gpt,gemini`. El
#: cross-model sigue intacto (Claude + GPT ya son dos familias distintas, que es
#: lo que hace del acuerdo una evidencia y no una opinión); lo que cambia es
#: cuál se usa cuando hay que elegir, no que haya uno solo.
LECTORES = [x.strip() for x in
            os.environ.get("LECTORES", "claude,gpt").split(",") if x.strip()]
#: `3.6-flash` gastó su cuota LIBRE del día; los `lite` son los que el free tier
#: sirve con holgura y leen imagen igual (verificado con un PNG real, no supuesto).
GEMINI = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
#: Páginas leídas por documento. ACOTADO y DECLARADO: el nombre del modelo vive en
#: la portada y las primeras páginas, así que 3 basta para el resultado POSITIVO
#: («la página recupera el nombre»). Para el NEGATIVO no basta —y por eso el
#: negativo sólo se interpreta en los documentos con cobertura completa, que aquí
#: son 3 y tienen 1-2 páginas: en ésos se leen TODAS.
TOPE_PAGINAS = 3
#: Los dos 429 de Gemini NO son el mismo hecho y confundirlos fue mi error:
#:   · `...PerMinute...`  → ventana; se espera y se reintenta.
#:   · `...PerDay...`     → la cuota LIBRE del día se acabó; esperar no sirve de
#:                          nada y reintentar sólo maquilla el recibo.
#: La primera corrida perdió 58 de 61 llamadas contra el cap DIARIO (quotaId
#: `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, quotaValue 20) y yo lo
#: leí como si fuera por minuto. Aquí se separan por `quotaId`, y el diario
#: APAGA el lector para el resto de la corrida con un veredicto propio
#: (`CUOTA_DIARIA_AGOTADA`) que NUNCA puede leerse como «no lo vio».
GEMINI_RPM = int(os.environ.get("GEMINI_RPM", "20"))
_ultima_gemini = [0.0]
_gemini_agotado = [False]


class CuotaDiaria(RuntimeError):
    """La cuota libre del día se agotó: no es un fallo de lectura."""
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


def _violaciones(r: httpx.Response) -> list[dict]:
    try:
        det = r.json().get("error", {}).get("details", [])
    except Exception:                                          # noqa: BLE001
        return []
    return [v for x in det if "QuotaFailure" in x.get("@type", "")
            for v in x.get("violations", [])]


def _es_cuota_diaria(r: httpx.Response) -> bool:
    """`PerDay` en el quotaId: esperar no lo arregla. `PerMinute`: sí."""
    return any("PerDay" in (v.get("quotaId") or "") for v in _violaciones(r))


def _cuota_txt(r: httpx.Response) -> str:
    return " · ".join(f"{v.get('quotaId')}={v.get('quotaValue')}" for v in _violaciones(r))


def lee_gemini(img: bytes, mime: str, esperado: str, fichero: str, url: str) -> dict:
    payload = {"contents": [{"parts": [
        {"inline_data": {"mime_type": mime, "data": base64.b64encode(img).decode()}},
        {"text": PROMPT}]}]}
    sin_fuga(payload, esperado, fichero, url)
    if _gemini_agotado[0]:
        raise CuotaDiaria("cuota libre del día agotada antes de esta página")
    # Paso derivado del límite por minuto, no inventado: 20 rpm → 3,0 s.
    espera = max(0.0, 60.0 / GEMINI_RPM - (time.monotonic() - _ultima_gemini[0]))
    if espera:
        time.sleep(espera)
    for intento in range(4):
        _ultima_gemini[0] = time.monotonic()
        r = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI}:generateContent",
            headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"],
                     "Content-Type": "application/json"}, json=payload, timeout=240)
        if r.status_code == 429 and _es_cuota_diaria(r):
            _gemini_agotado[0] = True
            raise CuotaDiaria(f"{GEMINI}: cuota libre DIARIA agotada · {_cuota_txt(r)}")
        if r.status_code not in (429, 503) or intento == 3:
            break
        # La API dice cuánto esperar («Please retry in 35.87s»): se le hace caso.
        m = re.search(r"retry in ([0-9.]+)s", r.text)
        time.sleep(float(m.group(1)) + 1.0 if m else 8.0 * (intento + 1))
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


def estado(respuestas: list[dict], esperado: str) -> str:
    """Tres estados, no un booleano. El booleano es lo que produjo «gemini 0/37»
    en la v2a: un documento cuyas llamadas fallaron TODAS puntuaba igual que uno
    leído entero sin encontrar el nombre. Un fallo de infraestructura no es un
    dato negativo, y la única forma de que no vuelva a colarse en el recibo es
    que no comparta celda con él."""
    if any(acierta(r, esperado) for r in respuestas):
        return "ACIERTA"
    if not any("error" not in r for r in respuestas):
        return "SIN_LECTURA"          # ninguna página se llegó a leer → no interpretable
    return "NO_LO_VE"


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
        por_lector = {n: [] for n in LECTORES}
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
            todos = {"claude": lee_claude, "gpt": lee_gpt, "gemini": lee_gemini}
            for nombre, fn in ((n, todos[n]) for n in LECTORES if n in todos):
                try:
                    por_lector[nombre].append(fn(im.content, mime, esperado, fich, url))
                except Fuga:
                    raise
                except CuotaDiaria as e:
                    por_lector[nombre].append({"error": f"CUOTA_DIARIA_AGOTADA: {e}"})
                except Exception as e:                         # noqa: BLE001
                    por_lector[nombre].append({"error": str(e)[:160]})
                time.sleep(0.4)
        fila = {"document_id": doc["document_id"], "source_file": fich, "esperado": esperado,
                "n_paginas_leidas": len(paginas),
                "n_paginas_renderizadas": doc["n_paginas_renderizadas"],
                "cobertura_completa_VERIFICADA": doc["cobertura_completa_VERIFICADA"]}
        for nombre, respuestas in por_lector.items():
            fila[nombre] = respuestas
            fila[f"{nombre}_estado"] = estado(respuestas, esperado)
            fila[f"{nombre}_acierta"] = fila[f"{nombre}_estado"] == "ACIERTA"
        # «De acuerdo» sólo entre los que de verdad LEYERON: si uno no leyó, no
        # hay acuerdo ni desacuerdo con él, hay ausencia.
        leyeron = [n for n in por_lector if fila[f"{n}_estado"] != "SIN_LECTURA"]
        fila["lectores_que_leyeron"] = leyeron
        fila["acuerdan_los_que_leyeron"] = (
            bool(leyeron) and all(fila[f"{n}_acierta"] for n in leyeron))
        filas.append(fila)
        # G=acierta · ·=leyó y no lo ve · x=NO llegó a leer (no es un negativo)
        marca = "".join((n[0].upper() if fila[f"{n}_estado"] == "ACIERTA"
                         else ("x" if fila[f"{n}_estado"] == "SIN_LECTURA" else "·"))
                        for n in LECTORES)
        print(f"  [{i}/{len(objetivo)}] {fich[:38]:40s} esp={esperado[:14]:16s} {marca}")
        PARCIAL.write_text(json.dumps({"filas": filas}, ensure_ascii=False, indent=1), "utf-8")

    n = len(filas)
    # El DENOMINADOR es lo que el lector llegó a leer, no la población. Un lector
    # que no leyó nada sale como «no evaluable», nunca como 0 aciertos.
    res = {}
    for k in LECTORES:
        leidos = [f for f in filas if f[f"{k}_estado"] != "SIN_LECTURA"]
        res[k] = {"acierta": sum(1 for f in leidos if f[f"{k}_acierta"]),
                  "leidos": len(leidos), "sin_lectura": n - len(leidos)}
    print(f"\n=== RESULTADO (unidad = DOCUMENTO, población={n}) ===")
    for k, v in res.items():
        if not v["leidos"]:
            print(f"  {k:8s} NO EVALUABLE · 0 documentos leídos ({v['sin_lectura']} sin lectura)")
        else:
            cola = f"  ({v['sin_lectura']} sin lectura, fuera del denominador)" if v["sin_lectura"] else ""
            print(f"  {k:8s} {v['acierta']}/{v['leidos']} leídos{cola}")
    coinciden = [f for f in filas if len(f["lectores_que_leyeron"]) >= 2]
    print(f"  de acuerdo entre los que leyeron (≥2 lectores): "
          f"{sum(1 for f in coinciden if f['acuerdan_los_que_leyeron'])}/{len(coinciden)}")
    SALIDA.write_text(json.dumps(
        {"que_es": "Sonda multimodal v2 (s336). Arregla los 3 defectos que el dúo r41 señaló en "
                   "la v1: cobertura verificada contra pdf_page_count, unidad = DOCUMENTO (n "
                   "independientes) y guardarraíl anti-fuga con auto-test. Patrón de PLATA "
                   "(nombre de fichero, R8 dice que miente). NADA aplicado.",
         "lectores": LECTORES,
         "modelos": {"claude": CLAUDE, "gpt": GPT, "gemini": GEMINI},
         "n_documentos": n, "aciertos": res,
         "como_leer_aciertos": "por lector: acierta / leidos. `sin_lectura` son documentos "
                               "donde NINGUNA llamada devolvió lectura (cuota, crédito, red): "
                               "quedan FUERA del denominador — no son negativos.",
         "acuerdan_los_que_leyeron": sum(1 for f in filas
                                         if len(f["lectores_que_leyeron"]) >= 2
                                         and f["acuerdan_los_que_leyeron"]),
         "filas": filas}, ensure_ascii=False, indent=1), "utf-8")
    print(f"\n→ {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
