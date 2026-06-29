# Revisión adversarial — REGLA de granularidad para construir `document_models` (s83, F2)

## Qué se decide (zona de dolor: identidad/esquema)
Tengo la extracción dúo (Opus 4.8 + GPT-5.5) de identidad multi-label de 1014 docs PCI (qué modelos
cubre cada manual). Reconciliados ya 985 (757 agree + 228 superset; 29 conflict pendientes de Alberto).
Ahora construyo la tabla normalizada `document_models` (1 fila = 1 producto físico; arrastra todos sus
identificadores) con un **transform determinista** (`scripts/s83_build_document_models.py`, $0,
re-ejecutable desde el JSONL crudo). **No toca la DB ni retrieval** — es el activo de identidad limpia (F2).
Marcador de éxito = **findability** (técnico busca "SCD-100" o "55310400" y cae en el doc), NO el eval de golds.
Debe **escalar a 30+ fabricantes**. Contrato: BP + raíz + precisión>velocidad + **no perder info**.

## La REGLA (lo que se revisa)
- **R1** 1 fila = 1 producto físico distinto.
- **R2** `canonical_model` = nombre comercial limpio; `aliases[]` = SKU/part-number/descriptivo/base-sin-sufijo.
- **R3** cadenas COMPUESTAS ("DS 5 / DS 10 - TAS", "MPS-24A/MPS-24AE") NUNCA se guardan → se **parten**.
  Split **evidence-gated**: solo si las piezas están atestiguadas por separado (otra extracción o alias
  atestiguado). → NO parte "DS 10 -3G/3D" (un solo modelo ATEX). **[VALIDADO en muestra]**
- **R4** SKU + nombre comercial = UN registro (canonical=nombre, SKU en aliases). **[VALIDADO: TMD-100/55310008]**
- **R5** variantes pedibles reales (DS 5 vs DS 10; -TF) → registros SEPARADOS, `role=secondary`, enlazables.
- **R6** reconciliación: agree→conjunto; superset→UNIÓN; granular-vs-comprimido→el GRANULAR (split).
  Secundario hallado por UN solo modelo → `candidate=True` (guardarraíl, no auto-acepta).
- **Agrupación**: dos covered-objs (uno Opus, otro GPT) = mismo producto si sus key-sets
  {model ∪ canonical ∪ aliases} normalizados **intersectan** (union-find).

## ISSUE A — DECLARADO por mí (regla C, auto-revisión): el bridging de aliases genéricos
La agrupación por intersección de key-set usa CUALQUIER alias compartido como puente, incluidos los
**no-discriminantes** (familia/serie/base) → **fusiona productos HERMANOS DISTINTOS**:
- `DS 10` absorbió `DS 5` (vía alias "DS series" / "sounders of type series DS") — pero DS 5 ≠ DS 10
  (Alberto confirmó: modelos diferentes, distinta potencia).
- `FS24X-9` ⟷ `FS24X-2` (vía base "FS24X"); `VLI-880` ⟷ `VLI-885` (vía "VESDA VLI"); `2X-AE2-P` ⟷ `2X-AF2-P`.
- **Magnitud**: 976/2065 filas (47.3%) tienen un alias = modelo-limpio distinto (cota SUPERIOR; incluye
  descriptores de familia legítimos como "VESDA VLF" que SÍ son alias válido de VLF-250). El bug real es
  un subconjunto, pero sistemático.

### 3 fixes candidatos (pido que el dúo critique/elija el BP + escalable a 30+)
- **Fix 1 — match primary↔primary (mi lean).** Fusionar solo si `model` o `canonical_model` norm-coinciden;
  los aliases se ARRASTRAN pero NUNCA son merge-key. Pro: mata todos los puentes, 0 heurística, 0
  hiperparámetro. Con: sub-merge si el primary difiere solo por formato (mitigable normalizando espacios
  internos en `norm`); hace que la variante granular de Opus gane al fold de GPT (deseado, ver JC1).
  Verificado a mano: arregla DS/FS24X/2X-AE-AF y PRESERVA TMD-100/55310008 (canonical match) y los splits.
- **Fix 2 — excluir tokens genéricos del merge-key** (freq≥K en el doc, o /SERIE(S)?/, o base-prefijo de
  ≥2 modelos limpios). Pro: mantiene matching laxo para sinónimos reales. Con: hiperparámetro K + "genérico"
  es heurístico y puede fallar ("VESDA VLI" parece limpio pero es familia) → más piezas que razonar a 30+.
- **Fix 3 — bloquear merge si ambos tienen primaries-limpios DISTINTOS** (salvo uno-contiene-al-otro).
  Pro: apunta al bug exacto, preserva SKU↔nombre. Con: misma heurística "limpio"; puede sub-mergear
  prefijos ("VEU-A00" vs "VESDA-E VEU-A00").

## Decisiones de JUICIO genuinas (no bugs — pido criterio)
- **JC1 (granular vs fold, ya hablado con Alberto):** NRT-586T — Opus da 4 registros (TW/TF/TWF como
  variantes de enlace), GPT da 1 con TW/TF/TWF en aliases. Alberto pidió "registrar granular + enlazado"
  (que "NRT-586TF" sea buscable). ¿`default=granular` es correcto, o arriesga inflar con config-options
  que no son SKU? ¿Cómo enlazar la variante al base sin perder ninguno?
- **JC2 (ruido de `field_conflicts`):** casi TODO doc marca conflicto de identidad (family_scope/doc_type/
  protocol/brand) porque reconcilio por match-exacto → "instalacion"≈"manual de instalacion",
  "Notifier"≈"Honeywell"(padre) se marcan. ¿Suavizar (normalizar sinónimos), tratarlo como señal-soft
  no-bloqueante, o solo marcar brand/oem (lo consecuente)?
- **JC3 (bucket `candidate`=19.4%, 401 filas):** secundario hallado por 1 solo modelo → `candidate`.
  Ej. doc NRT lista AFP-200/300/AM2020 como candidates (probable "mencionado compatible", no cubierto).
  ¿`candidate` (guardar, no-validado) basta, o el secundario-de-1-modelo se DEBE DESCARTAR (no guardar)?

## Lo que pido (bite concreto, anclado en evidencia)
1. **Confirmar/cuantificar ISSUE A** y elegir/criticar el fix (¿cuál es BP + escala a 30+ sin tuning?).
2. **Encontrar issues que YO NO VI** (B, C…) en la regla o el transform (`scripts/s83_build_document_models.py`)
   — p.ej. ¿el split R3 puede perder una pieza? ¿`pick_canonical` elige mal el comercial? ¿`norm` colapsa
   algo que no debe? ¿la reconciliación de identidad pierde el OEM evidenciado?
3. **Pronunciarse sobre JC1-JC3** con criterio de findability + escala.
4. ¿Hay algo que NO estoy capturando que obligue a re-extraer (re-pagar)? (la tabla es re-transform $0;
   re-extraer NO lo es).

Contexto adjunto: `evals/s83_build_sample.md` (muestra de 17 docs con la salida real del transform).
Código: `scripts/s83_build_document_models.py`. JSONL crudo: `evals/s83_full_extraction_merged.jsonl`.
