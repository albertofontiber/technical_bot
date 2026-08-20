# -*- coding: utf-8 -*-
"""Levanta el panel REAL para medirlo con un navegador (s328).

POR QUÉ EXISTE. El CSS del panel no tenía red de seguridad: `TECH_DEBT #94` lo
declaró y el primer cambio posterior lo cobró — las gráficas de s327 se
ampliaban ×2,3 en escritorio y los rótulos se despegaban de sus barras hasta
264 px. Ningún test lo vio porque todos llaman a las funciones de render y
miran el HTML; **la geometría solo existe cuando un navegador la calcula**.

QUÉ HACE. Sirve la app ASGI de verdad —misma puerta de sesión, mismas
cabeceras, mismo CSS— con el transporte a PostgREST doblado, porque aquí no hay
red ni la queremos: lo que se mide es el LAYOUT, no los datos. Las filas se
fabrican a partir de las COLUMNAS DECLARADAS de cada vista, así que un doble no
puede inventarse un nombre de columna y dejar una gráfica vacía sin que se note
(pasó al escribir esto: puse `consultas` donde la vista declara `consultas_rag`
y el gráfico salió sin barras, con el smoke en verde).

Uso:
    python -m scripts.s328_panel_servidor_de_medida [--puerto 8099]

Imprime `COOKIE=...` en la primera línea: una sesión válida FIRMADA por el
propio panel, para que el navegador entre sin pasar por el login.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

#: Credenciales de mentira: este servidor no habla con Supabase ni con nadie.
#: El registro scrypt es real en FORMATO (la sonda de arranque lo valida) y su
#: contraseña no abre nada — el navegador entra con la cookie, no por el login.
_ENTORNO = {
    "SUPABASE_URL": "https://ejemplo.invalid",
    "SUPABASE_SERVICE_KEY": "clave-de-mentira",
    "SUPABASE_SERVICE_ROLE_KEY": "clave-de-mentira",
    "DASHBOARD_SECRET": "medida-local-" + "x" * 36,
    "DASHBOARD_USUARIOS": (
        "alberto:scrypt$n=32768,r=8,p=1$gnjiyyM+XdSRnKvg0XGEUA$"
        "k9KVoI0/E1gXMPjhl8T1LeJZkqp/VfN4co6bi3wMv5Y"),
}
for _clave, _valor in _ENTORNO.items():
    os.environ.setdefault(_clave, _valor)

from dashboard import app as panel                          # noqa: E402
from dashboard import datos, sesion                         # noqa: E402

_SELLO = "sello-de-mentira"
#: Un valor por FORMATO declarado. Lo que se mide es el layout: hacen falta
#: filas plausibles, no datos reales.
_POR_FORMATO = {
    "numero": 7, "ms": 900, "pct": 42.0, "fecha": "2026-08-19T10:00:00Z",
}
_FILAS = 8


#: Etiquetas DISTINTAS por fila. Con un solo texto repetido, las vistas
#: `grafico_agregado` suman todo en UNA barra y el gráfico que se mide no se
#: parece al de producción (me pasó: las cuatro dimensionales salían con una
#: columna de 40 y parecía un fallo del render).
#: Incluye los ids de taxonomía LARGOS a propósito: son los rótulos reales más
#: hostiles del panel y son los que ejercitan el recorte. Sin ellos el gate de
#: «ningún rótulo cortado» pasaría en vacío, que es no tener gate.
_TEXTOS = ("catalogo_especificaciones", "instalacion_configuracion",
           "averias_diagnostico", "Morley-IAS", "Securiton",
           "Aritech", "Honeywell", "Bosch")


def _fila(vista, indice: int) -> dict:
    fila = {}
    for columna in vista.columnas:
        valor = _POR_FORMATO.get(columna.formato)
        if columna.formato == "numero":
            valor = (indice * 3) % 11          # incluye ceros: barra a cero
        elif columna.formato == "dia":
            # DESCENDENTE, como el `orden` de las vistas temporales
            # (`dia.desc`): el gráfico invierte esa lista para que el tiempo
            # avance hacia la derecha, así que un doble ascendente pintaba la
            # serie del revés y el error parecía del código.
            valor = f"2026-08-{24 - indice:02d}"
        elif columna.formato == "semana":
            valor = f"2026-08-{24 - indice * 7 % 28:02d}"
        elif valor is None:
            valor = _TEXTOS[indice % len(_TEXTOS)]
        fila[columna.nombre] = valor
    return fila


def _leer(recurso, params, presupuesto=None):
    vista = datos.VISTAS_POR_CLAVE.get(recurso)
    if vista is None:                                  # `documents` y demás
        return datos.Resultado(datos.OK, [{"manufacturer": "Detnov"}])
    return datos.Resultado(datos.OK,
                           [_fila(vista, i) for i in range(_FILAS)])


class _BackendDeMentira:
    def sello(self, usuario): return _SELLO


def cookie_de_sesion() -> str:
    """Una sesión VÁLIDA, firmada con el secreto del propio panel."""
    payload = sesion.nueva("alberto")
    payload["h"] = _SELLO                       # cuadra con `_BackendDeMentira`
    return f"{sesion.NOMBRE_COOKIE}={sesion.firmar(payload, sesion.secreto())}"


def instalar_dobles() -> None:
    datos.leer = _leer
    panel.auth.backend_activo = lambda: _BackendDeMentira()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--puerto", type=int, default=8099)
    args = parser.parse_args()

    import uvicorn

    instalar_dobles()
    print("COOKIE=" + cookie_de_sesion(), flush=True)
    uvicorn.run(panel.app, host="127.0.0.1", port=args.puerto, log_level="error")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
