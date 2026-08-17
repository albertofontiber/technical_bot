# -*- coding: utf-8 -*-
"""Arranque local del panel:  `python -m dashboard`

En Railway el comando es el mismo de siempre para un ASGI —
`uvicorn dashboard.app:app --host 0.0.0.0 --port $PORT` — y este módulo NO se
usa allí: existe para que arrancarlo en el portátil sea una línea y para que los
tres motivos por los que no arranca se lean en castellano en vez de en una traza.

Antes de servir comprueba lo mismo que comprobará el `lifespan` en producción
(secreto de firma y usuarios), así que un fallo de configuración se ve aquí y no
en el primer intento de login.
"""
from __future__ import annotations

import os
import sys

# Importar `src.config` (vía el paquete) carga el `.env` del repo, que es donde
# viven las credenciales de Supabase en local.
from .app import app, comprobar_arranque

PUERTO_DEFECTO = 8080


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    puerto = int(os.getenv("PORT", str(PUERTO_DEFECTO)))
    if argv:
        try:
            puerto = int(argv[0])
        except ValueError:
            print(f"Uso: python -m dashboard [puerto]   (por defecto "
                  f"{PUERTO_DEFECTO})")
            return 2

    try:
        comprobar_arranque()
    except RuntimeError as exc:
        print("El panel NO puede arrancar:\n")
        print(f"  {exc}\n")
        return 2

    try:
        import uvicorn
    except ImportError:
        print("Falta `uvicorn`, que es el servidor. Está declarado en "
              "requirements.txt:\n\n    pip install -r requirements.txt\n")
        return 2

    print(f"Panel en http://localhost:{puerto}  (Ctrl+C para parar)")
    # `localhost` y no `0.0.0.0`: en local no hay motivo para escuchar en toda
    # la red, y el panel enseña datos de personas.
    uvicorn.run(app, host="127.0.0.1", port=puerto, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
