# s334b — Segundo asalto a los manuales huérfanos: 134 → 18, y dos errores míos de la ronda 1

**Qué se decide:** aplicar un lote firmado de 134 promociones + 25 redirects + 43 `doc_map_altas`
+ 3 alias sobre el catálogo gobernado. Dry-run **PASS**. Nada aplicado todavía.

**Encargo (Alberto, 21-ago):** «el ataque a huérfanos me parece todavía subóptimo. Que aún queden
193 no me parece correcto, y deberías atacarlo hasta que queden 10 como máximo».

## 1. Tenía razón, y por dos motivos distintos, los dos míos

**(a) 59 nunca fueron huérfanos.** Mi definición no seguía los `redirect`; el resolver sí
(`catalog_resolver.py:187` llama `follow_redirect` ANTES de indexar el documento, y
`catalog_store._consumable` lo sigue por diseño, «fix dúo s90»). Reimplementé la definición en vez
de usar la del consumidor y me inventé 59 problemas. **Huérfanos reales: 134, no 193.** La Wiki
tenía el mismo fallo y ya está corregida (usa `cat._consumable`), con test y control negativo.

**(b) Descarté por prior lo que un instrumento sabía medir.** Aparté los 181 `unresolved:`
diciendo «asignar fabricante es adjudicación». Cierto, e irrelevante: **promover no exige
asignarlo**. El detector se construye con `_add(p["canonical_model"])` y el índice con
`norm_token(canonical_model)` — **el namespace no interviene**. Lo mismo con los acrónimos cortos
y con los que no tenían cita: precauciones, no medidas.

## 2. Los tres mecanismos, cada uno verificado ANTES de entrar en el plan

**(A) Promover** (134). Sonda G4 fila a fila: `resolve_query(canónico)` pasa de no traer su manual
a traerlo.

**(B) Promover + `doc_map`** (43 altas). El veredicto `DESBLOQUEA_PERO_ESTRECHA` que el dúo r42 me
obligó a cablear marcaba 21 ids: promover les quitaba el paraguas de `models` bajo `replace` y les
dejaba MENOS fuentes que antes (mecanismo hp009/DEC-091b). **No era un muro: era una señal de que
al plan le faltaba su acompañamiento.** Se añaden al `doc_map` del producto, como `secondary`, las
fuentes que perdería. Medido sobre el caso peor (`notifier:tg-6000`): 4 fuentes → 1 con sólo
promover, y **4 → 5 con el doc_map**. Cero perdidas, una ganada.

**(C) Redirects** (25). El validador tumbó mi primera versión con 13 «canonical_model DUPLICADO», y
el error resultó ser el hallazgo: **varios `unresolved:X` son duplicados de un `<marca>:X` que ya
existe**. La operación correcta no es promover los dos, es **redirigir** — `follow_redirect` hace
que la fila del `doc_map` apunte al producto con marca, así que el manual se alcanza **sin añadir
un término al detector** y arreglando de paso la atribución. Estrictamente mejor que promover.
Tres variantes: duplicado sin marca, gemelo detectado por ALIAS (`notifier:notifier-inspire-e10` →
`notifier:inspire-e10`) y misma marca con grafía distinta (`notifier:id-3000` → `notifier:id3000`).
Cuando el destino sigue en cuarentena se promueve también: un redirect a una fila `candidate` no
desbloquea nada.

**(D) Alias de marca** (3). Para los bloqueados por homónimo abierto. El token desnudo (`SP-200` en
Morley y en Notifier) **debe seguir fallando abierto**: es ambiguo y resolverlo es adjudicar un
rebrand (R8). El alias `Morley SP-200` da una vía inequívoca. Medido: funciona en 3 de 4; el cuarto
(`APIC`) no lleva dígitos y el detector sólo admite alias `nombre-largo` con dígito.

## 3. La colisión de canónicos: qué es mecánico y qué no

El validador prohíbe dos productos activos no-candidate con el mismo canónico (`_by_canonical`
sería last-wins silencioso). Mi primera reacción fue apartar los dos lados de cada colisión — otra
vez el prior por delante de la medida. La regla buena distingue cuatro casos, y sólo el último es
adjudicación: `unresolved:` vs marca → **redirect**; misma marca, grafías distintas → **redirect**;
dos marcas, todos en cuarentena y **sólo uno con manual huérfano** → se promueve **ése**, porque
cuál necesita el manual no es arbitrario; dos marcas y **los dos con manual huérfano** → elegir
deja el otro perdido, y el arreglo que desbloquea LOS DOS es fusionarlos → **Alberto**.

## 4. Riesgo léxico: medido, y mi primera medida estaba mal

