# s324j — Revisión 2º-frontera por TROZOS del cableado (tanda 3/3): GESTIÓN Y OPERACIÓN

**Contexto** (igual que tandas 1-2): pasada 2º-frontera pagada por Alberto sobre el
cableado mergeado, por trozos compactos (DEC-236). Sol ya auditó estos bytes; tú
completas el dúo. No des nada por sellado.

## Alcance de ESTA tanda (lee solo esto, con tools, ancla fichero:línea)

- `dashboard/gestion.py` — ENTERO. Invitar / anular / revocar, `op`, `DUPLICADO`.
- `scripts/s324j_panel_usuario.py` — ENTERO. Alta/revocación de usuarios del panel.
- `scripts/s324e_invitaciones.py` — las partes que el cableado tocó: PATCH
  condicional de anulación con `revocada_por`, cabeceras `Prefer`.
- `migrations/020_invitaciones_op.sql` — el contrato del lado base (op UNIQUE,
  backfill, CHECK de revocación completa, GRANTs).
- Contrato: v9 §6 (gestión), puerta 7 (idempotencia por `op`), §13 (transporte
  `return=minimal`).

**FUERA de alcance**: tandas 1-2 (selladas hoy con sus cierres), `cerrojo.py` /
`panel_puerta` / 019 (DEC-241), el diseño v9 en sí.

## Qué afirmamos (verifícalo o refútalo)

1. **Idempotencia por `op`**: mismo `op` dos veces → UNA invitación y el segundo
   intento responde `DUPLICADO` (código 23505 detectado) SIN enlace nuevo; `op`
   distinto → dos invitaciones. El `op` nace en el formulario (campo oculto) y
   viaja al INSERT.
2. **El token**: se genera con CSPRNG, se enseña UNA vez (la página de resultado),
   solo su SHA-256 viaja a la base; ni token ni hash en logs.
3. **Anular**: PATCH condicional (`revocada_at=is.null`) con `revocada_por =
   "panel:<usuario>"` — el 42501 latente de `nota` está cerrado (la 020 concede
   UPDATE solo de `canjeada_*`/`revocada_*` + `op` en INSERT).
4. **Alta de usuario (script)**: valida `usuario_admisible` + estricto CON
   `exigir_produccion=True` (cierre de la tanda 1) + challenge (verificar antes de
   INSERT) + `Prefer: return=minimal` (la 019 no concede SELECT de `alta_por` a la
   API); revocar = UPDATE de `activo` a false, efectivo en la siguiente petición.
5. **Ningún dato personal de más**: `creada_por`/`revocada_por` llevan etiqueta de
   operador (`panel:X` / `cli:X`), no emails; las notas van escapadas al HTML
   (tanda 2 verificó el escapado — aquí verifica que gestion no las re-inyecte).
6. **Errores**: cualquier >=400 del transporte en gestión → estado de error SIN
   filtrar la URL/clave; nada de `str(exc)` con secretos.

## Dónde morder

- ¿El PATCH condicional de anular puede pisar una invitación YA canjeada (carrera
  anular↔canjear) o el WHERE lo impide de verdad?
- ¿`op` del formulario: acotado (charset/longitud, CHECK 8-64 de la 020) ANTES de
  viajar en el INSERT? ¿Un `op` hostil puede romper el filtro PostgREST?
- ¿El script de alta puede dejar estado a medias (usuario sin registro válido, o
  INSERT que pisa un usuario existente)? ¿`ON CONFLICT`/PK lo corta?
- ¿La revocación de usuario distingue «no existe» de «ya revocado» sin mentir?
- ¿Los GRANTs de la 020 dejan algún camino que gestion ejerce sin permiso (el
  patrón del 42501 de `nota`) o un permiso de más que nadie usa?
- ¿Algún `print`/log del script con la contraseña, el registro o la service key?

## Formato de salida

Hallazgos `[severidad][confianza][ancla]` + veredicto (`SÓLIDO` si procede).
Framing falso = hallazgo aunque el código sea correcto.
