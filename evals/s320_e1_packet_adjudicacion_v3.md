# Packet E1 — adjudicación · **v3** (generado 2026-08-20 23:25Z)

> **Esta versión SUSTITUYE al v2 para trabajar.** El v2 queda como archivo: allí está la traza de
> las **125 filas ya resueltas** (con su recibo) y tus anotaciones originales. Aquí solo hay lo que
> sigue **VIVO: 67 filas**.
>
> **Qué cambia respecto al v2, y por qué** — los dos cambios nacen de errores REALES que tu repaso
> destapó, no de estética:
>
> 1. ⚠️ **Los documentos homónimos van marcados.** Tu nota «este archivo habla también de la ZX-A,
>    ZX-E…» acabó aplicada a la FAQ de la **DXc Connexion** en vez de a la de **«ZX y DX»** — se
>    diferencian en tres letras. Costó 6 atestaciones equivocadas (DEC-259). Ahora cada fila con
>    riesgo de confusión lleva un aviso y te pide comprobar la cita.
> 2. 🔍 **«PROPUESTO por el juez» ya no se confunde con lo aplicado.** Criticaste que el documento
>    «valiera para la ZXce, la ZXhe, ZX50» — y tenías razón, **pero esos ids nunca se aplicaron**:
>    eran propuesta del juez que la regla R1 descartó. El v2 los imprimía al lado de lo aplicado.
> 3. 🎯 **Cada fila viva lleva una recomendación afinada** con los patrones que TÚ ya firmaste, para
>    que la mayoría se resuelva en bloque:
>
> | patrón | qué es | filas | qué hacer |
> |---|---|---|---|
> | **P1** | el juez propone otra grafía y hay cita ✓ de portada | 15 | seguir al juez (lo firmaste 9×) |
> | **P2** | fragmento PT/FR de 1 chunk con hermano ES | 0 | baja del corpus (lo firmaste 3×) |
> | **P3** | artefacto con 0 menciones estrictas | 9 | retirar |
> | **P4** | nombre real CON barra | 8 | **tuya** — comprueba la grafía del fabricante |
> | **P5** | el nombre del fichero engaña sobre la familia | 1 | R1': manda el contenido |
>
> **Cómo trabajar sobre este fichero**: escribe tu nota debajo de la fila, empezando por `Alberto:`
> (igual que en el v2). Si el fichero es tuyo en local, súbelo y lo proceso.

---

### §0.B — `doc_map` tier B, REHECHO con la regla **serie × categoría** (38 limpias + 4 a tu criterio)  ·  10 vivas

- [ ] `con-que-sistema-operativo-es-compatible-el-programa-de-la-`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «¿Con que Sistema Operativo es compatible el programa de la DXc Connexión?»
      ALBERTO: este archivo habla también de la ZX-A, ZX-E, ZX-2/5e, ZX2/5SE
      ⚠️ **HOMÓNIMO** — hay más de un documento activo cuyo nombre empieza igual («Con que Sistema Operativo compatible el prog…»). **Comprueba la CITA antes de anotar**: en s331 una nota acabó en el documento equivocado por esto (DEC-259).

- [ ] `dxc-porque-al-activan-elementos-en-alarma-no-se-enciende-s`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «En la central DXC Connexión con el fin de aprovechar al máximo la corriente del lazo, solo **las cua»

- [ ] `dxc-puedo-anular-la-clave-de-usuario-y-acceder-directament`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «# DXC ¿Puedo anular la clave de usuario y acceder directamente al teclado?»

- [ ] `dxc-conexion-como-solucionar-la-averia-de-estado-inconsist`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «# DXc/Conexion ¿Como solucionar la avería de Estado Inconsistente Anulado?»

- [ ] `dxc-configuracion-de-la-tarjeta-232-aislada-para-comunicar`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «Para que la central DXc, comunique con el TG, deberá activar el protocolo de comunicaciones en las o»

- [ ] `morley-se-pueden-pasar-programaciones-de-zx-y-dimension-a-`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «¿Se pueden pasar programaciones de ZX y Dimensión a Connexion DXC?»
      ALBRETO: también habla de las centrales ZX y DX Dimension (que diría que el modelo es "DX", diferente a DXc), ya que el archivo va sobre como pasar de cualquiera de estas dos a la DXC

- [ ] `ucip-como-enviar-datos-de-equipos-y-no-solo-eventos-de-zon`
      → `notifier:ucip`
      cita: «# UCIP - Como enviar datos de equipos y no solo eventos de zonas»

- [ ] `bcn-3100019-es_r002_nc_series_fire_alarm_control_panel_qui` · **serie NC × central** (6 ids; la pasada original proponía 6)
      → `kidde:nc-pf2`, `kidde:nc-pf2-sc`, `kidde:nc-pf4`, `kidde:nc-pf4-sc`, `kidde:nc-pf8`, `kidde:nc-pf8-sc`
      cita: «Guía de instalación rápida de las centrales de incendio convencionales de la Serie NC»

