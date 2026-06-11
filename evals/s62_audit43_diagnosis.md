# s62 — Diagnóstico del audit #43 (con verificaciones regla-C)

**Artefactos:** `s62_audit43.yaml` (inventario completo: shingles 8-palabras por doc,
Jaccard por bloques de fabricante, B3 por metadata, cruce con pools s61) + las 4
verificaciones puntuales de este doc (scripts temporales, evidencia citada aquí).

## El resultado central: el audit REFUTA el diagnóstico de s61

DEC-042d decía: "el CE llena el top-5 con near-duplicates — la fórmula §11 en 3
ediciones casi idénticas de la familia AM-8200 conviviendo". **MEDIDO: FALSO en el
mecanismo.** Jaccard real entre los 3 manuales de instalación (AM-8200 / AM 8200G
Rv3 / AM 8200N RV4): **0.001-0.032 a nivel doc; 0.00-0.06 entre los chunks de la
fórmula de docs distintos** (la única pareja con J=0.50 son dos páginas consecutivas
del MISMO doc). No hay duplicación textual: hay **tres PRODUCTOS HERMANOS distintos
cuyos manuales contienen secciones conceptualmente equivalentes** (cada central
tiene SU fórmula de baterías §11, redactada distinto).

**El mecanismo real de cat012 (3ª iteración, ahora con datos completos):**
1. La query pide la **AM-8200**; `_filter_to_query_models` matchea por SUBSTRING
   normalizado → "am8200" ⊂ "am8200g"/"am8200n" → los chunks de los productos
   HERMANOS pasan el filtro (la dirección inversa del caso #11e/hp003 que el filtro
   nació para bloquear).
2. El cross-encoder puntúa par-a-par: las "fórmulas de baterías" de los TRES
   productos son semánticamente casi intercambiables para esa query → llenan el
   top-5 y EXPULSAN la tabla de consumos del producto CORRECTO.
3. En el harness (paridad, sin `target_models`) ninguna señal le dice al reranker
   QUÉ producto pide la query — el header 2.0 le da la identidad de cada doc, pero
   no la del pedido.

→ **Es el #43 ORIGINAL en su forma pura** (identidad producto↔serie/variantes), no
"supersesión/near-dups". La redundancia que mordió es SEMÁNTICA y CROSS-PRODUCTO,
no textual.

## Las tres capas reales de la deuda #43 (con números)

**Capa A — identidad producto↔familia en retrieval (la que mordió el gate):**
el filtro de modelo es substring direccional; no existe noción de serie/variante.
Antecedentes medidos: cat012 (gate s61, mecanismo arriba) + el caso de diseño
CAD-201↔CAD-250 (DEC-032) + hp003/#11e (la dirección opuesta). Fix candidato YA
escrito en TECH_DEBT #43: modelar `series`/`applies_to` + match exacto-o-serie.
Es cambio de RETRIEVAL → ciclo medido completo (diseño + dúo + gate + A/B).

**Capa B — metadata de identidad ROTA en lotes viejos (inventario nuevo):**
- ≥15 docs de Spectrex/Pfannenberg/Sensitron con `manufacturer=Detnov` (verificado:
  PA5/PA20/DS10/PY X/SharpEye/SGMCB...).
- `product_model=unknown` masivo (grupo Morley-unknown ~120 docs; Detnov-unknown
  ~35 — mezcla además 5+ marcas).
- `revision` con basura sistemática del parser ("Rev isar", "Rev ise", "Rev io",
  "Rev iamente", "Rev iaturas" — caza la palabra Revisar/previamente/abreviaturas).
- `revision_date` 0/1065; `language` NULL 974/1065.
- `document_family` poblada (1065/1065) pero INSERVIBLE como familia: 943 valores
  distintos para 1.000 docs = filename normalizado (el par ES/EN del mismo manual
  cae en "familias" distintas).
- `supersedes_id`/`superseded_by_id`: 0 pobladas (el esquema existe, vacío).
- 165 documents sin chunks en chunks_v2 (huérfanos de ingesta — inventariar).

**Capa C — near-dup textual REAL (marginal):**
- 1 revisión conviviendo: MAD-472 "…ES GB FR IT_V2" vs "…ES GB FR GB IT" (J=0.74;
  shas backfilled no comparables) — **toca cat024** (4 docs del cluster en su pool).
- 1 FAQ DXc bilingüe (J=0.78).
- B3 (mismo modelo, idioma distinto): 41 grupos ES/EN/PT/FR legítimos —
  **se conservan SIEMPRE** (hp011/conflictos ES↔US viven de esto).

## Implicaciones

1. **"Supersesión" NO es el ciclo**: con 1 caso real de revisión conviviendo, poblar
   `supersedes_id` masivamente no tiene materia. El contrato de supersesión queda
   para el flujo de INGESTA futura (cuando entren revisiones nuevas de docs
   existentes), no como limpieza retroactiva.
2. **El ciclo con daño MEDIDO en eval es la capa A** (cat012 + antecedentes); la
   capa B es pre-requisito parcial (no se puede modelar series sobre manufacturer
   mal asignado) y deuda de identidad transversal (catalog/filtros/atribución).
3. La lectura de DEC-042 ("near-dups del corpus") queda CORREGIDA en canon — el
   rumbo "atacar #43" sigue siendo correcto, pero el #43 real es identidad
   producto↔serie + metadata, no near-dups.
