# Revisión uno a uno — manuales huérfanos

> Generado por `scripts/s337_packet_revision_alberto.py` sobre el catálogo vivo (**82 huérfanos**) y el diagnóstico `evals/s336c_diagnostico_huerfanos.json`.
> **Una fila = una decisión**, no un manual: si una firma desbloquea 12 manuales, es una fila que dice 12. Ordenado por lo que desbloquea cada una.
> Marca `[x]` lo que apruebes y escribe al lado si quieres otra cosa. Nada está aplicado.

---

## ✅ Lo que ya decidiste hoy — comprueba que te leí bien

| tu palabra | lo que entendí | efecto |
|---|---|---|
| «Detnov OK» | El **nº de referencia del fabricante vale como cita bajo R4** cuando el manual no usa el nombre de modelo (`MAD-491` ↔ `55349102`) | desbloquea el bloque Detnov, abajo |
| «los TG son software» | La familia TG es **software**, y por **R10** el software ES producto consultable → **no se retiran**. Propongo además marcarles `categoria: software de configuración`, campo que ya existe y usan 4 productos | ninguno de los TG sale del catálogo |
| «1 OK» | `HLSI-MN-025-I_NFS Supra Series v05` — el `unresolved:vsn12-2plus` se resuelve; **propongo `morley:`** porque el manual es de la serie NFS Supra de Morley | 1 manual |
| «3 OK» | `TG-1020-INT` — se resuelve a favor de **Notifier**, coherente con que los TG sean su software. ⚠️ Ojo: hoy existe `desico:tg-1020` **consumible**; si TG es software de Notifier, eso huele a atribución equivocada y te lo pregunto abajo | 1 manual |

---

## 1 · Redirects de una línea — el gemelo YA es consumible

Mismo canónico, uno con la marca puesta y otro sin ella. **R21 dice que lo firmas tú.** Simulado sobre una copia del catálogo: **0 huérfanos nuevos**.

### 1.1 — `unresolved:id50` → `notifier:id-50`  ·  **12 manual(es)**

- **Recomendación: SÍ.** Mismo canónico «ID50»; el destino ya es consumible, así que el redirect no crea nada nuevo — sólo deja de perder los manuales.
- Manuales: `BIDT077`, `MADT155_01`, `MADT155_05_A`, `MADT155_07`, `MADT155_08`, `MCDT155`, `MCDT156_A`, `MFDT155`, `MFDT156`, `MIDT155`, `MIDT156`, `TIDT107`

  - [X] OK  ·  [ ] otra cosa: ______

### 1.2 — `unresolved:tg` → `notifier:tg`  ·  **2 manual(es)** · **software (R10)**

- **Recomendación: SÍ.** Mismo canónico «TG»; el destino ya es consumible, así que el redirect no crea nada nuevo — sólo deja de perder los manuales.
- Manuales: `Como-configurar-correos-en-un-TG-HONEYWELL`, `TG-Como-exportar-el-historico-desde-el-progr`

  - [ ] OK  ·  [X] otra cosa: Ojo que TG sale tanto para Morley como para Notifier, por lo que debería ser findable para ambas marcas.

### 1.3 — `unresolved:mad-450` → `detnov:mad-450`  ·  **1 manual(es)**

- **Recomendación: SÍ.** Mismo canónico «MAD-450»; el destino ya es consumible, así que el redirect no crea nada nuevo — sólo deja de perder los manuales.
- Manuales: `55345103 Manual Pulsador Analogico MAD-450 E`

  - [X] OK  ·  [ ] otra cosa: ______

### 1.4 — `unresolved:id60` → `notifier:id-60`  ·  **1 manual(es)**

- **Recomendación: SÍ.** Mismo canónico «ID60»; el destino ya es consumible, así que el redirect no crea nada nuevo — sólo deja de perder los manuales.
- Manuales: `MADT155_02`

  - [X] OK  ·  [ ] otra cosa: ______

### 1.5 — `unresolved:tg-gsm` → `notifier:tg-gsm`  ·  **1 manual(es)** · **software (R10)**