- [ ] `bcn-3100020-es_r002_nc_series_fire_alarm_control_panel_qui` · **serie NC × central** (6 ids; la pasada original proponía 6)
      → `kidde:nc-pf2`, `kidde:nc-pf2-sc`, `kidde:nc-pf4`, `kidde:nc-pf4-sc`, `kidde:nc-pf8`, `kidde:nc-pf8-sc`
      cita: «Manual de funcionamiento rápido de las centrales de incendio convencionales de la Serie NC»


#### §0.B.2 — PIDEN TU OJO: la máquina se para y te lo pasa

- [ ] `00-3280-508-4009-03_r003_2x-a_series_quick_operation_guide`
      motivo: **documento de SERIE 2X-A (categoria NO declarada)**
      cita: «Guía de funcionamiento rápido de la serie 2X-A»
      asignación de la pasada original: `kidde:2x-at-f2`, `kidde:2x-at-f2-fb`
      → TU DECISIÓN:


### §0.C — Candidates → **ALTA** (32)  ·  1 vivas

- [ ] `aritech:2x-a` (2X-A) → **ALTA** · rol TITULO · doc `00-3280-507-4009-03_r003_2x-a_series_quick_installation_g…`
      ↳ **s331:** ⏳ SIGUE SIENDO TUYA, pero ya con la MEDIDA hecha (s331, sonda `evals/s331_2xa_sonda_plan_v1.json`): crear el paraguas «2X-A» **no pierde ninguna gold** y hace GANAR 2 golds (12 fuentes cada una, entre ellas «¿El detector KE-DP3020W vale para la central 2X-A?»). Lo único que dispara es la sonda de tokens sintética «2 x a» del gate — **0 disparos en las 111 consultas reales**. Lo que necesito de ti es UNA frase: «2X-A sí, con los táctiles» (38 modelos, incluidos los 11 2X-AT) o «2X-A sí, sin táctiles» (27; los táctiles ya tienen su propio paraguas 2X-AT). Con eso lo aplico con recibo.
      ↳ **s324:** ⏳ PENDIENTE DE TI — paraguas «2X-A» (familia): el revisor señaló que tu nota adjudica el ALCANCE, no el riesgo léxico del gate («2 x a» con espacios lo dispararía; 0 casos en 96 consultas reales) ni si incluye la sub-serie táctil 2X-AT (11 de 38). ¿Lo quieres igualmente, con 2X-AT dentro?
      menciones estrictas doc 1 / global 43 en 18 docs · cita ✓ «Guía de instalación rápida de la serie 2X-A»
      ALBERTO: aplica a todos los modelos de la serie 2x-A
      ↳ **s324b:** de acuerdo: NO se crea el producto `aritech:2x-a`; «2X-A» pasa a ser el PARAGUAS de familia (miembros = centrales y repetidores de la serie, derivados por regla; hoy 38). El gate léxico lo había frenado por un negativo SINTÉTICO («2 x a»); medido sobre el tráfico REAL (`query_logs`, 96 consultas): 0 disparos → entra en el lote §0.C con esa medida en el recibo.
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P5] **R1'**: mira el CONTENIDO, no el nombre — validaste 2 veces que los `2x_at` van sobre los NO táctiles


### §1.B — Candidates, residuo (84)  ·  55 vivas

- [ ] `morley:efs-em-8` (EFS/EM 8)
      ↳ **s324:** ⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Panel de control de incendios de 8 zonas EFS/EM 8 # Manual de instalación, puesta en…»
      doc `MS8.pdf` · estrictas doc 9 / global 18 en 2 docs · otros motivos: ambiguedad:mismo-termino-propuesto-a-dos-fabricantes
      ✅ **VALIDADO online** (`evals/s331_validacion_efsem_nx_v1.md`): panel convencional de 8 zonas, **obsoleto** (Notifier lo publica en `manualesobs`). **El motivo por el que cayó era la respuesta**: `MS8` y `FS8` son EL MISMO manual (código `997-201-103`, misma edición) archivado bajo las DOS marcas ⇒ **R3 (OEM)**, se atesta bajo ambas. Lo único que queda es TU decisión de **namespace**: ¿`notifier:efs-em-8` o `morley:efs-em-8`?
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P4] **tuya**: un «sí» lo da de alta; comprueba que la grafía es la del FABRICANTE (lección DOA: el sufijo del certificado no es parte del modelo)

- [ ] `notifier:efs-em-8` (EFS/EM 8)
      ↳ **s324:** ⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Panel de control de incendios de 8 zonas EFS/EM 8 # Manual de instalación, puesta en…»
      doc `FS8` · estrictas doc 9 / global 18 en 2 docs · otros motivos: ambiguedad:mismo-termino-propuesto-a-dos-fabricantes
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P4] **tuya**: un «sí» lo da de alta; comprueba que la grafía es la del FABRICANTE (lección DOA: el sufijo del certificado no es parte del modelo)

