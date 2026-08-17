# Consulta a asesoría jurídica — asistente técnico interno (protección de datos)

> **Cómo usar este documento (nota para Alberto, borrar antes de enviar):** está escrito para
> **reenviarse tal cual** al abogado. Lo preparó el asistente de ingeniería del proyecto: describe
> con exactitud qué hace el sistema y qué datos toca, y plantea **seis preguntas concretas**. No
> contiene ni pretende contener criterio jurídico. Lo único que hay que rellenar antes de mandarlo
> son los dos datos entre `<…>` del apartado 1 (a quién se abre el piloto y cuándo).
>
> Las seis preguntas están ordenadas por bloqueo: **P1 y P3 bloquean el piloto**; P2, P4, P5 y P6
> se pueden resolver en paralelo mientras el piloto arranca, pero conviene cerrarlas en semanas.

---

## 1. Qué queremos hacer y qué necesitamos de vosotros

Fontiber Industrial Partners, S.L. tiene en marcha un **asistente técnico interno** en Telegram:
un técnico le pregunta por escrito o por audio («¿cuántos lazos admite la central X?») y el
sistema responde citando el manual del fabricante. Hoy lo usa **una sola persona** (el
responsable del proyecto) y ha atendido **96 consultas**.

Queremos abrirlo a un **piloto con <número> directores generales de empresas del grupo**, a partir
de <fecha aproximada>. Antes de abrirlo:

1. hemos redactado un **aviso de privacidad nuevo** (v8, anexo A) que sustituye al vigente;
2. hemos añadido tres mecanismos que tratan datos: un **control de acceso por invitación**, un
   **registro de incidencias técnicas** y un **panel web de administración**.

**Lo que necesitamos**: que reviséis el aviso del anexo A y contestéis las seis preguntas del
apartado 2. No buscamos un informe extenso; buscamos un «sí / no / cambiad esto» sobre puntos
concretos, y que nos digáis si veis algo que no hayamos preguntado.

---

## 2. Las seis preguntas

### P1 — ¿Es válido el aviso de privacidad del anexo A? *(bloquea el piloto)*

Es el texto que la persona ve **antes** de poder usar el sistema, y que acepta escribiendo
`/accept`. Sustituye al vigente (v7) en cuatro puntos: se anuncia como versión en desarrollo, se
corrige el número de fabricantes cubiertos, se aclara que el responsable es Fontiber aunque el
usuario trabaje en otra empresa del grupo, y se explicita el reconocimiento interno de quien
aporta correcciones útiles.

Concretamente: **¿cubre la información exigida y es válido como recogida de consentimiento?**
Al desplegarlo, **todos los usuarios actuales deben volver a aceptar** (el sistema invalida las
aceptaciones de la versión anterior). Hoy eso afecta a una persona; si se despliega con el piloto
en marcha, afecta a todos los participantes. Por eso queremos cerrarlo **antes** de abrir.

### P2 — Registro de incidencias técnicas: ¿finalidad nueva?

Cuando el sistema falla (se cae una conexión, un proveedor devuelve error), se guarda desde ahora
una **ficha técnica del fallo**: qué clase de error, en qué módulo, a qué hora y con qué gravedad.
Esa ficha **no contiene ni el identificador de la persona ni el texto de su pregunta**, pero sí
una **referencia a la consulta** que lo provocó — de modo que, cruzando ambas, se puede llegar a
la persona. Es lo mismo que ya se guardaba (el fallo se registraba en una línea de texto), pero
ahora en columnas separadas para poder agruparlo y corregir el sistema.

**¿Consideráis que esto es la misma finalidad ya declarada («identificar errores y mejorar el
sistema») o una finalidad nueva que exija informar por separado?** Nuestra lectura de ingeniería
es que es la misma, pero no es una valoración que nos corresponda.

### P3 — Invitaciones: dos puntos sobre terceros *(bloquea el piloto)*

El acceso será **por invitación de un solo uso**: el administrador genera un enlace, se lo manda
a una persona concreta, y ese enlace caduca en 2 días y sólo sirve una vez. Hay dos cosas que
queremos que valoréis:

**(a) Se anota el nombre y el cargo del invitado *antes* de que acepte nada.** Al generar el
enlace se guarda una nota del tipo «Juan Pérez, DG de Acme» para saber a quién se le dio. Es un
dato de una persona que en ese momento **todavía no ha aceptado los términos** y que puede no
llegar a usar el sistema nunca. ¿Sobre qué base lo tratamos, y hay que informarle de algo?

**(b) Al canjearse el enlace, el administrador recibe un aviso con la identidad de quien lo
canjeó** — nombre de perfil, alias de Telegram e identificador. Existe por una razón declarada:
si alguien reenvía su invitación a un tercero, el administrador lo ve en minutos y puede revocar.
Es decir, es una **medida de control frente al reenvío**, y comunica a una persona (el
administrador) la identidad de otra (quien canjeó). ¿Es proporcionado? ¿Debe anunciarse en el
aviso —«al usar este enlace, el administrador sabrá que has sido tú»— o basta con que esté en la
información general?