- **Recomendación: SÍ.** Mismo canónico «TG-GSM»; el destino ya es consumible, así que el redirect no crea nada nuevo — sólo deja de perder los manuales.
- Manuales: `TG-GSM-Fallo-al-enviar-SMS-desde-TG`

  - [ ] OK  ·  [X] otra cosa: OK a lo que propone (ten en cuenta que es software). no obstante, TG-GSM debería pertenecer a la familia de software TG

## 2 · Ambiguos — el token lo disputan dos ids

No te doy «mi lectura»: te doy **en cuántos documentos de cada marca aparece el token**, que es el único discriminador que no me invento.

### 2.1 — «VSN12-2Plus»  ·  1 manual(es)  ·  ✅ **YA LO DECIDISTE**

- Ids que se lo disputan: `morley:vsn12-2plus`, `notifier:vsn12-2plus` (+ el candidate del manual)
- **Aparece en documentos de**: **Morley** 2 · **Notifier** 1
- Manuales: `HLSI-MN-025-I_NFS Supra Series v05`
- ✅ Dijiste «1 OK» → lo entiendo como **`morley:vsn12-2plus`** (el manual es de la serie NFS Supra de Morley). La evidencia de arriba lo respalda.

  - [ ] confirmado  ·  [X] te leí mal, era: Morley. no obstante, ojo que hay más modelos de la familia VSN-2Plus, en concreto VSN4-2Plus, VSN8-2Plus, y VSN12-2Plus. los 3 son Morley.

### 2.2 — «TG-1020»  ·  1 manual(es)  ·  ✅ **YA LO DECIDISTE**

- Ids que se lo disputan: `desico:tg-1020`, `unresolved:tg-1020` (+ el candidate del manual)
- **Aparece en documentos de**: **Notifier** 15 · **Morley** 1 · **Xtralis** 1
- Manuales: `TG-1020-INT`
- ✅ Dijiste «3 OK» → lo entiendo como **`notifier:tg-1020`** (coherente con que los TG sean software de Notifier). La evidencia de arriba lo respalda.

  - [X] confirmado. no obstante, que pertenezca a la familia TG al igual que el TG-GSM.  ·  [ ] te leí mal, era: ______

### 2.3 — «ID-3000»  ·  1 manual(es)

- Ids que se lo disputan: `notifier:id3000`, `unresolved:id3000` (+ el candidate del manual)
- **Aparece en documentos de**: **Notifier** 88 · **Morley** 8 · **Xtralis** 2 · **?** 1
- Manuales: `TG-Honeywell_Usuario_PT`
- ⚠️ **Esto NO es una disputa entre marcas**: `notifier:id3000` y el candidate del manual son **el mismo producto de notifier, escrito distinto** (el guion). Los `unresolved:` no son un bando.
- **Recomendación: redirect `notifier:id-3000` → `notifier:id3000`.** No hay que elegir marca: hay que dejar de tener dos filas para lo mismo. Sigue siendo tuyo por R21.

  - [X] OK al redirect  ·  [ ] otra cosa: ______

### 2.4 — «VSN-CO»  ·  1 manual(es)

- Ids que se lo disputan: `morley:vsn-co`, `notifier:vsn-co` (+ el candidate del manual)
- **Aparece en documentos de**: **Morley** 3
- Manuales: `VSN-CO-Mantenimiento-y-vida-util-del-detecto`
- **Recomendación: canónico en `morley`**, y el otro id a `redirect` con `vendido_bajo` = ambas (R3). El corpus es claro: el token vive en documentos de Morley.

  - [X] fusionar, canónico `Morley`  ·  [ ] son distintos (homónimo)  ·  [ ] otra cosa

## 3 · Resueltos por evidencia — tu «Detnov OK» + el mecanismo nuevo (s338)

**21 manuales.** Dos orígenes, los dos con la evidencia a la vista:

- **tu «Detnov OK»**: el manual cita su **nº de referencia**, que ya es alias del producto y coincide con el nombre del fichero (doble ancla) → cumple R4.
- **s338, tu pushback**: canales independientes. `FICHERO` (R8 protege de INVENTARSE un producto, no impide CONFIRMAR uno que el `doc_map` ya enlaza), `URL_FABRICANTE` (el fabricante publica ese PDF con el modelo en la URL) y `CATALOGO_FABRICANTE` (su catálogo lo lista con descripción impresa). **RESUELTO exige ≥2 canales independientes.**