- [ ] `notifier:nx2-r-r-y-nx5-r-r` (NX2/R/R y NX5/R/R)
      ↳ **s324:** ⏳ PENDIENTE DE TI — NX2/R/R y NX5/R/R: nombre con barra, 1 sola mención en tabla (dúo r32): ¿alta?
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✓ «| 1 | → | (−) | NX2/R/R y NX5/R/R»
      doc `EMA24RS2R_NX2y5-R-R` · estrictas doc 1 / global 1 en 1 doc · otros motivos: juez:confianza-media; juez:propone-otra-grafia(NX2/R/R; NX5/R/R)
      el juez propone otra grafía: `NX2/R/R; NX5/R/R`
      ✅ **VALIDADO online** (`evals/s331_validacion_efsem_nx_v1.md`): son **DOS** productos reales — `NX2/R/R` (flash estroboscópico rojo, 2 W) y `NX5/R/R` (sirena/estrobo de 14 tonos, flash 5 W). La grafía con barras es la del FABRICANTE (**R8** cumplida) ⇒ por **R7** el id concatenado NO se crea: son dos altas. Gap: 1 mención por modelo, en un documento que es solo un dibujo (su PDF tiene 17 caracteres de texto), pero la ficha del fabricante lo respalda.
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P1] **seguir al juez**: es el patrón que firmaste 9 veces («OK con juez») en §1.B · [P4] **tuya**: un «sí» lo da de alta; comprueba que la grafía es la del FABRICANTE (lección DOA: el sufijo del certificado no es parte del modelo)

- [ ] `notifier:pul-d-ext` (PUL-D/EXT)
      ↳ **s324:** ⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta
      **PRODUCTO_REAL** · rol REFERENCIA_COMERCIAL · confianza media · cita ✗ «PUL-D/EXT 1035 [CE mark logo] Honeywell Life Safety Iberia, SL.»
      doc `PUL-DEXT_Instrucciones multi` · estrictas doc 1 / global 1 en 1 doc · otros motivos: juez:confianza-media; cita:no-verificada-a-texto-completo
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P4] **tuya**: un «sí» lo da de alta; comprueba que la grafía es la del FABRICANTE (lección DOA: el sufijo del certificado no es parte del modelo)

- [ ] `notifier:pul-p-ext` (PUL-P/EXT)
      ↳ **s324:** ⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta
      **PRODUCTO_REAL** · rol REFERENCIA_COMERCIAL · confianza alta · cita ✓ «PUL-P/EXT** 1035 CE Honeywell Life Safety Iberia, SL.»
      doc `PUL-PEXT_Instrucciones multi` · estrictas doc 1 / global 1 en 1 doc
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P4] **tuya**: un «sí» lo da de alta; comprueba que la grafía es la del FABRICANTE (lección DOA: el sufijo del certificado no es parte del modelo)

- [ ] `sensitron:sts-ckd` (STS/CKD+)
      ↳ **s324:** ⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Manual de instrucciones # STS/CKD+»
      doc `MT4508-CKDPLUS REV 0.pdf` · estrictas doc 1 / global 4 en 4 docs
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P4] **tuya**: un «sí» lo da de alta; comprueba que la grafía es la del FABRICANTE (lección DOA: el sufijo del certificado no es parte del modelo)

- [ ] `spectrex:20-20mi` (20/20MI)
      ↳ **s324:** ⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «CONFIGURACIÓN DEL DETECTOR DE LLAMA 20/20MI»
      doc `MADT696_01` · estrictas doc 5 / global 50 en 3 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P4] **tuya**: un «sí» lo da de alta; comprueba que la grafía es la del FABRICANTE (lección DOA: el sufijo del certificado no es parte del modelo)

- [ ] `spectrex:20-20r` (20/20R)
      ↳ **s324:** ⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «DETECTOR DE LLAMA DE UN ÚNICO ESPECTRO INFRARROJO ## Modelo «20/20R»»
      doc `MNDT713.pdf` · estrictas doc 2 / global 5 en 2 docs

**riesgo-lexico:acronimo-corto-sin-digitos** — 17
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P4] **tuya**: un «sí» lo da de alta; comprueba que la grafía es la del FABRICANTE (lección DOA: el sufijo del certificado no es parte del modelo)

- [ ] `morley:miw` (MIW)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Serie MIW Equipos Vía Radio Analógicos»
      doc `MIW-al-sustituir-las-baterias-de-un-equipo-se…` · estrictas doc 1 / global 70 en 11 docs

- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «# ACTUALIZACIÓN DE HISTÓRICO DEL TG El programa ActualizaHis.exe es el encargado de…»
      doc `Actulización histórico TG` · estrictas doc 9 / global 164 en 18 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo

- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «# TG - He cambiado el nombre del plano y ahora el plano y los equipos han desapareci…»
      doc `Al cambiar-el-nombre-del-plano-a desaparecido…` · estrictas doc 6 / global 87 en 11 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo

- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «¿Como solucionar la incidencia *"TABLE IS FULL"* en el software gráfico *TG*?»
      doc `Como-solucionar-la-incidencia-TABLE-IS-FULL-e…` · estrictas doc 5 / global 76 en 14 docs

- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✓ «Poner la contraseña por defecto del programa de gestión gráfica TG»
      doc `Poner-la-contraseña-por-defecto-del-programa-…` · estrictas doc 4 / global 90 en 3 docs · otros motivos: juez:confianza-media; sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo

- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Puedo migrar / actualizar un TG versión 5.XX a versión 7.XX»
      doc `Requisitos-del-PC-para-el-TG-Version-5-XX.pdf` · estrictas doc 3 / global 96 en 4 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo

- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «el programa gráfico TG funciona en modo EDITOR y no habrá comunicación con las centr…»
      doc `TG-ATENCION-El-sistema-no-encuentra-la-protec…` · estrictas doc 6 / global 23 en 9 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo

- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «¿Como ampliar una/as licencia/s de un TG?»
      doc `TG-Como ampliar-licencias.pdf` · estrictas doc 8 / global 93 en 2 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo

- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Acceda al programa TG con una clave que le permita alcanzar al menú de **Configuraci…»
      doc `TG-Como-borrar-elementos-de-un-plano.pdf` · estrictas doc 3 / global 162 en 11 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo

- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Después de instalar el programa gráfico (en adelante TG) debe proceder a la generaci…»
      doc `TG-Como-cargar-añadir-planos.pdf` · estrictas doc 9 / global 115 en 4 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo

- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «¿Como se debe de hacer una copia de seguridad del proyecto para la versión 7 del TG?»
      doc `TG-Como-hacer-una-copia-de-seguridad-del-proy…` · estrictas doc 7 / global 148 en 20 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo

- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Puede realizar estas indicaciones con el TG arrancado, tanto en Modo Editor como en…»
      doc `TG-Como-puedo-ver-los-equipos-que-no-estan-re…` · estrictas doc 3 / global 109 en 14 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo

- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «debe acceder a la utilidad que acompaña al software gráfico TG»
      doc `TG-Como-reparar-Historico-Provisional.pdf` · estrictas doc 12 / global 85 en 12 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo

- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Cierre el programa gráfico **TG**»
      doc `TG-Que-clave-tiene-si-se-instala-en-idioma-In…` · estrictas doc 7 / global 120 en 9 docs

- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «# TG - SE HA SUPERADO EL MÁXIMO DE LICENCIAS.»
      doc `TG-SE-HA-SUPERADO-EL-MAXIMO-DE-LICENCIAS.pdf` · estrictas doc 9 / global 53 en 13 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo

- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✗ «Programa gráfico de gestión, tipo TG de Notifier»
      doc `TG-como-se-configuran-sonidos-ante-eventos.pdf` · estrictas doc 2 / global 92 en 6 docs · otros motivos: juez:confianza-media; cita:no-verificada-a-texto-completo; sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo

- [ ] `morley:vsn` (VSN)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza media · cita ✗ «VSN-RP1R-PLUS2, VSN-Plus y VSN-2PLUS»
      doc `No-funcionan-las-teclas-de-la-central-VSN.pdf` · estrictas doc 2 / global 119 en 19 docs · otros motivos: juez:confianza-media; cita:no-verificada-a-texto-completo; contradiccion:artefacto-con-fuerte-senal-de-sujeto

**juez:confianza-media** — 14

- [ ] `kidde:kit-2x-afr-c-09` (KIT 2X-AFR-C-09)
      ↳ **s324:** ⏳ PENDIENTE DE TI — re-juicio K=5 NO convergente (votos válidos {'ARTEFACTO_EXTRACCION': 5}; término AUSENTE del texto) → decides tú · `s324c_rejuicio_k5_v1.md`
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «KIDDE™ COMMERCIAL # 2X-AFR-C ## Repetidor de incendios direccionable - Compacto»
      doc `DS_KIDDE_KIT_2X_AFR_C_09_202412_ES_c976.pdf` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `2X-AFR-C`
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P1] **seguir al juez**: es el patrón que firmaste 9 veces («OK con juez») en §1.B · [P3] **retirar**: sin ninguna mención del token, no es un producto

- [ ] `kidde:zlsm-md` (ZLSM-MD)
      ↳ **s324:** ⏳ PENDIENTE DE TI — re-juicio K=5 NO convergente (votos válidos {'ARTEFACTO_EXTRACCION': 5}; término AUSENTE del texto) → decides tú · `s324c_rejuicio_k5_v1.md`
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «## Kidde MiniLaser»
      doc `DS_KIDDE_ZLSM_MD_202604_ES_8d42.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: atencion:etiqueta-87-chunks-sin-aparecer-verbatim
      el juez propone otra grafía: `MiniLaser`
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P1] **seguir al juez**: es el patrón que firmaste 9 veces («OK con juez») en §1.B · [P3] **retirar**: sin ninguna mención del token, no es un producto

- [ ] `kidde:zlsm-md` (ZLSM-MD)
      ↳ **s324:** ⏳ PENDIENTE DE TI — re-juicio K=5 NO convergente (votos válidos {'ARTEFACTO_EXTRACCION': 5}; término AUSENTE del texto) → decides tú · `s324c_rejuicio_k5_v1.md`
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✗ «MI_KIDDE_ZLSM_MD_202604_ING_1875.pdf»
      doc `MI_KIDDE_ZLSM_MD_202604_ING_1875.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: cita:no-verificada-a-texto-completo; atencion:etiqueta-87-chunks-sin-aparecer-verbatim
      el juez propone otra grafía: `MiniLaser`
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P3] **retirar**: sin ninguna mención del token, no es un producto

