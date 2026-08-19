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

LO QUE **NO** ENCAJA, y está declarado (tanda 2 del 2º frontera cazó aquí un
párrafo legacy que aún describía el cerrojo en memoria): el cerrojo YA es
distribuido — `panel_intentos` + la RPC `panel_puerta` (migración 019, DEC-239),
enchufado abajo — así que contar intentos NO depende de la instancia. Lo que
serverless sí deja fuera es la **sonda de arranque** (`comprobar_arranque`):
corre en el lifespan ASGI y en `python -m dashboard`, y el runtime de Vercel no
garantiza el lifespan, así que el fail-CERRAR de arranque puede no ejecutarse
aquí. El control compensatorio es del runbook (`docs/DASHBOARD_DESPLIEGUE.md`
pasos 3-4): la MISMA sonda lanzada a mano con credenciales de producción tras
aplicar la 019, más el smoke del cerrojo contra el despliegue real. En runtime
la protección no depende de la sonda: un `panel_puerta` ausente o sin GRANT
responde >=400 → `CerrojoNoDisponible` → 503 (fail-CERRAR por petición).
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