| # | manual | producto | evidencia | tus notas |
|---|---|---|---|---|
| 1 | `55310008 Manual Tarjeta Modbus TMD-100 Insta` | TMD-100 | FICHERO + CATALOGO_FABRICANTE · [fuente](https://www.detnov.com/wp-content/uploads/2025/05/Catalogo-prodotti-Detnov-2025-TP003-it-2025-d.pdf) |  | Alberto: OK
| 2 | `55310401 Manual Sirenas Convencionales SCD-1` | SCD-100 | FICHERO + URL_FABRICANTE + CATALOGO_FABRICANTE · [fuente](https://www.detnov.com/wp-content/uploads/2019/04/Manual-SCD-100-55310401-MI-635-m-2024-b.pdf) |  | Alberto: Ok
| 3 | `55311003 Manual Sirenas Convencionales SCD-1` | SCD-110, SCD-110 con flash | ref. `55311003` |  | Alberto: Ok
| 4 | `55315012 Manual Tarjeta de bucle TBUD-150 In` | TBUD-150 | FICHERO + URL_FABRICANTE + CATALOGO_FABRICANTE · [fuente](https://www.detnov.com/wp-content/uploads/2019/04/55315012-Manual-Tarjeta-de-bucle-TBUD-150-Instalacion-ES-FR-GB-IT.pdf) |  | Alberto: OK
| 5 | `55320002 Manual Programador PGD-200 ES FR GB` | PGD-200 | FICHERO + URL_FABRICANTE · [fuente](https://www.detnov.com/wp-content/uploads/2019/04/55320002-Manual-Programador-PGD-200-ES-FR-GB-IT.pdf) |  | Alberto: OK
| 6 | `55320011 Manual zocalo con relé Z-200-R` | Z-200-R | FICHERO + CATALOGO_FABRICANTE · [fuente](https://www.detnov.com/wp-content/uploads/2025/05/Catalogo-prodotti-Detnov-2025-TP003-it-2025-d.pdf) |  | Alberto: OK
| 7 | `55320102 Manual Buzzer Analogico PAD-10A ES ` | PAD-10A | FICHERO + CATALOGO_FABRICANTE · [fuente](https://www.detnov.com/wp-content/uploads/2025/05/Catalogo-prodotti-Detnov-2025-TP003-it-2025-d.pdf) |  | Alberto: OK
| 8 | `55320103 Manual Zocalo Conexion ES FR GB IT_` | 55320103 | FICHERO + PDF | Alberto: este es el Z-200 |
| 9 | `55340103 Manual Modulo 1-2 Entradas Tecnicas` | MAD-402 | FICHERO + URL_FABRICANTE + CATALOGO_FABRICANTE · [fuente](https://www.detnov.com/wp-content/uploads/2019/04/Manual-MAD-401-MAD-402-55340103-MI-627-m-2024-b.pdf) | Alberto: Este también sirve para el MAD-401. |
| 10 | `55341101 Manual Modulo 1-2 Reles libre de te` | MAD-412 | FICHERO + URL_FABRICANTE + CATALOGO_FABRICANTE · [fuente](https://www.detnov.com/wp-content/uploads/2019/04/Manual-MAD-411_MAD-412-55341101-MI-629-m-2024-b.pdf) |  | Alberto: este también sirve para el MAD-411 (1 salida de relé - link: https://www.detnov.com/productos/sistema-analogico/modulos-analogicos-y-accesorios/modulo-analogico-de-control-de-1-salida-mad-411/)
| 11 | `55342102 Manual Modulo 1-2 Entradas 1-2 Sali` | MAD-422 | FICHERO + CATALOGO_FABRICANTE · [fuente](https://www.detnov.com/wp-content/uploads/2025/05/Catalogo-prodotti-Detnov-2025-TP003-it-2025-d.pdf) | Alberto: Este también sirve para el MAD-421. |
| 12 | `55343101 Manual Modulo 1-2 Sirenas Convencio` | MAD-432, MAD-432 Módulo 1 Sirena | FICHERO + URL_FABRICANTE + CATALOGO_FABRICANTE · [fuente](https://www.detnov.com/wp-content/uploads/2019/04/55343102-Manual-Modulo-1-2-Sirenas-Convencionales-MAD-432-ES-FR-GB-IT.pdf) | Alberto: este también sirve para el MAD-431 |
| 13 | `55344103 Manual Modulo 1-2 Zonas MAD-442 ES ` | MAD-442 | FICHERO + URL_FABRICANTE + CATALOGO_FABRICANTE · [fuente](https://www.detnov.com/wp-content/uploads/2019/04/55344103-Manual-Modulo-1-2-Zonas-MAD-442-ES-FR-GB-IT.pdf) | Alberto: este también sirve para el MAD-441 |
| 14 | `55346102 Manual Sirena Analogica MAD-461 ES ` | MAD-461 | FICHERO + CATALOGO_FABRICANTE · [fuente](https://www.detnov.com/wp-content/uploads/2025/05/Catalogo-prodotti-Detnov-2025-TP003-it-2025-d.pdf) |  |
| 15 | `55347101 Manual Sirena Analogica MAD-471 ES ` | MAD-471 | ref. `55347101` |  |
| 16 | `55347200 Manual Sirena Analogica MAD-472 ES ` | MAD-472 | FICHERO + CATALOGO_FABRICANTE · [fuente](https://www.detnov.com/wp-content/uploads/2025/05/Catalogo-prodotti-Detnov-2025-TP003-it-2025-d.pdf) | Alberto: este también sirve para el MAD-473. no obstante, ojo que este documento y el de la fila 17 son muy similares, y que además parece haber otro más actual (porque es el que está actualmente disponible en la web: https://www.detnov.com/wp-content/uploads/2019/04/Manual-MAD-472_MAD-473-55347200-MI-634.pdf). deberíamos descargarnos el del link, ingestarlo, y poner superseded los de las filas 16 y 17. |
| 17 | `55347200 Manual Sirena Analogica MAD-472 ES ` | MAD-472 | FICHERO + CATALOGO_FABRICANTE · [fuente](https://www.detnov.com/wp-content/uploads/2025/05/Catalogo-prodotti-Detnov-2025-TP003-it-2025-d.pdf) | Alberto: ver fila 16. |
| 18 | `55349102 Manual Modulo Aislador MAD-491 ES F` | MAD-491 | ref. `55349102` | Alberto: parece MAD-490 y MAD-492 (de hecho, este link parece más actualizado porque es el que está live en la web, así que deberíamos poner el de la fila 18 como superseded y que el del link (https://www.detnov.com/wp-content/uploads/2019/04/Manual-MAD-490-55349102-MI-628-m-2024-b.pdf) sea el actual. |
| 19 | `55350005 Manual Central Monoxido CMD-500 ES ` | CMD-500 | FICHERO + URL_FABRICANTE + CATALOGO_FABRICANTE · [fuente](https://www.detnov.com/wp-content/uploads/2019/04/55350005-Manual-Central-Monoxido-CMD-500-ES-FR-GB-IT.pdf) | Alberto: en realidad, la familia es la CMD-500, pero están la CMD-501, CMD-502, y CMD-503, en función del número de zonas (link de la CMD-503 por ejemplo - https://www.detnov.com/productos/sistema-monoxido/centrales-de-monoxido/central-de-deteccion-de-monoxido-de-carbono-de-3-zonas-cmd-503/). |
| 20 | `55350007 Manual Tarjeta Regulacion Motores T` | 55350007, TRMD-50X | FICHERO + PDF | Alberto: es la familia TRMD-500, que incluyela TRMD-501 y la TRMD-502. |
| 21 | `55350008 Manual Detectores Monoxido DMDX-500` | DMDX-500 | FICHERO + URL_FABRICANTE · [fuente](https://www.detnov.com/wp-content/uploads/2019/04/55350008-Manual-Detectores-Monoxido-DMDX-500-ES-FR-GB-IT.pdf) |  | Alberto: la familia es DMDX-500, pero hay dos modelos: DMD-500 (https://www.detnov.com/productos/sistema-monoxido/detectores-de-monoxido/detector-monoxido-estandard-dmd-500/) y DMDP-500 (https://www.detnov.com/productos/sistema-monoxido/detectores-de-monoxido/detector-monoxido-compacto-dmdp-500/)

- [ ] Adelante con todos  ·  [X] mira los ajustes de Alberto: te he hecho los siguientes ajustes arriba.

### 3.b — Nombres que el FABRICANTE usa y nosotros no tenemos

El canal web no sólo confirma: **descubre**. Tu ejemplo del `S3-T2` era esto — el catálogo los tiene como número de referencia y Fidegas los llama por su nombre. Bautizar un producto es adjudicación tuya (R21), así que sólo se proponen.

| manual | lo que tenemos | como lo llama el fabricante |
|---|---|---|
| `55310007 Manual Tarjeta Expansion TRD-10` | TRD-100, TSD-100 | **CCD-100** | Alberto: son las TSD-100 y TRD-100, que son accesorios para la CCD-100 (TSD-100: https://www.detnov.com/productos/sistema-convencional/accesorios-centrales-convencionales-serie-ccd-100/tarjeta-de-4-salidas-supervisadas-tsd-100/; TRD-100: https://www.detnov.com/productos/sistema-convencional/accesorios-centrales-convencionales-serie-ccd-100/tarjeta-de-4-reles-lt-trd-100/)
| `55310008 Manual Tarjeta Modbus TMD-100 I` | TMD-100 | **TSD100** | Alberto: es la TMD-100
| `55340103 Manual Modulo 1-2 Entradas Tecn` | MAD-402 | **MAD-401** | Alberto: son ambos modelos, solo que el MAD-401 (https://www.detnov.com/productos/sistema-analogico/modulos-analogicos-y-accesorios/modulo-analogico-monitor-de-1-entrada-mad-401/) tiene 1 entrada, y el otro (https://www.detnov.com/productos/sistema-analogico/modulos-analogicos-y-accesorios/modulo-monitor-analogico-de-2-entradas-mad-402/) 2.
| `55341101 Manual Modulo 1-2 Reles libre d` | MAD-412 | **MAD-411** | Alberto: son ambos modelos, solo que MAD-411 (https://www.detnov.com/productos/sistema-analogico/modulos-analogicos-y-accesorios/modulo-analogico-de-control-de-1-salida-mad-411/) tiene 1 salida, y el otro (https://www.detnov.com/productos/sistema-analogico/modulos-analogicos-y-accesorios/modulo-analogico-de-control-de-2-salidas-mad-412/) 2.
| `55345103 Manual Pulsador Analogico MAD-4` | MAD-450 | **MAD-451-I** | Alberto: son ambos modelos, solo que el MAD-450 no tiene aislador (https://www.detnov.com/productos/sistema-analogico/pulsadores-analogicos/pulsador-analogico-mad-450/) y el MAD-451-I sí (https://www.detnov.com/productos/sistema-analogico/pulsadores-analogicos/pulsador-de-alarma-analogico-rearmable-con-aislador-incorporado-mad-451-i/).
| `55350005 Manual Central Monoxido CMD-500` | CMD-500 | **CMD-503** | Alberto: en realidad, la familia es la CMD-500, pero están la CMD-501, CMD-502, y CMD-503, en función del número de zonas (link de la CMD-503 por ejemplo - https://www.detnov.com/productos/sistema-monoxido/centrales-de-monoxido/central-de-deteccion-de-monoxido-de-carbono-de-3-zonas-cmd-503/). (mismo mensaje que te he puesto arriba).
| `Manual-de-Usuario-S3-T2-y-S2-T2` | 00051, 00052 | **S2-T2, S3-T2, S/3-T2** | Alberto: los modelos son S3-T2 y S2-T2. Ojo que igual en algún otro sitio lo tenemos como "S/3-T2" (mismo modelo que S3-T2) y "S/2-T2" (mismo modelo que S2-T2).

> Aviso honesto: junto a los hallazgos reales cuela algún vecino de contexto — `CCD-100` es la serie de central donde se enchufa el TRD-100, no el producto de ese manual. Por eso no se aplican solos.

- [ ] añade los que marque  ·  [ ] ninguno  ·  [X] otra cosa: Alberto: te he dejado comentarios por cada uno.

## 4 · Fusiones Morley ↔ Notifier — cada una desbloquea los DOS lados

El mismo canónico existe **en cuarentena en dos marcas**, y cada lado tiene manual huérfano. Elegir uno solo deja el otro perdido; **fusionar los desbloquea a la vez**.

### 4.1 — «NFS8REL» en ['morley', 'notifier']  ·  **2 manual(es)**

- Manuales: `MADT015_02`, `MIE-MA-100_02`
- **Recomendación: fusionar** — un id canónico, el otro `redirect`, `vendido_bajo` = ambas (R3). Es el mismo aparato con dos etiquetas comerciales.

  - [X] fusionar, canónico `Notifer`, pero es el mismo producto vendido bajo Notifier y Morley.  ·  [ ] son distintos  ·  [ ] otra cosa

### 4.2 — «MCX-55M» en ['morley', 'notifier']  ·  **2 manual(es)**

- Manuales: `MIE-MI-480`, `MNDT1005`
- **Recomendación: fusionar** — un id canónico, el otro `redirect`, `vendido_bajo` = ambas (R3). Es el mismo aparato con dos etiquetas comerciales.

  - [X] fusionar, canónico `Notifier`, pero es el mismo producto vendido bajo Notifier y Morley   ·  [ ] son distintos  ·  [ ] otra cosa

### 4.3 — «MMX-10M» en ['morley', 'notifier']  ·  **2 manual(es)**

- Manuales: `MIE-MI-490`, `MNDT1006`
- **Recomendación: fusionar** — un id canónico, el otro `redirect`, `vendido_bajo` = ambas (R3). Es el mismo aparato con dos etiquetas comerciales.

  - [X] fusionar, canónico `Notifier`, pero es el mismo producto vendido bajo Notifier y Morley  ·  [ ] son distintos  ·  [ ] otra cosa

### 4.4 — «APIC» en ['aritech', 'notifier']  ·  **1 manual(es)**

- Manuales: `04-4001-501-1700-06_r006_aritech_apic_instal`
- **Recomendación: fusionar** — un id canónico, el otro `redirect`, `vendido_bajo` = ambas (R3). Es el mismo aparato con dos etiquetas comerciales.

  - [ ] fusionar, canónico `______`  ·  [ ] son distintos  ·  [X] otra cosa. Alberto: la realidad es que parecen el mismo producto pero al ser vendidos por fabricantes que no pertenecen al mismo grupo prefiero tratarlos como productos que se llaman igual pero que son de distinto fabricante, por lo que entiendo que si un técnico pregunta por ello debería clarificar el bot.

## 5 · Gemelos por alias — el nombre YA es alias de un producto vivo

Su canónico ya existe como **alias** de un producto consumible: son filas duplicadas, no productos nuevos. (Este caso me lo cazó el gate cuando intenté promoverlos.)

### 5.1 — `notifier:notifier-inspire-e10` «Notifier INSPIRE E10» → alias de ['notifier:inspire-e10']  ·  2 manual(es)

- Manuales: `HOP-338-9ES issue 4_01-2026_Op`, `HOP-338-9PT-issue 4_01-2026_Op`
- **Recomendación: redirect `notifier:notifier-inspire-e10` → `notifier:inspire-e10`.**

  - [] OK  ·  [X] otra cosa: aquí lo llamaría directamente `notifier:inspire-e10`, para evitar tener los dos nombres en la BD via redirect.

### 5.2 — `unresolved:tg-honeywell` «TG-HONEYWELL» → alias de ['notifier:tg']  ·  1 manual(es)

- Manuales: `LEER PRIMERO_MADT951_10`
- **Recomendación: redirect `unresolved:tg-honeywell` → `notifier:tg`.**

  - [] OK  ·  [X] otra cosa: Como es el software de Notifier y Morley, no se si tiene sentido que el canónico sea Notifier pero que también sea "findable" bajo Morley, entiendo que con la mecánica del "redirect" que decías en 4.2, 4.3, etc.

## 6 · Candidates que mi filtro paró — uno a uno, porque cada uno es distinto

Tienen marca y cita, pero **R19 (producto-hood)** los frenó: el token está en el texto y eso no lo hace producto. Te digo qué frenó a cada uno y qué propongo.

### 6.1 — `notifier:am-lcd` «AM-LCD»  ·  1 manual(es)

- Manuales: `AM-LCD manual de instalacion y usuario RV 0`
- **Qué lo frenó**: lo saqué del lote yo: su core casa «Pantalla **FM/AM LCD**» de un manual de radio (1 falso positivo real de 6 documentos).
- **Recomendación**: propongo promoverlo **y** meter el falso positivo en `DETECT_STOPWORDS`, que es el mecanismo que ya existe para esto.

  - [ ] adelante  ·  [ ] déjalo  ·  [X] otra cosa: la verdad que esto es un producto en sí "AM-LCD", como puedes ver en la portada del manuual que me has indicado (y en el siguiente link aparece como producto - https://www.notifier.es/index.php/producto/category/am-lcd).

### 6.2 — `notifier:eev2` «EEV(2)»  ·  1 manual(es)

- Manuales: `MADT608`
- **Qué lo frenó**: el canónico es `EEV(2)` y **los paréntesis no los ve el detector**.
- **Recomendación**: necesita un canónico sin paréntesis (¿`EEV2`?) o se queda inalcanzable.

  - [ ] adelante  ·  [ ] déjalo  ·  [X] otra cosa: no es un producto, sino una "TABLA DE APROXIMACIONES A GAS PATRÓN".

### 6.3 — `notifier:nas` «NAS»  ·  3 manual(es)

- Manuales: `MNDT740P`, `MNDT741`, `MNDT741I`
- **Qué lo frenó**: sigla de 3 letras sin dígitos. Precedente DEC-272: `NAS` llegó a arrastrar 231 documentos.
- **Recomendación**: ¿es NAS un producto con nombre propio, o una sigla genérica? Si es producto, dime su nombre completo y lo uso de canónico.

  - [ ] adelante  ·  [ ] déjalo  ·  [X] otra cosa: para empezar, el manual "MNDT740P" es portugués, así que deberíamos sacarlo. el modelo existe, es el Notifier Air Sample (equipo de muestreo de aire) - lo puedes ver en la portada del segundo documento, así que diría `notifier:nas`. el tercer documento (MNDT741I), es la versión inglesa, así que si los documentos 2 y 3 son iguales, y solo cambia el idioma, quitaría el de "MNDT741I".

### 6.4 — `notifier:rhistorico.exe` «RHistorico.exe»  ·  1 manual(es)

- Manuales: `MADT951_04`
- **Qué lo frenó**: es el **ejecutable**, no el software. R10 dice que el software SÍ es producto: el canónico debería ser el nombre del programa.
- **Recomendación**: propongo canónico «Utilidad de Reparación de Históricos» y `RHistorico.exe` como alias.

  - [ ] adelante  ·  [ ] déjalo  ·  [X] otra cosa: es un ejecutable que pertenece al software TG, así que OK a tu recomendación.

### 6.5 — `notifier:serie-800` «Serie 800»  ·  1 manual(es)

- Manuales: `MNDT020`
- **Qué lo frenó**: «Serie 800» es una **familia**, no un modelo.
- **Recomendación**: propongo tratarlo como paraguas (`umbrellas`), no como producto.

  - [ ] adelante  ·  [X] déjalo. Alberto: déjalo como Serie-800  ·  [ ] otra cosa: ______

## 7 · `unresolved:` sin gemelo — ¿promover tal cual?

**5 ids**, 10 manuales. No existe ese canónico en ninguna marca, así que no hay redirect posible.

- **Recomendación: promoverlos tal cual, sin asignar marca.** El detector **no usa el namespace** para nada, así que asignarla es trabajo de adjudicación que no cambia lo que el bot hace. Si luego aparece el fabricante, se añade sin tocar el id (son inmutables).

  - [ ] OK a promover sin marca  ·  [X] prefiero asignar marca uno a uno

| id | canónico | manuales | nota |
|---|---|---|---|
| `unresolved:tg-ip-1-sec` | TG-IP-1-SEC | 4 | **software (R10)** · la familia `TG-IP-*` ya existe en `notifier:` (`tg-ip-1`, `tg-ip-10`, `tg-ip-100`), así que aquí sí hay marca natural |
| `unresolved:itac` | ITAC | 3 |  |
| `unresolved:trd-100` | TRD-100 | 1 |  |
| `unresolved:indicator` | INDICATOR | 1 |  |
| `unresolved:vision-plus` | VISION PLUS | 1 |  |

## 8 · El suelo — esto NO baja, y no es cola pendiente

**13 manuales.** Los dejo listados para que se vea que están medidos, no olvidados.

| manual | por qué |
|---|---|
| `55310600 Manual TCD-106 kit_ES` | el manual no nombra su producto (ni por referencia) | Alberto: producto TCD-106 de Detnov. para que aprendas para la próxima vez, viene el nombre del modelo en el nombre del documento, y sigue la nomenclatura típica de Detnov.
| `55312000 SCD-120_Manual_ES` | PDF escaneado; leído con Claude, la página no nombra el modelo | Alberto: el pdf está girado y por eso igual no lo has leído. el modelo es el SCD-120 (que aparece en el nombre del documento), y es una Sirena Exterior de Incendios de 24V.
| `55393002 Manual Fuentes de Alimentacion FAD-905 ES F` | el manual no nombra su producto (ni por referencia) | Alberto: modelo FAD-905 (Detnov), que está en el nombre del documento. Es una fuente de alimentación de 24V.
| `D 1100-4 Sounder` | el manual no nombra su producto (ni por referencia) | Alberto: el fabricante es KAC alarm (que creo que tenemos algún producto más de ellos), y los modelos son "CWSO-xx-S1", "CWSO-xx-S2", "CWSO-xx-W1", y "CWSO-xx-W2", donde la XX "Indica el color de la sirena y del flash"
| `F3000M_Spanish User Guide_0044-047-02-ES` | el manual no nombra su producto (ni por referencia) | Alberto: el modelo es el F3000M de Notifier, que es un "detector de humo de haz óptico".
| `F5K-2H-UserGuide-SPANISH_Manual F5000` | el manual no nombra su producto (ni por referencia) | Alberto: es el modelo F5000 de Morley, que es un "Detector de humos con haz óptico infrarrojo motorizado". también se denomina al producto como "F5K"
| `F5K-Additional-Information-Spanish` | el manual no nombra su producto (ni por referencia) | Alberto: es el modelo F5000 de Morley.
| `FS2-1` | el manual no nombra su producto (ni por referencia) | Alberto: en realidad es la familia "FS" de Notifier, que son centrales antiguas conencionales de 1, 2, y 4 zonas.
| `MADT190_10` | el canónico es sólo dígitos — el detector los excluye a propósito | Alberto: es un rack de Notifier para el montaje de centrales i.e. accesorios. son los siguientes racks: 020-596, 020-606, 020-590, 020-591, 020-593, 020-592, 020-598, 020-594, 020-595, 
| `MNDT021` | el manual no nombra su producto (ni por referencia) |
| `MNDT635` | el manual no nombra su producto (ni por referencia) | Alberto: modelo LISA 2, de Notifier. son "DETECTORES INFRARROJOS PARA GAS". aquí puedes ver el link con un documento sobre su esquema de conexión (doc: MADT635_01, link: https://www.notifier.es/index.php/productos/sistemas-analogicos/item/anexo-manual-esquema-de-conexion-del-detector-lisa-2)
| `Manual-de-Usuario-S3-T2-y-S2-T2` | el canónico es sólo dígitos — el detector los excluye a propósito — **pero 3.b propone un nombre del fabricante**: si lo apruebas, sale del suelo | Alberto: esto ya lo hemos comentado. Son los modelos "S/3-T2" (o S3-T2, es lo mismo) y el "S/2-T2" (o S2-T2, es lo mismo).
| `S3466R_Eng_ital` | PDF escaneado; leído con Claude, la página no nombra el modelo | Albreto: retira este manual del corpus.

---

## Y una pregunta que sale de lo que me dijiste

Si los **TG son software de Notifier**, ¿qué hace `desico:tg-1020` como producto consumible de Desico? O es una atribución equivocada (y entonces sobra), o Desico tiene su propio TG-1020 (y entonces es un **homónimo** y hay que declararlo como tal, no dejar dos dueños del mismo token).

- [ ] es atribución equivocada, quita `desico:tg-1020`  ·  [ ] son distintos, decláralo homónimo  ·  [ ] déjalo como está

