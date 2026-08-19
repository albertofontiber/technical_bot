# s324j — Revisión 2º-frontera por TROZOS del cableado (tanda 1/3): IDENTIDAD Y SESIÓN

**Contexto**: el cableado del panel (PR #296, mergeado) tiene el dúo así: el cross-model
(Sol xhigh) lo auditó ENTERO en 4 rondas talladas; el 2º frontera solo vio el núcleo del
cerrojo (`panel_puerta`/`admitir`) al sellar el seguimiento (DEC-241). Alberto adjudicó
PAGAR la pasada 2º-frontera del resto, por trozos compactos (el remedio DEC-236: nunca
el diff entero). **Los ficheros de esta tanda son BYTE-IDÉNTICOS al snapshot que Sol
auditó** (verificado: `git diff 8298c74..HEAD -- dashboard/ api/ scripts/...` vacío), así
que tu pasada COMPLETA el dúo para ellos. Eres el control fresco: no des nada por sellado
por venir de rondas previas.

## Alcance de ESTA tanda (lee solo esto, con tools, ancla fichero:línea)

- `dashboard/auth.py` — ENTERO. El corazón de identidad.
- `dashboard/sesion.py` — ENTERO. La cookie firmada.
- El contrato: `evals/s324i_panel_vercel_propuesta_v9.md` §4 (sello), §5 (backend +
  señuelo + charset), §11 (validador estricto) y el bloque de puertas 6/6-bis/11
  (líneas ~886-925). NO releas la v9 entera: esas secciones.

**FUERA de alcance** (ya con dúo completo o en otra tanda): `panel_puerta`/`cerrojo.py`
(sellado en DEC-241), `app.py`/rutas (tanda 2), `gestion.py`/scripts (tanda 3).

## Qué afirmamos de estos ficheros (verifícalo o refútalo)

1. **El sello**: `sello_de_registro` = b64url sin relleno de sha256(registro)[:16] — 22
   chars; cambia exactamente con el registro. `Usuario.sello` obligatorio sin default
   (un doble de test sin sello REVIENTA en construcción, a propósito).
2. **`BackendSupabase.autenticar`**: filtro `activo` EN la consulta (ausente e inactivo
   indistinguibles); charset acotado ANTES de viajar en el filtro PostgREST
   (`USUARIO_RE`); señuelo scrypt EXACTAMENTE una vez en las ramas
   no-existe/inactivo/charset-malo y CERO en transporte caído; TODO no-OK del transporte
   (ConnectError, >=400, tabla ausente, sin credenciales) = `IdentidadNoDisponible`,
   NUNCA «credencial mala».
3. **`validar_registro_estricto`**: exige sal=16 / clave=32 / params n,r,p exactos —
   rechaza lo legible-pero-no-canónico (el usuario inalcanzable).
4. **`sesion.py`**: firma HMAC con `DASHBOARD_SECRET`, expiración, y el payload lleva
   `h` (el sello) que `despachar` revalida — cookie válida SIN `h` o con `h` no-cadena
   → fuera por el camino normal, sin excepción.
5. **Nada de esto filtra secretos**: ni contraseña ni service key en logs/errores/HTML.

## Dónde morder

- ¿Alguna rama de `autenticar`/`verificar` donde el tiempo o el error DISTINGA
  existe/no-existe (oráculo de enumeración) pese al señuelo?
- ¿El parseo del registro scrypt (`_partir`) puede aceptar algo que `verificar` trate
  distinto de lo que `validar_registro_estricto` promete?
- ¿La cookie: firma sobre TODOS los campos que importan? ¿algún campo del payload que
  se use sin estar cubierto por la firma? ¿comparación de firma en tiempo constante?
- ¿`sello()` (la revalidación) distingue revocado (None → fuera) de caído
  (`IdentidadNoDisponible` → 503 sin matar cookie) en TODAS las rutas?
- Los tests de estas piezas (`tests/test_s324j_panel_auth.py`,
  `tests/test_s324f_dashboard_auth.py`): ¿afirman el contrato o la implementación?

## Formato de salida

Hallazgos `[severidad][confianza][ancla]` + veredicto final (`SÓLIDO` si procede).
Severidades: critico/medio/menor. Si un claim de arriba es falso, eso es hallazgo aunque
el código sea correcto (framing falso = hallazgo).
