# s322i — Propuesta: resultado del encogido de packets E1/E1b/E2 + hallazgo del doc_map fantasma

## Qué se hizo
Workflow de 9 agentes (2 deterministas + 5 de juicio + síntesis + verificador adversarial)
sobre los tres packets de adjudicación pendientes de Alberto. **Nada se aplicó**: todo el
output son recibos en `evals/` y packets v2. Verificado por git y por grep estático de
verbos mutantes en los 8 scripts (0 `.post(`/`.patch(`/`.delete(`).

## Resultado agregado
2.108 filas → **1.181 en bloque** (un solo «sí» por bolsa) + **911 una-a-una** + 16 fuera.

| Bolsa | Total | Bloque | Individual |
|---|---|---|---|
| E1 §1 colisiones | 49 | 49 | 0 |
| E1 §2 tier B | 67 | 42 | 13 (+12 fuera) |
| E1 §3 candidates nuevos | 133 | 50 | 83 |
| E1 §4 pm sucios | 4 | 3 | 1 |
| E1b confirmar | 359 | 327 | 32 |
| E1b revisar | 261 | 148 | 113 |
| E2 altas detector | 1.235 | 562 | 669 (+4 obsoletas) |

## Verificación adversarial (agente independiente, dentro del workflow)
- **Censo COMPLETO de las 570 citas de bloque** re-ejecutadas desde cero contra `chunks_v2`
  (no la muestra de 12 que pedía el encargo: «12 sobre 570 detecta un fallo aislado con ~2%
  de probabilidad — habría sido teatro de rigor»): **0 citas inventadas**. 531 verifican en
  el documento atribuido; 39 verifican en OTRO documento del corpus (defecto de atribución,
  no de existencia).
- **0 fallos de criterio** en las 1.181 filas de bloque (0 con confianza≠alta, 0 con cita
  vacía, 0 con veredicto no decidible).
- Defectos MEDIOS reportados: (a) el titular de los tres packets subestima sus propias
  casillas (E1 dice 98 decisiones y escribe 241 casillas; E1b 146 vs 432; E2 20 vs 94);
  (b) 5 filas imprimen la cita junto a una procedencia que no la contiene (`prov` es la
  procedencia del ID, no la fuente de la cita).
- El verificador declaró además **5 tandas de falsos positivos propios** que descartó antes
  de reportar (recorte con «…», comillas angulares del original, definición de chunk_count,
  listado por modelo vs por id, ficheros que viven en `chunks_v2.source_file`).

## EL HALLAZGO: la premisa del packet E1 §1 era falsa, y la clase es mayor de lo que decía
El packet afirmaba «dos filas ACTIVAS para el mismo manual» (49 casos). **Falso**: en 49/49
la fila que el `doc_map` referencia está **retirada** y vacía (0 chunks en las cinco tablas
que referencian `document_id`); la activa es otra. Son fichas fantasma retiradas en s65.
Origen del error localizado: `scripts/s320_e1_reconciliacion_censo.py:71` testea que la fila
EXISTA, nunca filtra por `status` — el packet elevó «existe» a «está activa».

**Consecuencia medida end-to-end (no teorizada)**: `must_preserve.attest_identity` hace join
por `document_id` entre el chunk servido y el doc_map. Los chunks llevan el id ACTIVO y el
doc_map guarda el FANTASMA → atesta False con el id que realmente se sirve. **El anexo
must_preserve NUNCA actúa para esos manuales.** El seam de `allowed_sources` está intacto
(indexa por `source_file`, que sí coincide): el arreglo no recupera retrieval, recupera la
atestación del anexo.

**Y la clase es MAYOR que las 49 del packet** (censo propio, hoy): de las 887 entradas del
`doc_map`, **60 apuntan a un documento no-activo** — 50 retired + 3 superseded + 7
needs_review — afectando **209 entries** del catálogo. Incluye `MIE-MI-431rv2` (el manual
ZXr-A/ZXr-P que adjudicamos ayer: sus 18 chunks cuelgan del id ACTIVO, pero el doc_map
apunta al fantasma `needs_review`) y `CAD-250-MC-380-es` (**superseded**, usado ayer como
fuente de la cita «hasta 32 lazos» de #76 — el dato es correcto y la edición 2026 activa lo
repite, pero la atribución apunta a una edición supersedida).

## Recomendación
1. **Un solo «sí»** para repuntar las 60 entradas `doc_map.document_id` fantasma→activo
   (no es supersede ni borrado: en `documents` no hay nada que tocar, la retirada ya está
   aplicada desde s65; es repuntar UN campo, dejando `source_file` intacto). Colapsa en la
   misma clase que las 11 «reconciliaciones» ya aplicadas sin incidencia en s320.
2. Arreglar antes de la firma los dos defectos MEDIOS de presentación (titular y las 5
   atribuciones), que son minutos.
