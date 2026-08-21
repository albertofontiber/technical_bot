# s331 — LOTE §1.A + §1.B: las anotaciones de Alberto, verificadas — propuesta para el dúo

**Origen**: Alberto repasó el packet E1 en local y subió su copia con **30 anotaciones nuevas**
(11 en §1.A, 19 en §1.B). Encargo: «Revísalo en este lote». **NADA aplicado todavía.**

## Lo verificado antes de proponer (todo con dato, no con memoria)

### §1.A — 11 anotaciones

| Su nota | Verificación | Acción |
|---|---|---|
| `996-130` «baja del corpus» | ya `retired` en s331 | — |
| `hlsi-ti-007` «lo veo OK» · `ke_io3144` «OK» · `mie-mi-120p` «OK» · `miemu520p` «OK» | estado real coincide | — |
| `asd harsh` «solo System Sensor, no Xtralis» | el doc cierra «© 2015 **System Sensor**», 22 menciones de FAAST, **0** de Xtralis/VESDA. Su ficha dice `manufacturer=Xtralis`. Los 13 ids atestados ya son todos FAAST | **retag de ficha** |
| `zx-y-dx` «incluir ZXA y ZXE — ¿existen?» | **ZXAE/ZXEE**: prueba directa en la tabla TG «TG-ZXA \| PROGRAMA GRAFICO **ZXAE**». Corpus: ZXAE 197 menciones/12 docs, ZXEE 224/13; «ZX-A»/«ZX-E» 1 vez cada una y solo en esta FAQ. **No están en su doc_map** | **+2 entries** |
| `zx-y-dx` «¿de dónde sacas ZXce, ZXhe, ZX50?» | tiene razón: **no se aplicaron**; son la línea `juez:` que R1 descartó. Defecto de presentación del packet | — (nota) |
| `finales-de-linea` «¿no veo la vsn-4-plus?» | **sí está** (iba en el «+2»): 8 ids con `vsn-4-plus`, `-8-plus`, `-12-plus` | — |
| `gr_kidde_2x_at` «¿lo tenemos en ESP?» | **sí**, dos docs ES de la serie táctil (11 ids cada uno) | — |
| `mi_kidde_2x_at_f2_fb` «parece ir sobre los no táctiles» | **confirmado**: 0 tokens `2X-AT` frente a 183 de la serie `2X-A`. Lo aplicado ya son 26 no-táctiles | — |
| `mu_kidde_2x_at_fr_fb_s` «el 2x-af2 no está, el -s sí» | ambos **sí** están, en texto y en doc_map (0 táctiles / 65 no-táctiles) | — |
| `ke_dp312x` «KE-DP3121B y W no están en catálogo» | los dos **sí** están. En este doc, `KE-DP3121W` sale 8 veces y está mapeado; `KE-DP3121B` a secas **no aparece** (sale `-SNV`), por eso no está | — |

### §1.B — 19 anotaciones

**Sus «OK con juez» sobre lo que R7 ya resolvió — verificado que existen, sin acción**:
`fidegas:s2-t1`+`s3-t1` · `kidde:ke-dba-adpw-kil`+`-zit` · `ke-dp3121b`+`-snv` · `ke-dp3121w`+`-sn`+`-snv` ·
`ke-iu3111-zme` · `n-io-mbx-1`+`-2` · `n-io-sbx-1g`+`-2g`.

**Sus preguntas, contestadas**: R7 partió los concatenados y **creó ambos componentes** en los tres
casos que pregunta (`n-io-mbx`, `n-io-sbx`); el `DS` nombra solo el `-1` porque es su ficha y el `MI`
cubre la serie — coherente. En `ZLSM-ME/MR` R7 **no dio de alta** (son artefactos: 0 menciones), y el
producto real del documento es **`9-30520`**, «Carcasa de expansión MiniLaser».

**Altas que sus notas firman** (todas con cita de portada verificada full-text):

