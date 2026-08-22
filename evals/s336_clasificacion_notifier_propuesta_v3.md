# s336 · Clasificación del catálogo (Notifier) — v3 VINCULANTE (ronda limpia adjudicada)

> Sustituye a la v2. **Ronda de registro ts=2026-08-21T18:59:43, EMPAREJADA** (Sol 6 +
> Fable 4 = 10 hallazgos, 0 FP; veredictos «no sólido todavía» por reconciliaciones de
> especificación — ninguno toca el método de fondo). Adjudicación completa en §5.
> Precedente de corte (s335/s331 anti-parálisis): una ronda válida adjudicada con
> cierres visibles habilita el build; una tercera ronda sería ritual.

## 0 · Población y cifras — DERIVADAS DEL CÓDIGO, no de mi contador (Sol2-3 + Fable2-1)

Mis «505/484/18» mezclaban el join real con un contador propio de ids CRUDOS: los «18
sin docs» eran ARTEFACTO — `_productos_marca` exige docs vía `follow_redirect`
(`telegram_bot.py:382`), la misma clase de fallo redirect que s334b corrigió (G3, dos
veces en un día). Cifras canónicas, reproducidas por el join del código:

- **Diana = 502 productos sin `clasificacion` de la vista Notifier — TODOS con docs**
  (por construcción del join). Denominador del gate de utilidad: **502**.
- La vista incluye namespaces reales vía `vendido_bajo`: notifier 456 · firelite 14 ·
  systemsensor 12 · spectrex 10 · morley 3 · ada 3 (+…). Clasificarlos paga su vista
  de origen además de la Notifier; tranches posteriores DEDUPLICAN por id.
- `unresolved:*` fuera (no están en la vista). Barra heredada: 29/29=100% (recibo
  congelado s322-76). B1 regenera el censo EXCLUSIVAMENTE con `_productos_marca` +
  `follow_redirect` y su recibo imprime la derivación.

## 1 · Método (cierra los 6 de Sol r2)

1. **Pasada** = s322b completo (v2 §1.1-1.3): muestra 3 docs × 3 chunks, cita verbatim
   por campo, degradación, smoke 10, **repesca dirigida a tablas de modelos** heredada.
2. **Full-text pre-escritura**: la cita ÍNTEGRA del veredicto se verifica contra el
   TEXTO COMPLETO del doc atribuido ANTES de truncar a 200 para almacenar (espejo
   `verifica_citas_v1`); sin full-text → packet.
3. **`clasificacion` persiste su doc (Sol2-2, crítico)**: el writer YA localiza
   `doc_cat` y lo tiraba — pasa a almacenarse: `clasificacion.doc = <source_file>`
   (cambio de esquema; el validador de `catalog_store` se extiende para admitir/exigir
   la clave en filas nuevas; las 171 filas viejas quedan válidas sin ella — migración
   NO retroactiva en este lote, declarada).
4. **Completitud multi-doc para CAPACIDAD (Sol2-1, crítico)**: lazos/zonas de un
   producto solo se escriben si TODAS sus fuentes mapeadas fueron examinadas para
   capacidad (la pasada muestrea 3 docs; para productos con categoria=central|repetidor
   o con capacidad hallada en ≥1 doc, una sub-pasada barata recorre TODOS sus docs
   buscando menciones de lazos/zonas — regex + ventana, LLM solo si hay mención). Si
   quedan fuentes sin examinar o hay divergencia (cualquier eje) → **packet, jamás
   write-fusión**. La categoría NO exige este barrido (una fuente que la ancla basta).
5. **`alcance` con forma CERRADA v1 (Sol2-4)**: `{"eje": "idioma_doc", "valor": iso}`,
   derivado mecánicamente del doc atribuido (sufijo `_es`/`_en`/`_ml` del source_file o
   metadato) y declarado como derivación. Ejes mercado/variante NO se reclaman en v1:
   cualquier divergencia de capacidad entre docs —del eje que sea— va a packet, y el
   display sirve POR FUENTE las entradas con alcance distinto (nunca el max fusionado).
   **#76b NO se declara CERRADO**: se declara «write-fusión imposible por construcción
   + display por-fuente + eje idioma_doc cableado; ejes mercado/variante abiertos y el
   cierre contra producción espera la primera divergencia real» (Fable2-4: el test
   AFP1010 es fixture — se dice así en el DEC).
