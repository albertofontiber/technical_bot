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

  - [ ] OK  ·  [ ] otra cosa: ______

### 1.2 — `unresolved:tg` → `notifier:tg`  ·  **2 manual(es)** · **software (R10)**

- **Recomendación: SÍ.** Mismo canónico «TG»; el destino ya es consumible, así que el redirect no crea nada nuevo — sólo deja de perder los manuales.
- Manuales: `Como-configurar-correos-en-un-TG-HONEYWELL`, `TG-Como-exportar-el-historico-desde-el-progr`

  - [ ] OK  ·  [ ] otra cosa: ______

### 1.3 — `unresolved:mad-450` → `detnov:mad-450`  ·  **1 manual(es)**

- **Recomendación: SÍ.** Mismo canónico «MAD-450»; el destino ya es consumible, así que el redirect no crea nada nuevo — sólo deja de perder los manuales.
- Manuales: `55345103 Manual Pulsador Analogico MAD-450 E`

  - [ ] OK  ·  [ ] otra cosa: ______

### 1.4 — `unresolved:id60` → `notifier:id-60`  ·  **1 manual(es)**

- **Recomendación: SÍ.** Mismo canónico «ID60»; el destino ya es consumible, así que el redirect no crea nada nuevo — sólo deja de perder los manuales.
- Manuales: `MADT155_02`

  - [ ] OK  ·  [ ] otra cosa: ______

### 1.5 — `unresolved:tg-gsm` → `notifier:tg-gsm`  ·  **1 manual(es)** · **software (R10)**

- **Recomendación: SÍ.** Mismo canónico «TG-GSM»; el destino ya es consumible, así que el redirect no crea nada nuevo — sólo deja de perder los manuales.
- Manuales: `TG-GSM-Fallo-al-enviar-SMS-desde-TG`

  - [ ] OK  ·  [ ] otra cosa: ______

## 2 · Ambiguos — el token lo disputan dos ids

No te doy «mi lectura»: te doy **en cuántos documentos de cada marca aparece el token**, que es el único discriminador que no me invento.

### 2.1 — «VSN12-2Plus»  ·  1 manual(es)  ·  ✅ **YA LO DECIDISTE**

- Ids que se lo disputan: `morley:vsn12-2plus`, `notifier:vsn12-2plus` (+ el candidate del manual)
- **Aparece en documentos de**: **Morley** 2 · **Notifier** 1
- Manuales: `HLSI-MN-025-I_NFS Supra Series v05`
- ✅ Dijiste «1 OK» → lo entiendo como **`morley:vsn12-2plus`** (el manual es de la serie NFS Supra de Morley). La evidencia de arriba lo respalda.

  - [ ] confirmado  ·  [ ] te leí mal, era: ______

### 2.2 — «TG-1020»  ·  1 manual(es)  ·  ✅ **YA LO DECIDISTE**

- Ids que se lo disputan: `desico:tg-1020`, `unresolved:tg-1020` (+ el candidate del manual)
- **Aparece en documentos de**: **Notifier** 15 · **Morley** 1 · **Xtralis** 1
- Manuales: `TG-1020-INT`
- ✅ Dijiste «3 OK» → lo entiendo como **`notifier:tg-1020`** (coherente con que los TG sean software de Notifier). La evidencia de arriba lo respalda.

  - [ ] confirmado  ·  [ ] te leí mal, era: ______

### 2.3 — «ID-3000»  ·  1 manual(es)

- Ids que se lo disputan: `notifier:id3000`, `unresolved:id3000` (+ el candidate del manual)
- **Aparece en documentos de**: **Notifier** 88 · **Morley** 8 · **Xtralis** 2 · **?** 1
- Manuales: `TG-Honeywell_Usuario_PT`
- ⚠️ **Esto NO es una disputa entre marcas**: `notifier:id3000` y el candidate del manual son **el mismo producto de notifier, escrito distinto** (el guion). Los `unresolved:` no son un bando.
- **Recomendación: redirect `notifier:id-3000` → `notifier:id3000`.** No hay que elegir marca: hay que dejar de tener dos filas para lo mismo. Sigue siendo tuyo por R21.

  - [ ] OK al redirect  ·  [ ] otra cosa: ______

### 2.4 — «VSN-CO»  ·  1 manual(es)

