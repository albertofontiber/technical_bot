# s316 v2 — #70: guarda de CAMBIO DE MARCA pre-routing (rediseño tras dúo NO-SÓLIDO ×2)

> **El v1 fue NO-SÓLIDO por los dos revisores y su premisa central era FALSA.** Este v2 no
> es una enmienda: cambia el mecanismo, el estado que toca y el punto donde actúa.

## Qué invalidó el v1 (verificado, no aceptado de palabra)

| Claim del v1 | Realidad verificada |
|---|---|
| «F1 no está activo; corrió el carry-forward legacy» | **FALSO.** Railway: `CONVERSATION_POLICY=impl`, `ORCHESTRATOR_PATH=on`. La inferencia «no hay clave `policy` en `rag_trace`» era inválida: `runtime_trace.py` **nunca** emite política conversacional (solo `release_policy`, que es el perfil de release) |
| El seam debe limpiar `last_detected_models` | **NO-OP en producción**: con F1 activo el carry-forward legacy está apagado (`if not f1_active`, `:1094`) y la política lee `mt_working_state` (`:1176`). El v1 habría pasado sus tests sin arreglar nada |
| «Ruta de marca ⇒ limpiar» | Incorrecto en `manufacturer_mismatch` (`:860-871`): ahí el bot INVITA a preguntar por ese modelo ⇒ la semántica correcta es FIJARLO. Y `catalog_shortcut` también cubre el catálogo GENÉRICO sin marca |
| «No existe harness conversacional» | **FALSO**: `scripts/test_multiturn_vs_gold.py` (32KB) + `evals/multiturn_golds_v1.yaml` |
| «Resolver modelo→marca es caro» | **FALSO**: `classify_model_manufacturer` es in-memory, catalog-first, sin roundtrip. Probado: `NC-PF2→Kidde`, `2X-A→Aritech`, `CAD-150→Detnov` |
| «Censo de 6 rutas cierra la clase» | No: `«¿y en Morley cómo se hace el reset?»` cae a RAG por fall-through y reproduce el fallo sin tocar ninguna de las 6 |
| Seam llamado a mano en cada `return` | Sigue siendo una convención olvidable: no obliga a la ruta nº7 |

**OBJETIVO + MÉTRICA de HOY**: que un cambio de marca EXPLÍCITO no sea ignorado.
Reproducción determinista del caso orgánico A→B→C (RAG Kidde → «pasemos a productos
Morley» → follow-up) sin arrastre, **más un control que NO debe cambiar**: la pregunta de
compatibilidad («¿es compatible con Hochiki?»), que hoy acierta vía
`brand_compatibility_in_window` y debe seguir acertando. Instrumento: el harness MT
existente, ampliado — no un test de handler aislado.

**LEVER (Protocolo 2 §5)**: NO es el lever «identidad como recall» (SETTLED · métrica
retrieval-miss · −3 banked, DEC-084/091b): allí se AÑADE señal para ganar recall; aquí se
INVALIDA un producto que el usuario contradijo. Métricas distintas, y DEC-154 declara que
el veredicto respuesta-única no transfiere a lo conversacional. Matiz que el dúo exigió:
no añado filtro, **retiro** uno en el turno siguiente ⇒ **el eval single-turn medirá delta
0 por construcción**; la medida vive en el eje MT.

## El mecanismo real del fallo (dos causas independientes)

1. **Ceguera de ruta**: el turno B (`catalog_shortcut`) responde y `return`a en
   `handle_message` (`:838-840`), así que **F1 nunca ve el cambio de marca**; el turno C
   resuelve contra un `mt_working_state` que aún lleva `NC-PF2`.
2. **La política, aunque lo viera, arrastraría igual**: `conversation_policy_impl:398-403`
   clasifica «marca sola + in-window» como `CARRY_FORWARD:"brand_compatibility_in_window"`.
   Es un default RAZONABLE para compatibilidad y equivocado para un cambio de tema: la
   política **conflaciona marca-como-diana-de-compatibilidad con marca-como-cambio-de-tema**.

## Recomendación: una guarda ÚNICA, pre-routing

Un helper invocado al **principio** del camino de todo turno de texto —desde
`handle_message` y desde `handle_voice`, que no pasa por el primero—, ANTES de enrutar:

```
_invalidar_producto_si_cambia_marca(context, query) -> str | None
```

Dispara **solo** si se cumplen las cuatro:
1. la consulta nombra un fabricante (resuelto contra la lista real, no el regex);
2. la consulta **NO** trae token de modelo (`extract_product_models` vacío);
3. la intención es **cambio de tema**, no compatibilidad (`_intencion_inventario` ya
   existente + frases de switch «pasemos a», «ahora con», «cambiando a»);
4. la marca nombrada **≠** `classify_model_manufacturer(mt_working_state.last_target_models[0])`.

