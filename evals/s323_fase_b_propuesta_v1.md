# s323 FASE B — resolución TIPADA del documento en la ingesta (diff para el dúo)

Cierra la raíz de TECH_DEBT #80/#81 con lo que el dúo r32 exigió. **Ya implementado y con
tests; se somete el DIFF antes de commitear** (Protocolo 3).

## El defecto
`resolve_document_id` devolvía `None` para CUATRO situaciones distintas
(`src/reingest/index.py`, antes del cambio): documento nuevo · solo filas no-activas ·
2+ filas que casan (`limit=2`, `len==2` → caía a `None` en silencio) · excepción tragada
por un `except Exception` que solo logueaba. El llamador no podía distinguirlas, así que
`index_chunks` indexaba igual: o creaba chunks huérfanos (`document_id=NULL`, #81) o los
ligaba a un documento retirado (#80). Y como el writer **BORRA antes de insertar**, seguir
adelante además destruía las filas buenas.

## Lo aplicado
1. **`EstadoResolucion` + `ResolucionDocumento`** (dataclass congelada): estados
   `ACTIVO | SOLO_NO_ACTIVO | SIN_MATCH | AMBIGUO | ERROR`, con `detalle` legible y la
   propiedad `enlazable`.
2. **`resolver_documento()`**: casa primero por **hash** (autoridad de identidad) y solo
   después por nombre (corroboración); **exige `status='active'`**; devuelve AMBIGUO con
   2+ activas en vez de elegir a ojo; y **propaga los errores de infraestructura** como
   `ERROR` en vez de tragarlos como «no hay match».
3. **`resolve_document_id()` se conserva como compat** (devuelve el id solo si hay una
   única fila activa) para no romper llamadores externos.
4. **Guarda DENTRO del writer**: `index_chunks` lanza `ValueError` si hay chunks y no hay
   `document_id`, **antes del DELETE**. El dúo fue explícito: un gate posterior solo
   constata el daño. Con 0 chunks no exige nada (caso legítimo de limpieza).
5. **`pipeline.process_file` para y reporta**: si la resolución no es enlazable devuelve
   `status="sin_indexar"` con `motivo` y `detalle` tipados, sin tocar la tabla.
6. **Docstring corregido**: decía «no enlazar es seguro» y este cambio lo vuelve falso por
   diseño — era la clase de prosa obsoleta que causó el defecto conceptual del censo s320.

## El camino del documento NUEVO (lo que Fable exigió declarar)
No queda bloqueado: `scripts/ingest_new.py:419` **da de alta la fila en `documents` ANTES**
de indexar, así que un PDF nuevo llega a `resolver_documento` ya con su fila activa y
resuelve `ACTIVO`. Un `SIN_MATCH` en el pipeline significa exactamente lo que dice —falta
el alta— y ahora se reporta en vez de degradar a huérfano.

## Tests (8, nuevos)
Uno por cada estado + el hash manda sobre el nombre + **el writer no llega a borrar sin
`document_id`** (se afirma `sb.borrados == []`, que es lo que de verdad protege) + 0 chunks
no exige id.

## Alternativas descartadas
- **Devolver `None` y que el llamador mire por su cuenta**: es el estado actual; el
  llamador no tiene con qué distinguir.
- **Guarda solo en `process_file`**: deja el writer desprotegido para cualquier otro
  llamador, y es el writer el que borra.
- **Enlazar a la fila no-activa cuando es la única**: el retrieval descarta esos chunks —
  peor que no indexar.

## Gaps declarados
- Cambia la conducta de la INGESTA: un documento sin alta previa ahora **no se indexa** en
  vez de indexarse huérfano. Es lo pretendido, pero cualquier flujo que dependiera del
  comportamiento viejo se detendrá — visible en el `status` del recibo, no en silencio.
- No se puede validar contra una ingesta real hasta la próxima; la cobertura es de tests.
- La fase C (invariante de coherencia con hash/lineage + contrato CI↔DB) sigue SIN cablear:
  este diff evita crear referencias rotas nuevas, pero no las detecta si ya existen.

---

# ADENDA post-dúo r33 (Sol 5/5 + Fable 5/5, 0 FP, 2 críticos) — TODO APLICADO ANTES DE COMMITEAR

**Crítico 1 (identidad mal tipada)**: el esquema define unicidad por
`(manufacturer, source_pdf_sha256)` y yo consultaba el hash **globalmente** → riesgo de
enlazar un OEM/relabel al documento de otra marca. Y mi «el nombre corrobora» era **falso**
(Fable): el nombre es un fallback INDEPENDIENTE — un PDF re-exportado cambia de hash y los
nombres de manual se repiten entre fabricantes. Aplicado: hash **acotado a la marca**, y el
nombre **solo** se consulta acotado; sin marca conocida, no se usa.

**Crítico 2 (ventana que oculta ambigüedad)**: `limit=5` se aplicaba ANTES de filtrar
`status` en cliente, así que una segunda fila activa podía quedar fuera y devolver ACTIVO
donde había AMBIGUO. Aplicado: **filtro `status='active'` EN SERVIDOR**.

**Medios**: (a) la guarda dejaba pasar `chunks=[]` y el DELETE se ejecutaba igual — ahora
exige identidad **también al limpiar**; (b) `sin_indexar` caía en el `else` de «vacíos» y el
estado persistido descartaba `motivo`/`detalle`, con lo que un ERROR de red se agregaba como
«vacío» — ahora tiene rama propia, contador propio y persiste el motivo tipado; (c) el gate
estaba DESPUÉS de pagar Haiku + Voyage y se re-pagaba en cada reintento — **movido justo
tras B5**, que es cuando ya se conoce todo lo que la resolución necesita.

**Menores aceptados**: docstring de módulo obsoleto corregido; y **«cierra la raíz de
#80/#81» era una sobre-afirmación** — este diff PREVIENE referencias rotas nuevas, pero no
repara las existentes ni detecta las que ya hay: eso es la fase C, que sigue sin cablear.

**Tests**: 10 (antes 8). Dos re-contratados por cambio deliberado de conducta — el de
`chunks=[]` (ahora exige identidad) y el doble de Supabase, que debe respetar el filtro de
estado porque ya no se filtra en cliente. Nuevos: el nombre no se usa sin marca, y la
segunda activa no queda oculta.
