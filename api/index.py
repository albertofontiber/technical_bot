# -*- coding: utf-8 -*-
"""Punto de entrada del panel en Vercel.

Vercel busca las funciones en `api/`; para Python detecta la variable `app` del
módulo y, si es una aplicación ASGI, la sirve tal cual. Por eso este fichero es
literalmente una línea de importación: **el panel no sabe que está en Vercel**, y
esa ignorancia es la propiedad que se quiere. Si mañana vuelve a Railway o corre
en un portátil, no cambia nada suyo — cambia quién lo arranca.

POR QUÉ VERCEL Y NO UN SERVICIO SIEMPRE ENCENDIDO (s324f, decisión de Alberto):
el war room ya vive ahí, así que el panel comparte cuenta, dominio y forma de
configurar credenciales; y al ser serverless no se paga por tenerlo encendido, que
para un panel que se abre unas veces al día es la diferencia correcta.

LO QUE ENCAJA SIN TOCAR NADA:
  · la sesión va en una **cookie firmada**, no en una tabla ni en memoria de
    proceso, así que no hay estado que compartir entre invocaciones — se decidió
    para no montar infraestructura para dos usuarios y resulta ser exactamente lo
    que serverless necesita;
  · el panel sólo arrastra `httpx` y `python-dotenv` al importarse (medido): ni
    anthropic, ni voyage, ni telegram. El bundle es pequeño;
  · la clave de servicio de Supabase sigue SIN salir del servidor — las funciones
    corren en el servidor, no en el navegador. La decisión de DEC-231 §1 se
    mantiene intacta, que es la diferencia con montar una SPA que hable con la
    base directamente.

LO QUE **NO** ENCAJA, y está declarado en `docs/DASHBOARD_DESPLIEGUE.md`: el
cerrojo contra fuerza bruta cuenta los intentos fallidos en memoria del proceso.
En un servicio siempre encendido eso sólo se pierde al reiniciar; aquí, cada
invocación puede caer en una instancia distinta, así que el cerrojo protege mucho
menos de lo que su código promete. Hasta que se mueva a la base, la defensa real
es `scrypt` (~170 ms por intento) más una contraseña larga.
"""
# EL PUNTO DE ARRANQUE ELIGE (s324j, v9 §9): el panel no sabe que está en
# Vercel — quien lo arranca, sí. Aquí se enchufan los backends de Supabase:
#   · usuarios en `panel_usuarios` (revocación efectiva en la SIGUIENTE
#     petición — el motivo de (a2), DEC-237/DEC-239);
#   · cerrojo distribuido en `panel_intentos` (el de memoria no protege en
#     serverless: cada intento puede caer en una instancia distinta).
# `python -m dashboard` (local) NO pasa por aquí y conserva `BackendEntorno` +
# cerrojo en memoria: dobles, tests y modo local intactos. Sin variable mágica.
from dashboard import auth, cerrojo
from dashboard.app import app  # noqa: F401  (Vercel lo descubre por nombre)

auth.usar_backend(auth.BackendSupabase())
cerrojo.usar_cerrojo(cerrojo.CerrojoSupabase())
