# -*- coding: utf-8 -*-
"""s324j — Alta y revocacion de usuarios del PANEL (`panel_usuarios`, 019).

    python -m scripts.s324j_panel_usuario alta alberto
    python -m scripts.s324j_panel_usuario alta alberto --registro 'scrypt$...'
    python -m scripts.s324j_panel_usuario revocar alberto --por alberto

El panel LEE usuarios y no los gestiona (alcance v1 del diseño, v9 §1.1): el
alta y la revocacion son operaciones de operador, con la service key, desde
este script — el mismo patron que el CLI de invitaciones. Diseño completo:
`evals/s324i_panel_vercel_propuesta_v9.md` (DEC-239).

LO QUE ESTE SCRIPT GARANTIZA antes de escribir una fila (v9 §1.1, puerta 11):

1. El nombre pasa el charset de `panel_usuarios` (`auth.usuario_admisible`) —
   un nombre que la tabla no puede contener no llega a la base.
2. El registro es ESTRICTAMENTE canonico (`auth.validar_registro_estricto`):
   sal de 16, hash de 32, solo `n,r,p`. `_partir` a secas tolera sal/hash de
   1 byte, y ese registro seria LEGIBLE y jamas verificaria — un usuario
   inalcanzable (hallazgos S3-M3/S4-M2 del duo).
3. El par registro↔contraseña VERIFICA (challenge): se pide la contraseña y se
   corre `auth.verificar` ANTES del INSERT. En el camino normal (el script
   deriva el registro de la contraseña tecleada) es cierto por construccion;
   en el camino `--registro` (pegado) es el control que falta — un hash de 32
   bytes ajeno a la contraseña pasa la forma y no verificaria nunca.

La contraseña en claro no se escribe en ningun sitio (ni argumento, ni
fichero): se pide por `getpass`, como en `s324f_dashboard_password`.

TRANSPORTE: `Prefer: return=minimal` SIEMPRE (v9 §13, hallazgo S6-M3): el
`return=representation` por defecto del CLI exigiria SELECT sobre columnas de
auditoria que la 019 no concede, y el INSERT valido moriria en el RETURNING.
"""
from __future__ import annotations

import argparse
import getpass
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard import auth                                       # noqa: E402
from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL        # noqa: E402

_TIMEOUT = 15.0


def _cabeceras(representar: bool) -> dict:
    # `return=minimal` por defecto (v9, S6-M3): la 019 concede SELECT solo
    # sobre (usuario, registro, activo) y un RETURNING de columnas de
    # auditoria tumbaria la escritura valida. Cuando hace falta contar filas
    # tocadas se pide representation de UNA columna concedida via `select=`.
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation" if representar else "return=minimal",
    }


def _pedir(metodo: str, *, params: dict | None = None,
           json: dict | None = None, representar: bool = False) -> httpx.Response:
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        raise SystemExit("Faltan SUPABASE_URL / SUPABASE_SERVICE_KEY en el entorno.")
    with httpx.Client(timeout=_TIMEOUT) as cliente:
        return cliente.request(
            metodo, f"{SUPABASE_URL}/rest/v1/panel_usuarios",
            headers=_cabeceras(representar), params=params, json=json,
        )


def _operador(explicito: str | None) -> str:
    if explicito and explicito.strip():
        return explicito.strip()
    return getpass.getuser() or "operador"


