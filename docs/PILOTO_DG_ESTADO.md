# Qué falta para abrir el bot al primer DG

> **Qué es este doc.** La respuesta a «¿qué falta para compartirlo con el primer DG?», con el
> estado **verificado contra el código y la base el 20-ago-2026**, no contra la memoria. El
> *cómo* operar (mensaje al DG, política de iteración, comandos) sigue en
> [`DG_DEPLOYMENT.md`](DG_DEPLOYMENT.md); esto es el **semáforo**.
>
> **Resumen en una línea**: la máquina está lista y probada; **lo único que bloquea de verdad es
> el paquete del abogado** (sin enviar), y hay que actualizarlo antes de mandarlo porque describe
> un aviso que ya no es el que está en producción.

## Semáforo

| # | Frente | Estado | ¿Bloquea? |
|---|---|---|---|
| 1 | **Paquete del abogado** (P1 y P3) | ⛔ **sin enviar** · ✅ **ya NO desfasado** (20-ago: anexo A al **v9**, generado del código; P7/P8 añadidas; plazo de `panel_usuarios` puesto) | **SÍ — solo falta mandarlo** |
| 2 | Puerta de acceso (allowlist + invitación de un solo uso) | ✅ viva y probada con tráfico real | no |
| 3 | Aviso de privacidad y consentimiento | ✅ mecanismo vivo (v9) · ⚠️ 1 de los 2 usuarios actuales sigue en v8 | no |
| 4 | Tope de gasto por persona | ✅ `BOT_DAILY_LIMIT=30/día`, kill-switch sin deploy | no |
| 5 | Red de errores + aviso al técnico | ✅ viva (3 incidencias en 30 días, ver §3) | no |
| 6 | Supresión RGPD a petición | ✅ procedimiento escrito y completo (9 pasos, incluidas las tablas que NO cascadean) | no |
| 7 | Panel de control | ✅ vivo, con métricas de uso y calidad | no |
| 8 | Calidad de las respuestas | ⚠️ conocida y medida; ver §4 — **no es un bloqueante, es una expectativa a fijar** | no |

---

## 1. Lo único que bloquea: el paquete del abogado

`docs/PAQUETE_ABOGADO_PILOTO_DG.md` está **escrito y listo para reenviar**, con seis preguntas de
las que **P1 (validez del aviso) y P3 (invitaciones y terceros) bloquean el piloto** por decisión
propia del documento. No consta que se haya enviado ni respondido.

**Ya está tocado (20-ago-2026)** — lo que quedaba de edición está hecho:
- el **anexo A lleva el v9**, y ya no transcrito: se **genera del código que se sirve**
  (`python -m scripts.s328d_anexo_aviso`, con `--comprobar` que avisa si vuelve a quedarse atrás).
  Llevaba el v8 mientras producción servía el v9, que es el fallo que esto cierra de raíz;
- el **anexo B** lleva el delta v8→v9, con el cambio de fondo señalado: **la mención a que los
  datos salen de la UE bajó de la primera capa a la segunda**, y eso va como pregunta expresa en P1
  porque es lo único del v9 que podría afectar a la validez del consentimiento;
- **P7 (leer conversaciones desde el Explorador)** y **P8 (clasificación automática con un LLM)**
  añadidas y marcadas como nuevas;
- **P4** cierra el plazo de `panel_usuarios`: **24 meses**, decidido por Alberto el 20-ago.

**Acción concreta que queda**: rellenar los dos `<…>` del apartado 1 (a quién se abre el piloto y
cuándo), borrar la nota de cabecera y **enviarlo**. Es lo único que bloquea el piloto, y es de
Alberto.

## 2. Lo que ya está y no hay que tocar

Verificado en la base el 20-ago:

- **2 personas con acceso**, 1 invitación emitida y canjeada, **0 pendientes**. La puerta
  (`BOT_ALLOWLIST=on`) lleva viva desde el 17-ago con tráfico real.