- Ids que se lo disputan: `morley:vsn-co`, `notifier:vsn-co` (+ el candidate del manual)
- **Aparece en documentos de**: **Morley** 3
- Manuales: `VSN-CO-Mantenimiento-y-vida-util-del-detecto`
- **Recomendación: canónico en `morley`**, y el otro id a `redirect` con `vendido_bajo` = ambas (R3). El corpus es claro: el token vive en documentos de Morley.

  - [ ] fusionar, canónico `______`  ·  [ ] son distintos (homónimo)  ·  [ ] otra cosa

## 3 · Detnov — desbloqueado por tu «OK», para que lo repases de un vistazo

**14 manuales.** Cada uno cita su **nº de referencia** en el texto del PDF, y esa referencia **ya es alias** del producto en el catálogo y **coincide con el nombre del fichero** (doble ancla). Con tu OK, la cita cumple R4.

| # | manual | producto | referencia citada |
|---|---|---|---|
| 1 | `55310008 Manual Tarjeta Modbus TMD-100 Instala` | TMD-100 | `55310008` |
| 2 | `55311003 Manual Sirenas Convencionales SCD-110` | SCD-110, SCD-110 con flash | `55311003` |
| 3 | `55315012 Manual Tarjeta de bucle TBUD-150 Inst` | TBUD-150 | `55315012` |
| 4 | `55320011 Manual zocalo con relé Z-200-R` | Z-200-R | `55320011` |
| 5 | `55320102 Manual Buzzer Analogico PAD-10A ES FR` | PAD-10A | `55320102` |
| 6 | `55340103 Manual Modulo 1-2 Entradas Tecnicas M` | MAD-402 | `55340103` |
| 7 | `55341101 Manual Modulo 1-2 Reles libre de tens` | MAD-412 | `55341101` |
| 8 | `55342102 Manual Modulo 1-2 Entradas 1-2 Salida` | MAD-422 | `55342102` |
| 9 | `55343101 Manual Modulo 1-2 Sirenas Convenciona` | MAD-432, MAD-432 Módulo 1 Sirena | `55343101` |
| 10 | `55346102 Manual Sirena Analogica MAD-461 ES FR` | MAD-461 | `55346102` |
| 11 | `55347101 Manual Sirena Analogica MAD-471 ES FR` | MAD-471 | `55347101` |
| 12 | `55347200 Manual Sirena Analogica MAD-472 ES GB` | MAD-472 | `55347200` |
| 13 | `55349102 Manual Modulo Aislador MAD-491 ES FR ` | MAD-491 | `55349102` |
| 14 | `55350008 Manual Detectores Monoxido DMDX-500 E` | DMDX-500 | `55350008` |

- [ ] Adelante con todos  ·  [ ] quita los que marque arriba

## 4 · Fusiones Morley ↔ Notifier — cada una desbloquea los DOS lados

El mismo canónico existe **en cuarentena en dos marcas**, y cada lado tiene manual huérfano. Elegir uno solo deja el otro perdido; **fusionar los desbloquea a la vez**.

### 4.1 — «NFS8REL» en ['morley', 'notifier']  ·  **2 manual(es)**

- Manuales: `MADT015_02`, `MIE-MA-100_02`
- **Recomendación: fusionar** — un id canónico, el otro `redirect`, `vendido_bajo` = ambas (R3). Es el mismo aparato con dos etiquetas comerciales.

  - [ ] fusionar, canónico `______`  ·  [ ] son distintos  ·  [ ] otra cosa

### 4.2 — «MCX-55M» en ['morley', 'notifier']  ·  **2 manual(es)**

- Manuales: `MIE-MI-480`, `MNDT1005`
- **Recomendación: fusionar** — un id canónico, el otro `redirect`, `vendido_bajo` = ambas (R3). Es el mismo aparato con dos etiquetas comerciales.

  - [ ] fusionar, canónico `______`  ·  [ ] son distintos  ·  [ ] otra cosa

### 4.3 — «MMX-10M» en ['morley', 'notifier']  ·  **2 manual(es)**

- Manuales: `MIE-MI-490`, `MNDT1006`
- **Recomendación: fusionar** — un id canónico, el otro `redirect`, `vendido_bajo` = ambas (R3). Es el mismo aparato con dos etiquetas comerciales.

  - [ ] fusionar, canónico `______`  ·  [ ] son distintos  ·  [ ] otra cosa

