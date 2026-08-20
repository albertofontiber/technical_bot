# s331 — APLICACIÓN «A + E» v2 (POST-DÚO r39) — lo aplicado y lo que el dúo cambió

**SUPERSEDE a `evals/s331_aplicacion_AE_propuesta_v1.md`** (la versión que atacó el dúo).
**Firma**: Alberto, 20-ago-2026, «A + E, aplícalo», tras leer `s331_sondas_alcance_resultado_v1.md`.
**Dúo r39 EMPAREJADO** (esta vez sí): Sol xhigh 3/3 confirmados (0 FP, máx. medio) + Fable 4/4
confirmados (0 FP, máx. medio). **Aplicado**: recibo `evals/s331_lote_AE_aplicar_20260820T204701Z.json`.

## Lo que el dúo cambió antes de escribir

1. **[Sol medio] Freeze-contract**: A y E tenían recibos separados contra el mismo estado inicial;
   aplicar uno invalidaba el freeze del otro. → Se generó el **plan combinado**
   `evals/s331_lote_AE_plan_v1.json` (provenance de FIRMA, sin marcas de sonda) y se corrió un
   **dry-run nuevo del plan exacto** antes del `--aplicar`. PASS: detector 1744→1755 (+11/−0),
   0 gold perdidas, 0 disparos (sintéticos y 111 reales).
2. **[Sol medio + Fable menor] Sobre-atestación del software.** MNDT701 no enumera modelos: su
   única evidencia es «El software permite comunicarse con hasta 64 detectores IR3». Verificado
   contra el corpus, el cuadro es peor de lo que la propuesta admitía:
   - **RS-485 no discrimina**: lo tienen los tres IR³ **y** el 20/20R (single IR); los UV
     (20/20U/UB) y UV/IR (20/20L/LB) no lo tienen — se configuran por microinterruptores SW1/SW2.
   - **El software es de 1997 v1.0 y es ANTERIOR a los tres manuales** (20/20I 1999-2003,
     S20/20SI 2003-06, S20/20MI rev D 2010-11).
   → Las 3 entries de MNDT701 se escriben como **`secondary`**, no `primary`. Efecto verificado en
   el código (`catalog_resolver.py:182-191`): una entry `secondary` **sí** mete el documento en las
   fuentes del producto (`_docs_by_id`), pero **no** reclama propiedad del scope gobernado — el
   manual se sirve al preguntar por esos detectores sin afirmar compatibilidad individual. Es el
   modelado que la evidencia sostiene.
3. **[Sol menor] Cifra de filas.** U/UB comparten `document_id`, igual L/LB: el writer fusiona
   entries por documento. Son **9 filas documentales de la serie + 13 vínculos** (no «11 filas»).
   Total del lote aplicado: 12 operaciones de doc_map.
4. **[Fable medio] Gap mal declarado.** Dije que 20/20I (3 chunks) era «la cita más floja»; la
   **más floja es 20/20R con 2 chunks**. Ambas son titular de portada, pero el gap ahora nombra la
   fila correcta.
5. **[Fable medio] «8 documentos huérfanos» era falso**: el manual del 20/20ML **ya tenía fila** de
   doc_map (3 entries `secondary`: fs-1200, 380114-2, model-787640). Son **7 huérfanos + 1 fila
   ampliada**. Verificado que el writer fusiona por `document_id` (no duplica): la fila resultante
   lleva las 3 previas + `spectrex:20-20ml` como `primary`.
6. **[Fable medio] La marca del packet queda contradictoria** — MNDT600 estaba anotado «RESUELTO →
   pm `unknown`, **sin doc_map**» y ahora lleva doc_map. → Se **supersede explícitamente** en el
   packet (script `s331_packets_estado.py`) y se declara aquí.

## Lo aplicado (verificado tras escribir)

- **A**: `MNDT600` → 3 entries `primary`: `notifier:smart3g-c3`, `notifier:smart3g-d3`,
  `sensitron:smart-2`. **+0 términos** al detector. El `product_model` del documento sigue siendo
  `unknown` a propósito: el doc no nombra un modelo, y el vínculo vive en el doc_map, que es su
  sitio.
- **E**: 9 altas en catálogo (`spectrex:s20-20mi`, `s20-20si`, `20-20i`, `20-20r`, `20-20u`,
  `20-20ub`, `20-20l`, `20-20lb`, `20-20ml`), 2 alias (`20/20MI`, `20/20SI`), 12 filas de doc_map.
  **+11 términos**, todos de modelo. 9 productos que no existían pasan a tener 1-3 fuentes.

## Gaps que siguen declarados

1. **Ninguna gold se mueve** (0 ganancias / 0 pérdidas): cobertura de catálogo, **no delta medido**.
2. El vínculo software→familia IR³ es `secondary` por la evidencia de fecha; si se quisiera servir
   como fuente primaria de un modelo concreto haría falta adjudicación explícita o una lista de
   compatibilidad. **No la hay.**
3. `20/20R` es la cita más floja del lote (2 chunks), seguida de `20/20I` (3). Ambas son titular de
   portada del manual del propio modelo.
4. **Sesgo declarado en A** (Fable): elegir «los 3 confirmados» es un proxy del estado del catálogo,
   no una razón documental — Alberto habló de GD3/GD2, no de `smart-2` ni `smart3g-c3`. **Plan de
   re-visita**: cuando E1b promueva los 8 candidates SMART, esta fila debe re-evaluarse para no
   quedar sesgada a 3 sin motivo. Queda anotado en el `no_aplicar` del plan y en DEC-258.
5. No se crea paraguas «20/20»/«S20/20» (47+41 menciones sueltas) ni se mapea MNDT690 (catálogo de
   gama, clase R1): ambos son lote aparte.
