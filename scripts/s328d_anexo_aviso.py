# -*- coding: utf-8 -*-
"""Genera el Anexo A del paquete del abogado A PARTIR DEL CÓDIGO QUE SE SIRVE.

POR QUÉ EXISTE. El paquete llevaba el aviso **v8** transcrito a mano mientras
producción servía el **v9** — o sea, el asesor iba a validar un texto que ya no
es el que la gente acepta. La causa no es un despiste: es que el anexo era una
COPIA, y toda copia se desfasa. Aquí deja de serlo.

CÓMO LO LEE. Por AST, sin importar `telegram_bot` — ese módulo arrastra medio
bot (PTB, Supabase, config) y un anexo no puede depender de que el entorno esté
completo. Se localizan las asignaciones `_CONSENT_TERMS` y `_PRIVACY_DETAIL` y
se evalúa su literal, que es concatenación de cadenas: `ast.literal_eval` sobre
el nodo da EXACTAMENTE los bytes que el bot manda por Telegram.

QUÉ NO HACE. No reescribe el paquete entero: emite el bloque del anexo por la
salida estándar, y quien lo pega decide dónde. El resto del documento tiene
prosa que ninguna herramienta debería tocar.

Uso:
    python -m scripts.s328d_anexo_aviso              # el anexo, a stdout
    python -m scripts.s328d_anexo_aviso --comprobar  # ¿coincide con el paquete?
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ / "src/bot/telegram_bot.py"
PAQUETE = RAIZ / "docs/PAQUETE_ABOGADO_PILOTO_DG.md"
VERSION = RAIZ / "src/logging_db.py"


def _literal(nombre: str) -> str:
    arbol = ast.parse(FUENTE.read_text(encoding="utf-8"))
    for nodo in arbol.body:
        if (isinstance(nodo, ast.Assign) and len(nodo.targets) == 1
                and isinstance(nodo.targets[0], ast.Name)
                and nodo.targets[0].id == nombre):
            return ast.literal_eval(nodo.value)
    raise RuntimeError(f"no se encontró la asignación {nombre} en {FUENTE}")


def version_vigente() -> str:
    texto = VERSION.read_text(encoding="utf-8")
    encontrado = re.search(r'TERMS_VERSION\s*=\s*"([^"]+)"', texto)
    if not encontrado:
        raise RuntimeError("no se encontró TERMS_VERSION")
    return encontrado.group(1)


def _sin_markdown_de_telegram(texto: str) -> str:
    """Telegram pinta `*negrita*` y `_cursiva_`; en un anexo para un asesor esos
    asteriscos son ruido. Se quitan los marcadores y se deja el TEXTO, que es lo
    que la persona lee en pantalla."""
    texto = re.sub(r"\*([^*\n]+)\*", r"\1", texto)
    texto = re.sub(r"_([^_\n]+)_", r"\1", texto)
    return texto


def anexo() -> str:
    v = version_vigente()
    capa1 = _sin_markdown_de_telegram(_literal("_CONSENT_TERMS"))
    capa2 = _sin_markdown_de_telegram(_literal("_PRIVACY_DETAIL"))
    return f"""## Anexo A — Texto del aviso VIGENTE ({v})

> Este anexo **se genera del código que se sirve** (`python -m scripts.s328d_anexo_aviso`),
> no se transcribe. El paquete llegó a llevar el v8 mientras producción servía el {v}: una
> copia a mano se desfasa, y un asesor no puede validar un texto que ya no es el que la
> gente acepta.

### A.1 · Lo que se ve al iniciar, antes de poder usar nada

```
{capa1.strip()}
```

### A.2 · Detalle completo, disponible en todo momento sin aceptar nada (`/privacidad`)

```
{capa2.strip()}
```
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--comprobar", action="store_true",
                        help="no imprime: dice si el paquete lleva el texto vigente")
    args = parser.parse_args(argv)

    generado = anexo()
    if not args.comprobar:
        print(generado)
        return 0

    # Se compara el TEXTO de las dos capas, no el bloque entero: el paquete
    # puede tener prosa alrededor sin que eso sea una deriva.
    en_paquete = PAQUETE.read_text(encoding="utf-8")
    v = version_vigente()
    problemas = []
    for nombre, literal in (("A.1", _literal("_CONSENT_TERMS")),
                            ("A.2", _literal("_PRIVACY_DETAIL"))):
        limpio = _sin_markdown_de_telegram(literal).strip()
        if limpio not in en_paquete:
            problemas.append(f"el texto de {nombre} no es el vigente")
    # Y la ETIQUETA, que es la mitad que el control negativo destapó: comparar
    # solo el texto deja pasar un bump de `TERMS_VERSION` sin cambio de prosa —
    # el anexo seguiría titulado con la versión vieja y el asesor validaría un
    # texto correcto bajo un nombre falso.
    if f"## Anexo A — Texto del aviso VIGENTE ({v})" not in en_paquete:
        problemas.append(f"el título del anexo A no dice {v}")
    if problemas:
        print(f"DESFASADO ({', '.join(problemas)}) · TERMS_VERSION = {v}",
              file=sys.stderr)
        return 1
    print(f"AL DÍA: el paquete lleva el aviso {v} tal cual se sirve, y así lo titula")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
