# s339 — Lote de catálogo desde el packet firmado por Alberto (ronda 2, tras el dúo)

## Qué cambió desde la ronda 1

El dúo devolvió 14 hallazgos (Sol 8, Fable 6). **Verifiqué los 14 contra el código y los 14
eran ciertos.** Lo corregido, y cómo:

1. **§3 y §3.b no generaban NI UNA mutación** (Sol, crítico). Estaban excluidas del cruce de
   integridad y sin entrada en `LECTURA`, mientras la propuesta afirmaba traducir sus
   adjudicaciones. Añadidas: 19 anotaciones suyas → 17 modelos hermanos (`MAD-401/411/421/431/441/473`,
   `Z-200`, `CMD-501/502/503`, `TRMD-501/502`, `DMD-500`/`DMDP-500`, `TRD-100`/`TSD-100`).
2. **Borrar un id violaba el contrato** (Sol, crítico; Fable lo dio por defendible y se
   equivocaba). `IDENTITY_CATALOG_CONTRACT.md` dice literal «Los ids son INMUTABLES: nunca se
   borran ni se reciclan» y prescribe `redirect` para el merge. Mi premisa era además falsa:
   el id está en 4 entradas de `doc_map` y 1 alias. Ahora es redirect, y hay que explicárselo
   a Alberto (el redirect le da lo que pide: deja de existir como producto consultable).
3. **«Huérfanos» no ve el estrechamiento hp009/R20** (Fable, crítico). Es doc-side; el
   mecanismo es query-side. Corrido `s334_huerfanos_seam1` bajo `replace` (producción) sobre
   163 consultas: **0 pierden**, 0 ganan.
4. **La simulación no aplicaba `familia`/`alias`/`marca`** (Sol + Fable). Arreglado de RAÍZ, no
   op a op: el lote se emite ahora en el **formato de plan de `s324`** (`s339e`), así que el
   «después» lo construye `aplicar_plan()` —el mismo código que escribirá— y con él funcionan
   sin tocar nada tanto seam-1 como la puerta.
5. **La grafía de `vendido_bajo`** (Sol). El filtro de marca compara contra el `manufacturer`
   de `documents`, así que `Morley-IAS` → `morleyias` NO casa la consulta «Morley», que es la
   que el bot hace. Medido: **480 de 640 entradas cross-brand del catálogo son hoy
   inalcanzables**, las 114 de Morley entre ellas. El lote usa la grafía que el consumidor
   alcanza. (La deuda de las 480 preexistentes queda anotada, no se toca aquí.)
6. **`canonico: "VSN Plus"` no llegaba a la mutación** (Sol). Ahora sí.
7. **§6.5 «déjalo»**: mi lectura («lo quiere como producto») no se seguía de la casilla (Sol).
   BLOQUEADO y a preguntarle. La huella lo respalda: dispara en 14 docs, 11 con dueño.
8. **F5000 mutaba con una divergencia declarada** (Sol). BLOQUEADO.
9. **§6.4 `rhistorico.exe`** (Fable): s334 lo dejó fuera por riesgo léxico («R10 se cumple, la
   grafía no») y esto reintroducía esa grafía como alias indexado. BLOQUEADO.

## Estado medido AHORA

- **Plan `s324`**: 25 altas · 7 promociones · 16 redirects · 7 `vendido_bajo` · 1 alias retirado
  · 2 paraguas · 18 modificaciones de `doc_map`.
- **Huérfanos 82 → 27** (cierra 55, **abre 0**), `validate` limpio.
- **Seam-1** (`replace`, 163 consultas): **0 pérdidas de modelo**.
- **Huella de detección**: 1 término ALTO (`NAS`). Abiertos los contextos: **16 de 20
  documentos hablan del producto** (MNDT742/744/747/748, 22-66 apariciones) — lo que el número
  llamaba «robo» era el `doc_map` incompleto. Los `MAD-4xx` altos son cross-references
  legítimas (tablas de consumo, esquemas), el confundidor de DEC-272.
- **Puerta extendida**: `products_vendido_bajo` (aditivo, 5 tests) porque `aplicar_plan` no
  sabía expresar R3, que es lo que Alberto pide («findable para ambas marcas»).

## Lo que sigue BLOQUEADO (y por qué NO lo desbloqueo yo)

`§2.2 TG-1020` (choca con `desico:tg-1020`; es su pregunta sin responder) · `§6.4` ·
`§6.5 Serie 800` · `suelo F5000` (divergencia) · `suelo MAD-490/492` («parece», no firma) ·
`suelo MADT190_10` (9 racks digit-only: el detector no los ve) · `suelo D 1100-4`
(`CWSO-xx` donde xx es el color) · `suelo FS2-1` (¿familia o tres modelos?) ·
`suelo MNDT021` (no lo anotó).

## Preguntas para esta ronda

1. Emitir en formato `s324` para que `aplicar_plan` construya el «después»: ¿resuelve de raíz
   el «mi simulador miente», o mueve el problema a que ahora el plan pueda estar mal formado
   sin que nada lo note?
2. Seam-1 da 0 pérdidas **y 0 ganancias**: ninguna de las 163 consultas menciona los términos
   nuevos. ¿Es «0 pérdidas» evidencia real de seguridad, o sólo dice que el instrumento no
   toca este lote? Si es lo segundo, ¿qué instrumento SÍ lo tocaría?
3. `_grafias()` traduce el namespace a la grafía alcanzable. ¿Es correcto, o estoy fijando en
   el lote una convención que contradice las 114 filas `Morley-IAS` que ya existen?
4. La extensión `products_vendido_bajo` de la puerta: ¿aditiva de verdad?
5. ¿Qué sigo sin mirar?
