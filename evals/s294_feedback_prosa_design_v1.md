# s294 · #60 punto 5b — el 👎 invita a la PROSA (diseño de Alberto) + anclaje del texto libre

**Objetivo + MÉTRICA.** Que un 👎 produzca un **caso diagnosticable** en vez de una etiqueta
vacía. Métrica de aceptación: por cada 👎, (a) el voto queda registrado como hoy, (b) el
técnico recibe UNA invitación a explicar, (c) si escribe, su texto queda **anclado a la
consulta** y por tanto unible al voto, a la evidencia servida (`rag_trace`) y a las anclas de
mensaje. NO es métrica de eval: es de instrumentación pre-técnicos (#60, trigger «antes del
primer técnico real»).

**Impacto: MEDIO en zona de dolor** (conducta conversacional + **esquema**) ⇒ dúo completo.

## Evidencia que lo motiva (prueba real de Alberto, 2-ago)

Secuencia medida en la DB de producción (`bot_version=aae2f27`, deploy ya vivo):

| hora | hecho |
|---|---|
| 16:05:17 | consulta CAD-171 · ancla estampada (1 parte) |
| 16:09:25 | 👎 → salió «¿Qué falló?» → pulsó **«Otra cosa»** (`reason_class='other'`) |
| 16:10:32 | escribió el motivo REAL: «AJUSTES > GENERAL me llevaría dentro de General, pero AVANZADO está al mismo nivel» → fila en `feedback`, **sin `query_log_id`** |

Dos defectos, ambos verificados en la DB, no inferidos:
1. **El peaje**: se le pide clasificar ANTES de dejarle hablar, y ninguna de las 4 clases
   describe «ruta de menú mal anidada» ⇒ `other`, que no informa.
2. **La huérfana**: `public.feedback` **no tiene `query_log_id`** (columnas verificadas: id,
   telegram_user_id, feedback_text, previous_query, previous_response, created_at). Guarda
   COPIAS del texto de la pregunta y la respuesta, sin FK ⇒ no se puede unir al voto ni a la
   evidencia, y **no cae en la cascada** de retención de `query_logs`.

## Cambio propuesto

**(a) Un solo mensaje tras un 👎 REGISTRADO** — texto adjudicado por Alberto, que es el que el
bot YA usa en el canal de texto libre (`telegram_bot.py:574`), de modo que el acuse es el mismo
venga por donde venga:

> Gracias por el aviso 🙏
>
> Tu feedback queda registrado. ¿Puedes indicarme qué dato concreto es incorrecto y qué dice el
> manual? Así podré mejorar.

…con los **4 botones colgando como teclado** (se mantienen: atajo opcional, ya no puerta).
Sustituye al actual «¿Qué falló? (opcional)».

**(b) Acuse secundario acortado.** Si el técnico escribe y el detector de texto libre dispara
justo después de un 👎 reciente del mismo usuario, el segundo acuse NO repite el mismo párrafo
(hoy repetiría el idéntico): se acorta («Anotado 👍») o se omite. Un bot que da las gracias dos
veces por lo mismo parece roto.

**(c) Anclaje del texto libre**: `feedback.query_log_id UUID REFERENCES query_logs(id) ON
DELETE CASCADE`, NULLABLE (el histórico no lo tiene y el feedback sin consulta previa sigue
siendo válido). Binding, en este orden:
   1. **exacto** — si el mensaje es un *reply* de Telegram a un mensaje del bot, se resuelve por
      `answer_messages` (`message_id → query_log_id`), la pieza del punto 1. Sin estado en
      memoria: funciona tras reinicio y días después.
   2. **fallback** — última consulta de ese usuario, que es lo que el código ya usa hoy de
      forma implícita vía `context.user_data["last_query"]`.

**(d) La clase se DERIVA del texto** (no se construye ahora, se declara): la taxonomía sigue
siendo útil para agregar, pero clasificar es trabajo nuestro, no del técnico.

## Invariantes (se testean)

- **I1** El voto NUNCA está en riesgo: cualquier fallo de la invitación o del anclaje se traga;
  `answer_feedback` ya escrito no se toca.
- **I2** Flag `TELEGRAM_FEEDBACK_REASON` sigue gobernando la invitación (default off ⇒ conducta
  byte-idéntica a hoy).
- **I3** El anclaje es **aditivo**: `query_log_id` nullable; el texto libre se sigue guardando
  aunque no se pueda anclar (nunca se pierde feedback por no saber a qué consulta va).
- **I4** RGPD: el anclaje **reduce** exposición (hoy la copia sobrevive al borrado de la
  consulta; con la FK+CASCADE, no). No se almacena texto nuevo: el que hay ya se guarda.
- **I5** Un 👍 nunca invita a explicar.

## Gates pre-registrados

- **G-0**: suite + flag off byte-idéntico.
- **G-1 (conducta)**: con flag on, un 👎 produce EXACTAMENTE un mensaje; el acuse secundario no
  duplica el párrafo; un 👍 no produce ninguno.
- **G-2 (anclaje)**: reply a un mensaje del bot ⇒ `query_log_id` exacto; sin reply ⇒ fallback;
  sin consulta previa ⇒ fila guardada con `query_log_id` NULL (no se pierde).
- **G-3 (cascada)**: borrar la consulta se lleva el feedback anclado y NO el histórico sin
  anclar.
- **G-smoke real**: un 👎 + prosa en Telegram, verificado en la DB (el criterio con el que se
  cazó que el flag estaba puesto sin código desplegado).

## Riesgos declarados

1. **Mal-atribución del fallback**: si tras el 👎 el técnico hace otra PREGUNTA en vez de
   explicar, el detector de texto libre no debería dispararse — pero si lo hiciera, anclaría
   prosa equivocada. Mitigación: el binding exacto por reply es la vía preferente; el fallback
   solo actúa cuando el detector YA clasifica el mensaje como feedback (maquinaria existente).
2. **Doble acuse**: resuelto en (b), pero es conducta y la ve el usuario ⇒ va a G-1.
3. **Histórico**: las filas viejas de `feedback` quedan con `query_log_id` NULL para siempre
   (no hay forma fiable de re-anclarlas). Se declara, no se inventa un backfill.
4. **Cambio de esquema en tabla de datos personales**: `feedback` ya está en la frontera RLS;
   añadir columna no cambia grants, pero la migración debe re-verificar las postcondiciones.
