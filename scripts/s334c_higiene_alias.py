#!/usr/bin/env python3
"""s334c — CENSO de higiene de `aliases.jsonl` (TECH_DEBT #99), medido.

POR QUÉ BLOQUEA. El trigger de #99 dice: cuando un lote de promoción active más
de 20 alias, pasada de higiene **antes** del siguiente lote grande. El lote de
huérfanos activa 85 hasta en su versión más conservadora, así que esto va primero.
Y el dúo r43 (Fable) dio los casos concretos: la excepción «nombre-largo CON
dígito» de `catalog_resolver._add` deja entrar al detector frases genéricas como
«1 Relay Module», «2 Zones Module» o «Caja de central de tamaño 10U», que son
vocabulario de CUALQUIER fabricante — y mi recuento con frontera de palabra se
había hecho sólo sobre los 25 términos que el censo flageaba.

CÓMO SE DECIDE, y por qué NO es por regex de «suena genérico». Un identificador
de producto aparece en los pocos documentos que hablan de él; una frase genérica
se reparte por el corpus. Se cuenta en cuántos `source_file` DISTINTOS aparece
cada alias **con frontera de palabra** —que es como lo busca el detector— y en
cuántos FABRICANTES distintos. Un alias que sale en varias marcas no identifica
un producto: identifica una categoría.

  · La primera vez que hice este recuento usé `ilike *X*` (SUBSTRING) y habría
    tirado `ITAC` (270 documentos → **11** con frontera: casaba dentro de
    «capaci*tac*ión») y `NAS` (231 → 11). Medir con un operador distinto del que
    usa el consumidor es la forma silenciosa de equivocarse.

SEÑALES MECÁNICAS que se declaran aparte del recuento (no deciden solas):
  · CÓDIGO DE EDICIÓN documental (`MU 591 m 2024 a`, `MI-DT-951_V7.2`)
  · CADENA DE VERSIÓN (`Programa Fuera Linea Version 2.1`, `TG-6000 VER 3.2`)
  · FRASE CON ARTÍCULO (`La central AM-200`) — el canónico ya la cubre

NO escribe. Produce el censo que alimenta el lote de higiene.

Uso:  python scripts/s334c_higiene_alias.py [--limite N]
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ["IDENTITY_RESOLVE"] = "on"

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY      # noqa: E402
from src.rag import catalog_resolver as R                      # noqa: E402
from src.rag import catalog_store as cs                        # noqa: E402

H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
SALIDA = ROOT / "evals/s334c_higiene_alias_v1.json"

#: A partir de cuántos documentos DISTINTOS (con frontera) un alias deja de
#: parecer un identificador. Umbral declarado, no oculto: se eligió mirando la
#: distribución de los términos ya conocidos (`VIEW` 331 · `INDICATOR` 260 ·
#: `ITAC` 11 · `NAS` 11), y el censo publica la cifra de cada uno para que
#: cualquiera pueda mover la raya y recontar.
TOPE_DOCS = 25
#: Un alias que sale en documentos de VARIOS fabricantes no identifica un
#: producto: identifica una categoría. Es la señal más fuerte de las dos.
TOPE_MARCAS = 3

#: LA SEÑAL PRINCIPAL, y la que responde a lo que el dúo señaló de verdad. El
#: recuento por corpus mide DISPERSIÓN, y el problema de «1 Relay Module» no es
#: que se disperse —sale en pocos documentos— sino que es **vocabulario de
#: cualquier fabricante**: un técnico de Morley que escriba «el módulo de 2 relés»
#: acabaría en un producto de Notifier. Eso se ve en la FORMA, no en la
#: frecuencia: un identificador de producto tiene al menos un token CON FORMA DE
#: MODELO —letras y dígitos juntos (`AM-200`, `ZX2e`, `10U`)—; una descripción no
#: tiene ninguno, sólo palabras corrientes y números sueltos.
#:
#: `10U` SÍ tiene forma de modelo, así que «Caja de central de tamaño 10U» no cae
#: por esta señal; cae por la de abajo (todas sus demás palabras son corrientes).
#: Por eso las dos señales se declaran por separado y ninguna decide sola.
MODELO_SHAPE = re.compile(r"^(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*\d)[A-Za-z0-9]+$")
#: Palabras que por sí solas no identifican nada: son la categoría del producto o
#: la lengua del manual. Salen del vocabulario REAL de los alias del catálogo, no
#: de un diccionario general.
CORRIENTES = {
    "module", "modulo", "módulo", "relay", "rele", "relé", "relés", "zone", "zones",
    "zona", "zonas", "input", "output", "entrada", "salida", "unit", "unidad",
    "card", "tarjeta", "panel", "central", "caja", "box", "detector", "sensor",
    "sirena", "sounder", "base", "kit", "series", "serie", "de", "del", "la", "el",
    "los", "las", "con", "y", "and", "with", "for", "para", "type", "tipo",
    "supervised", "supervisado", "expansion", "expansor", "tamaño", "size",
    "siren", "sirens", "sirenas", "outputs", "output", "inputs", "salidas", "entradas",
    "sounders", "modules", "modulos", "módulos", "cards", "units", "zocalo", "zócalo",
    "aislador", "isolator", "interface", "interfaz", "remoto", "remote", "indicador",
    "indicator", "pulsador", "optico", "óptico", "termico", "térmico", "convencional",
    "conventional", "addressable", "direccionable", "installation", "instalacion",
    "single", "double", "simple", "doble", "analogico", "analógico", "conexion",
    "conexión", "modelo", "model", "version", "versión", "manual", "guia", "guía",
}

EDICION = re.compile(r"\b(MU|MI|MN|MA|DT)[\s.-]?\d{2,4}\b.*\b(19|20)\d{2}\b|_?[Vv]\d+\.\d+", re.I)
VERSION = re.compile(r"\b(ver|version|versión|rev|v)\W?\s?\d", re.I)
ARTICULO = re.compile(r"^(el|la|los|las|un|una)\s+", re.I)


def _pag(c: httpx.Client, tabla: str, params: dict, tope: int = 3000) -> list[dict]:
    out, off = [], 0
    while len(out) < tope:
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
    return out


def main() -> int:
    limite = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else 0
    cat = cs.load()
    R._loaded = False
    R._pattern = None
    R._build()
    terminos = R._resolvable_terms(cat)
    nk_detector = set(terminos)

    # los alias que HOY entran (o entrarían al promover su producto) en el detector
    candidatos = []
    for a in cat.aliases:
        alias = a.get("alias") or ""
        if not alias or len(alias) < 4:
            continue
        # la puerta real de `_add`: tipo elegible O con dígito
        if a.get("tipo") not in R.DETECT_ALIAS_TIPOS and not any(c.isdigit() for c in alias):
            continue
        candidatos.append(a)
    print(f"alias que la puerta de `_add` deja entrar: {len(candidatos)}")
    if limite:
        candidatos = candidatos[:limite]

    marca_de_doc: dict[str, str] = {}
    with httpx.Client(timeout=180) as c:
        docs = _pag(c, "documents", {"select": "source_pdf_filename,manufacturer",
                                     "status": "eq.active"}, tope=3000)
        for d in docs:
            marca_de_doc[str(d.get("source_pdf_filename") or "")] = str(d.get("manufacturer") or "")

        filas = []
        for i, a in enumerate(candidatos, 1):
            alias = a["alias"]
            r = c.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=H,
                      params={"select": "source_file,content",
                              "content": f"ilike.*{alias}*", "limit": "2000"})
            crudo = r.json() if r.status_code == 200 else []
            pat = re.compile(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])", re.I)
            sfs = {x["source_file"] for x in crudo if pat.search(x.get("content") or "")}
            marcas = {marca_de_doc.get(s, "") for s in sfs} - {""}
            señales = []
            if EDICION.search(alias):
                señales.append("codigo-de-edicion")
            if VERSION.search(alias):
                señales.append("cadena-de-version")
            if ARTICULO.match(alias):
                señales.append("frase-con-articulo")
            palabras = re.findall(r"[A-Za-z0-9ñÑáéíóúÁÉÍÓÚ]+", alias)
            con_forma = [w for w in palabras if MODELO_SHAPE.match(w)]
            resto = [w for w in palabras if w.lower() not in CORRIENTES
                     and not w.isdigit() and w not in con_forma]
            if not con_forma:
                señales.append("sin-token-con-forma-de-modelo")
            if not resto and not con_forma:
                señales.append("solo-palabras-corrientes")
            # LA REGLA, corregida tras leer su propia salida (s334c). La primera
            # versión marcó 82 y al mirarlos uno a uno se pasaba de frenada en dos
            # clases enteras — la misma forma de error que G1-G6 nombran, ahora en
            # mi instrumento de higiene:
            #
            #  · **56 de los 82 eran alias PURAMENTE NUMÉRICOS** (`020-579`,
            #    `55347200`, `7251`). Los marcaba «sin token con forma de modelo»
            #    y **ninguno entra hoy al detector**: `_add` descarta los tokens
            #    digit-only a propósito (`segs.isdigit()`). Retirar lo que no
            #    puede disparar es ruido, y encima destruye números de parte
            #    legítimos que un técnico sí escribe.
            #  · **`n_marcas` marcaba CROSS-REFERENCES como si fueran categorías.**
            #    `AFP400` sale en documentos de Morley, Notifier y Xtralis porque
            #    las centrales de una marca se citan en los manuales de otra —
            #    eso es una referencia cruzada, no vocabulario genérico. Lo mismo
            #    `AM2000`, `8100E`, `TG-ID3000`.
            #
            # Lo que queda es lo que el dúo señaló de verdad y sólo eso: un alias
            # se retira si es una DESCRIPCIÓN —varias palabras, ninguna con forma
            # de modelo, ninguna propia— **y además puede llegar al detector**. La
            # dispersión y el número de marcas se siguen midiendo y publicando,
            # pero como CORROBORACIÓN, no como gatillo.
            solo_numerico = not re.search(r"[A-Za-z]", alias)
            descripcion = (not con_forma and not resto and len(palabras) > 1
                           and not solo_numerico)
            veredicto = "GENERICO" if descripcion else "identificador"
            if solo_numerico:
                señales.append("solo-numerico-INERTE-en-el-detector")
            filas_extra = {"palabras_con_forma_de_modelo": con_forma,
                           "palabras_propias": resto}
            filas.append({**filas_extra,
                          "alias": alias, "id": a["id"], "tipo": a.get("tipo"),
                          "docs_frontera": len(sfs), "docs_substring": len(crudo),
                          "marcas": sorted(marcas)[:6], "n_marcas": len(marcas),
                          "senales": señales, "veredicto": veredicto,
                          "ya_en_detector": cs.norm_token(alias) in nk_detector})
            if i % 25 == 0:
                print(f"  …{i}/{len(candidatos)}", flush=True)

    gen = [f for f in filas if f["veredicto"] == "GENERICO"]
    print(f"\n=== CENSO DE HIGIENE ===")
    print(f"  examinados ................... {len(filas)}")
    print(f"  GENÉRICOS (a retirar) ........ {len(gen)}")
    print(f"     de ellos ya en el detector  {sum(1 for f in gen if f['ya_en_detector'])}")
    for f in sorted(gen, key=lambda x: -x["docs_frontera"])[:25]:
        print(f"    {f['alias'][:44]:46s} docs={f['docs_frontera']:4d} marcas={f['n_marcas']:2d} "
              f"{f['senales']} → {f['id']}")
    por_señal = defaultdict(int)
    for f in filas:
        for s in f["senales"]:
            por_señal[s] += 1
    print(f"\n  señales mecánicas (se declaran, NO deciden solas): {dict(por_señal)}")

    SALIDA.write_text(json.dumps(
        {"que_es": "Censo de higiene de aliases.jsonl (TECH_DEBT #99). El veredicto GENERICO se "
                   "MIDE: documentos distintos con FRONTERA DE PALABRA y nº de fabricantes. "
                   "NADA aplicado.",
         "umbrales": {"docs": TOPE_DOCS, "marcas": TOPE_MARCAS},
         "resumen": {"examinados": len(filas), "genericos": len(gen),
                     "genericos_ya_en_detector": sum(1 for f in gen if f["ya_en_detector"]),
                     "senales": dict(por_señal)},
         "filas": filas}, ensure_ascii=False, indent=1), "utf-8")
    print(f"\n→ {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
