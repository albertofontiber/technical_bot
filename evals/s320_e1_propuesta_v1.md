# s320 E1 — Propuesta: completar doc_map (279) + QA total de candidates (620) — v3 (tras dúo r22)

> **v2→v3 (dúo r22: Sol 4 con 1 crítico · Fable 4, convergentes en la atestación,
> 0 FP — TODO aplicado; cifras v3: A 46 · B 67 · C 162 · no-producto 4):**
> 1. **Sol C1: resolución PARCIAL de compuestos** (2X-A/2X-AT-F2/… tenía 2 de 3
>    partes YA en products y caía a C como candidato compuesto falso) → modo
>    `split-parcial` a tier B CON las trazas por parte.
> 2. **Sol M2 ≡ Fable F1: la atestación E1b queda CODIFICADA** — contra CONTENIDO
>    de chunks EXCLUYENDO los docs de los que nació el candidato; los tier-C van
>    SIEMPRE a «revisar» (el lote «confirmar» es solo para candidates pre-existentes
>    con atestación no-circular).
> 3. **Sol M3 + Fable F2: tier A endurecida** — coherencia por PREFIJO real del
>    normkey (no substring en cualquier posición) + check `vendido_bajo` (OEM→B);
>    framing honesto: el pm de ingesta viene de sidecar/regex con fallback, la
>    puerta de identidad no lo garantiza (por eso A exige la triple coincidencia).
> 4. **Sol M4: freeze-contract del gate ANTES de escribir** — artefacto
>    pre-registrado con queries dirigidas a los docs tier-A, commit del catálogo,
>    config pineada, y la métrica primaria = sonda `allowed_sources` (Fable F4:
>    el Δ≈0 del sweep-39 es NO-informativo por diseño — queda como no-regresión
>    secundaria, declarado).
> 5. **Fable F3: el cubo `no_producto` es REVISIÓN HUMANA** (un pm-norma sucio
>    puede tapar un producto real — EMA1224B4R con pm «EN-54-3»), no basura.

> **v1→v2 (Sol r21: 5 hallazgos con 2 CRÍTICOS, 0 FP — TODO aplicado; Fable r21
> ABORTADO por presupuesto: el recibo v1 de ~5.000 líneas reventaba su preflight
> → recibos v2 compactos-por-diseño + dúo r22 FRESCO con seeds idénticos):**
> 1. **C1: el cruce era por filename, no por `document_id`** (la clave estable del
>    contrato). Re-censado: son **279 sin entrada, no 219** — 60 docs ocultos tras
>    renames. Censo E0 y derivación re-corridos por id.
> 2. **C2: `pm.split("/")` fabricaba entidades compuestas** (20/20I → fragmentos;
>    PUL-D/EXT ídem). v2 = tokenización RESOLUTION-FIRST: el pm ENTERO primero
>    (rescató 20 docs a tier A: 35→55); split solo si TODAS las partes resuelven;
>    jamás se propone un fragmento.
> 3. **M3: atestación circular + basura como candidato** → cubo `no_producto`
>    léxico (fechas/normas/unknown: 4 cazados) y la atestación de E1b va contra
>    CONTENIDO de chunks, nunca contra el pm del que nacieron; los tier-C van a
>    lote «revisar», jamás «confirmar».
> 4. **M4: los IDs son inmutables — NADA se auto-crea**: tier C = packet de
>    PROPUESTAS (draft fuera de data/catalog/); solo tras tu aprobación por lotes
>    entran como candidate.
> 5. **M5: gates completados**: PASS±2 + tally de salud + la sonda de equivalencia
>    mide el efecto `allowed_sources` (queries que TOCAN los docs recién mapeados),
>    no solo ids servidos.

**Mandato**: E1 del plan v2 del elefante (dúo r20), en autónomo. **Regla madre**:
el matching REUSA `Catalog.resolve()` (homónimo-primero, candidate-gating,
redirects) — JAMÁS fuzzy, JAMÁS un matcher paralelo (DEC-074).

## E1a — doc_map para los 219 activos sin entrada

Derivación ejecutada (`evals/s320_e1_docmap_derivacion_v1.json`, 219/219):

| Tier | N | Qué es | Destino |
|---|---|---|---|
| A | 35 | TODOS los tokens del pm resuelven exact/alias con 1 id + marca coherente con el doc | **Escritura directa** vía catalog_store (valida), provenance por-entry |
| B | 47 | Paraguas/homónimo/parcial/multi-marca | **Packet** con la traza completa de resolve por token |
| C | 137 | Ningún token resuelve — el producto NO está en el catálogo (mayoría: lote Kidde s314) | **Productos `candidate` nuevos derivados** (abajo) |

**Tier C — la vía estructural (precedente F1-bulk, DEC-080)**: proponer producto
`candidate=true` por cada pm no resuelto (id `marca:pm-normalizado`, derivado del
`documents.pm` + `manufacturer` que YA pasaron la puerta de identidad de la
ingesta) + su entrada doc_map. Los candidate son NO-CONSUMIBLES por diseño
(candidate-gating fail-open) → cero efecto en serving hasta el QA de Alberto;
entran al flujo E1b como lote propio. Alternativa descartada: packet crudo de
137 filas (caro para Alberto, y el dato ya existe estructurado).

## E1b — QA TOTAL de los 620 candidates (r20: no muestras)

Pre-clasificación barata para que los lotes de Alberto sean rápidos:
1. **Atestación en corpus**: el normkey del candidate aparece en algún
   `documents.pm`/chunk pm → lote «confirmar» (probable sí).
2. **Veneno alfanumérico** (clase DEC-093): tokens cortos/dígitos/colisión con
   vocabulario → lote «retirar» (probable no).
3. Resto → lote «revisar» con contexto (marca, docs que lo citan).
Packets de ~50 con checkbox; el QA es TOTAL (cobertura 620/620 + los nuevos de
tier C), solo que ordenado por probabilidad para abaratar la sentada.

## Gates (contrato §7, plan v2)

- `catalog_store validate` (CI) sobre TODO el catálogo tras cada escritura.
- Sweep de EQUIVALENCIA Δ≈0 pre-registrado: las entradas tier-A y los candidates
  nuevos NO cambian ids servidos en el sweep-39 (los candidate no se consumen;
  las entradas doc_map solo AÑADEN alcance a docs que hoy no resuelven — si un
  gold cambia de composición, se investiga antes de mergear).
- hp018/hp009/hp011 (los 3 del contrato) sin cambio — mismos tests pineados.
- Provenance 100%: cada entrada lleva script+criterio; el recibo lista TODAS.

## Gaps declarados

- La coherencia de marca tier-A es prefijo-en-normkey (morley ⊂ morleyias):
  determinista pero declarada — un OEM legal≠marca iría a B, no a A (el caso
  vendido_bajo existe en el esquema y NO se auto-deriva).
- Los ids nuevos tier-C usan el pm de la ingesta como canonical_model: si el pm
  del documento era sucio, el candidate hereda la suciedad — por eso nacen
  candidate (QA los limpia o retira) y jamás consumibles sin adjudicación.
- E1 NO toca: relations/docrel sin consumidor (fase posterior), pm de familia
  (E3), el doble catálogo (E2).