### 4.4 — «APIC» en ['aritech', 'notifier']  ·  **1 manual(es)**

- Manuales: `04-4001-501-1700-06_r006_aritech_apic_instal`
- **Recomendación: fusionar** — un id canónico, el otro `redirect`, `vendido_bajo` = ambas (R3). Es el mismo aparato con dos etiquetas comerciales.

  - [ ] fusionar, canónico `______`  ·  [ ] son distintos  ·  [ ] otra cosa

## 5 · Gemelos por alias — el nombre YA es alias de un producto vivo

Su canónico ya existe como **alias** de un producto consumible: son filas duplicadas, no productos nuevos. (Este caso me lo cazó el gate cuando intenté promoverlos.)

### 5.1 — `notifier:notifier-inspire-e10` «Notifier INSPIRE E10» → alias de ['notifier:inspire-e10']  ·  2 manual(es)

- Manuales: `HOP-338-9ES issue 4_01-2026_Op`, `HOP-338-9PT-issue 4_01-2026_Op`
- **Recomendación: redirect `notifier:notifier-inspire-e10` → `notifier:inspire-e10`.**

  - [ ] OK  ·  [ ] otra cosa: ______

### 5.2 — `unresolved:tg-honeywell` «TG-HONEYWELL» → alias de ['notifier:tg']  ·  1 manual(es)

- Manuales: `LEER PRIMERO_MADT951_10`
- **Recomendación: redirect `unresolved:tg-honeywell` → `notifier:tg`.**

  - [ ] OK  ·  [ ] otra cosa: ______

## 6 · Candidates que mi filtro paró — uno a uno, porque cada uno es distinto

Tienen marca y cita, pero **R19 (producto-hood)** los frenó: el token está en el texto y eso no lo hace producto. Te digo qué frenó a cada uno y qué propongo.

### 6.1 — `notifier:am-lcd` «AM-LCD»  ·  1 manual(es)

- Manuales: `AM-LCD manual de instalacion y usuario RV 0`
- **Qué lo frenó**: lo saqué del lote yo: su core casa «Pantalla **FM/AM LCD**» de un manual de radio (1 falso positivo real de 6 documentos).
- **Recomendación**: propongo promoverlo **y** meter el falso positivo en `DETECT_STOPWORDS`, que es el mecanismo que ya existe para esto.

  - [ ] adelante  ·  [ ] déjalo  ·  [ ] otra cosa: ______

### 6.2 — `notifier:eev2` «EEV(2)»  ·  1 manual(es)

- Manuales: `MADT608`
- **Qué lo frenó**: el canónico es `EEV(2)` y **los paréntesis no los ve el detector**.
- **Recomendación**: necesita un canónico sin paréntesis (¿`EEV2`?) o se queda inalcanzable.

  - [ ] adelante  ·  [ ] déjalo  ·  [ ] otra cosa: ______

### 6.3 — `notifier:nas` «NAS»  ·  3 manual(es)

- Manuales: `MNDT740P`, `MNDT741`, `MNDT741I`
- **Qué lo frenó**: sigla de 3 letras sin dígitos. Precedente DEC-272: `NAS` llegó a arrastrar 231 documentos.
- **Recomendación**: ¿es NAS un producto con nombre propio, o una sigla genérica? Si es producto, dime su nombre completo y lo uso de canónico.

  - [ ] adelante  ·  [ ] déjalo  ·  [ ] otra cosa: ______

### 6.4 — `notifier:rhistorico.exe` «RHistorico.exe»  ·  1 manual(es)

- Manuales: `MADT951_04`
- **Qué lo frenó**: es el **ejecutable**, no el software. R10 dice que el software SÍ es producto: el canónico debería ser el nombre del programa.
- **Recomendación**: propongo canónico «Utilidad de Reparación de Históricos» y `RHistorico.exe` como alias.

  - [ ] adelante  ·  [ ] déjalo  ·  [ ] otra cosa: ______

### 6.5 — `notifier:serie-800` «Serie 800»  ·  1 manual(es)

