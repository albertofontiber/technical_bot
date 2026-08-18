# s324h — La voz no pasa por el plan: unificar el despacho con el de texto

**Nace de un dato del piloto, no de una hipótesis.** Alberto cambió a
`gpt-4o-transcribe`, la transcripción de «Detnov» salió PERFECTA, y aun así el bot
contestó «No he encontrado información relevante en los manuales disponibles». La
MISMA pregunta tecleada devolvió el listado correcto de 14 centrales.

**Estado**: diagnosticado y medido. **Nada cableado.** Esta propuesta va al dúo ANTES
de tocar código (Protocolo 3: impacto MEDIO en zona de dolor — el enrutado decide si
el retrieval llega a correr).

---

## 1. El diagnóstico, medido

Los dos textos exactos de la captura, contra `plan_turn`:

```
VOZ    '¿Qué centrales de Detnov tienes?'
       ruta='inventario'  datos={'marca': 'Detnov', 'filtros': {'categoria': 'central'}}
TEXTO  'Qué centrales de Detnov tienes?'
       ruta='inventario'  datos={'marca': 'Detnov', 'filtros': {'categoria': 'central'}}
```

**El plan acierta con los dos.** El fallo es que por voz nadie se lo pregunta.

`plan_turn` y el despacho completo de rutas viven DENTRO de `handle_message`
(`telegram_bot.py:1513` y ss.). `handle_voice` llama sólo a `_decidir_transicion`
—el predicado de invalidación de marca— y salta directo a `_process_query`, que es
el RAG completo. El propio código lo declara en dos sitios:

- `handle_voice`: «Expandir la voz al plan completo — cortesia/catalogo hablados —
  sigue siendo una decision de producto SEPARADA, v3 seccion 2.»
- `_process_query`: «La voz NO pasa por `plan_turn` y por eso nunca lo trae:
  declarado, no olvidado.»

Fue un aplazamiento consciente de la fase B del #70. El piloto lo ha convertido en
defecto: **por voz son inalcanzables las SIETE rutas de atajo** — `inventario`,
`catalogo`, `fabricantes`, las tres cortesías, `mismatch`, `marca_no_servida` y
`feedback`. Un «hola» hablado también se va al RAG completo.

Desde el técnico se ve así: el bot contesta lo escrito y se niega a lo mismo dicho.
Es la peor forma de perder confianza en la primera sesión, y el canal de voz es
precisamente el que un técnico usa subido a una escalera.

---

## 2. Recomendación

**Extraer el plan + despacho de `handle_message` a una función compartida y que
`handle_voice` la llame.** Boceto del contrato:

```
async def _servir_plan(update, context, query, *, meta, user_id) -> bool
    # True  = una ruta de atajo sirvió el turno (ya respondió y logueó)
    # False = no hay atajo; el llamador cae a _process_query como hoy
```

- `handle_message`: la llama; si `False`, `_process_query(source="text", ...)`.
- `handle_voice`: la llama con `Meta(fuente="voz", es_reply=...)`; si `False`,
  `_process_query(source="voice", transcription=raw_transcription)` — igual que hoy.

Efecto lateral bueno: **desaparece la llamada duplicada a `_decidir_transicion`** en
`handle_voice`. `plan_turn` ya la hace por dentro y devuelve `plan.transicion`; hoy
la voz corre el predicado por su cuenta y el texto lo corre otra vez dentro del plan.
Queda un único punto de decisión para las dos entradas.

## 3. Alternativas consideradas y por qué se descartan

| Alternativa | Por qué no |
|---|---|
| Cablear a la voz **sólo** la ruta de inventario | Es el mismo parche que Alberto rechazó en la tabla de transcripción: arregla el síntoma de hoy y deja seis rutas rotas. Y obliga a acordarse de cablear DOS sitios cada vez que nazca una ruta — el olvido es la conducta por defecto |
| Que `handle_voice` **fabrique un Update de texto** y delegue en `handle_message` | Cero duplicación, pero pierde `transcription=raw` en `_process_query` (rompe la auditoría del ASR), reevalúa el consentimiento y reenvía el `typing`. Acoplar por un objeto falsificado es frágil: cualquier campo que `handle_message` lea mañana se convierte en un fallo silencioso |
| Mover el despacho a `_process_query` | Mezcla dos responsabilidades que hoy están limpias: `_process_query` es el pipeline RAG, no un enrutador. Y los atajos existen precisamente para NO entrar ahí |
| Dejarlo como está y documentarlo | Ya está documentado — dos veces, en el código — y aun así el piloto tropezó. La documentación no es el control |

## 4. Gaps y riesgos declarados

1. **El contrato de log de la voz es el punto delicado.** Las rutas de atajo llaman
   `log_query(query=query)` con la forma NORMALIZADA. En voz, el contrato vigente
   (s324e, dúo r37) dice que lo que se registra es el ASR crudo y que la forma de
   búsqueda se declara aparte cuando difiere. Cablear la voz a los atajos sin tocar
   esto registraría la forma normalizada y perdería la cruda —justo el contrato que
   el dúo r40 nos hizo arreglar hace dos días—. **Es lo primero que debe mirar el dúo.**
2. **Cambios de conducta visibles, no todos neutros**: un «hola» hablado deja de ir al
   RAG (mejor, pero distinto) y deja de loguearse (coherente con la promesa v7 de
   «cortesía sin log», pero es un cambio); un «está mal» hablado pasa a capturarse
   como feedback en vez de ir al RAG.
3. **`Meta.es_reply`**: hoy la voz construye `Meta(fuente="voz")` sin ese campo. Si no
   se pasa, un audio en reply se enrutaría distinto que el mismo texto en reply.
4. **Mueve la frontera del fail-open.** Hoy la voz envuelve el predicado en un
   `try/except` local con warning (Sol fase-B M5) para que un fallo del clasificador no
   tumbe el turno. `plan_turn` tiene su propio fail-open interno, pero NO es el mismo
   alcance. Hay que decidir cuál manda y probarlo, no asumirlo.
5. **Sin smoke real contra Telegram** hasta que Alberto mande un audio. Los tests
   prueban el enrutado, no el canal.

## 5. Por qué es BP, estructural y escalable

**BP**: la misma pregunta obtiene la misma respuesta por los dos canales — que es lo
que el usuario ya da por supuesto. **Estructural**: ataca la causa (dos despachadores,
uno mutilado) y no el síntoma (una ruta que falta); el punto de decisión pasa a ser
único de verdad, no único-para-texto. **Escalable**: la ruta que nazca mañana funciona
por voz sin tocar nada, y `plan_turn` sigue pura y testeable sin Telegram delante.

---

## 6. Apéndice — el segundo hallazgo de Alberto (separado, no entra en este lote)

«Diferenciar entre central analógica y convencional» en el listado. **No es campaña de
datos**: el atributo ya está poblado.

```
Detnov: 39 productos, 14 centrales clasificadas
  CAD-150-1 … CAD-250-P   tecnologia=['analogica']  lazos anclados   (13 de 14)
  CCD-103                 tecnologia=None           sin lazos/zonas  (1 de 14)
```

El camino FILTRADO (`_inventario_filtrado._casa`) ya compone la descripción con
tecnología y capacidad; el listado SIN filtro imprime «— central» y tira lo que tiene.
Es un cambio de render.

Gap declarado aparte: **CCD-103 no tiene tecnología anclada**. La nomenclatura (CCD vs
CAD) sugiere que es la convencional de la gama, pero eso es una HIPÓTESIS: hay que
verificarla contra el manual antes de anclar nada. No se ancla por parecido de nombre.