### P4 — Plazo de conservación de los datos de acceso

Hemos decidido conservar los datos del control de acceso **24 meses**, el mismo plazo que ya
aplicamos al resto (la decisión fue de consistencia: un plazo único es más simple de cumplir y de
explicar que tres). El detalle:

| Dato | Plazo | Qué se hace al vencer |
|---|---|---|
| Invitación nunca usada | 24 meses desde su emisión | Se borra la nota con el nombre del invitado |
| Invitación usada, con el acceso ya retirado | 24 meses desde la retirada | Se borran nota e identificador; queda «hubo un alta» sin la persona |
| Permiso de acceso ya retirado | 24 meses desde la retirada | **Se borra la fila entera** |
| Permiso de acceso vigente | — | Se conserva mientras dure el acceso |

La tercera fila es una **excepción** que declaramos expresamente: en esa tabla el identificador de
la persona *es* la clave del registro, así que no se puede anonimizar sin destruir la fila; por eso
ahí se borra en lugar de disociar. **¿Os parece correcto el plazo y esa excepción?**

### P5 — Panel web de administración

Estamos construyendo un **panel web** (usuario y contraseña, sin registro público) desde el que el
administrador podrá: gestionar invitaciones y accesos, ver métricas de uso y consultar errores
agregados. Implica que **datos personales del sistema serán accesibles desde un navegador**, y no
sólo desde herramientas internas de línea de comandos.

**¿Qué nos exigís aquí?** Nos interesa concretamente si veis necesario: registrar quién accede al
panel y cuándo, limitar qué datos personales se muestran (por ejemplo, ocultar el texto de las
consultas), o alguna medida adicional que demos por supuesta y no lo esté.

### P6 — Base jurídica del control de acceso

Hay un punto que nos genera dudas por su orden lógico: **la comprobación de si alguien tiene
permiso ocurre antes de que esa persona haya aceptado nada** — es lo primero que hace el sistema
al recibir un mensaje. Por tanto, el tratamiento del identificador de Telegram para decidir «esta
persona pasa o no pasa» **no puede apoyarse en el consentimiento de esa misma persona**, porque
todavía no lo ha dado (y si no está autorizada, no lo dará nunca).

**¿Cuál es la base correcta para ese tratamiento concreto?** ¿Interés legítimo en controlar el
acceso a un sistema corporativo? ¿Y cambia algo el hecho de que los usuarios sean empleados del
grupo? Relacionado: si alguien **retira su consentimiento**, damos por hecho que hay que retirarle
también el acceso — pero queremos confirmarlo, porque son dos registros distintos.

---

## 3. Qué datos trata el sistema, con precisión

**De la persona que usa el asistente** (lo que ya se venía tratando):

| Dato | Detalle |
|---|---|
| Identificador de Telegram | Número que asigna Telegram; permanente por persona |
| Nombre | El que la propia persona escribe al aceptar. Opcional |
| Preguntas y respuestas | El texto íntegro. Los saludos y despedidas no se registran |
| Audios | **No se guardan.** Se transcriben y se descarta el audio; se conserva sólo la transcripción |
| Valoraciones 👍/👎 | Y el comentario que escriba al marcar una respuesta como incorrecta |
| Fecha y hora | De cada consulta |

**Nuevo, del control de acceso**: nombre/cargo del invitado (escrito por el administrador),
identificador de quien canjea, fechas de emisión, canje, caducidad y revocación, y quién realizó
cada acción. Del enlace de invitación **no se guarda el enlace**, sólo una huella criptográfica
que no permite reconstruirlo.

**Nuevo, del registro de incidencias**: clase de error, módulo, gravedad, fecha y referencia a la
consulta afectada. Sin identificador de persona ni texto de la pregunta.

**Quién más interviene** (todos por función; los datos que reciben son la pregunta, no el
histórico):

| Función | Proveedor | Ubicación |
|---|---|---|
| Canal de mensajería | Telegram | Fuera de la UE |
| Generación de la respuesta | Anthropic (Claude) | Fuera de la UE |
| Búsqueda en los manuales | Voyage AI | Fuera de la UE |
| Transcripción de audio | OpenAI (Whisper) | Fuera de la UE |
| Almacenamiento | Supabase | **UE — Estocolmo** |
| Ejecución del sistema | Railway | Fuera de la UE |

**Conservación**: 24 meses vinculado a la persona; después se retira su identificador de consultas
y valoraciones y el contenido se conserva disociado. Existe un procedimiento automático mensual
que lo ejecuta, y un procedimiento de supresión a petición.