def cmd_alta(args) -> int:
    usuario = (args.usuario or "").strip().lower()
    if not auth.usuario_admisible(usuario):
        print(f"El usuario {args.usuario!r} no pasa el charset del panel "
              f"(minusculas, digitos y ._@-, maximo 64). La tabla lo "
              f"rechazaria igual: su CHECK es el mismo regex.")
        return 2

    if args.registro:
        registro = args.registro.strip()
        contrasena = getpass.getpass(
            "Contraseña de ese registro (challenge, no se guarda): ")
    else:
        contrasena = getpass.getpass(f"Contraseña para {usuario!r}: ")
        repetida = getpass.getpass("Otra vez: ")
        if contrasena != repetida:
            print("No coinciden. Nada escrito.")
            return 2
        if len(contrasena) < 12:
            print("Demasiado corta (minimo 12; tres palabras al azar valen).")
            return 2
        registro = auth.hash_contrasena(contrasena)

    # Puerta 11: estricto, no solo legible.
    try:
        auth.validar_registro_estricto(registro)
    except auth.RegistroInvalido as exc:
        print(f"Registro RECHAZADO ({exc}). Nada escrito.")
        return 2
    # Challenge (v9 §1.1): el par registro↔contraseña VERIFICA antes del alta.
    if not auth.verificar(contrasena, registro):
        print("La contraseña NO verifica contra ese registro. Nada escrito: "
              "un alta asi seria un usuario que jamas podria entrar.")
        return 2

    resp = _pedir("POST", json={
        "usuario": usuario,
        "registro": registro,
        "activo": True,
        "alta_por": _operador(args.por),
    })
    if resp.status_code >= 400:
        print(f"Supabase respondio {resp.status_code}: {resp.text[:300]}")
        print("¿Falta aplicar migrations/019_panel_usuarios_cerrojo.sql, o el "
              "usuario ya existe?")
        return 1
    print(f"Alta de {usuario!r} hecha (por {_operador(args.por)}). "
          f"Puede entrar en el panel desde YA.")
    return 0


def cmd_revocar(args) -> int:
    usuario = (args.usuario or "").strip().lower()
    ahora = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    # El CHECK `panel_usuarios_revocacion_coherente` exige los TRES campos
    # juntos: desactivar sin autor/fecha no puede existir (v9 §1.1, S2-M5).
    # El PATCH es condicional (`activo=is.true`): revocar dos veces no inventa
    # un exito. Para saber cuantas filas toco se pide representation de UNA
    # columna CONCEDIDA (`usuario` esta en el GRANT SELECT de la 019) — la
    # regla de S6-M3 al derecho: representation implica lectura de lo devuelto,
    # asi que se devuelve solo lo legible.
    resp = _pedir("PATCH",
                  params={"usuario": f"eq.{usuario}", "activo": "is.true",
                          "select": "usuario"},
                  json={"activo": False,
                        "revocado_en": ahora,
                        "revocado_por": _operador(args.por)},
                  representar=True)
    if resp.status_code >= 400:
        print(f"Supabase respondio {resp.status_code}: {resp.text[:300]}")
        return 1
    filas = resp.json() if resp.content else []
    if not filas:
        print(f"{usuario!r} no estaba activo (no existe o ya revocado). "
              f"Nada que hacer.")
        return 2
    print(f"{usuario!r} revocado (por {_operador(args.por)}). Su siguiente "
          f"peticion al panel lo expulsa — el sello deja de casar.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.s324j_panel_usuario",
        description="Alta y revocacion de usuarios del panel (panel_usuarios).",
    )
    sub = parser.add_subparsers(dest="orden", required=True)

    alta = sub.add_parser("alta", help="da de alta un usuario del panel")
    alta.add_argument("usuario", help="nombre de entrada (charset del panel)")
    alta.add_argument("--registro", default=None,
                      help="registro scrypt YA generado (p. ej. por "
                           "s324f_dashboard_password); se exige el challenge")
    alta.add_argument("--por", default=None, help="quien da el alta")
    alta.set_defaults(funcion=cmd_alta)

    rev = sub.add_parser("revocar", help="revoca un usuario del panel")
    rev.add_argument("usuario")
    rev.add_argument("--por", default=None, help="quien revoca")
    rev.set_defaults(funcion=cmd_revocar)

    args = parser.parse_args(argv)
    return args.funcion(args)


if __name__ == "__main__":
    raise SystemExit(main())