| id propuesto | canónico | cita | doc |
|---|---|---|---|
| `kidde:ke-dba-labw-s` | KE-DBA-LABW-S | «# **KE-DBA-LABW-S** Accesorio detector inteligente direccionable - etiqueta en blanco (pequeña)» | hd ke dba labw lxs es |
| `notifier:conv232-485` | CONV232/485 | «Convertidor RS232 a RS485/422 para TG a centrales ID3000 - punto a punto. **Ref.: CONV232/485**» | TIDT110 |
| `kidde:9-30520` | 9-30520 | «# **9-30520** ## Carcasa de expansión MiniLaser» | ds kidde zlsm me es (+ MI en inglés) |
| `avotec:doa-fj-cpd` | DOA FJ/CPD | «**DOA FJ/CPD** – Fire alarm sounding device for fire signalling conform to regulation EN54-3» | Manual Rotulo REXD-103_EN |

**Baja de corpus**: `MNDT730P` — fragmento PT de 1 chunk («# Controlos e Indicadores») con hermano ES
completo (`MNDT730`, 6 chunks). Misma clase que los PT retirados en s324.

## Las DOS divergencias con sus notas (declaradas, no silenciadas)

1. **«marca DOA, producto FJ/CPD»** → propongo `avotec:doa-fj-cpd`, **no** crear una marca `doa:`.
   Evidencia en contra de la marca: el documento es «® AVOTEC» dos veces, «MADE IN ITALY», copyright
   «AVOTEC Srl»; el fabricante registrado es Avotec (2 docs en el corpus); y **«DOA» no aparece
   suelta ni una sola vez en todo el corpus** — sus 2 únicas menciones son «DOA FJ/CPD», una de ellas
   dentro de «CERTIFICATION DOA FJ/CPD 12 0051-CPD-0384», que es un número de certificado CE (el
   `/CPD` apunta a *Construction Products Directive*, no a un producto). Crear un namespace de marca
   nuevo con esa base es frágil y el contrato manda namespace = marca del fabricante. Su intención
   queda capturada en el canónico verbatim. **Si Alberto confirma que DOA es una línea comercial de
   Avotec, se rehace como merge — los ids son inmutables, así que conviene acertar ahora.**
2. **`STRATOS HSSD` «modelo que propone el juez»** → propongo **NO crear el producto** y mapear
   `MNDT730` a los 3 miembros del paraguas STRATOS por R1. Motivo: el paraguas `STRATOS` ya existe
   (s324b, 3 ids) y el documento es una **miniguía de familia** que dice literalmente «El equipamiento
   puede variar según el modelo» — no es un modelo. Además, en s324b se retiraron **2 alias erróneos
   de esa misma grafía** (`Stratos-HSSD`→SenseNET y →MiniLáser25): crear ahora un producto con ese
   nombre reintroduce la confusión que aquel lote limpió.

## Lo que NO entra (él lo dice, o falta su decisión)

`morley:efs-em-8` («pending.») · `notifier:nx2-r-r-y-nx5-r-r` (anotación vacía) · los candidates SMART
de E1b · el paraguas 2X-A.

## Mecanismo nuevo que hace falta

El retag de `manufacturer` **no lo soporta el writer** (`retags_db` es solo `product_model`). Propongo
un script hermano acotado, `s331_retag_manufacturer.py`, con dry-run, backup por fila y recibo
reversible — mismo patrón que `s324_retirar_docs.py`. **Verificado que el campo NO es cosmético**:
`_diversify_by_manufacturer` (retriever.py:2207) reparte resultados por marca, y
`get_available_manufacturers`/`get_manufacturers_by_docs` alimentan lo que el bot enseña. También
verificado que **«System Sensor» ya existe** (30 documentos activos) y «Xtralis» tiene 28: el retag
mueve 1 documento entre dos marcas existentes, sin inventar ninguna.

## Gaps declarados de entrada

1. `9-30520` es un **número de parte**, no un nombre comercial. Hay precedente en catálogo
   (`spectrex:777163`, `380114-2`, `model-787640`), pero es un token numérico: **el riesgo léxico lo
   decide el gate**, y si el censo lo marca, se cae del lote.
2. El alta de `avotec:doa-fj-cpd` descansa en **2 menciones en 1 documento**, la cita más floja del
   lote.
3. `CONV232/485` aparece como **`Ref.:`** (referencia comercial), no como título de producto — es el
   rol `REFERENCIA_COMERCIAL` que el propio packet le asignó.
4. Este lote **no mueve ninguna gold**: es identidad de catálogo, no calidad de respuesta. La única
   excepción esperable es la FAQ de la DXc, donde el efecto es **quitar** una fuente equivocada.
