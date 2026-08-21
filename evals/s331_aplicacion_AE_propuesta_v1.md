# s331 — APLICACIÓN del alcance «A + E», firmado por Alberto (20-ago) — propuesta para el dúo

**Firma**: Alberto, 20-ago-2026, tras leer `evals/s331_sondas_alcance_resultado_v1.md`: **«A + E,
aplícalo»**. A = MNDT600 → doc_map a los 3 SMART confirmados. E = serie 20/20 SharpEye completa
(9 altas) + el software MNDT701 → familia IR³.

**Estado**: NADA aplicado todavía. Las sondas ya midieron el radio de explosión (los 5 planes PASS);
lo que el dúo debe atacar es el **MODELADO** de las altas, que la sonda no juzga.

## Lo que se va a escribir

**A (MNDT600)** — 1 fila de doc_map, 3 entries: `notifier:smart3g-c3`, `notifier:smart3g-d3`,
`sensitron:smart-2`. Cero productos, cero alias, **+0 términos al detector**.
Base: el doc imprime la familia en su contenido indexado (portada descrita: «smart GASDETECTOR» /
«sensitron») y las células «S1096/2096… S1097.2097…»; adjudicación previa de Alberto en el packet
(«aplica a los detectores de gas smart (sensitron)»). NO se promueve ningún candidate (esos siguen
en E1b).

**E (serie 20/20 SharpEye)** — 9 altas con cita de portada verificada full-text, 2 alias, 11 filas
de doc_map (+11 términos al detector, todos de modelo, sin alias descriptivos):

| id | canónico | tipo | manual (chunks con el token) |
|---|---|---|---|
| `spectrex:s20-20mi` | S20/20MI | **Triple IR (IR³)** | MNDT696 (43) · alias `20/20MI` · + MADT696_01 |
| `spectrex:s20-20si` | S20/20SI | **Triple IR (IR³)** | MNDT694 (40) · alias `20/20SI` |
| `spectrex:20-20i` | 20/20I | **Triple IR (IR³)** | MNDT700 C (3) |
| `spectrex:20-20r` | 20/20R | IR único espectro | MNDT713 (2) |
| `spectrex:20-20u` / `-ub` | 20/20U · 20/20UB | UV | MNDT710 B (9 · 9) |
| `spectrex:20-20l` / `-lb` | 20/20L · 20/20LB | UV/IR | MNDT720 (8 · 8) |
| `spectrex:20-20ml` | 20/20ML | UV/IR Mini | manual SharpEye 20/20ML (13) |

Y **MNDT701 (el software) → doc_map a los 3 IR³**, por su propia frase: «El software permite
comunicarse con hasta 64 detectores IR3».

## Decisiones de modelado que el dúo debe atacar (son mías, no de Alberto)

1. **Namespace `spectrex:`** aunque MNDT694/696/700 tengan `manufacturer='Notifier'` en la ficha
   (son manuales de HLSI/Notifier España para detectores Spectrex/Spectronix). Sigo la convención
   que Alberto firmó en s324b para la serie hermana: `spectrex:s40-40m` con la S. `vendido_bajo`
   = ["Spectrex", "Notifier"].
2. **S20/20MI y 20/20MI = el MISMO producto** (uno canónico + el otro alias), no dos altas. Base:
   MADT696_01 («CONFIGURACIÓN DEL DETECTOR DE LLAMA 20/20MI») documenta la configuración del mismo
   detector que MNDT696 («…MODELO S20/20MI»). Igual con SI.
3. **Los tres IR³**: S20/20MI, S20/20SI y 20/20I llevan los tres el mismo titular verbatim
   («DETECTOR DE LLAMA DE TRIPLE ESPECTRO INFRARROJO IR³ MODELO …»). Por eso el software mapea a
   los tres y no solo al MI. **Riesgo declarado**: si el software fuera exclusivo de una variante,
   estaría sobre-atestando dos.
4. **20/20U y 20/20UB (y L/LB) como productos SEPARADOS** aunque compartan manual: el título los
   nombra a los dos («MODELOS 20/20U, 20/20UB»), que es la regla R7 (concatenados → componentes con
   cita propia) aplicada al revés — aquí cada uno tiene su token.
5. **Lo que NO se hace**: no se crea paraguas «20/20» ni «S20/20» (47+41 menciones sueltas) — riesgo
   léxico real con proporciones/fracciones, se mediría aparte; MNDT690 (catálogo de gama Spectrex)
   se queda sin mapear (clase R1, otro lote); los candidates SMART **no** se promueven.

## Medida ya hecha (sondas A y E, recibos en el repo)

- A: detector 1744→1744 (**+0/−0**), 0 gold perdidas, 0 disparos (sintéticos y 111 reales), PASS.
- E: detector 1744→1755 (**+11/−0**), 0 gold perdidas, 0 disparos, PASS. 13 vínculos doc→producto;
  **9 productos que hoy no existen** pasan a tener 1-3 fuentes; los 8 documentos huérfanos de la
  serie quedan enganchados.

## Gaps declarados de entrada

1. **Ninguna gold se mueve** (0 ganancias / 0 pérdidas): es cobertura de catálogo, **no un delta
   medido en eval**. No debe contarse como mejora de calidad.
2. La atestación del software a los 3 IR³ descansa en «64 detectores IR3» + los tres titulares
   IR³ — no en una lista explícita de compatibilidad.
3. `20/20I` tiene solo **3 chunks** con el token (los otros 8 modelos van de 8 a 43): es la cita
   más floja del lote, aunque es titular de portada.
4. Los retags/altas de hoy no protegen contra `TECH_DEBT #97` (una re-ingesta de esos manuales
   re-derivaría el pm), pero **las altas de catálogo sí son persistentes** — la deuda solo afecta a
   `product_model`, no al catálogo gobernado.
