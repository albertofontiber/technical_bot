#!/usr/bin/env python3
"""s334 — SONDA MULTIMODAL: ¿recupera una lectura de la PÁGINA los nombres de
modelo que la extracción de texto perdió?

LA PREGUNTA, y por qué NO es la del dúo anterior. La ronda r40 midió «¿un juez
mejor clasifica mejor nuestros chunks?» y la respuesta fue que no: lo vinculante
era la rúbrica, no el modelo. Ésta es otra pregunta y otra capacidad — **leer la
imagen de la página**, no opinar otra vez sobre el mismo texto. Nace de una
observación empírica de Alberto («Gemini parece que hace mejor la detección de
modelos cuando le he subido pdf sin nombres de modelos») y del caso `MAD-491`,
cuyo manual está en el corpus, cuyo texto extraído sólo dice «MÓDULO AISLADOR» y
«REF: 55349102», y cuyo modelo real sólo sobrevive en el nombre del fichero.

EL PATRÓN ORO, y por qué es de PLATA. Para esta población el nombre del modelo
está en el NOMBRE DEL FICHERO (`…Manual Modulo Aislador MAD-491 ES FR GB IT`),
así que se puede puntuar sin adjudicación humana — que es justo el coste que el
dúo r40 (Fable F3) señaló como no presupuestado. Pero **R8 dice que el nombre del
fichero miente** (el caso `D838-1_kac sounders`), así que esto es un patrón de
PLATA, no de oro, y se declara: un fallo puede ser del lector O del patrón. Los
dos lectores lo desambiguan en parte — si ambos coinciden en OTRA respuesta, la
sospecha recae sobre el patrón.

LOS TRES GUARDARRAÍLES, que son lo que hace que la cifra valga algo:

  1. **CERO FUGA.** Al modelo se le mandan los BYTES de la imagen y nada más. Ni
     el nombre del fichero, ni la URL (que contiene el nombre del fichero), ni el
     modelo esperado, ni la marca. Se comprueba en `_sin_fuga()` antes de cada
     llamada: si el token esperado aparece en el prompt, el script ABORTA.
  2. **GRUPO DE CONTROL.** Se leen también documentos cuyo token SÍ está en el
     texto. Si los lectores fallan también ahí, un fallo en los perdidos no dice
     nada del multimodal: dice que el instrumento no sirve.
  3. **DOS FAMILIAS.** Claude y GPT sobre la MISMA imagen. Una sola familia
     comparte puntos ciegos — es la misma razón por la que el Protocolo 3 exige
     cross-model. (Gemini, que es lo que Alberto observó, no tiene clave en este
     entorno: se declara como limitación. Si estas dos ya recuperan los nombres,
     la capacidad queda confirmada y Gemini sería optimización, no requisito.)

NO escribe en el catálogo. Produce un recibo con cada respuesta cruda.

Uso:
  python scripts/s334_sonda_multimodal_lector.py [--limite N] [--solo-control]
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)

POBLACION = ROOT / "evals/s334_sonda_multimodal_poblacion_v1.json"
RECIBO = ROOT / "evals/s334_sonda_multimodal_resultado_v1.json"

#: La pregunta va EN FRÍO: no se nombra ningún modelo, ni la marca, ni se sugiere
#: que haya que encontrar algo. Preguntar «¿es esto el MAD-491?» mediría otra cosa
#: (reconocimiento con pista), no recuperación.
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

MODELO_CLAUDE = "claude-fable-5"
MODELO_GPT = "gpt-5.6-sol"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _sin_fuga(prompt: str, esperado: str, extra: str = "") -> None:
    """ABORTA si el token esperado —o el nombre del fichero— viajan en el prompt.

    Es el guardarraíl del que depende toda la sonda: si el modelo puede leer el
    nombre del fichero, la medida no vale nada y encima parece buena."""
    tn = _norm(esperado)
    if tn and tn in _norm(prompt + extra):
        raise SystemExit(
            f"FUGA: el token esperado «{esperado}» aparece en lo que se le manda "
            f"al modelo. La sonda quedaría invalidada; se aborta.")


def _imagen(url: str) -> tuple[bytes, str]:
    r = httpx.get(url, timeout=90)
    r.raise_for_status()
    return r.content, r.headers.get("content-type", "image/jpeg").split(";")[0]


def _json_de(texto: str) -> dict:
    """La respuesta debería ser JSON puro; si el modelo lo envuelve, se rescata."""
    t = (texto or "").strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.MULTILINE).strip()
    try:
        return json.loads(t)
    except Exception:                                       # noqa: BLE001
        m = re.search(r"\{.*\}", t, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:                               # noqa: BLE001
                pass
    return {"modelos": [], "confianza": "baja", "donde": "", "_crudo": t[:400]}


def lee_claude(img: bytes, mime: str) -> dict:
    from anthropic import Anthropic
    cli = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY_SCRIPTS")
                    or os.environ["ANTHROPIC_API_KEY"])
    r = cli.messages.create(
        model=MODELO_CLAUDE, max_tokens=600,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": mime,
                                         "data": base64.b64encode(img).decode()}},
            {"type": "text", "text": PROMPT}]}])
    return _json_de("".join(b.text for b in r.content if b.type == "text"))


def lee_gpt(img: bytes, mime: str) -> dict:
    from openai import OpenAI
    cli = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    r = cli.responses.create(
        model=MODELO_GPT, store=False,
        input=[{"role": "user", "content": [
            {"type": "input_text", "text": PROMPT},
            {"type": "input_image",
             "image_url": f"data:{mime};base64,{base64.b64encode(img).decode()}"}]}])
    return _json_de(r.output_text)


def acierta(respuesta: dict, esperado: str) -> bool:
    """¿Está el modelo esperado entre los que devolvió el lector?

    Comparación NORMALIZADA y por contención en los dos sentidos: `MAD-491` casa
    con `MAD 491` y con `Módulo aislador MAD-491`. Deliberadamente generosa: la
    sonda pregunta si la lectura RECUPERA el nombre, no si lo formatea igual."""
    e = _norm(esperado)
    if not e:
        return False
    for m in respuesta.get("modelos") or []:
        n = _norm(str(m))
        if n and (e in n or n in e):
            return True
    return False


def main() -> int:
    if not POBLACION.exists():
        raise SystemExit(f"falta {POBLACION} — corre primero la población")
    pob = json.loads(POBLACION.read_text("utf-8"))
    limite = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else 0

    tandas = [("control", pob.get("controles", [])),
              ("perdido", [] if "--solo-control" in sys.argv else pob["medibles"])]

    previo = json.loads(RECIBO.read_text("utf-8")) if RECIBO.exists() else {"filas": []}
    hechos = {(f["grupo"], f["id"]) for f in previo["filas"]}
    filas = list(previo["filas"])

    for grupo, items in tandas:
        if limite:
            items = items[:limite]
        for i, it in enumerate(items, 1):
            if (grupo, it["id"]) in hechos:
                continue
            pag = it["paginas"][0]
            url, esperado = pag["storage_url"], it["canonico"]
            # GUARDARRAÍL 1: nada del nombre del fichero viaja al modelo.
            _sin_fuga(PROMPT, esperado, extra="")
            try:
                img, mime = _imagen(url)
            except Exception as e:                          # noqa: BLE001
                filas.append({"grupo": grupo, "id": it["id"], "canonico": esperado,
                              "error": f"imagen: {e}"})
                continue
            fila = {"grupo": grupo, "id": it["id"], "canonico": esperado,
                    "source_file": it["source_file"], "page_index": pag["page_index"],
                    "visual_role": pag["visual_role"]}
            for nombre, fn in (("claude", lee_claude), ("gpt", lee_gpt)):
                try:
                    resp = fn(img, mime)
                    fila[nombre] = resp
                    fila[f"{nombre}_acierta"] = acierta(resp, esperado)
                except Exception as e:                      # noqa: BLE001
                    fila[nombre] = {"error": str(e)[:220]}
                    fila[f"{nombre}_acierta"] = None
                time.sleep(0.3)
            filas.append(fila)
            RECIBO.write_text(json.dumps({"filas": filas}, ensure_ascii=False, indent=1), "utf-8")
            ok = ("C" if fila.get("claude_acierta") else "·") + \
                 ("G" if fila.get("gpt_acierta") else "·")
            print(f"  [{grupo} {i}/{len(items)}] {it['id'][:34]:36s} {ok}", flush=True)

    _resumen(filas)
    return 0


def _resumen(filas: list[dict]) -> None:
    salida = {"que_es": "Sonda multimodal s334. Patrón de PLATA (nombre de fichero). "
                        "Cero fuga verificada. NADA aplicado.",
              "modelos": {"claude": MODELO_CLAUDE, "gpt": MODELO_GPT},
              "limitacion_declarada": "Gemini —lo que observó Alberto— no tiene clave "
                                      "en este entorno; se mide con las dos familias "
                                      "disponibles.",
              "resumen": {}, "filas": filas}
    print("\n=== RESULTADO ===")
    for grupo in ("control", "perdido"):
        g = [f for f in filas if f.get("grupo") == grupo and "error" not in f]
        if not g:
            continue
        c = sum(1 for f in g if f.get("claude_acierta"))
        p = sum(1 for f in g if f.get("gpt_acierta"))
        amb = sum(1 for f in g if f.get("claude_acierta") and f.get("gpt_acierta"))
        alg = sum(1 for f in g if f.get("claude_acierta") or f.get("gpt_acierta"))
        salida["resumen"][grupo] = {"n": len(g), "claude": c, "gpt": p,
                                    "ambos": amb, "alguno": alg}
        print(f"  {grupo:8s} n={len(g):3d}  Claude {c}/{len(g)}  GPT {p}/{len(g)}  "
              f"ambos {amb}  alguno {alg}")
    RECIBO.write_text(json.dumps(salida, ensure_ascii=False, indent=1), "utf-8")
    print(f"\n→ {RECIBO}")


if __name__ == "__main__":
    raise SystemExit(main())