6. **Writer atómico con SHADOW COMPLETO (Sol2-6)**: copia de los 7 jsonl a temporal →
   products candidato → `validate(temp_dir)` ENTERO → backup timestamped → `os.replace`
   → test de rollback (validación fallida ⇒ vivo byte-idéntico).
7. **GT 30 SIN circularidad (Sol2-5 + Fable2-2/5)**: etiqueto leyendo el TEXTO COMPLETO
   de los docs (todos los chunks; render PDF si una tabla lo exige), no los 2 primeros
   chunks del instrumento heredado; el recibo del GT registra la profundidad de lectura
   por fila. Estratos: nº-docs (objetivo) + **cuota ≥1 por namespace de origen presente
   en la diana** (notifier/firelite/systemsensor/spectrex/morley/ada) + familia-aparente
   SOLO como proxy de muestreo declarado. Congelado con SHA antes de la pasada.
8. **Suelo del gate de efecto CON procedencia (Fable2-3)**: B1 censa las
   centrales-APARENTES de la diana (proxy de nombre, DECLARADO como apuesta); el suelo
   «≥N centrales servidas» se fija en el freeze del GT como min(15, ⌈proxy×0,5⌉) con la
   derivación visible — pre-registrado ANTES de la pasada, jamás ajustado después.
9. Enum cerrado, veredicto PARCIAL bajo 60% de 502, no-regresión byte de 171 filas,
   replay `a9ba756a`, suite+MT — como v2.

## 2-4 · Alternativas, coste, colas — como v2

(Coste sube con la sub-pasada de capacidad: ~502 llamadas + repesca + barrido de docs
de centrales; estimación ~$15-30, smoke primero con coste real estampado.)

## 5 · Adjudicación ronda ts=2026-08-21T18:59:43 (10/10, 0 FP)

| # | hallazgo | cierre |
|---|---|---|
| Sol2-1 crít | divergencia NO observada pasa como alta (falta completitud multi-doc) | §1.4 barrido de capacidad + packet |
| Sol2-2 crít | `clasificacion` no persiste el doc que la fundó | §1.3 clasificacion.doc + validador |
| Sol2-3 med | 505/484/18 contradice el join declarado | §0 cifras re-derivadas; 18 = artefacto redirect |
| Sol2-4 med | `alcance` subespecificado; «CERRADO» = sobre-framing | §1.5 forma cerrada v1 + #76b sin declarar cerrado |
| Sol2-5 med | GT desde los 2 primeros chunks = acuerdo circular | §1.7 lectura completa + profundidad en recibo |
| Sol2-6 men | validar solo products omite referencias cruzadas | §1.6 shadow de los 7 jsonl |
| Fable2-1 crít | «18 sin docs» imposibles bajo el join citado | §0 (=Sol2-3) reconocido como error mío |
| Fable2-2 med | un solo gate para varios namespaces reales | §1.7 cuota por namespace en el GT |
| Fable2-3 men | «≥15 centrales» sin procedencia | §1.8 suelo derivado del censo, pre-registrado |
| Fable2-4 men | cierre #76b solo contra fixture | §1.5 declarado en DEC tal cual |

## 6 · Build (B1-B7)

B1 censo por `_productos_marca`+redirect (recibo con derivación + proxy de centrales +
suelo del gate) · B2 GT 30 lectura-completa con cuotas + freeze SHA · B3 esquema
`clasificacion.doc` + `alcance` + validador + writer atómico shadow + display por-fuente
+ tests (rollback, AFP1010 fixture) · B4 smoke 10 → pasada → repesca → barrido
capacidad → full-text → gate ≥95% · B5 escritura + efecto (suelo pre-registrado) +
veredicto PASS/PARCIAL honesto + suite/MT · B6 packet §1 + recibos + DEC + digest/PLAN/
HISTORY · B7 PR + mergeabilidad.
