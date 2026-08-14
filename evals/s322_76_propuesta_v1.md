# s322 #76 — Categoría + atributos del catálogo (mostrador) — v2 (dúo r27 aplicado)

> **v1→v2 (r27: Sol 3 · Fable 4, 2 críticos, 0 FP — TODO aplicado):**
> 1. **Atributos MULTI-VALOR por-fuente** (Sol C1 — AFP1010: 2 lazos en docs
>    España, 4 en US; el escalar único lo falseaba como «ampliación»):
>    `lazos: [{base, max?, doc, cita}]` y cita POR CAMPO también en categoria/
>    tecnologia; DIVERGENCIA entre fuentes → packet, jamás fusión automática.
> 2. **El JOIN de identidades es EL aparato, declarado** (Fable C1): la vista
>    de inventario-con-filtro se construye desde el CATÁLOGO (products
>    consumibles de la marca ∩ doc_map→docs activos = «lo que tenemos»), NO
>    desde los pm de chunks (strings de FAMILIA por diseño T3). Los pm siguen
>    para conteo de docs; «sin clasificar» = productos consumibles sin
>    categoria; los pm sin producto en catálogo (el gap E1) se cuentan
>    honestos como «referencias sin catalogar».
> 3. **El caso dorado debe DISPARAR** (Fable M2): el léxico de intención de
>    inventario (`_ENUM_FABRICANTE`) se extiende con las categorías
>    (centrales/detectores/sirenas… es/en) — cirugía declarada en el PLAN
>    (turn_plan puro, testeable a $0), manteniendo el pre-gate barato.
> 4. **Filtros TIPADOS en TurnPlan + caché compuesta** (Sol M2 + Fable m4):
>    `inventario_filtros` viaja en el plan; `_inventario_cache` se clavea por
>    (marca, filtros); el gate byte-igual sin-filtro cubre caché Y truncado.
> 5. **NADA se escribe sin tu sí** (Fable M3 — el precedente candidate-birth
>    manda y el mandato es cita de memoria): la población entera va a PACKET;
>    los alta+cita-verificada en «§0 aplicable en bloque» (patrón E3 §0, que
>    ya funcionó). La excepción queda ADJUDICADA por packet, no presupuesta.
> 6. **Métrica poblacional con umbral** (Sol M3): mini-GT de 30 productos
>    (5 marcas, ES/EN) etiquetado A MANO leyendo docs ANTES de la pasada;
>    gate: precisión ≥95% de la alta-confianza contra el GT, o la pasada no
>    sale del recibo (cobertura = informativa, jamás gate).

**El caso que la manda** (Alberto, 13-ago): «¿Qué centrales de cuatro lazos
analógicas de Detnov tienes?» → el bot soltó TODOS los productos Detnov. La ruta
de inventario lista por fabricante sin poder filtrar por categoría ni atributo —
con 30+ fabricantes es la primera pregunta de un DG. Mandato explícito: capa
categoría + atributos (analógica, nº lazos), con la pasada del mejor modelo para
poblar y recomendaciones fundamentadas para el resto.

## Diseño v1 (3 piezas, cada una con su gate)

### 1. ESQUEMA en el catálogo gobernado (extiende products.jsonl)

Campos OPCIONALES, validados por la puerta, adjudicables:
- `categoria`: enum CERRADO v1 (semilla a adjudicar en el packet):
  `central | detector | pulsador | sirena | modulo | fuente | repetidor |
  aspiracion | barrera | retenedor | pasarela | software | accesorio`.
- `atributos`: dict de CLAVES CERRADAS v1 (desconocida = error de validación):
  `tecnologia ∈ {analogica, convencional, algoritmica, aspiracion, via_radio}` ·
  `lazos: {base: int≥1, max: int≥base}` · `protocolo: str`.
- `atributos_provenance`: obligatoria si hay categoria/atributos — cita
  manual+página o «llm-fable5+cita (mandato 13-ago)» o adjudicación.

Conexión E4 declarada: `clarify.eje_terminos` (léxico) ES la versión-consulta
del atributo `lazos` — #76 pone el dato tipado; una fase posterior puede derivar
el clarify del atributo (no en v1: cirugía mínima).

### 2. POBLACIÓN asistida (patrón E1b/E3, mandato del mejor modelo)

Por producto consumible con docs en doc_map: fable-5 lee muestra del contenido
REAL de SUS manuales (vía doc_map, no búsqueda libre) → `{categoria, tecnologia,
lazos, cita VERBATIM, confianza}`. Reglas heredadas de r25/r26:
- cita verificada contra la muestra o la confianza se degrada sola;
- **alta+cita-verificada → SE ESCRIBE** con provenance LLM (la adjudicación
  operativa del mandato 13-ago: «los que estés muy seguro no hace falta»);
- media/baja/sin-cita → packet de recomendaciones por lotes;
- productos sin docs → packet «sin evidencia» (jamás inventar).
Orden: Detnov y Kidde PRIMERO (los casos reportados), luego el resto por marca.

### 3. CONSUMO: la ruta de inventario filtra (extensión fase A, NO canal nuevo)

`_intencion_inventario` gana filtros: léxico CERRADO de categoría (plurales
es/en) + tecnología + «N lazos» (regex numérico). Respuesta:
- con filtro y datos: solo los que casan, con su atributo citado;
- productos de la marca AÚN sin clasificar: línea honesta «y N productos sin
  clasificar aún» (JAMÁS se omiten en silencio — el catálogo se está poblando);
- sin datos para el filtro pedido: se dice («aún no tengo lazos clasificados
  para X») y se cae al RAG — nunca una lista falsa.

## Gates pre-registrados

1. `catalog_store validate` (esquema cerrado; clave desconocida = error).
2. **El caso Detnov como test dorado** (+ Kidde): la query exacta de Alberto →
   solo centrales analógicas 4-lazos (con los datos poblados de verdad).
3. No-regresión de la ruta de inventario existente (tests fase A s316e: las
   queries SIN filtro responden byte-igual).
4. Población: recibo con distribución de confianzas + % citas verificadas +
   muestreo manual de 10 en el packet; suite completa.

## Gaps declarados

- El enum de categoría es semilla MÍA hasta el packet (el dúo y Alberto lo
  ajustan); un producto multi-categoría real (central+repetidor) iría a packet.
- `lazos` en centrales modulares puede ser rango ampliable con tarjetas — por
  eso {base, max} y la cita manda; si el manual no lo fija, no se escribe.
- La detección de filtros es léxico cerrado v1 (sin LLM en el turno): barato y
  determinista; si el léxico no matchea, conducta de hoy (lista completa).
