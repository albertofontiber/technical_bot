# -*- coding: utf-8 -*-
"""s324f — Genera el registro de contrasena del panel para pegarlo en Railway.

    python -m scripts.s324f_dashboard_password alberto

Pide la contrasena por teclado (sin eco), la deriva con scrypt e imprime la
linea que hay que pegar en la variable `DASHBOARD_USUARIOS`. La contrasena en
claro no se escribe en ningun sitio: ni en el repo, ni en un fichero, ni en el
historial del shell (por eso NO hay un argumento `--contrasena`, y no lo va a
haber: un argumento acaba en `history` y en la lista de procesos).

VARIAS PERSONAS: se ejecuta una vez por cada una y se pegan las lineas separadas
por `;` en la misma variable.

    DASHBOARD_USUARIOS=alberto:scrypt$...;autor:scrypt$...

LO OTRO QUE HACE FALTA EN RAILWAY, que este script tambien recuerda al final:
`DASHBOARD_SECRET` (firma las cookies de sesion; rotarla cierra todas las
sesiones abiertas, que es el boton de panico si se roba una).
"""
from __future__ import annotations

import argparse
import getpass
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard import auth                                       # noqa: E402

#: Suelo de longitud. No se exige un zoo de simbolos —eso produce `P@ssw0rd!`—
#: sino LARGO, que es lo unico que de verdad cuesta romper. Tres palabras al
#: azar pasan de sobra y se recuerdan.
MINIMO_CARACTERES = 12


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.s324f_dashboard_password",
        description="Genera el registro scrypt de una contrasena del panel.",
    )
    parser.add_argument("usuario", help="nombre de usuario para entrar")
    parser.add_argument("--sugerir", action="store_true",
                        help="propone una contrasena aleatoria y la usa")
    args = parser.parse_args(argv)

    usuario = args.usuario.strip().lower()
    if not usuario or ":" in usuario or ";" in usuario:
        print("El usuario no puede estar vacio ni llevar ':' o ';' "
              "(son los separadores de la variable).")
        return 2

    if args.sugerir:
        contrasena = secrets.token_urlsafe(18)
        print(f"\nContrasena generada (guardala en tu gestor AHORA, no se "
              f"vuelve a ver):\n\n    {contrasena}\n")
    else:
        try:
            contrasena = getpass.getpass("Contrasena: ")
            repetida = getpass.getpass("Otra vez: ")
        except (EOFError, KeyboardInterrupt):
            print("\nCancelado.")
            return 2
        if contrasena != repetida:
            print("No coinciden.")
            return 2
        if len(contrasena) < MINIMO_CARACTERES:
            print(f"Demasiado corta: minimo {MINIMO_CARACTERES} caracteres. "
                  f"Tres palabras al azar valen y se recuerdan.")
            return 2

    registro = auth.hash_contrasena(contrasena)
    print("\nPega esto en la variable DASHBOARD_USUARIOS de Railway")
    print("(si ya hay otras personas, separa las entradas con ';'):\n")
    print(f"    {usuario}:{registro}\n")
    print("Y comprueba que existe tambien DASHBOARD_SECRET. Si no la tienes:\n")
    print(f"    DASHBOARD_SECRET={secrets.token_urlsafe(32)}\n")
    print("Rotar DASHBOARD_SECRET cierra TODAS las sesiones abiertas: es el")
    print("boton de panico si sospechas que alguien se llevo una cookie.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