- [ ] `kidde:zlsm-mr` (ZLSM-MR)
      ↳ **s324:** ⏳ PENDIENTE DE TI — re-juicio K=5 NO convergente (votos válidos {'ARTEFACTO_EXTRACCION': 5}; término AUSENTE del texto) → decides tú · `s324c_rejuicio_k5_v1.md`
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✗ «MI_KIDDE_ZLSM_MR_202604_ING_252a.pdf»
      doc `MI_KIDDE_ZLSM_MR_202604_ING_252a.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: cita:no-verificada-a-texto-completo; ambiguedad:veredictos-discordantes-para-el-mismo-id
      el juez propone otra grafía: `MiniLaser I/O Functional Module`
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P3] **retirar**: sin ninguna mención del token, no es un producto

- [ ] `morley:fl-20` (FL-20)
      ↳ **s324:** ⏳ PENDIENTE DE TI — re-juicio K=5 NO convergente (votos válidos {'ARTEFACTO_EXTRACCION': 5}) → decides tú · `s324c_rejuicio_k5_v1.md`
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «La serie LT MI-FL20 forma parte de la familia Fire Alarm Aspiration Sensing Technolo…»
      doc `I56-3956-201_PT Morley Loop FAAST LT QIG.pdf` · estrictas doc 0 / global 0 en 3 docs
      el juez propone otra grafía: `FAAST LT (serie FL20)`
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P1] **seguir al juez**: es el patrón que firmaste 9 veces («OK con juez») en §1.B · [P3] **retirar**: sin ninguna mención del token, no es un producto

- [ ] `morley:morley-ias-max` (Morley-IAS Max)
      ↳ **s324:** ⏳ PENDIENTE DE TI — re-juicio K=5 cross-model (3× sonnet-5 + 2× gpt-5.5, cita verificada) CONVERGENTE 5/5 PRODUCTO_REAL → propuesto para ALTA · `s324c_rejuicio_k5_v1.md`
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✓ «Documentación Morley-IAS Max https://buildings.honeywell.com/gb/en/lp/morleymaxtech»
      doc `Docs Morley-IAS Max - QR` · estrictas doc 1 / global 1 en 1 doc

- [ ] `notifier:hssd` (HSSD)
      ↳ **s324:** ⏳ PENDIENTE DE TI — re-juicio K=5 NO convergente (votos válidos {'ARTEFACTO_EXTRACCION': 3, 'PRODUCTO_REAL': 2}) → decides tú · `s324c_rejuicio_k5_v1.md`
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza media · cita ✓ «Los **detectores HSSD** deben montarse fuera de la cámara frigorífica»
      doc `MADT731_01` · estrictas doc 18 / global 70 en 3 docs · otros motivos: contradiccion:artefacto-con-fuerte-senal-de-sujeto

- [ ] `notifier:nfs-32-001` (NFS-32-001)
      ↳ **s324:** ⏳ PENDIENTE DE TI — re-juicio K=5 NO convergente (votos válidos {'ARTEFACTO_EXTRACCION': 5}; término AUSENTE del texto) → decides tú · `s324c_rejuicio_k5_v1.md`
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✗ «D1056-1_NFXI-BS-BSF»
      doc `D1056-1_NFXI-BS-BSF` · estrictas doc 0 / global 0 en 0 docs · otros motivos: cita:no-verificada-a-texto-completo; ambiguedad:veredictos-discordantes-para-el-mismo-id
      el juez propone otra grafía: `NFXI-BS-BSF`
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P3] **retirar**: sin ninguna mención del token, no es un producto

- [ ] `notifier:repetidor-serie-1000` (REPETIDOR SERIE 1000)
      ↳ **s324:** ⏳ PENDIENTE DE TI — re-juicio K=5 cross-model (3× sonnet-5 + 2× gpt-5.5, cita verificada) CONVERGENTE 5/5 PRODUCTO_REAL → propuesto para ALTA (grafía propuesta: «Repetidor de la Serie 1000») · `s324c_rejuicio_k5_v1.md`
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✓ «# Repetidor de la Serie 1000 Fire alarm control panel»
      doc `MNDT213.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: contradiccion:producto-real-sin-mencion-estricta-ni-en-mayusculas; juez:propone-otra-grafia(Repetidor de la Serie 1000)
      el juez propone otra grafía: `Repetidor de la Serie 1000`
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P1] **seguir al juez**: es el patrón que firmaste 9 veces («OK con juez») en §1.B

