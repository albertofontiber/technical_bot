# s316 — #70: el estado conversacional es ciego a las rutas que no pasan por RAG

**OBJETIVO + MÉTRICA de HOY**: que un cambio de marca EXPLÍCITO del usuario no sea
ignorado por el carry-forward. Fallo ORGÁNICO verificado en `query_logs` (9-ago
21:58-21:59Z, Alberto): tras hablar de la NC-PF2 (Kidde) pidió «pasemos a productos
Morley…» y el turno siguiente se respondió **con `target_models=[NC-PF2]` arrastrado**,
citando manuales Kidde. Métrica: reproducción determinista del escenario A→B→C (RAG
Kidde → inventario Morley → follow-up) sin arrastre, con la suite verde y sin tocar
retrieval.

**DECLARACIÓN DE LEVER (Protocolo 2 §5).** Esto **NO** es el lever «identidad como
recall» del digest (SETTLED · métrica = retrieval-miss del eval · `−3 banked`,
DEC-084/091b). Aquel mide *añadir* señal de identidad para GANAR recall; aquí se trata de
*dejar de inyectar* un filtro obsoleto que el usuario ya contradijo. **Las métricas NO
coinciden**: settled-en-retrieval-miss ≠ objetivo-de-hoy (corrección de contexto
conversacional). Y el digest lo dice explícito para este eje (DEC-154): el veredicto de
utilidad respuesta-única **no transfiere** a la utilidad conversacional, que se mide en
métrica MT propia. **Este cambio no añade ningún filtro nuevo a retrieval.**

## Diagnóstico (verificado en código y en producción, no teorizado)

| Hecho | Evidencia |
|---|---|
| El fallo corrió por el carry-forward LEGACY, no por F1 | ninguna traza de `query_logs` tiene clave `policy` ⇒ `CONVERSATION_POLICY` no está activo |
| El turno de inventario no deja traza ninguna | su fila tiene `rag_trace = NULL` |
| `catalog_shortcut` responde y `return`a en `handle_message` | `telegram_bot.py:838-840, 927-930, 946-949` |
| TODO el estado conversacional vive en `_process_query` | `:1300-1305` (`last_query`, `last_response`, `last_query_time`, `last_detected_models`) |
| `handle_message` (775-960) y `_process_query` (1053-1540) son funciones DISTINTAS | las rutas tempranas nunca llaman a la segunda |

**La raíz no es el carry-forward: es que el estado se actualiza como EFECTO SECUNDARIO de
una sola ruta.** Cualquier máquina de estados que viva dentro de `_process_query` es
ciega a las demás. **Corolario que descarta el atajo obvio: activar F1 NO arregla #70** —
la política vive dentro de `_process_query` y heredaría la misma ceguera;
`conversation_policy_impl` no menciona catálogo ni inventario.

**#70 es una instancia de una clase de ~6**: `catalog_shortcut` (×3),
`manufacturer_mismatch`, `manufacturer_no_model` (×2) — todas responden contenido y dejan
el estado congelado en el último turno RAG.

## Recomendación

**Un seam único de registro de turno**, llamado por TODA ruta que responda contenido:

```
_registrar_turno(context, *, query, respuesta, ruta, modelos=None, marca=None)
```

- Siempre: `last_query`, `last_response`, `last_query_time`, `last_route`.
- `modelos` explícitos (RAG con modelos) → se fijan.
- `modelos=None` **y ruta de marca** (`catalog_shortcut`, `manufacturer_*`) → **se LIMPIA**
  `last_detected_models` y se registra `last_manufacturer`.
- RAG sin modelos → NO toca los modelos (el carry-forward legítimo sigue vivo).

El carry-forward de `:1096` no se toca: pasa a leer un estado que ya es coherente con la
conversación. `last_manufacturer` se registra **solo como estado/traza**; NO se conecta a
retrieval en este cambio (ver alternativas).

## Alternativas consideradas y descartadas

- **Hot-patch: `context.user_data.pop("last_detected_models", None)` en las 3 salidas de
  `catalog_shortcut`.** Arregla el síntoma reportado y nada más; deja vivas las otras 3
  rutas de la misma clase y repite el patrón que causó el bug (estado actualizado
  ad-hoc en cada sitio). La 4ª vez que aparezca la clase, seguirá sin haber seam.
- **Activar `CONVERSATION_POLICY=impl` (F1/MT-1a).** Descartada por MEDICIÓN de código, no
  por opinión: la política se instancia en `_process_query:1083`, después de los `return`
  de las rutas tempranas ⇒ no las ve. Además activar F1 es un cambio de gate propio
  (Fase 2, métrica MT) y mezclarlo con un bugfix contaminaría ambos.
- **Conectar `last_manufacturer` a un filtro de retrieval.** Es territorio del lever de
  identidad, EXHAUSTO en su métrica y con `−3 banked`; y ADD es un band-aid declarado
  (DEC-091b). Meter un filtro nuevo aquí sería re-litigar un lever medido dentro de un
  bugfix. Se registra el dato, no se enchufa.
- **Mover `catalog_shortcut` dentro de `_process_query`.** Le haría pagar el coste del
  camino RAG (o exigiría un by-pass) a una ruta cuyo valor es ser $0 e instantánea.
- **Arreglar también «no filtró por central de incendios»**: es OTRO defecto
  (`_inventario_fabricante` no admite filtro por tipo de producto). Fuera de alcance
  aquí; se declara como ítem separado para no mezclar dos fixes en un dúo.

## Gaps / riesgos declarados

1. **El fix corrige la marca, NO la segunda queja de Alberto.** Su mensaje señalaba dos
   cosas; esta propuesta cubre una. La otra queda anotada, sin arreglar.
2. **Limpiar puede ser peor que arrastrar en un caso**: si el usuario pregunta el
   inventario de la MISMA marca del modelo en curso («¿qué más centrales Kidde tienes?»)
   y luego hace un follow-up de modelo, hoy el arrastre acierta por accidente y con el fix
   se pierde. Mitigación posible: limpiar solo si la marca pedida ≠ marca del modelo en
   curso. Añade una resolución modelo→marca en el camino caliente; **no decidido — es la
   pregunta principal para el dúo**.
3. **`last_query_time` pasa a refrescarse en rutas $0**, lo que ALARGA la ventana de
   `SESSION_TIMEOUT` para el carry-forward. Efecto lateral real; puede querer lo contrario.
4. **Sin test multi-turno hoy**: no existe harness conversacional (la métrica MT es de
   Fase 2). El contrato se fijará con un test de handler que simule A→B→C sobre
   `context.user_data`, que es más débil que una medida de calidad.
5. **`user_data` es memoria de proceso**: un redeploy de Railway lo borra. El fix no
   cambia eso (ya era así), pero significa que el escenario no es reproducible en
   producción tras un reinicio.
6. **No hay métrica de calidad**: se declarará corrección de comportamiento, NO mejora
   medida. Nada de delta.

## Por qué BP + estructural + escalable

- **BP**: una sola función responsable del estado, invocada por todas las rutas; el
  invariante («todo turno que responde actualiza el estado») deja de ser una convención
  que cada ruta puede olvidar y pasa a ser un punto único auditable.
- **Estructural**: ataca la raíz (estado como efecto secundario de UNA ruta), no la
  instancia reportada. Cierra las ~6 rutas de la clase a la vez.
- **Escalable**: la ruta nº7 que se añada tendrá que pasar por el seam; y cuando F1 se
  active en Fase 2, encontrará un estado ya coherente en vez de heredar la ceguera.