El censo marca 25 términos de riesgo y hace PASS (ninguno es `palabra_comun`). No me fié: conté en
cuántos `source_file` aparece cada uno. **Con `ilike *X*` (substring) salían cuatro palabras:
`VIEW`, `INDICATOR`, `ITAC`, `NAS`.** Pero el detector usa FRONTERA DE PALABRA, así que la cuenta
buena es ésa — y con frontera `ITAC` cae de 270 a **11** documentos (casaba dentro de
«capaci**tac**ión») y `NAS` de 231 a **11**. **Dos productos legítimos que habría perdido por medir
con un operador distinto del que usa el consumidor.** Fuera quedan sólo los dos reales: `VIEW`
(331 documentos) e `INDICATOR` (260).

También se **heredan** las exclusiones de producto de la ronda 1 (`eia-485` = el bus RS-485,
`ad-pe` = sufijo de variante, `rhistorico.exe` = nombre de fichero, y los prefijos/etiquetas de
familia). Un generador nuevo que no hereda las decisiones del anterior las deshace en silencio:
aquí `RHistorico.exe` había vuelto a colarse.

## 5. Lo medido

| | |
|---|---|
| dry-run del gate | **PASS** · validador PASS en copia |
| detector | 1891 → 2131 (**+240 / −0**) |
| gold | **0 pierden**, **7 ganan** (ID3000 +2, INSPIRE +3, CBE +1, lazo +3…) |
| negativos sintéticos (36) | **0 disparos** |
| tráfico real (131 consultas) | 1 detección nueva: «¿Cómo se conecta el módulo MAD-461?» → verdadero positivo |
| seam 1 (`models`, política `replace`) | **0 pérdidas** en 156 consultas |
| **manuales huérfanos** | **134 → 18** (245 al empezar la sesión) |

## 6. Los 18 que quedan, uno a uno

- **6** = las 3 parejas simétricas Morley↔Notifier (`NFS8REL`, `MCX-55M`, `MMX-10M`), cada una con
  manual huérfano en los dos lados. **Fusionarlas desbloquea las 6 de golpe** y es una decisión de
  Alberto (R8) que ya está en su doc de pendientes.
- **5** = tokens que el detector **no puede ver**: `020-590`…, `55320103`, `3466`, `00051`… son
  referencias puramente numéricas (`_add` excluye los digit-only a propósito) y `EEV(2)` lleva
  paréntesis. Promoverlos es inerte.
- **5** = los que dejo fuera **a sabiendas** porque promoverlos costaría más de lo que da:
  `VIEW` e `INDICATOR` (palabras), `RHistorico.exe` (nombre de fichero), `AM-LCD` (prefijo de
  `AM-LCD-SPA`) y el de `serie-800`.
- **1** = `aritech:apic` — colisiona con `notifier:apic` y `APIC` no admite alias de marca
  detectable (4 letras, sin dígitos).
- **1** = `TG-1020-INT` — `notifier:tg-1020` colisiona con `desico:tg-1020`, que YA es consumible y
  es de otra marca.

**Con las 3 fusiones de Alberto: 12.** El objetivo de 10 no se alcanza sin decidir además sobre
los digit-only (que necesitan un nombre de producto, no una promoción).

## 7. Gaps declarados

1. **Sin medición end-to-end de retrieval/generación.** Los instrumentos son las 52 gold (0
   pérdidas, 7 ganancias), el seam 1 (0 pérdidas) y el censo. **Los 134 productos nuevos no tienen
   gold propia**: sé que no rompen lo medido, no que respondan bien.
2. **+240 términos de golpe** es el mayor radio de un lote hasta hoy. El censo los mira uno a uno y
   ninguno dispara en los 36 negativos ni en las 131 consultas reales, pero es una cifra grande.
3. **43 `doc_map_altas` como `secondary`** afirman que esos manuales «mencionan y sirven como
   fuente» para el producto. Lo deduzco de que el resolver los traía ANTES vía paraguas, no de
   haber leído los 43. Es la inferencia más débil del lote.
4. **Los alias de marca** (`Morley SP-200`) sólo casan si el técnico escribe marca+modelo EN ESE
   ORDEN. «el SP-200 de Morley» no los activa.
5. **`TECH_DEBT #99` sigue abierto**: promover ENCIENDE alias que nadie adjudicó, y este lote
   promueve 134 productos.

## 8. Qué le pido al dúo

1. ¿Los redirects hacen lo que digo? En concreto: ¿`follow_redirect` deja el manual REALMENTE
   alcanzable, o hay una vía por la que el `doc_map` de un id redirigido se pierda?
2. Los 43 `doc_map_altas` (gap 3): ¿es legítimo inferir `secondary` de «el paraguas los traía», o
   estoy metiendo atestaciones falsas en el catálogo?
3. El umbral de «palabra» (25 documentos con frontera) lo elegí yo mirando la distribución.
   ¿Aguanta, o hay un término del lote que se me cuela?
4. +240 términos: ¿hay algo que el censo no mire y que a esta escala sí importe?
5. ¿Los 18 que quedan están bien clasificados, o alguno es alcanzable con una operación que no he
   considerado?