- Manuales: `MNDT020`
- **Qué lo frenó**: «Serie 800» es una **familia**, no un modelo.
- **Recomendación**: propongo tratarlo como paraguas (`umbrellas`), no como producto.

  - [ ] adelante  ·  [ ] déjalo  ·  [ ] otra cosa: ______

## 7 · `unresolved:` sin gemelo — ¿promover tal cual?

**5 ids**, 10 manuales. No existe ese canónico en ninguna marca, así que no hay redirect posible.

- **Recomendación: promoverlos tal cual, sin asignar marca.** El detector **no usa el namespace** para nada, así que asignarla es trabajo de adjudicación que no cambia lo que el bot hace. Si luego aparece el fabricante, se añade sin tocar el id (son inmutables).

  - [ ] OK a promover sin marca  ·  [ ] prefiero asignar marca uno a uno

| id | canónico | manuales | nota |
|---|---|---|---|
| `unresolved:tg-ip-1-sec` | TG-IP-1-SEC | 4 | **software (R10)** · la familia `TG-IP-*` ya existe en `notifier:` (`tg-ip-1`, `tg-ip-10`, `tg-ip-100`), así que aquí sí hay marca natural |
| `unresolved:itac` | ITAC | 3 |  |
| `unresolved:trd-100` | TRD-100 | 1 |  |
| `unresolved:indicator` | INDICATOR | 1 |  |
| `unresolved:vision-plus` | VISION PLUS | 1 |  |

## 8 · El suelo — esto NO baja, y no es cola pendiente

**20 manuales.** Los dejo listados para que se vea que están medidos, no olvidados.

| manual | por qué |
|---|---|
| `55310401 Manual Sirenas Convencionales SCD-100 ES FR` | el manual no nombra su producto (ni por referencia) |
| `55310600 Manual TCD-106 kit_ES` | el manual no nombra su producto (ni por referencia) |
| `55312000 SCD-120_Manual_ES` | PDF escaneado; leído con Claude, la página no nombra el modelo |
| `55320002 Manual Programador PGD-200 ES FR GB IT` | el manual no nombra su producto (ni por referencia) |
| `55320103 Manual Zocalo Conexion ES FR GB IT_V2` | el canónico es sólo dígitos — el detector los excluye a propósito |
| `55344103 Manual Modulo 1-2 Zonas MAD-442 ES FR GB IT` | el manual no nombra su producto (ni por referencia) |
| `55347200 Manual Sirena Analogica MAD-472 ES GB FR GB` | no hay PDF en Storage |
| `55350005 Manual Central Monoxido CMD-500 ES FR GB IT` | el manual no nombra su producto (ni por referencia) |
| `55350007 Manual Tarjeta Regulacion Motores TRMD-50X ` | el canónico es sólo dígitos — el detector los excluye a propósito |
| `55393002 Manual Fuentes de Alimentacion FAD-905 ES F` | el manual no nombra su producto (ni por referencia) |
| `D 1100-4 Sounder` | el manual no nombra su producto (ni por referencia) |
| `F3000M_Spanish User Guide_0044-047-02-ES` | el manual no nombra su producto (ni por referencia) |
| `F5K-2H-UserGuide-SPANISH_Manual F5000` | el manual no nombra su producto (ni por referencia) |
| `F5K-Additional-Information-Spanish` | el manual no nombra su producto (ni por referencia) |
| `FS2-1` | el manual no nombra su producto (ni por referencia) |
| `MADT190_10` | el canónico es sólo dígitos — el detector los excluye a propósito |
| `MNDT021` | el manual no nombra su producto (ni por referencia) |
| `MNDT635` | el manual no nombra su producto (ni por referencia) |
| `Manual-de-Usuario-S3-T2-y-S2-T2` | el canónico es sólo dígitos — el detector los excluye a propósito |
| `S3466R_Eng_ital` | PDF escaneado; leído con Claude, la página no nombra el modelo |

---

## Y una pregunta que sale de lo que me dijiste

Si los **TG son software de Notifier**, ¿qué hace `desico:tg-1020` como producto consumible de Desico? O es una atribución equivocada (y entonces sobra), o Desico tiene su propio TG-1020 (y entonces es un **homónimo** y hay que declararlo como tal, no dejar dos dueños del mismo token).

- [ ] es atribución equivocada, quita `desico:tg-1020`  ·  [ ] son distintos, decláralo homónimo  ·  [ ] déjalo como está

