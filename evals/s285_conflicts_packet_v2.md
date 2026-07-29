# s285 — Packet de adjudicación: los 80 conflictos QA (s83 propone X, la DB tiene Y)

> **Formato excepción-only:** cada fila lleva recomendación + evidencia leída del corpus real
> (14 agentes + escépticos; los escépticos cazaron un bug de mi frame — corregido y
> reconciliado contra la fuente canónica `s83_document_identity_final.jsonl`). **Solo
> contesta donde DISCREPES**: con «OK» (o «OK salvo #n») genero el SQL de aplicación
> (contrato T2: conteos exactos + before-image + rollback) y lo pegas tú.
>
> Origen: el fill-only del T2 SALTÓ estas filas porque la DB ya tenía OTRO valor. Aquí se
> decide cuál es verdad. (El «121» de DEC-156 era pre-v3; el frame congelado real son 80.)

## Resumen

| recomendación | n | qué implica |
|---|---|---|
| **corregir la DB al valor s83** | 72 | la DB tiene un valor erróneo (mayoría: FAQs en español etiquetadas de/en; familia UCIP con db=`programacion`, etiqueta fuera de taxonomía) |
| **la DB ya está bien** | 6 | el s83 se equivoca — no se toca nada |
| **decisión tuya (refutada)** | 1 | escéptico vs agente — abajo con ambos argumentos |
| **fila muerta** | 1 | documento borrado en T3 |

## ⚠️ La única decisión de fondo tuya — VESDA-E VEP `Product_Guide`

**`33976_13_VESDA-E_VEP-A00-P_Product_Guide_A4_Spanish_lores`** — doc_type: DB=`hoja_datos` · s83=`instalacion`
- Agente (por contenido de instalación): `instalacion`. Escéptico (por precedente de corpus y peso de capítulos): `guia_usuario`. escéptico: correcto='guia_usuario' (precedente corpus: los 2 Product_Guide VESDA poblados son guia_usuario; cap. Configuración 30pp > Instalación 28pp)
- **TU MARCA:** `[ ] instalacion` · `[ ] guia_usuario` · `[ ] otro: ____`

## Corregir la DB al valor s83 (72)

**#1 · `997-671-005-3_Configuration_ES`** (Notifier) — doc_type `programacion`→`configuracion`
- (alta) p1 literal: 'Central de alarma contra incendios Pearl™ Manual de configuración de la central' (997-671-005-3); índice con '1.4 Operaciones de configuración' y '3 Menús de configuración de la central'; p27 '5.2 Edición de texto ... Esta función se encuentra en el «Menú de Configuración de Central»'. El término del propio documento es 'configuración' (s83); 'programacion' (db) no aparece en el texto.

**#2 · `Averia-de-resistencia-de-baterias-en-central-DXc`** (Morley) — language `en`→`es`
- (alta) El documento tiene 1 solo chunk (p1) y es íntegramente español: 'Tengo avería de resistencia de baterías en central DXc', pasos '1- Entrar en opción 5 «Menu»' / '4- Entrar en opción 7 «Voltajes»' y umbral 'entre 200 - 500 mohmios'. Ni una frase en inglés, así que db='en' es falso y s83='es' correcto. (doc_type db=NULL, no en conflicto; s83 'mantenimiento' encaja con el diagnóstico y sustitución de baterías.)

**#3 · `CAD-250_Manual-Configuracion-MC-380-es-2026-c`** (Detnov) — doc_type `programacion`→`configuracion`
- (alta) p1 literal 'GUIA DE CONFIGURACION CENTRALES VESTA' (Detnov, 136 chunks / 89 páginas); p31 '5.5. CONECTIVIDAD ... AJUSTES (Menú principal) > CONECTIVIDAD' con DHCP/IP local/Gateway/Máscara, y p59 'Configuración de dispositivos ... 8.2.2. Definición de una condición temporal'. El título propio dice 'configuración'; 'programacion' (db) no aparece. Idioma español confirmado (db='es' ya correcto, sin conflicto).

**#4 · `CAD-250_Manual-software-configuracion-MS-416-es-2026-b`** (Detnov) — doc_type `programacion`→`configuracion`
- (alta) p1 literal 'SOFTWARE DE CONFIGURACION' (Detnov Vesta, 88 chunks / 71 páginas), tabla de revisiones 'Primera edición. Versión de software (1.1.1 (jun 2020))', y p31/p51 son pantallas del software (filtros de red ALARMA/FALLO/TÉCNICOS por panel y nodo, pantalla MANIOBRAS). Es el manual del software de configuración → 'configuracion' (s83); 'programacion' (db) no consta en el texto.

**#5 · `Como-configurar-correos-en-un-TG-HONEYWELL`** (Morley) — doc_type `programacion`→`configuracion` · language `en`→`es`
- (alta) Los 2 chunks son 100% español: '¿Como se configura en un TG-HONEYWELL el correo electrónico?' y 'acceda al menú de «Configuración» desde el margen superior de la pantalla del software gráfico TG ... Seleccione el sub-menú «Centrales»'; el único inglés son nombres de campo sueltos (Host, Puerto SMTP, SSL) → db='en' es falso, s83='es' correcto. En doc_type, el contenido es configuración de mensajería del software gráfico TG, término literal del documento → s83 'configuracion' sobre db 'programacion'.

**#6 · `Como-solucionar-la-incidencia-TABLE-IS-FULL-en-el-TG`** (Morley) — language `en`→`es`
- (alta) Chunk único en español: '¿Como solucionar la incidencia «TABLE IS FULL» en el software gráfico TG?' y 'Abra el Panel de Control en el Ordenador donde esta instalado el TG ... pulse en PARADOX y en la linea BLOCK SIZE duplique el valor'. Lo único en inglés son literales de UI/error de Windows-BDE ('TABLE IS FULL', 'BLOCK SIZE', 'BDE Administrator'), no prosa → db='en' es falso, s83='es' correcto. (doc_type db=NULL, sin conflicto; s83 'mantenimiento' encaja: es resolución de incidencia.)

**#7 · `Compatibilidad-detectores-de-monoxido-NCO10-NCO100-VSN-CO`** (Morley) — language `de`→`es`
- (alta) Chunk único íntegramente español: 'Los detectores de monóxido NCO10 / NCO100 / VSN-CO **no son compatibles** entre si' y 'Si necesita sustituir detectores NCO10 (descatalogados) puede hacerlo por el KDM-300 (DET+BASE+ZÓCALO) únicamente en centrales G10'. Cero alemán en todo el texto → db='de' es falso, s83='es' correcto. Aviso de proceso: la fila viene marcada write_op='excluded_t3' (el packet T3 es dueño de este source_file).

**#8 · `Compatibilidad-entre-equipos-Notifier-y-Morley`** (Morley) — language `en`→`es`
- (alta) Chunk único en español: '¿Puedo instalar equipos de Notifier en una central de Morley o equipos de Morley en una central de Notifier?' / 'No, no es posible ... pués los protocolos de comunicación son distintos ... la central indicará una avería, AVERÍA DE TRANSMISIÓN'. Lo único no-español es la dirección soporteHLSI@Honeywell.com → db='en' es falso, s83='es' correcto. Aviso: fila con write_op='excluded_t3'.

**#9 · `Configuracion-entrada-digital-de-la-central-NFS-Supra-VSN-Plus2-ESS-2Plus`** (Morley) — doc_type `programacion`→`configuracion` · language `en`→`es`
- (alta) Chunk único 100% español: 'La central NFS Supra / VSN-Plus2 / ESS-2Plus admite diversas formas de funcionamiento, que son configurables desde Nivel de acceso 3 (Programador)', con maniobras 'Rearme / Evacuación / Silencio Sirenas y Zumbador' → db='en' es falso, s83='es' correcto sin ambigüedad. En doc_type el título propio es 'Configuración entrada digital de la central...' (apoya s83 'configuracion'), si bien el cuerpo cita 'acceda al menú de programación', así que db 'programacion' no es absurdo: el eje idioma es el que decide la fila. Aviso: write_op='excluded_t3'.

**#10 · `DXC-Como-conectar-una-sirena-de-lazo`** (Morley) — language `de`→`es`
- (alta) Chunk único en español: 'Este artículo es válido para la conexión de una sirena de lazo que tiene la base B501AP' con bornes 'Entrada Negativo = 1 / Salida Negativo = 1 / Positivo entrada = 2 / Salida Positivo = 4'. Cero alemán → db='de' es falso, s83='es' correcto. Nota fuera del eje en conflicto: doc_type coincide en ambos lados ('otro'), pero por contenido (conexionado de bornes) encajaría mejor 'instalacion'.

**#11 · `DXC-Connexion-Como-programar-una-salida-de-averia-general`** (Morley) — language `de`→`es`
- (alta) Español: «¿Cómo programar una salida de avería general en la central DXC Connexion?» y «Utilizar un módulo de salida MI-CMO, configurado como libre de tensión». documents.language='de' es falso; chunks_v2.language='es'. doc_type en DB es NULL (no hay conflicto real); el 'configuracion' de s83 encaja con el contenido (configurar una zona lógica asociada al evento «Avería General»).

**#12 · `DXC-Connexion-Compatibilidad-de-programas-con-versiones`** (Morley) — language `de`→`es`
- (alta) Español: «¿Que versión de programa MK-DXC Configuration Tools necesito para cada versión de central?» y «No todas las versiones del software de configuración MK-DXC Configuration Tools se pueden usar con cualquier versión de central DXC Connexion». documents.language='de' es falso; chunk lang='es'. doc_type DB NULL; 'boletin' de s83 es razonable (nota de compatibilidad de versiones).

**#13 · `DXC-Connexion-Instalacion-y-configuracion-del-modulo-de-comunicacion-RS232`** (Morley) — doc_type `instalacion`→`configuracion` · language `de`→`es`
- (media) Idioma (alta): español, «¿Como instalar y configurar la comunicación RS-232 para conectar a TG?»; documents.language='de' es falso, chunk lang='es'. doc_type MIXTO (por eso media): el doc sí instala hardware —«Instalar la tarjeta de comunicaciones 795-122... en el conector SK2», «Apague la central antes de instalar», conexionado GND/TX/RX— lo que justifica el 'instalacion' de la DB; pero el grueso del cuerpo son dos procedimientos de configuración (Puerto Serie 2: Protocolo TPP, Velocidad 9600, Control Remoto Habilitar) vía CONNEXION TOOL y vía teclado → domina 'configuracion' (s83). El valor …

**#14 · `DXC-Porque-al-activan-elementos-en-alarma-no-se-enciende-su-led`** (Morley) — language `en`→`es`
- (alta) Español: «Al activar elementos de lazo en alarma (detectores, pulsadores, módulos) no se enciende su led». documents.language='en' es falso; chunks_v2.language='es'. doc_type en DB es NULL, así que no hay conflicto en ese eje; s83 propone 'otro' (FAQ de soporte), aceptable.

**#15 · `DXC-Puedo-anular-la-clave-de-usuario-y-acceder-directamente-al-teclado`** (Morley) — doc_type `usuario`→`otro` · language `de`→`es`
- (media) Idioma (alta): español, «Debido a la norma EN54-2 es necesario introducir una clave u otro sistema de seguridad (llave)... KIT de llave referencia 795-118»; documents.language='de' es falso, chunk lang='es'. doc_type (por eso media): el valor DB 'usuario' es una etiqueta no canónica —solo 3 docs en documents frente a 61 'guia_usuario'— y el contenido es un FAQ de soporte de un párrafo, no una guía de usuario; 'otro' de s83 es preferible aunque ninguno de los dos es ideal.

**#16 · `DXC-puedo-cambiar-la-clave-de-nivel-3`** (Morley) — language `de`→`es`
- (alta) Español: «La clave de acceso a centrales Morley modelo DXc por defecto es 9898 y NO puede ser modificada ni desde la central ni a través del soft de programación PK-DXc». documents.language='de' es falso; chunk lang='es'. doc_type DB NULL (sin conflicto); 'otro' de s83 razonable para un FAQ.

**#17 · `DXc-Configuracion-de-la-tarjeta-232-aislada-para-comunicarse-con-el-TG`** (Morley) — doc_type `programacion`→`configuracion` · language `de`→`es`
- (alta) Español: «Para que la central DXc, comunique con el TG, deberá activar el protocolo de comunicaciones en las opciones generales»; documents.language='de' es falso, chunk lang='es'. doc_type: el texto es íntegramente ajuste de parámetros (Protocolo Serie TPP, Velocidad Bauds 9600, Supervisión NO, Control Remoto SI) por teclado o por DXc Config Tool, sin ningún paso de montaje → 'configuracion' (s83) frente a 'programacion' (DB, fuera de taxonomía).

**#18 · `DXc-Connexion-Como-solucionar-la-averia-de-Ent-Placa-1-o-2`** (Morley) — language `de`→`es`
- (alta) Español: «¿Como poder solucionar las averías de Entrada de Placa 1 o 2 en la DXc / Conexion?» y «es indicada por la central cuando no supervisa la resistencia de final de línea de 6k8». documents.language='de' es falso; chunk lang='es'. doc_type DB NULL; 'mantenimiento' de s83 coherente (diagnóstico de averías con causas y soluciones).

**#19 · `DXc-Opciones-de-disparo-de-programas-Matrices`** (Morley) — language `de`→`es`
- (alta) Español: «Las opciones de disparo de programas y sus funciones en la central DXc son:» seguido de tabla con columnas Condición / Abreviatura / Comentarios. documents.language='de' es falso; chunks_v2.language='es'. doc_type DB NULL; 'configuracion' de s83 encaja (parámetros de disparo de programas/matrices).

**#20 · `DXc-Tipos-Abreviaturas-de-equipos`** (Morley) — language `de`→`es`
- (alta) Español: tabla «Abreviatura / Tipo — Descripción» con «TER = Detector térmico», «OPT = Detector óptico», «ION = Detector de humo iónico», «PUL = Pulsador / Módulo monitor». documents.language='de' es falso; chunk lang='es'. doc_type DB NULL; 'otro' de s83 aceptable (tabla de referencia).

**#21 · `DXc-Tipos-de-accion-para-entradas`** (Morley) — language `en`→`es`
- (alta) Español: «Los tipos de acción para entradas y sus funciones para la central DXc son:» con columnas Acción / Enclavado / Comentarios / Activación de programa, y fila «No usado — Entrada sin efecto sea cual sea su condición de entrada». documents.language='en' es falso; chunk lang='es'. doc_type DB NULL; 'configuracion' de s83 coherente.

**#22 · `DXc_Connexion Averia-de-resistencia-de-baterias`** (Morley) — language `de`→`es`
- (alta) resuelta a mano (chunk 100% es, DB de)

**#23 · `Eventos-Averias-de-Equipos-en-DXc`** (Morley) — language `en`→`es`
- (alta) Español: «Eventos de equipos en la central DXc (NO RESPONDE, EQUIPO NUEVO, DOBLE DIRECCION, TIPO EQUIPO CAMBIADO)» con tabla Evento / Causa / Posible Solución. documents.language='en' es falso; chunks_v2.language='es'. doc_type DB NULL; 'mantenimiento' de s83 coherente.

**#24 · `Fallo-I2C-en-RP1rSupra`** (Morley) — language `en`→`es`
- (alta) Español: «Fallo debido a que se ha habilitado la conexión a un repetidor remoto por error», con pasos «Sitúe la central en el nivel 3 de acceso, cerrando el jumper PROG». documents.language='en' es falso; chunk lang='es'. doc_type no está en conflicto: 'mantenimiento' tanto en DB como en s83, y encaja con el contenido.

**#25 · `Finales-de-linea-de-las-centrales-convencionales`** (Morley) — language `de`→`es`
- (alta) Español: «¿Que final de línea debo poner en centrales convencionales?» y «Condensador de 0,47F (por defecto), o, resistencia de 4k7» para la NFS2-8. documents.language='de' es falso; chunks_v2.language='es'. doc_type DB NULL; 'otro' de s83 aceptable (artículo de referencia que cubre varias centrales).

**#26 · `HOP-138-8ES  issue 6_01-2026_Co`** (Notifier) — doc_type `programacion`→`configuracion`
- (media) Portada: "INSPIRE E10/E15 - Instrucciones de puesta en marcha"; el indice y el cuerpo son configuracion de central ("Configuracion inicial y primer encendido", "Programa de Configuracion de CLSS", p24 "Configure la central", p26 "Enviar configuracion a la central"). NO es un manual de programacion: p26 da por supuesto que "las maniobras estan configuradas en el programa". 'configuracion' (s83) describe el doc; 'programacion' (DB) no. Matiz: la etiqueta mas exacta seria puesta-en-marcha/comisionado, que no existe en ninguno de los dos vocabularios.

**#27 · `ITAC-Como-asignar-la-direccion-en-el-ITAC`** (Morley) — language `en`→`es`
- (alta) Chunk p1 en espanol: "Para asignar la direccion al ITAC utilice los dos microinterruptores decadicos" y "El microinterruptor que tiene letras es el de las decenas". DB dice 'en'; s83 propone ['es']. El doc_type de DB esta vacio y el 'configuracion' de s83 encaja (procedimiento de direccionamiento).

**#28 · `ITAC-no-reconocido-por-la-Central`** (Notifier) — language `pt`→`es`
- (alta) Chunk p1 en espanol: "ITAC no es reconocido por la central y los leds parpadean a la vez", con "puente JP1 quitado" / "SW2 en ON" para PEARL/ID3000/ID50 y DXc. DB dice 'pt' (portugues), erroneo; s83 propone ['es'].

**#29 · `MIW-INT-Asignar-de-direccion-pasarela-detectores-y-Modulos-Via-radio-Morley`** (Morley) — language `de`→`es`
- (alta) Chunk p1 en espanol: "Para asignar las direcciones de los equipos via radio debe utilizar el teclado del modulo MIW-INT (pasarela)", tabla SA=DIRECCION DE SENSORES / MA=DIRECCION DE MODULOS. DB dice 'de' (aleman), erroneo; s83 propone ['es']. Hay lusismos puntuales ("direciones", "via radio") pero el texto es espanol, no portugues.

**#30 · `MIW-INT-Averia-de-TAMPER`** (Morley) — language `de`→`es`
- (alta) Chunk p1 en espanol: "La averia de TAMPER se indica en la pantalla de la pasarela via radio" y "la central DXc indicara D020 NO RESPONDE ... realice el REARME de la central DXc". DB dice 'de', erroneo; s83 propone ['es'].

**#31 · `MIW-INT-Dar-de-alta-un-detector`** (Morley) — language `de`→`es`
- (alta) Chunk p1 en espanol: "Como se da de alta un detector en un transmisor MIW-INT?" con pasos "Colocar la pila boton con el + hacia arriba" / "Mover el switch a ON". DB dice 'de', erroneo; s83 propone ['es'].

**#32 · `MIW-INT-La-central-indica-averia-de-datos-de-sensor`** (Morley) — language `de`→`es`
- (alta) Texto integro (chunks=1, p1) en espanol: "¿Cómo solucionar la avería de datos en sensor tras dar de alta los sensores vía radio?" / "debe cambiar la posición del swicth de direccionamiento a la posición 1". No hay una sola frase en aleman. DB dice 'de' (falso) y s83 no propone valor (null) -> ninguno de los dos sirve; el correcto es 'es'.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#33 · `MIW-INT-Mensaje-de-error-LOEr-via-radio-Morley`** (Morley) — language `de`→`es`
- (alta) Prosa 100% espanola (chunks=1, p1): "Mientras se produce la incidencia/avería 'LOEr' del display del interface vía radio MIW-INT significa que el sistema no esta totalmente programado" y la secuencia "Pulse [↑] el display presentará INFO". Los tokens INFO/LOOP/RF/LOAD/done son etiquetas del display, no el idioma del documento. DB='de' es falso; s83=null no aporta valor. Correcto: 'es'.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#34 · `MIW-al-sustituir-las-baterias-de-un-equipo-se-necesita-programarlo-de-nuevo`** (Morley) — language `de`→`es`
- (alta) Documento completo (chunks=1, p1) en espanol: "¿Cuando se sustituen las baterías de un equipo, es necesario reprogramar el equipo?" / "No, no es necesario reprogramar el equipo, pues todos los datos se guardan en una memoria no volatil." DB='de' es falso; s83=null no propone nada. Correcto: 'es'.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#35 · `Morley-Se-pueden-pasar-programaciones-de-ZX-y-Dimension-a-Connexion-DXC`** (Morley) — language `de`→`es`
- (alta) Texto integro (chunks=1, p1) en espanol, incluido el procedimiento numerado: "La programación de centrales ZX, en cualquiera de sus variantes, No se pueden trasladar a formato DXC Connexion" y "En la ventana 'Programa' seleccione 'Abrir una programación existente' y pulsar OK". DB='de' es falso; s83=null. Correcto: 'es'.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#36 · `NFS-SUPRA-VISION-PLUS-2-Como-solucionar-el-Fallo-de-alimentacion`** (Morley) — language `de`→`es`
- (alta) Documento completo (chunks=1, p1) en espanol: "El sistema supervisa las baterías mediante mediciones periódicas de la resistencia interna" y "NO INSTALE BATERÍAS descargadas"; cita la norma "UNEEN 54-4:A2:2006". DB='de' es falso; s83=null. Correcto: 'es'. (El db_doc_type='mantenimiento' encaja con el contenido —diagnostico del led FALLO DE ALIMENTACION— pero ese eje no estaba en conflicto.)
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#37 · `NFS-SUPRA-VSN12-2PLUS-Funcionamiento-de-la-central-en-modo-prueba`** (Morley) — language `en`→`es`
- (alta) Texto integro (chunks=1, p1) en espanol: "Para poner una zona en pruebas, presione la tecla de zona desde el estado anterior de anulado" / "Las alarmas de zonas en pruebas activan todas las sirenas durante unos segundos y la zona se rearma automáticamente." DB='en' es falso; s83=null. Correcto: 'es'. (db_doc_type='operacion' es coherente con el contenido; eje no en conflicto.)
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#38 · `NFS-SUPRA-VSN2-PLUS-Entrada-Digital`** (Notifier) — language `en`→`es`
- (alta) Documento completo (chunks=1, p1) en espanol: "¿Que tipo de operaciones puedo hacer con la entrada digital?" y la lista REARME / EVACUACIÓN / SILENCIO SIRENAS / ACTIVAR-ANULAR RETARDOS, mas el aviso "¡No use contactos o cables con tensión en la entrada digital o dañará el panel de forma irreparable!". DB='en' es falso; s83=null. Correcto: 'es'. (db_doc_type='configuracion' encaja; eje no en conflicto.)
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#39 · `Niveles-de-control-de-acceso-de-la-central-DXC-CONEXION`** (Morley) — language `de`→`es`
- (alta) Texto integro (chunks=1, p1) en espanol: "No puedo acceder a los menús de la central DX, no conozco o no funcionan las claves" y "Clave de Nivel 2 :1234 / Clave de Nivel 3 :9898". DB='de' es falso; s83=null. Correcto: 'es'.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#40 · `No-funcionan-las-teclas-de-la-central-VSN`** (Morley) — language `de`→`es`
- (alta) Documento completo (chunks=1, p1) en espanol: "Comprobar que el led de la tecla 'TECLADO' esta encendido" / "Pulsar despacio las siguientes teclas 'Z1' 'Z2' 'Z2' 'Z1'". DB='de' es falso; s83=null. Correcto: 'es'.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#41 · `No-puedo-hacer-Rearme-o-silenciar-sirenas-en-la-VSN-LT`** (Morley) — language `en`→`es`
- (alta) Texto integro (chunks=1, p1) en espanol: "Para activar el teclado (o Nivel acceso 2) presione la tecla 'TECLADO' mientras pulsa el código de acceso (1221)" y "conectando el puente KEY que se encuentra en el canto inferior izquierdo de la tarjeta". DB='en' es falso; s83=null. Correcto: 'es'.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#42 · `Poner-la-contraseña-por-defecto-del-programa-de-gestion-grafica-TG`** (Morley) — language `pt`→`es`
- (alta) Documento completo (chunks=1, p1) en espanol, no portugues: "¿Qué hacer en caso de si he olvidado de la contraseña del software gráfico TG?" y "Envíe el fichero compactado a soporteHLSI@honeywell.com". Lexico castellano ('contraseña', 'fichero', 'carpeta'), no PT ('palavra-passe'/'ficheiro'/'pasta'). DB='pt' es falso; s83=null. Correcto: 'es'.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#43 · `Puesta-en-marcha-repetidor-ZXrA-en-central-CONNEXION`** (Morley) — language `en`→`es`
- (alta) Texto integro (chunks=1, p1) en espanol a lo largo de los 3 pasos: "La tarjeta RS485 de comunicaciones ya viene integrada en la placa base de la central DXc Conexion", "Si la distancia entre central y repetidor es superior a 100 metros debe usar el cable de comunicaciones CSR485" y "OJO: No confundir el conexionado de alimentación y señal". Los encabezados de plantilla Steps/Warnings/Description estan en ingles pero todo el cuerpo es espanol. DB='en' es falso; s83=null. Correcto: 'es'.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#44 · `RP1R-Supra_VSN-RP1R-PLUS2-Averia-Rl_y_Fallo-de-sistema-intermitente`** (Morley) — language `de`→`es`
- (alta) Chunk unico = documento completo (p1), integramente en castellano: "La central indica Rl y Fallo de sistema intermitente" / "compruebe que esten conectadas correctamente en MOD AUX". DB dice language='de' (verificado en vivo): falso; el correcto es 'es', que es lo que propone s83. doc_type no esta en conflicto: DB 'mantenimiento' == s83 'mantenimiento' y encaja con el contenido (averia de tarjeta VSN-4REL y su reemplazo/desprogramacion).

**#45 · `RP1r-Supra-VSN-RP1R-PLUS2-Como-cambiar-el-tipo-de-final-del-linea`** (Morley) — language `de`→`es`
- (alta) Chunk unico = documento completo (p1) en castellano: "?Como cambiar la opcion de final de linea de condensador a resistencia?" / "Coloque el puente de PROG situado en la parte inferior-central del circuito de la central". DB language='de' es falso; correcto 'es' (propuesta s83). doc_type sin conflicto: DB 'configuracion' == s83 'configuracion' y coincide con el contenido (menus LC/EL de configuracion de la central).

**#46 · `Rearme-remoto-en-central-DXc-Connexion`** (Morley) — language `en`→`es`
- (alta) Los 2 chunks del documento (p1) estan en castellano: "?Como hacer un rearme remoto para barreras 6500R, detectores de llama o modulos de zona MI-CZ6?" y "En la central debemos configurar una zona logica, asociada al evento de la central REARME". DB language='en' es falso; correcto 'es'. doc_type en DB = NULL (nada vigente que conservar); el contenido son pasos de programacion por teclado ("Opcion 7 Programacion. Niv 3" / "Opcion 6 Programas"), asi que el 'configuracion' de s83 es correcto.

**#47 · `Relacion-de-producto-obsoleto-de-Morley-IAS-by-Honeywell`** (Morley) — language `de`→`es`
- (alta) Chunk unico = documento completo, en castellano: "?Donde puedo encontrar la relacion de producto obsoleto de Morley-IAS?" y remite al PDF MIEIN004 y a soporteHLSI@honeywell.com. DB language='de' es falso; correcto 'es'. doc_type en DB = NULL; el contenido no es manual sino un puntero a la tabla de obsolescencia, por lo que 'otro' (s83) es correcto ('boletin' seria la unica alternativa defendible).

**#48 · `TG-ATENCION-El-sistema-no-encuentra-la-proteccion-del-TG`** (Morley) — language `en`→`es`
- (alta) Chunk unico = documento completo, en castellano: "Mientras se produce la incidencia ATENCION: El sistema no encuentra la proteccion del TG, el programa grafico TG funciona en modo EDITOR y no habra comunicacion con las centrales de deteccion de incendios". DB language='en' es falso; correcto 'es'. RESERVA en doc_type (DB=NULL, eje no marcado en conflicto): s83 propone 'otro', pero el contenido es resolucion de incidencia (instalar el driver Sentinel USB) y 'mantenimiento' encaja mejor; no avalo el 'otro' de s83 en ese eje.

**#49 · `TG-Como-borrar-elementos-de-un-plano`** (Morley) — language `de`→`es`
- (alta) Chunk unico = documento completo, en castellano: "Como poder borrar elementos de un plano en version 7 del TG" / "Acceda al menu Configuracion > Equipos y Simbolos" / "Salga de este menu grabando los cambios, con la tecla del Disquete". DB language='de' es falso; correcto 'es'. doc_type en DB = NULL; es un procedimiento paso a paso de manejo del software TG por el operador, asi que 'guia_usuario' (s83) es correcto.

**#50 · `TG-Como-exportar-el-historico-desde-el-programa-de-gestion-grafica`** (Morley) — language `de`→`es`
- (alta) Chunk unico = documento completo, en castellano: "?Como exportar los eventos del historico del TG a un archivo?" / "Desde la ventana superior de Historico y seleccione el submenu Eventos" / "exportar los datos obtenidos en diferentes formatos (TXT, CSV, XLS, PDF) no utilice QRP". DB language='de' es falso; correcto 'es'. doc_type en DB = NULL; how-to de uso del software para el usuario final -> 'guia_usuario' (s83) es correcto.

**#51 · `TG-Como-hacer-una-copia-de-seguridad-del-proyecto`** (Morley) — language `de`→`es`
- (alta) Chunk unico = documento completo, en castellano: "?Como se debe de hacer una copia de seguridad del proyecto para la version 7 del TG?" / "Se deben de copiar las carpetas BD_OPER y BD_TG que estan en la ruta por defecto de C:\Honeywell\". DB language='de' es falso; correcto 'es'. RESERVA en doc_type (DB=NULL, eje no en conflicto): s83 propone 'otro', pero es un procedimiento de usuario paso a paso y 'guia_usuario' encajaria mejor (mismo patron que los otros how-to del TG).

**#52 · `TG-Como-solucionar-problema-de-Error-CRC`** (Notifier) — language `de`→`es`
- (alta) Chunk unico = documento completo, en castellano: "?Como solucionar problema de Error CRC en el TG?" / "se han introducidos caracteres no reconocidos por el TG, como acentos, interrogaciones, etc. en los textos descriptivos en la central". DB language='de' es falso; correcto 'es'. doc_type en DB = NULL; el contenido es diagnostico de fallo + actualizacion de version/drivers, asi que 'mantenimiento' (s83) es correcto.

**#53 · `TG-GSM-Fallo-al-enviar-SMS-desde-TG`** (Morley) — language `en`→`es`
- (alta) Chunk unico = documento completo, en castellano: "?Por que TG-GSM comunica con TG, pero no envia SMS o envia algunos y se bloquea?" / "Revisar las telefonos en TG, en CONFIGURACION/EQUIPOS y chequeando que todos los telefono SEAN SOLO NUMERICOS". DB language='en' es falso; correcto 'es'. doc_type en DB = NULL; es diagnostico de un fallo con pasos de comprobacion -> 'mantenimiento' (s83) es correcto.

**#54 · `TG-IP-1-SEC-Que-direccion-IP-tiene-por-defecto`** (Morley) — language `pt`→`es`
- (alta) Chunk unico = documento completo, en castellano: "?Que direccion IP tiene por defecto el TG-IP-1-SEC por defecto?" -> "La IP por defecto es: 192.168.1.253". DB language='pt' es falso; correcto 'es'. doc_type sin conflicto: DB 'otro' == s83 'otro', razonable para un FAQ de un solo dato (no es datasheet ni guia_usuario).

**#55 · `TG-Que-clave-tiene-si-se-instala-en-idioma-Ingles`** (Morley) — language `en`→`es`
- (alta) El chunk unico (p1) es prosa espanola: "La clave de un TG cuando se instala en el idioma Ingles es: technician" y "Si quiere pasarlo nuevamente a Espanol, siga los siguientes pasos"; los unicos tokens ingleses son el valor de la clave (technician) y la cadena "Idioma= ENG" del fichero TG.INI. chunks_v2.language='es'; documents.language='en' es falso -> correcto 'es' (el detector doc-level se dejo llevar por 'idioma-Ingles' del filename).
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#56 · `TG-SE-HA-SUPERADO-EL-MAXIMO-DE-LICENCIAS`** (Morley) — language `de`→`es`
- (alta) Chunk unico (p1) integramente en espanol: "Esto es debido a que se han dado de alta centrales o estaciones que no estan generadas en la llave de proteccion" y "Cerrar el TG y volver a ejecutarlo sin la llave de seguridad puesta"; cero prosa alemana. chunks_v2.language='es' vs documents.language='de' -> ambos valores del frame fallan, el correcto es 'es'.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#57 · `UCIP-Borrado-a-valores-de-fabrica`** (Morley) — language `de`→`es`
- (alta) Chunk unico (p1) en espanol: "Para utilizar este articulo lea y revise previamente el articulo..." y la Nota "Con este comando no se borra la configuracion de IP, si esta hubiera sido modificada previamente"; lo unico no espanol es el comando de consola ">INI (ENTER)". chunks_v2.language='es' vs documents.language='de' -> correcto 'es'.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#58 · `UCIP-Borrar-configuracion-completa`** (Morley) — doc_type `programacion`→`configuracion`
- (media) El titulo y la Question dicen literalmente "Borrar configuracion completa" / "Como borrar la configuracion de UCIP-GPRS?", y el cuerpo son ordenes de consola CONFIG (ver) e INI (borrar parametros); en ningun punto se programa nada, asi que 'programacion' no esta sostenido por el texto -> el correcto es 'configuracion'. Refuerzo: los gemelos UCIP-Borrado-a-valores-de-fabrica (mismo INI) esta tagueado 'mantenimiento' y UCIP-Borrar-datos-de-CRA1-o-2 'configuracion' -> el label doc-level es inconsistente entre docs casi identicos.
- _Reconciliación:_ flip: el agente concluyó 'configuracion' = el valor s83 real (bug frame v1); db='programacion' además fuera de taxonomía

**#59 · `UCIP-Borrar-datos-de-CRA1-o-2`** (Morley) — language `de`→`es`
- (alta) Chunk unico (p1) en espanol: "Este comando borra parametros de CRAx. Si CRA1 no esta configurada CRA2 no funcionara."; lo unico no espanol es la orden "CRA1 OFF (enter)". chunks_v2.language='es' vs documents.language='de' -> correcto 'es'.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#60 · `UCIP-Cambio-de-puerto-TCP-en-GPRS`** (Morley) — language `en`→`es`
- (alta) Chunk unico (p1) en espanol: "Es aconsejable usar un puerto entre le 5001 y el 5059 ya que no suelen estar ocupados por otros programas" y "Si precisa salir de la red LAN interna, tambien debera estar abierto en el router este puerto como TCP"; los tokens ingleses son solo comandos (CONFIG GPRSSERVER 5010). chunks_v2.language='es' vs documents.language='en' -> correcto 'es'.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#61 · `UCIP-Cambio-de-puerto-TCP-red-LAN`** (Morley) — language `de`→`es`
- (alta) Chunk unico (p1) en espanol: "Una vez estamos conectado con la consola, introduciremos la siguiente orden, para cambiar IP" y "Si dicho puerto ya estuviera ocupado, el UCIP no comunicaria con el equipo externo"; ingles solo en el comando CONFIG TCPSERVER 5001. chunks_v2.language='es' vs documents.language='de' -> correcto 'es'.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#62 · `UCIP-Como-configurar-envio-de-eventos-por-equipo`** (Morley) — doc_type `programacion`→`configuracion` · language `en`→`es`
- (alta) LANGUAGE: prosa espanola "Esta opcion habilita el envio por EQUIPO y deshabilita el envio por ZONAS"; ingles solo en los comandos ZONE OFF / ZONE ON -> correcto 'es', no el 'en' de la DB (chunks_v2.language='es'). DOC_TYPE: la Question es "Como configurar UCIP para envio de eventos por equipo?" y el procedimiento fija un parametro de consola -> correcto 'configuracion', no el 'programacion' de la DB. Ambos ejes de la DB estan mal y s83 no propone valor.
- _Reconciliación:_ flip: el agente concluyó 'configuracion' = el valor s83 real (bug frame v1); db='programacion' además fuera de taxonomía

**#63 · `UCIP-Como-enviar-datos-de-equipos-y-no-solo-eventos-de-zonas`** (Morley) — language `en`→`es`
- (alta) Chunk unico (p1) en espanol, incluida la errata del original: "Para configuarar el envio por equipos escribir ZONE OFF y pulsar enter" y "Para volver al modo de ZONA, escribir ZONE ON y pulsar enter"; ingles solo en ZONE ON/OFF. chunks_v2.language='es' vs documents.language='en' -> correcto 'es'.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#64 · `UCIP-Configuracion-CRA1`** (Morley) — doc_type `programacion`→`configuracion`
- (alta) El titulo es "UCIP - Configuracion CRA1." y la Question "Como se configura la CRA1 en UCIP-GPRS?"; el cuerpo desglosa los parametros del comando CRA1 (abonado, IP_receptora, puerto, T_alive, clave, canal ETH/GPRS/ETH+GPRS) con el ejemplo "CRA1 000020 10.56.45.23 10001 60 123456 ETH+GPRS". Es 'configuracion' por autodescripcion explicita; el 'programacion' de la DB no aparece en el texto.
- _Reconciliación:_ flip: el agente concluyó 'configuracion' = el valor s83 real (bug frame v1); db='programacion' además fuera de taxonomía

**#65 · `UCIP-Configurar-PIN-tarjeta-SIM`** (Morley) — doc_type `programacion`→`configuracion`
- (alta) La Question dice "Como configurar PIN de tarjeta SIM, solo en UCIP GPRS" y el procedimiento es una sola orden de consola "PIN XXXX" (ejemplo "ORDEN A UCIP: PIN 4848") con nota sobre bloqueo/PUK. Ajuste de un parametro -> correcto 'configuracion'; el 'programacion' de la DB no esta sostenido por el texto.
- _Reconciliación:_ flip: el agente concluyó 'configuracion' = el valor s83 real (bug frame v1); db='programacion' además fuera de taxonomía

**#66 · `UCIP-Configurar-envio-de-SMS`** (Morley) — doc_type `programacion`→`configuracion` · language `en`→`es`
- (alta) Chunk único (p1, 1357 car.) íntegramente en español: «¿Como se configura UCIP para poder enviar SMS?», orden «SMS nº_CRA nº_Telef_1 nº_Telef_2» y cierre «soporte técnico de Honeywell». db_language='en' es falso → correcto 'es'. doc_type: procedimiento de configuración por comandos de consola, luego db='programacion' es semánticamente correcto (equivalente canónico 'configuracion'); s83 no propone nada en ninguno de los dos ejes.
- _Reconciliación:_ flip: el agente concluyó 'configuracion' = el valor s83 real (bug frame v1); db='programacion' además fuera de taxonomía

**#67 · `UCIP-Configurar-puerto-UART-de-UCIP`** (Morley) — doc_type `programacion`→`configuracion` · language `de`→`es`
- (alta) Chunk único (p1, 837 car.) todo en español: «Como configurar valores de puerto UART en UCIP», «CONFIG UART1 velocidad paridad», «ORDEN A UCIP: CONFIG UART1 9600 NONE», «9600: Velocidad de comunicacion a 9600 bps». Ni una frase en alemán → db_language='de' es falso, correcto 'es'. doc_type db='programacion' correcto para el contenido (configuración de puerto por consola; canónico 'configuracion'); s83 vacío.
- _Reconciliación:_ flip: el agente concluyó 'configuracion' = el valor s83 real (bug frame v1); db='programacion' además fuera de taxonomía

**#68 · `UCIP-No-conecta-por-IP`** (Morley) — language `pt`→`es`
- (alta) Chunk único (p1, 1067 car.) en español: «Al usar consola V2.2.2 e intentar conectar a la IP por defecto 192.168.0.100 no conecta», «Para desconectar el DHCP y estar como IP fija modificar el modo (OFF al final)». No hay portugués → db_language='pt' es falso, correcto 'es'. doc_type no está en conflicto (conflicto_doc_type=False) y db='otro' es aceptable: es un FAQ de resolución de avería, no un manual.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#69 · `UCIP-Programacion-IP-de-equipo`** (Morley) — doc_type `programacion`→`configuracion` · language `de`→`es`
- (alta) Chunk único (p1, 1027 car.) en español: «Como programar la IP del equipo cambiando la que viene por defecto», «TCPIP DIRECCIÓN_IP_NUEVA MÁSCARA PUERTA_ENLACE DHCP», «Una vez cambiada la IP, la consola se desconectará». db_language='de' es falso → correcto 'es'. doc_type db='programacion' correcto (procedimiento de configuración de red por consola; canónico 'configuracion'); s83 no aporta valor en ningún eje.
- _Reconciliación:_ flip: el agente concluyó 'configuracion' = el valor s83 real (bug frame v1); db='programacion' además fuera de taxonomía

**#70 · `UCIP-Que-datos-necesito-de-la-receptora`** (Morley) — language `de`→`es`
- (alta) Chunk único (p1, sólo 540 car.) en español: «¿Que datos que nos tiene que entregar la receptora para que podamos comunicar?», lista «Abonado (6 dígitos ejemplo 000020)», «Clave de encriptación: (6 dígitos obligatorio)». Cero alemán → db_language='de' es falso, correcto 'es'. doc_type db=NULL no está en conflicto (conflicto_doc_type=False) y s83 tampoco propone; el contenido es una lista de datos requeridos, encajaría en 'otro'.
- _Reconciliación:_ flip ninguno->s83: el agente vio s83=null (bug frame v1); s83 real=es

**#71 · `UCIP-Tabla-de-compatibilidad-con-receptoras-y-centrales`** (Notifier) — language `de`→`['en', 'es']`
- (alta) Chunk único (p1, 3314 car.) leído entero, todo español: tabla «Equipo | Versión Panel | Versión UCIP | Receptoras compatibles» con ID3000 5.22, ID50 5.18, DXc 1.19F, y cola «Todas las receptoras deben ser TCP/IP y soportar encriptación con clave». db_language='de' es falso → correcto 'es'. doc_type db=NULL no está en conflicto; el contenido es una tabla de compatibilidad (encajaría 'otro'), y s83 no propone valor.
- _Reconciliación:_ flip: el agente concluyó 'configuracion' = el valor s83 real (bug frame v1); db='programacion' además fuera de taxonomía

**#72 · `UCIP-Ver-configuracion-de-equipo`** (Morley) — doc_type `programacion`→`configuracion` · language `de`→`es`
- (alta) Chunk único (p1, 641 car.) en español: «¿Cómo ver la configuración guardada en equipo?», «En la línea de comandos, donde aparece el símbolo >, escriba CONFIG y clique enter», «Obtendrá la información del UCIP y su programación actual». db_language='de' es falso → correcto 'es'. doc_type: aquí sólo se CONSULTA la configuración (no se cambia), así que db='programacion' es discutible ('operacion' encajaría mejor), pero s83 no propone alternativa.
- _Reconciliación:_ flip: el agente concluyó 'configuracion' = el valor s83 real (bug frame v1); db='programacion' además fuera de taxonomía

## La DB ya está bien — sin cambio (6)

**#1 · `4188-1132-ES issue 3_04_2025_Qref`** (Notifier) — doc_type `guia_rapida`→`configuracion`
- (media) p1 literal: 'Notifier INSPIRE E10/E15 Central detección de incendios **Guía rápida**' y el índice p2 es PASO 1..PASO 10 ('PASO 3 Instalar la central y encender' ... 'PASO 10 Prueba del sistema'); 18 chunks / 19 páginas y sufijo '_Qref' en el nombre. El título del propio documento corrobora db='guia_rapida'. Confianza media porque s83='configuracion' también es defendible (7 de los 10 pasos son configuración CLSS) y 'guia_rapida' solo tiene 3 docs en todo el corpus.

**#2 · `HLSI-MN-103_RP1r-Supra_lr`** (Notifier) — doc_type `usuario`→`instalacion`
- (alta) La portada (p1) dice literalmente "RP1r-Supra / VSN-RP1r+ / ESS-RP1r-Supra - Central de extincion - Manual de usuario - HLSI-MN-103 v.07", y el pie de cada pagina repite "Manual de usuario"; el contenido medio (p36 "4.5 Estados de la central") es operacion, no montaje. El db_doc_type='usuario' es correcto; el 'instalacion' de s83 no lo es. Idioma 'es' en DB confirmado por el texto.

**#3 · `I56-3956-201_ES Morley Loop FAAST LT QIG`** (Morley) — doc_type `guia_rapida`→`instalacion`
- (alta) Titulo en p1: "GUIA DE INSTALACION RAPIDA DE FAAST LT DIRECCIONABLE MODELOS MI-FL2011EI, MI-FL2012EI Y MI-FL2022EI" (encabezado "ESPANOL"), con lista de piezas y Tabla 2 de designaciones de terminales. db_doc_type='guia_rapida' es el calco exacto del titulo; 'instalacion' de s83 pierde el matiz de QIG. Idioma DB 'es' correcto (el ingles que ve s83 son solo las descripciones de imagen generadas por el pipeline).

**#4 · `I56-3956-201_PT Morley Loop FAAST LT QIG`** (Morley) — doc_type `guia_rapida`→`instalacion`
- (media) Solo 2 chunks en DB (p3 y p10): p3 "Instalacao dos tubos" (portugues) y p10 "ADDENDUM to FAAST LT Quick Installation Guide - SWITCHING INDUCTIVE LOADS" (inglés). El propio texto se autodenomina Quick Installation Guide -> db_doc_type='guia_rapida' correcto frente a 'instalacion'. Documento MULTI-IDIOMA: cuerpo pt + addendum en, por lo que db_language='pt' es correcto como primario (s83 ['en','pt'] describe la mezcla).

**#5 · `TG-como-se-configuran-sonidos-ante-eventos`** (Morley) — doc_type `programacion`→`configuracion`
- (media) El propio documento usa el verbo 'programar' en su Question: "Como tengo que programar un sonido ante un evento en el TG?", y el cuerpo es un procedimiento GUI paso a paso (menu Tecnico/Sonido, Crear > Sonido, F2, menu Tecnico/Clases, salvar y aplicar cambios); content_type='procedure'. 'programacion' queda sostenido por el texto, aunque el titulo dice "como se configuran": la frontera programacion/configuracion es ambigua aqui.

**#6 · `Ver-Como-Cambiar-configuracion-de-las-Funciones-especiales-en-las-centrales-`** (Morley) — doc_type `programacion`→`configuracion`
- (alta) Chunk único (p1, 2466 car.) en español, y db_language='es' ya coincide (conflicto_language=False). doc_type: el texto es un procedimiento de configuración —«ponga el puente de programación (PROG) y alimente el panel normalmente, se iluminarán los leds de las funciones especiales»— con opciones tipo «Led Teclado = ON = Averías enclavadas» y sensibilidad RBAT 0,7/1,4 mOhms en centrales NFS-Supra/VSN-Plus2/ESS-2Plus. db='programacion' es correcto (canónico equivalente 'configuracion'); s83 no propone nada, luego no hay motivo para cambiar el vigente.

## Fila muerta (borrada en T3) (1)

**#1 · `Solicitud-asistencia-curso-de-formacion-puesta-en-marcha-consultas-tecnica`** (Morley) — language `None`→`es`

## Qué pasa tras tu OK

Genero `s285_conflicts_apply_v1.sql` (staging + conteos exactos + before-image + rollback;
OVERWRITE deliberado de los valores adjudicados como erróneos), pasa por el dúo, lo pegas,
y verifico 1:1 en vivo — el mismo circuito que acabamos de cerrar con T2.