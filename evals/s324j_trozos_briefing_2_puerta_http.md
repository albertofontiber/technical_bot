# s324j — Revisión 2º-frontera por TROZOS del cableado (tanda 2/3): LA PUERTA HTTP

**Contexto** (igual que la tanda 1): pasada 2º-frontera pagada por Alberto sobre el
cableado mergeado (#296/#298), por trozos compactos (DEC-236). Sol ya auditó estos
bytes en 4 rondas; tú eres el control fresco que completa el dúo. No des nada por
sellado.

## Alcance de ESTA tanda (lee solo esto, con tools, ancla fichero:línea)

- `dashboard/app.py` — ENTERO. El despacho, las rutas, los formularios, el HTML.
- `dashboard/datos.py` — ENTERO. El transporte de lectura.
- `api/index.py` + `vercel.json` — el enchufe serverless.
- Contrato: v9 §3 (despacho y sello), §7 (columnas declaradas), §10 (503 sin mentir)
  y las puertas 2/3/8 del bloque ~886-935. Solo esas secciones.

**FUERA de alcance**: `auth.py`/`sesion.py` (tanda 1 — sellada hoy, con 3 cierres ya
aplicados: estricto anti-duplicados, `exigir_produccion`, csrf sobre bytes),
`cerrojo.py`/`panel_puerta` (DEC-241), `gestion.py`/scripts (tanda 3).

## Qué afirmamos de estos ficheros (verifícalo o refútalo)

1. **`despachar` en orden**: parseo → rutas públicas (`/entrar`, `/salir` local) →
   origin+CSRF para POST (checks LOCALES primero — sin RTT) → sesión firmada →
   revalidación del SELLO contra la base (UN RTT) → handler. `/salir` NO revalida
   sello (funciona con la base caída).
2. **El sello revalida en CADA petición autenticada**: `h` del payload vs
   `backend.sello(usuario)`; revocado/ausente → fuera (redirect a `/entrar`);
   `IdentidadNoDisponible` → 503 con `_TEXTO_503` SIN matar la cookie.
3. **CSRF + Origin**: POST sin origin correcto o sin csrf de la sesión → rechazo
   ANTES de tocar la base; el token viaja en campo oculto de cada formulario.
4. **Ningún secreto al cliente**: el HTML no lleva SUPABASE_*, ni el registro, ni
   trazas; los errores 4xx/5xx tienen cuerpo fijo (sin `str(exc)` al usuario).
5. **`_tabla_de_vista` solo pinta columnas DECLARADAS** (v9 §7): una columna nueva
   no se pinta sola; una declarada que falta no rompe la página.
6. **`accion_entrar`**: cerrojo (`admitir` → 429 con espera) ANTES del backend;
   `CerrojoNoDisponible` → 503; con acierto → `acierto()` + cookie con
   `payload["h"] = usuario.sello`.
7. **`api/index.py`**: importa `app` y enchufa `BackendSupabase` + `CerrojoSupabase`
   una vez (arranque), con la sonda `comprobar_arranque` fail-CERRAR.
8. **`datos.py`**: select EXPLÍCITO por vista (nunca `*`), estados
   OK/VACIO/ERROR/TABLA_AUSENTE/SIN_CREDENCIALES sin fugas del detalle al HTML.

## Dónde morder

- ¿Algún handler alcanzable SIN pasar por la puerta completa (ruta registrada fuera
  del orden, método no contemplado, HEAD/OPTIONS, path traversal en el router)?
- ¿El 503 distingue de verdad «caído» de «credencial mala» en TODAS las ramas, o
  alguna rama de excepción devuelve algo que miente?
- ¿Formularios: algún campo del POST que viaje a Supabase sin acotar (inyección en
  filtros PostgREST tipo `usuario=eq.X`)?
- ¿El HTML escapa TODO lo que viene de la base (nota, usuario — XSS almacenado)?
- ¿Cabeceras de la cookie (HttpOnly/Secure/SameSite/Path) y del HTML
  (Content-Type/charset, no-store) correctas en TODAS las respuestas, también 4xx/5xx?
- ¿`vercel.json`/`api/index.py`: algo que rompa el aislamiento (rutas estáticas,
  otro entrypoint)?

## Formato de salida

Hallazgos `[severidad][confianza][ancla]` + veredicto (`SÓLIDO` si procede).
Framing falso = hallazgo aunque el código sea correcto.