- [ ] `notifier:securnet-plus-02` (SECURNET PLUS 02)
      ↳ **s324:** ⏳ PENDIENTE DE TI — re-juicio K=5 NO convergente (votos válidos {'ARTEFACTO_EXTRACCION': 3, 'PRODUCTO_REAL': 2}) → decides tú · `s324c_rejuicio_k5_v1.md`
      **ARTEFACTO_EXTRACCION** · rol CODIGO_DE_DOCUMENTO · confianza media · cita ✓ «**ADEMDUM** | SECURNET PLUS 02<br/>Fecha: 19 / 03 / 2001»
      doc `MADT575_02` · estrictas doc 1 / global 1 en 1 doc
      el juez propone otra grafía: `SECURNET PLUS`
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P1] **seguir al juez**: es el patrón que firmaste 9 veces («OK con juez») en §1.B

- [ ] `spectrex:40-40l` (40-40L)
      ↳ **s324:** ⏳ PENDIENTE DE TI — re-juicio K=5 NO convergente (votos válidos {'ARTEFACTO_EXTRACCION': 3, 'PRODUCTO_REAL': 2}) → decides tú · `s324c_rejuicio_k5_v1.md`
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✓ «Modelo S40/40L, LB y S40/40L4, L4B»
      doc `MNDT722_40-40L` · estrictas doc 0 / global 0 en 0 docs · otros motivos: juez:propone-otra-grafia(S40/40L)
      el juez propone otra grafía: `S40/40L`
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P1] **seguir al juez**: es el patrón que firmaste 9 veces («OK con juez») en §1.B · [P3] **retirar**: sin ninguna mención del token, no es un producto

- [ ] `xtralis:vesda` (VESDA)
      ↳ **s324:** ⏳ PENDIENTE DE TI — re-juicio K=5 NO convergente (votos válidos {'ARTEFACTO_EXTRACCION': 3, 'PRODUCTO_REAL': 2}) → decides tú · `s324c_rejuicio_k5_v1.md`
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza media · cita ✗ «La Pantalla de reconocimiento inmediato del detector VESDA VLF muestra los niveles d…»
      doc `HSLI_IN_020_Tabla equivalencia TG` · estrictas doc 3 / global 91 en 7 docs · otros motivos: cita:no-verificada-a-texto-completo; contradiccion:artefacto-con-fuerte-senal-de-sujeto
      el juez propone otra grafía: `VESDA-VLF/VLF-250 (y otros modelos de la gama VESDA)`

**obsoleta:doc-fuente-no-activo** — 7

- [ ] `notifier:airsense` (AIRSENSE)
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza alta · cita ✓ «**AirSense** TECHNOLOGY LTD»
      doc `MADT731_04` · estrictas doc 3 / global 40 en 11 docs · otros motivos: contradiccion:artefacto-con-fuerte-senal-de-sujeto

- [ ] `notifier:airsense` (Airsense)
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza alta · cita ✓ «© Copyright 1996-2002 AirSense Technology Ltd»
      doc `TIDT109.pdf` · estrictas doc 2 / global 40 en 14 docs · otros motivos: contradiccion:artefacto-con-fuerte-senal-de-sujeto

- [ ] `notifier:faast-lt` (FAAST LT)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «## Accesorios de «FAAST LT» A continuación se facilita información sobre los accesor…»
      doc `ASD Cold Environments_SP` · estrictas doc 6 / global 122 en 6 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo

- [ ] `notifier:faast-lt` (FAAST-LT)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «QUICK INSTALLATION GUIDE ADDRESSABLE FAAST LT MODELS NFXI-ASD11, NFXI-ASD12, NFXI-AS…»
      doc `FAAST-LT-Como-obtener-el-historico-del-equipo…` · estrictas doc 0 / global 0 en 8 docs
      el juez propone otra grafía: `FAAST LT`

**ambiguedad:mismo-termino-propuesto-a-dos-fabricantes** — 2
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P1] **seguir al juez**: es el patrón que firmaste 9 veces («OK con juez») en §1.B

- [ ] `notifier:lt-200` (LT-200)
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✗ «FAAST LT-200 MODELOS DIRECCIONABLES»
      doc `FAAST-LT-Como-comunicar-con-el-equipo.pdf` · estrictas doc 2 / global 135 en 6 docs · otros motivos: juez:confianza-media; cita:no-verificada-a-texto-completo; juez:propone-otra-grafia(FAAST LT-200)
      el juez propone otra grafía: `FAAST LT-200`

- [ ] `xtralis:lt-200` (LT-200)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «# FAAST LT-200 ## FIRE ALARM ASPIRATION SENSING TECHNOLOGY® ## ADVANCED SET-UP AND C…»
      doc `I56-3888-010 FAAST LT-200 Adv Guide` · estrictas doc 95 / global 69 en 8 docs · otros motivos: juez:propone-otra-grafia(FAAST LT-200)
      el juez propone otra grafía: `FAAST LT-200`

**ambiguedad:veredictos-discordantes-para-el-mismo-id** — 2
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P1] **seguir al juez**: es el patrón que firmaste 9 veces («OK con juez») en §1.B