- **Invitar es un comando**: `python -m scripts.s324e_invitaciones generar --nota "Nombre, DG de
  Acme"` → enlace de un solo uso, caduca en 2 días, y **te llega aviso por Telegram al canjearse**
  con quién lo usó (la contramedida contra el reenvío).
- **Revocar**: `revocar-acceso <id> --motivo "…"` → efecto en ≤10 min (caché de la puerta), o
  inmediato reiniciando en Railway. Desde el panel también.
- **Solo chat privado**: el bot rechaza grupos aunque quien escriba esté autorizado.
- **Supresión a petición**: procedimiento completo en `DG_DEPLOYMENT.md §6`, con las tablas que
  **no** cascadean ya identificadas (`bot_allowlist`, `bot_invitaciones.canjeada_por`,
  `answer_feedback` de votos ajenos, `persona_seudonimo`).

## 3. Riesgos operativos reales (no bloquean, pero conviene saberlos)

1. **Créditos del proveedor.** El 17-ago una consulta por voz murió con «You have no credits
   remaining» (429). El técnico **sí** recibió aviso, pero con un DG delante eso es una mala
   primera impresión. **Antes de invitar: comprobar saldo** de OpenAI (transcripción) y Anthropic
   (generación) y poner alerta de recarga.
2. **Ruido de redeploy en el panel.** Cada despliegue de Railway deja una incidencia
   `transporte_telegram / conflict_instancia` marcada **crítica** (3 en el histórico, una por
   deploy: `a4a3567`, `f314fe8`, `0582f91`). Es el solapamiento normal de la instancia vieja con
   la nueva, no un fallo del bot — pero si el panel lo va a mirar alguien más, esa clase debería
   degradarse a «esperado» o filtrarse. Deuda menor, no bloquea.
3. **Marcas destrozadas por voz** (DEC-233): el ASR devuelve algo que no es la marca y el bot
   puede afirmar un hueco de corpus que no existe. Ya es visible como métrica
   (`bot_marcas_sin_corpus_semanal` enseñó «death knife» y «death knob» = Detnov). El arreglo
   —generar las variantes de las 30 marcas— está pendiente con dueño.

## 4. Qué esperar del bot (la expectativa que hay que fijar con el DG)

No es un bloqueante técnico, es de encuadre. Lo que sabemos, medido:

- **Cobertura**: 30 fabricantes, ~1.700 productos de catálogo. Si el DG pregunta por una marca que
  no tenemos, el bot lo dice — y ahora ese hueco queda **registrado** como demanda no cubierta,
  que es exactamente la señal que interesa a Fontiber.
- **Dónde falla**: el cuello medido es la **síntesis** (transmitir todos los hechos de la fuente),
  no la búsqueda. El bot cita fuente y admite cuando no sabe, que es el contrato de diseño.
- **El framing que ya está escrito** (`DG_DEPLOYMENT.md §1`) convierte cada fallo en señal: «tú
  nos ayudas a calibrarlo con preguntas reales». Con el panel de anoche, esa promesa ahora es
  verificable: cada 👎 con motivo entra en las métricas de calidad por tipo de pregunta.

## 5. La secuencia recomendada

1. **Actualizar el paquete del abogado** (anexo A → v9 + las dos preguntas nuevas) y enviarlo.
2. Mientras responde: **comprobar créditos** de los dos proveedores y poner alerta.
3. Con P1 y P3 contestadas: **emitir la invitación** del primer DG (un comando) y avisarle por el
   canal habitual con el template del §1 de `DG_DEPLOYMENT.md`.
4. Primera semana: mirar el panel (uso, tipología, 👎 con motivo) y el Explorador para leer las
   preguntas reales. Ahí es donde el piloto paga.

> **Lo que NO hay que esperar a tener**: nada de lo pendiente del panel (plazo de retención de
> `panel_usuarios`, medición XFF) bloquea al DG — son gates para exponer **el panel** a más gente,
> no para que un técnico use **el bot**.
