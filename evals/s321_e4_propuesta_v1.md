# s321 E4 — Clarify GOBERNADO: sustituir el seed `FAMILY_REGISTRY` — v1 (a dúo r26)

**Marco**: última fase del elefante (plan v2 r20, mapa r20-M5): el clarify por
divergencia YA vive en producción **hardcoded** — `FAMILY_REGISTRY` en
`conversation_policy_impl.py:177-180` (ZXSE/ZXE con eje-lazo y variantes) y su
propio comentario promete «the durable version reads the catalog's variant
table (DEC-069)». E4 = cumplir esa promesa: UNA fuente (el catálogo gobernado),
cero segunda vía.

## Qué hay hoy (anclas verificadas)

- `FAMILY_REGISTRY: {ZXSE: (eje=_LOOP_AXIS, variants=(1,2,5,10)), ZXE: (eje=
  _LOOP_AXIS, variants=(1,2,5))}` — consumido por `_family_divergence` (ruta E
  del clarify: umbrella + pregunta-sobre-eje-divergente → CLARIFY con las
  variantes como opciones).
- El catálogo gobernado tiene `umbrellas` con `divergent` ADJUDICADO
  (true/false/unknown) y miembros — pero NO tiene ni el EJE (qué términos de la
  pregunta indican divergencia: «lazo/loop/bucle») ni la lista de variantes
  para el texto del clarify.
- `_INVARIANT_ATTRS` (atributos invariantes de familia que NUNCA clarifican)
  sigue siendo código — fuera del alcance v1, declarado.

## Diseño v1

1. **Esquema**: campo OPCIONAL `clarify` en umbrellas:
   `{"eje_terminos": ["lazo", "loop", "bucle"], "variantes": ["1", "2", "5"]}`
   — validado por catalog_store (lista de strings no vacías); ADJUDICABLE
   (provenance obligatoria), jamás inferido en runtime (la letra del contrato:
   «diverge no es decidible sin atributos normalizados»).
2. **Datos semilla**: migrar ZXSE/ZXE del registry HARDCODED al catálogo con
   provenance `s285-T3 adjudicación familia ZXe/ZXSe simétrica + s321-E4
   migración del seed` — los datos SON los adjudicados (T3), solo cambia dónde
   viven.
3. **Consumo**: `_family_divergence` lee del catálogo (carga perezosa cacheada
   a nivel proceso, fail-open a NO-clarify si el catálogo no carga — la
   conducta de hoy sin registry). `FAMILY_REGISTRY` se retira del código;
   los tests que lo importan se re-contratan al catálogo.
4. **Gate de EQUIVALENCIA**: con los datos semilla idénticos, la conducta es
   byte-idéntica — el instrumento MT + transporte s316e lo asserta (mismos
   goldens de clarify ZXe); suite completa.
5. **La conexión #76 declarada**: `clarify.eje_terminos` es el primer ATRIBUTO
   normalizado del catálogo — el esquema que #76 (categoría+atributos, mandato
   13-ago) extenderá; E4 no construye #76, le deja la puerta puesta.

## Gaps declarados

- El eje sigue siendo léxico (términos), no semántico — igual que hoy; #76
  decidirá si se normaliza a atributos tipados.
- Solo las 2 familias adjudicadas migran; añadir familias nuevas = adjudicación
  (exactamente el punto: hoy exigiría un PR de código; mañana, una fila de
  catálogo con provenance).
- `_INVARIANT_ATTRS` y el resto de la ruta E quedan intactos (cirugía mínima).