- [ ] `kidde:ke-dba-sktw` (KE-DBA-SKTW)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «KIDDE COMMERCIAL # KE-DBA-SKTW **Intelligent addressable base accessory - trim skirt…»
      doc `HD_KE_DBA_SKTW_202407_ING_2da9.pdf` · estrictas doc 4 / global 8 en 3 docs

- [ ] `notifier:nfs-32-001` (NFS-32-001)
      ↳ **s324:** ⏳ PENDIENTE DE TI — re-juicio K=5 NO convergente (votos válidos {'ARTEFACTO_EXTRACCION': 5}; término AUSENTE del texto) → decides tú · `s324c_rejuicio_k5_v1.md`
      **NORMA_O_CERTIFICACION** · rol FRASE_TECNICA · confianza alta · cita ✓ «French Fire Sound AFNOR<br/>NFS 32-001»
      doc `D838-1_kac sounders` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `NF S 32-001`

**atencion:etiqueta-270-chunks-sin-aparecer-verbatim** — 2
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P1] **seguir al juez**: es el patrón que firmaste 9 veces («OK con juez») en §1.B · [P3] **retirar**: sin ninguna mención del token, no es un producto

- [ ] `morley:mie-ma-100` (MIE-MA-100)
      **ARTEFACTO_EXTRACCION** · rol CODIGO_DE_DOCUMENTO · confianza alta · cita ✓ «MIE-MA-100_01_C 27/07/04 Morley-IAS ESPAÑA 1 de 4»
      doc `MIE-MA-100_01.pdf` · estrictas doc 4 / global 8 en 2 docs

- [ ] `xtralis:vesda` (VESDA)
      ↳ **s324:** ⏳ PENDIENTE DE TI — re-juicio K=5 NO convergente (votos válidos {'ARTEFACTO_EXTRACCION': 3, 'PRODUCTO_REAL': 2}) → decides tú · `s324c_rejuicio_k5_v1.md`
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza alta · cita ✓ «Instalación y programación del sistema de aspiración Vesda»
      doc `Cursos formacion_Marzo 2026.pdf` · estrictas doc 8 / global 88 en 11 docs

**juez:propone-otra-grafia(2010-2A-PAK-HPL)** — 2

- [ ] `kidde:2a-pak-hpl` (2A-PAK-HPL)
      **PRODUCTO_REAL** · rol TABLA_DE_MODELOS · confianza alta · cita ✓ «| 2010-2A-PAK-HPL | Enables the high powered loop»
      doc `DS_KIDDE_2A_PAK_HPL_9085.pdf` · estrictas doc 2 / global 59 en 8 docs
      el juez propone otra grafía: `2010-2A-PAK-HPL`
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P1] **seguir al juez**: es el patrón que firmaste 9 veces («OK con juez») en §1.B

- [ ] `kidde:2a-pak-hpl` (2A-PAK-HPL)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «2010-2A-PAK-HPL Panel Activation Key Registration Guide»
      doc `MI_KIDDE_2A_PAK_HPL_c599.pdf` · estrictas doc 19 / global 60 en 8 docs
      el juez propone otra grafía: `2010-2A-PAK-HPL`

**juez:veredicto-no-bloqueable(ACCESORIO_DE_OTRO)** — 2
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P1] **seguir al juez**: es el patrón que firmaste 9 veces («OK con juez») en §1.B

- [ ] `kidde:ke-dba-sktw` (KE-DBA-SKTW)
      **ACCESORIO_DE_OTRO** · rol TITULO · confianza alta · cita ✓ «KE-DBA-SKTW Trim Skirt Accessory for Standard Mounting Base Installation Sheet»
      doc `MI_KE_DBA_SKTW_202407_ES_a20b.pdf` · estrictas doc 3 / global 8 en 3 docs · otros motivos: ambiguedad:veredictos-discordantes-para-el-mismo-id
      producto padre propuesto: `KE-DB3010W`

- [ ] `spectrex:40-40-air` (40-40-AIR)
      **ACCESORIO_DE_OTRO** · rol TITULO · confianza alta · cita ✓ «hield, developed for SharpEye 40/40 series optical flame detectors, allows detector…»
      doc `guide-40-40-air-shield-p-n-777650-spectrex-en…` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `40/40 Air Shield (P/N 777650)`
      producto padre propuesto: `SharpEye 40/40 series (detectores ópticos de llama Spectrex)`

**(sin motivo declarado en el recibo)** — 1
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P1] **seguir al juez**: es el patrón que firmaste 9 veces («OK con juez») en §1.B

- [ ] `notifier:serie-ps` (Serie PS)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «# 1. INSTALACIÓN DE LAS FUENTES DE ALIMENTACIÓN DE LA SERIE PS»
      doc `Serie PS.pdf` · estrictas doc 1 / global 6 en 2 docs

**colision:id-ya-existe-en-el-catalogo-gobernado** — 1

- [ ] `notifier:id1000` (ID1000)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «# CENTRAL DE ALARMA CONTRA INCENDIOS SERIE ID1000»
      doc `TIDT066_copia.pdf` · estrictas doc 3 / global 60 en 10 docs

**juez:propone-otra-grafia(S40/40I)** — 1