3. Re-atribuir la cita del CAD-250 a la edición 2026 activa (el `max:32` no cambia).
4. **BLOQUEANTE antes de firmar el bloque**: re-atribuir o sacar del §0 las **39 filas**
   cuya cita existe en el corpus pero NO en el documento que se les atribuye (lista exacta
   en `s322h_verificacion_adversarial_v1.json -> d_citas_reejecutadas.verifican_solo_en_otro_doc`).
   Es trabajo de script, no de juicio: el documento correcto ya está identificado en el censo.

## Alternativas descartadas
- **Supersede o borrado de las filas fantasma**: modelaría mal el dato (supersede = revisión
  vieja sustituida por nueva; una ficha de 0 chunks nunca fue una revisión) y además ya están
  retiradas.
- **Dejarlo como está**: el anexo must_preserve seguiría sin actuar en 209 entries.

## Gaps declarados
- Las 911 filas individuales siguen siendo muchas: 669 son de E2, y de ellas 309 son calidad
  de catálogo (descripciones, marca delante, «Mod./Ref.») que no se deciden en el detector.
- El bloque de E1b depende en un 39,8% del juez LLM pese a que su recibo dice «el LLM solo
  interviene en el residuo» (framing minimizador; la estructura sí lo separa en 0.A/0.B).
- 130 veredictos del bloque E1b se REUSAN de una pasada previa (declarado en el recibo, con
  control de deriva: 0 filas cambiaron de conteo), pero el packet no lo dice en su cabecera.
- 4 filas de tier B crean entradas para productos que su manual no nombra ni una vez (son
  manuales de SERIE y la cita nombra la familia) — el packet no imprime ese contador.

---

## ADENDA post-dúo r29 (Sol xhigh, 5 hallazgos · 1 crítico — VERIFICADOS contra código)

**CORRECCIÓN DEL AUTOR (crítico, CONFIRMADO)**: mi recomendación 1 —«un solo sí para
repuntar las 60»— **era falsa por extrapolación mía**, no del workflow. El agente verificó
49 casos con 13 controles negativos; fui YO quien elevó 49→60 sin re-verificar la clase.
Comprobado ahora: `src/rag/catalog_store.py:446` exige `document_id` ÚNICO en `doc_map`, y
`CAD-250-MC-380-es` (superseded) y `CAD-250_Manual-Configuracion-MC-380-es-2026-c` (activa)
son **filas distintas** (`doc_map.jsonl:167-168`; y OJO: hay >=5 filas con
`detnov:cad-250` como primary — 167, 168, 170, 707, 708 —, o sea el censo de los 11
debe enumerar TODAS las filas rivales, no asumir pares). Repuntar la vieja al id de la activa
DUPLICARÍA el document_id → el validador lo rechaza; y dejaría un `source_file` que no
corresponde al documento destino. El propio clasificador ya mandaba ese mismatch a decisión
individual (`scripts/s322f_e1_colisiones_adjudicacion.py:259-267`).

**Recomendación 1 CORREGIDA**:
- **49 fantasmas `retired` (0 chunks, sin fila rival en doc_map)** → sí en bloque, repunte
  de `document_id`. Es la clase medida y controlada.
- **11 restantes (3 superseded + 7 needs_review)** → NO son la misma clase: van una a una,
  con su propio censo. En los `superseded` con edición nueva ya mapeada (CAD-250) la acción
  no es repuntar sino decidir si la fila vieja se retira del doc_map y si las CITAS de
  productos que la referencian se re-atribuyen a la edición activa.

**Otros 4 hallazgos de Sol, aceptados**:
- «0 fallos de criterio en 1.181 filas» **minimiza**: 611 filas no llevan cita por diseño y
  hacen `continue` antes de los chequeos. Lo correcto: **570 auditadas + 611 N/A**.
- Las **39 citas que verifican en otro documento** (no 5): mi arreglo renombró la etiqueta
  `prov` en **las 261 filas** que la llevaban (no 5 — el recibo
  `s322i_fix_packets_v2.json` lo registra), lo que elimina la lectura falsa de atribución;
  pero **re-atribuir o expulsar del bloque las 39 sigue PENDIENTE y es BLOQUEANTE**:
  ver recomendación 4.
- La consecuencia end-to-end de `must_preserve` está medida para 49/191, no para 209: «NUNCA
  actúa en 209 entries» es extrapolación presentada como medida. Corregido a 49/191 medido.
- **Falta el arreglo de RAÍZ** (y es el que importa a 30+ fabricantes): `resolve_document_id`
  (`src/reingest/index.py:68-87`) enlaza por hash/nombre **sin filtrar `status='active'`**, y
  el validador local no comprueba `doc_map→documents.active`. Sin un invariante que lo impida,
  la reingesta volverá a crear referencias fantasma. Propuesta: gate en la puerta del catálogo
  + filtro de status en la resolución, con su dúo propio. Nace como deuda declarada.
