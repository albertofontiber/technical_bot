# -*- coding: utf-8 -*-
"""Regenera `dashboard/fuente_marca.py`: descarga Playfair Display y la recorta.

POR QUÉ EXISTE. El módulo que genera lleva 4 KB de base64 que nadie puede
auditar a ojo. Sin una forma de reproducirlo, esos bytes son un binario opaco
en el repo — «confía en mí», que es justo lo que el resto del proyecto evita.
Con esto, cualquiera puede volver a generarlo y comparar.

QUÉ HACE, en orden: pide a Google el CSS de la familia, se queda con la URL del
subconjunto **latino del peso 400**, descarga ese `.woff2`, lo recorta a los
caracteres que se le pasen (por defecto, los del logotipo de la puerta) y
reescribe el módulo con el base64 resultante. La red se usa AQUÍ, en una
herramienta que corre a mano; el panel servido no le pide nada a nadie.

LICENCIA: Playfair Display es SIL OFL 1.1, que permite incrustarla. El aviso de
copyright viaja dentro del propio `.woff2` (`name` IDs 0 y 14) y el recorte los
conserva a propósito (`name_IDs` incluye 0, 13 y 14).

Uso:
    python -m scripts.s328c_recortar_fuente_marca              # texto por defecto
    python -m scripts.s328c_recortar_fuente_marca --texto "Fontiber Bot PCI"
    python -m scripts.s328c_recortar_fuente_marca --comprobar  # no escribe: compara
"""
from __future__ import annotations

import argparse
import base64
import re
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "dashboard/fuente_marca.py"

CSS_URL = ("https://fonts.googleapis.com/css2"
           "?family=Playfair+Display:wght@400&display=swap")
#: Un navegador moderno, o Google devuelve `ttf` en vez de `woff2`.
AGENTE = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

#: El texto del logotipo de la puerta, con su espacio duro. Cambiarlo obliga a
#: regenerar: un glifo que falte cae a la serif del sistema y el titular sale
#: con dos tipografías (lo cruza `test_s328c_la_fuente_cubre_el_logotipo`).
TEXTO_POR_DEFECTO = "Fontiber Bot PCI"


def _url_latin_400() -> str:
    peticion = urllib.request.Request(CSS_URL, headers={"User-Agent": AGENTE})
    css = urllib.request.urlopen(peticion, timeout=30).read().decode("utf-8")
    for nombre, cuerpo in re.findall(r"/\* (\S+) \*/\s*@font-face \{(.*?)\}",
                                     css, re.S):
        if nombre == "latin" and "font-weight: 400" in cuerpo:
            return re.search(r"url\((https://[^)]+\.woff2)\)", cuerpo).group(1)
    raise RuntimeError("no se encontró el subconjunto latino del peso 400")


def recortar(texto: str) -> bytes:
    from fontTools import subset
    from fontTools.ttLib import TTFont

    url = _url_latin_400()
    peticion = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    completo = urllib.request.urlopen(peticion, timeout=30).read()

    import io
    fuente = TTFont(io.BytesIO(completo))
    opciones = subset.Options()
    opciones.flavor = "woff2"
    opciones.desubroutinize = True
    opciones.layout_features = ["kern", "liga"]
    opciones.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14]   # conserva la licencia
    opciones.notdef_outline = False
    recortador = subset.Subsetter(options=opciones)
    recortador.populate(text=texto)
    recortador.subset(fuente)
    salida = io.BytesIO()
    fuente.flavor = "woff2"
    fuente.save(salida)
    return salida.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--texto", default=TEXTO_POR_DEFECTO)
    parser.add_argument("--comprobar", action="store_true",
                        help="no escribe: dice si lo versionado coincide")
    args = parser.parse_args(argv)

    crudo = recortar(args.texto)
    b64 = base64.b64encode(crudo).decode("ascii")
    print(f"subconjunto: {len(crudo)} bytes · base64 {len(b64)} chars · "
          f"glifos {sorted(set(args.texto))}")

    if args.comprobar:
        sys.path.insert(0, str(RAIZ))
        from dashboard.fuente_marca import PLAYFAIR_PUERTA_B64

        # Los bytes de woff2 NO son reproducibles bit a bit (la compresión
        # brotli y el orden de tablas pueden variar entre versiones de
        # fontTools), así que se compara lo que IMPORTA: el juego de glifos.
        import io

        from fontTools.ttLib import TTFont
        nuevo = {chr(c) for c in TTFont(io.BytesIO(crudo)).getBestCmap()}
        viejo = {chr(c) for c in TTFont(
            io.BytesIO(base64.b64decode(PLAYFAIR_PUERTA_B64))).getBestCmap()}
        if nuevo == viejo:
            print("COINCIDE: mismo juego de glifos que lo versionado")
            return 0
        print(f"DIFIERE · solo en el nuevo: {sorted(nuevo - viejo)} · "
              f"solo en el versionado: {sorted(viejo - nuevo)}", file=sys.stderr)
        return 1

    texto = DESTINO.read_text(encoding="utf-8")
    trozos = [b64[i:i + 76] for i in range(0, len(b64), 76)]
    bloque = "\n".join(f'    "{t}"' for t in trozos)
    # Sustituciones con LAMBDA, no con plantilla: el juego de glifos lleva un
    # espacio duro y `re.sub` lee la cadena de reemplazo COMO plantilla, así
    # que lo tomaba por un escape inválido («bad escape \u»). Mordió a la
    # primera, al regenerar el módulo por primera vez con el propio script.
    texto = re.sub(r"PLAYFAIR_PUERTA_B64 = \(\n.*?\n\)",
                   lambda _: f"PLAYFAIR_PUERTA_B64 = (\n{bloque}\n)",
                   texto, flags=re.S)
    glifos = "".join(sorted(set(args.texto))).replace("\xa0", "\\u00a0")
    texto = re.sub(r'GLIFOS = ".*"', lambda _: f'GLIFOS = "{glifos}"', texto)
    DESTINO.write_text(texto, encoding="utf-8")
    print(f"reescrito {DESTINO.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