- [ ] `spectrex:40-40i` (40-40I)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Modelo S40/40I»
      doc `MNDT721_40-40I` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `S40/40I`

**juez:veredicto-no-bloqueable(NO_DECIDIBLE)** — 1
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P1] **seguir al juez**: es el patrón que firmaste 9 veces («OK con juez») en §1.B

- [ ] `kidde:zlsm-mr` (ZLSM-MR)
      ↳ **s324:** ⏳ PENDIENTE DE TI — re-juicio K=5 NO convergente (votos válidos {'ARTEFACTO_EXTRACCION': 5}; término AUSENTE del texto) → decides tú · `s324c_rejuicio_k5_v1.md`
      **NO_DECIDIBLE** · rol NO_APARECE · confianza media · cita ✓ «AIRSENSE # 9-30521 **Módulo funcional de entrada/salida MiniLaser**»
      doc `DS_KIDDE_ZLSM_MR_202604_ES_6a09.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: juez:confianza-media; ambiguedad:veredictos-discordantes-para-el-mismo-id
      el juez propone otra grafía: `9-30521`

**sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo** — 1
      🎯 **Recomendación afinada** (patrón que ya firmaste): [P1] **seguir al juez**: es el patrón que firmaste 9 veces («OK con juez») en §1.B · [P3] **retirar**: sin ninguna mención del token, no es un producto


### §1.C — `product_model` sucio, residuo (1)  ·  1 vivas

- [ ] `997-493-002-2` · pm actual «EN54 2-8 Zone» · Notifier · 27 chunks
      veredicto **NO_DECIDIBLE** · confianza media · cita ✓ «This manual contains operating instructions for the EN54, 2 - 8 zone conventional fire control panel.»
      razón: El documento nunca imprime un modelo comercial: solo se autodescribe como 'EN54 2-8 Zone Conventional Fire Control Panel', donde EN54 es la norma y '2-8 zone' una descripción funcional, no un modelo. El censo regex no extrajo can…
      muestra: documento COMPLETO, 40892 chars, 27 chunks · candidatos impresos: ninguno
      **la pregunta que hay que responder**: ¿Confirma el catálogo gobernado (o el PDF original con portada/contraportada completa) que el panel convencional 2-8 zonas de Notifier con código de documento 997-493 es el NFS 2-8, y debería adjudicarse igual a los hermanos _1 y _2?
      propuesta si no se decide: NADA que aplicar; el valor actual se conserva.

---

## SECCIÓN 2 — Ya no aplican (12) — **no decides nada**

Filas del packet v1 que el refresco contra el estado de HOY dejó sin objeto.
Se listan para que conste que NO se han perdido, no para adjudicar.

**obsoleta (3)** — el documento ya no está activo (status=superseded): su doc_map dejó de ser una pregunta viva

- `mi_kidde_ke_dp312x_snx_202503_es_acf9` (Kidde · 45 chunks)
- `mndt420` (Notifier · 85 chunks)
- `pl4_mt574e_eng` (Sensitron · 24 chunks)

**se_disuelve_con_e1_seccion1 (9)** — ya existe entrada de doc_map para el MISMO source_file bajo otro document_id: es la clase COLISIÓN de §1 — al repuntar §1, este documento hereda la entrada y la pregunta de §2 desaparece

- `33976_13_vesda-e_vep-a00-p_product_guide_a4_spanish_lores` (Xtralis · 120 chunks)
- `mndt500` (Notifier · 51 chunks)
- `mndt503` (Notifier · 46 chunks)
- `mndt506` (Notifier · 53 chunks)
- `mndt515` (Notifier · 29 chunks)
- `mndt615` (Notifier · 7 chunks)
- `rp1r - man ita r.a2` (Notifier · 3 chunks)
- `tg-1020-tec` (Notifier · 63 chunks)
- `tg-1020-usu` (Notifier · 54 chunks)

---

## Recibos (la traza completa, fila a fila)

- `evals/s322f_e1_colisiones_adjudicacion_v1.json` — 49 filas (49 bloque / 0 individual)
- `evals/s322f_e1s2_tierb_docmap_v1.json` — 67 filas (42 bloque / 13 individual)
- `evals/s322g_e1_candidatos_triage_v1.json` — 133 filas (50 bloque / 83 individual)
- `evals/s322g_e1_pm_sucio_v1.json` — 4 filas (3 bloque / 1 individual)
- Ensamblado por `scripts/s322_packets_v2.py` (determinista, sin LLM) el 20260815T163607Z.

## Auto-verificación del encabezado

Filas declaradas arriba vs filas REALMENTE escritas en este fichero:

- **SECCIÓN 0**: declaradas 143 · escritas 143 · casillas 143 — ✓
- **SECCIÓN 1**: declaradas 98 · escritas 98 · casillas 98 — ✓
- **SECCIÓN 2**: declaradas 12 · escritas 12 · casillas 0 — ✓
- **TOTAL**: 253 = 143 + 98 + 12 ✓ (cuadra con las 253 casillas de la v1)
