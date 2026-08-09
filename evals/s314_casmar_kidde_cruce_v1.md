# s314 — Cruce Casmar↔corpus de documentación Kidde (recibo)

**Origen.** Alberto (8-ago): pregunta orgánica al bot por el manual de instalación del
Kidde NC-PF2 → el bot respondió honesto («solo tengo ficha/especificaciones») y el gap
es real: la familia NC-PFx (centrales convencionales) solo tiene datasheets en corpus;
la serie NC (algorítmica) sí tiene manuales. Encargo: añadir el manual desde
casmarglobal.com, revisar TODA la documentación Kidde de Casmar contra el corpus
(SIN certificados ni homologaciones), y usar el lote para estrenar `ingest_new.py`.

## Método (reproducible)

1. **Catálogo**: búsqueda de tienda `catalogsearch/result/?q=kidde&product_list_limit=36`
   paginada → **88 SKUs**; unión con los 20 SKUs Kidde del corpus → **94 SKUs**.
2. **Docs por SKU**: `documentacion?form_id=af52b3cc…&filters[sku]=<SKU>` — el
   `form_id` es OBLIGATORIO (sin él el filtro se ignora en silencio y devuelve el
   listado global; guarda anti-fallback: resultado == baseline global ⇒ 0 docs).
   78/94 SKUs con documentación; **266 PDFs únicos** (dedup por URL).
3. **Clasificación por prefijo de filename** (taxonomía del portal): MI_=manual
   instalación · MU_/M_USO=manual usuario · G_INST_/G_USO_/G_USU_=guías · GR_/QG_/
   «Guía rápida»=guía rápida · DS_/HD_=datasheet · TG_/NT_=nota técnica ·
   **EXCLUIDOS (regla de Alberto): H_DOP_/H_CPR_/H_CE_/CE_/C_/DOP_/INCERT** =
   homologaciones/certificados/declaraciones. 134 incluibles / 132 excluidos / 0 sin
   clasificar.
4. **Cruce por (product_model, tipo) contra TODO el corpus activo** (no solo
   manufacturer=Kidde — los 2X-* son Aritech OEM por el override `2X-` de
   config/portal.yaml; comparar solo contra Kidde daba 3 falsos gaps, corregido).

## Resultado

- **104 gaps**: 41 manuales de instalación · 3 manuales de usuario · 3 guías de
  instalación · 2 guías de uso · 4 guías rápidas · 51 datasheets.
- **30 ya cubiertos** (mismo tipo ya en corpus para sus SKUs).
- El manual pedido por Alberto está: `MI_KIDDE_NC_PFx_202502_ES` (+ G_INST, G_USO y
  guía rápida de la familia NC-PFx).

## Riesgos declarados (sin caps silenciosos)

- **Vista filtrada del portal**: ignora `p=` y muestra todo en una página; ~6/94 SKUs
  devolvieron exactamente 10 PDFs (= tamaño de página del listado global). Si existiera
  un cap de 10, los docs de familia reaparecen bajo SKUs hermanos con <10 y el dedup
  por URL los recupera — riesgo residual acotado, no cero.
- **Familia 2X-AT**: el corpus la cubre bajo equipo «2X-A Táctil» (el sidecar existente
  ya lista los SKUs 2X-AT-*); los MI/MU de Casmar para 2X-AT pueden ser el mismo manual
  (¿o revisión más nueva?) — el sha-dedup de la descarga decide: byte-idéntico se
  descarta, distinto se revisa como posible revisión antes de ingestar.
- **Docs de familia duplicados por SKU**: el PIM de Casmar sube el mismo PDF con hash
  de media distinto por producto (p.ej. MI_KIDDE_NC_PFx aparece con sufijo 62f8 bajo
  NC-PF2 y 8f59 bajo NC-PF4) — dedup por sha256 del CONTENIDO tras la descarga.

Datos: `evals/s314_casmar_kidde_cruce_v1.json` (gaps/cubiertos/excluidos con SKUs y
URLs). Descarga+dedup+coste: `evals/s314_casmar_batch_report_v1.json` (el recibo del
lote descargado).

## CIERRE (post-lote, 9-ago)

Re-cruce con el instrumento corregido (split del pm-lista + mapa de tipos multi —
sin ambos, los docs recién ingestados aparecían como gaps de sí mismos):
**104 gaps → 1 residual declarado** (`MI_..._XIP` para KE-ASA-AUXR: la hoja XIP no
menciona ese SKU — el link de Casmar es cruce comercial; no existe doc de instalación
propio en ningún sitio y su datasheet SÍ está ingestada). 133/134 incluibles cubiertos:
74 ingestados (recibos `logs/ingest_new_*`) + 1 near-dup retirado + 2 byte-idénticos
resueltos por extensión de pm (KIT 2X-AT) + el resto cubierto por el fix de identidad.
JSON de cierre: `evals/s314_casmar_kidde_cruce_cierre_v1.json`. El hallazgo estructural
(el gap orgánico era FINDABILITY: pm de familia no matchea la variante de la query) y
sus fixes: DEC-192 + `evals/s314_identity_*_v1.json`.