Efecto: `mt_working_state = replace(ws, last_target_models=())` (el dataclass es `frozen`).
**No toca nada más**: ni el reloj, ni `last_query`/`last_response`, ni
`last_query_log_id`.

**Por qué pre-routing y no un seam por ruta**: es el único punto por el que pasan TODOS
los turnos, así que cubre las 6 rutas tempranas **y** el fall-through con un solo cambio;
y es **estructuralmente imposible de olvidar** para la ruta nº7 —responde a la objeción
conceptual de Sol de que una función llamada a mano sigue siendo convención—.

Cómo queda cada caso que el dúo levantó:

| Caso | Guarda | Resultado |
|---|---|---|
| «pasemos a productos Morley» (el fallo) | dispara | producto invalidado ✅ |
| «¿y en Morley cómo se hace el reset?» (fall-through) | dispara | ✅ cierra la mitad que el v1 dejaba viva |
| «¿es compatible con Hochiki?» | NO (intención de compatibilidad) | `brand_compatibility_in_window` intacto ✅ |
| «¿qué productos tienes?» (catálogo genérico) | NO (sin marca) | contexto preservado ✅ |
| «¿qué más centrales Kidde tienes?» (misma marca) | NO (marcas iguales) | arrastre legítimo preservado ✅ |
| `manufacturer_mismatch` (modelo + marca) | NO (hay token de modelo) | la ruta conserva su semántica ✅ |

## Alternativas consideradas y descartadas

- **Arreglar la clasificación dentro de `conversation_policy_impl`** (que `brand alone` mire
  la intención): es el sitio conceptualmente más limpio, pero **no cubre las rutas
  tempranas**, que ni llegan a la política — dejaría vivo el fallo ORGÁNICO reportado. Y
  tocar el clasificador mueve un contrato con tests congelados y gate MT propio.
- **Seam de registro por ruta (el v1)**: no-op sobre el estado vivo, semántica incorrecta
  en `manufacturer_mismatch`, y no cierra el fall-through.
- **Hot-patch en las 3 salidas del catálogo**: además de no-op (toca la clave muerta),
  deja 3 rutas y el fall-through.
- **Unificar `last_detected_models` y `mt_working_state` en una sola fuente**: es la deuda
  correcta a medio plazo (hoy hay dos estados y uno está muerto en producción), pero es
  refactor de la máquina conversacional, no un bugfix — se declara como deuda, no se hace aquí.
- **Enchufar la marca a un filtro de retrieval**: territorio del lever de identidad,
  EXHAUSTO en su métrica; se invalida contexto, no se añade filtro.

## Gaps / riesgos declarados

1. **La guarda es heurística de intención.** «pasemos a», inventario… no cubren todas las
   formas de cambiar de tema; y un falso positivo borraría contexto legítimo. Es
   fail-soft (se pierde carry-forward, no se responde de otra marca), pero es un
   trade-off real, no una victoria limpia.
2. **`classify_model_manufacturer` puede devolver `None`** para un modelo fuera del
   catálogo ⇒ la comparación de marcas no es concluyente y la guarda **no dispara**
   (fail-open deliberado). Verificado que resuelve el caso real (`NC-PF2→Kidde`), no que
   resuelva todos.
3. **Dos estados conviven**: `last_detected_models` (muerto bajo F1) y `mt_working_state`.
   Este cambio toca solo el vivo; el muerto sigue escribiéndose en `:1304-1305`. Deuda
   declarada, no resuelta — y es una trampa para quien lea el código mañana.
4. **`handle_voice` no pasa por `handle_message`**: si el helper no se invoca también allí,
   la voz queda sin guarda. Es la parte más fácil de olvidar del cambio.
5. **No arregla la segunda queja de Alberto** («no filtró por central de incendios»):
   `_inventario_fabricante` no admite filtro por tipo. Ítem separado.
6. **Sin medida de calidad**: el eval single-turn dará delta 0 por construcción. La
   evidencia será la reproducción A→B→C en el harness MT + el control de compatibilidad.
7. **`user_data` es memoria de proceso**: un redeploy lo borra. No lo cambia este fix.
8. **El fallo orgánico no es re-ejecutable tal cual**: el turno B ya no está en el estado
   vivo; la reproducción será sintética sobre el harness, no un replay de producción.

## Por qué BP + estructural + escalable

- **BP**: un invariante en un punto único y obligatorio, señal barata ya existente
  (in-memory, catalog-first), fail-open cuando la marca no se resuelve, fail-soft cuando
  la heurística se equivoca, y control explícito de no-regresión para el caso que hoy
  funciona.
- **Estructural**: ataca la conflación real (marca-compatibilidad vs marca-cambio-de-tema)
  en el único punto por el que pasan todos los turnos, en vez de parchear rutas una a una.
- **Escalable**: la ruta nº7 y cualquier transporte nuevo heredan la guarda por
  construcción; y cuando la Fase 2 unifique el estado, la guarda queda como una regla de
  intención, no como un parche de plomería.