---

## 4. Decisiones ya tomadas (no las preguntamos, pero conviene que las veáis)

- **Base jurídica del uso del asistente: consentimiento**, el que se da al aceptar los términos, y
  es revocable escribiendo a `info@fontiber.com`.
- **El responsable es Fontiber**, también para usuarios que trabajen en otras empresas del grupo, y
  el aviso lo dice expresamente.
- **Reconocimiento interno de aportaciones**: si el feedback de alguien sirve para corregir el
  sistema, se marca al revisarlo y puede tenerse en cuenta para reconocer su aportación. La marca
  **la pone una persona**, no un cálculo automático, y así está declarado en el aviso.
- **El sistema se anuncia como versión en desarrollo** y advierte de que no sustituye al manual
  oficial ni al criterio de un técnico cualificado.

---

## Anexo A — Texto del aviso propuesto (v8)

### A.1 · Lo que se ve al iniciar, antes de poder usar nada

```
🤖 Asistente técnico — versión beta, en desarrollo

Te doy información extraída de los manuales técnicos de una treintena de fabricantes
(Notifier, Morley, Detnov, Kidde, Aritech, System Sensor y más). Puedes preguntarme por
texto o por audio 🎤.

⚠️ Esto está EN DESARROLLO: puede equivocarse o quedarse corto. Mis respuestas no
sustituyen al manual oficial ni al criterio de un técnico cualificado — contrástalas
antes de usarlas en una instalación. Si algo no cuadra, dímelo con 👎: es la forma más
rápida de mejorarlo.

⚠️ Antes de empezar

Para mejorar el sistema, guardamos las preguntas que respondo y mis respuestas, junto
con tu ID de Telegram, el nombre que nos des al aceptar y tus valoraciones 👍/👎. Si
mandas un audio, guardamos solo su transcripción: el audio original NO se guarda.

Quién responde de tus datos: Fontiber Industrial Partners, S.L. — también si trabajas
en otra empresa del grupo: el responsable es Fontiber, no tu empresa.
Cuánto: 24 meses vinculado a ti; después se retira tu identificador de tus consultas y
valoraciones.
Quién lo ve: el equipo técnico de Fontiber. Para funcionar, tus preguntas pasan por
proveedores de IA y de alojamiento que operan fuera de la UE.
Tus derechos: escribe a info@fontiber.com para acceder o borrar tus datos.

📄 Detalle completo (qué proveedores, para qué, y qué pasa a los 24 meses): /privacidad

Para aceptar y empezar, envía:
/accept [tu nombre]   (el nombre es opcional pero ayuda a la revisión)
```

### A.2 · Detalle completo, disponible en todo momento sin aceptar nada

Se conserva íntegro el texto vigente —que incluye responsable con CIF y dirección, qué se guarda,
para qué, quién accede, la lista de proveedores del apartado 3, plazos, transferencias fuera de la
UE, derechos, retirada del consentimiento y reclamación ante la AEPD— con estos tres ajustes:

```
Responsable: Fontiber Industrial Partners, S.L. · CIF B24984759 · Calle de la Palma 10,
28004 Madrid · info@fontiber.com — Fontiber es el responsable del tratamiento aunque
trabajes en otra empresa del grupo.

Base jurídica: tu consentimiento, el que das al enviar /accept. Puedes retirarlo cuando
quieras escribiendo a info@fontiber.com; retirarlo no afecta a los tratamientos ya hechos.

Reconocimiento: si tu feedback ayuda a mejorar el sistema, Fontiber puede reconocerlo
internamente. Aplica a todas las personas que usen el asistente.
```

El texto completo vigente se envía como documento aparte si lo necesitáis para el cotejo.

---

## Anexo B — Qué cambia respecto de lo que hoy está vigente

| # | Cambio | Por qué |
|---|---|---|
| 1 | Se anuncia como **versión en desarrollo** y se advierte de que no sustituye al manual ni al criterio del técnico | El sistema puede equivocarse y se usa en instalaciones reales |
| 2 | «Tres fabricantes» → «**una treintena de fabricantes**» | El texto vigente se quedó corto: hoy son 30 exactos. Se evita una cifra que caduque |
| 3 | Se explicita que **el responsable es Fontiber**, no la empresa del usuario | El piloto abre a personas de otras empresas del grupo |
| 4 | Se explicita que el **reconocimiento interno aplica a todos** | Antes quedaba ambiguo |

---

### Nota final sobre el origen de este documento

Lo ha redactado el asistente de ingeniería que desarrolla el sistema, con acceso al código y a la
base de datos, y describe **lo que el sistema hace hoy**, verificado contra el código —no lo que
está previsto que haga. Las decisiones de negocio del apartado 4 son del responsable del proyecto.
Ninguna parte de este documento constituye criterio jurídico; es exactamente lo que os pedimos.
