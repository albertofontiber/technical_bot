# s331 — Censo VSN2-PLUS / «Plus2» (no-bloqueante del bloque 🟢 de E1 v2)

**Qué se preguntaba** (packet E1 v2, punto 6): qué es «VSN2-PLUS» / «Plus2», que solo aparece en
docs NFS-SUPRA/UCIP (y en la FAQ `finales-de-linea-de-las-centrales-convencionales`, donde quedó
como token sin id).

**Método:** censo por regex sobre los chunks de los ~60 docs activos cuyo `document_family` casa
`*supra*` / `*ucip*` / la FAQ de finales de línea (chunks_v2, 20-ago-2026).

## Grafías encontradas (18 distintas)

| n | grafía | docs (ej.) |
|---|---|---|
| 40 | `2Plus` | HLSI-MA-025 Guia Rapida NFS_Supra_ES, …_XP_c (11 docs) |
| 12 | `Vision Plus2` | HLSI-MA-025 (4 docs) |
| 9 | `ESS-2Plus` | Configuracion entrada digital…, HLSI-MN-025-I (4 docs) |
| 8 | `2PLUS` | HLSI-MN-192_UCIP, FAQs RP1R (5 docs) |
| 7 | `VSN-2Plus` | HLSI-MA-192_05 UCIP GPRS SP/GB (5 docs) |
| 6 | `VSN2plus` | UCIP Conectar con VSN2plus |
| 5 | `PLUS2` / `VSN-Plus2` | FAQs RP1R · HLSI-MN-025 |
| 4 | `VSN2-PLUS` | FAQ finales de línea, NFS SUPRA VSN2 PLUS Entrada Digital |
| ≤2 | `VISION PLUS 2`, `2 Plus`, `VSN12-2Plus`, `ESS-2PLUS`, `Plus2`, `plus 2`, `VSN12-2PLUS`, `VSN-2PLUS`, `VSN2PLUS` | varios |

## Lectura (con el catálogo delante)

- La generación **Supra** existe en TRES pieles de marca: **NFS Supra** (Notifier) ↔ **Vision
  «2Plus» / VSN-2Plus / Vision Plus2** (Morley/Vision) ↔ **ESS-2Plus** (Esser). El propio TI-007
  re-ingestado lo dice en una línea: «Las centrales convencionales y de extinción **serie NFS/VSN2
  y ESS**…». Variantes por zonas (p.ej. `VSN12-2Plus` en HLSI-MN-025-I) y repetidor
  (`VSNRP1r-2Plus`).
- En catálogo hoy: `morley:nfs4-supra`/`nfs8-supra`/`nfs12-supra` (candidates),
  `notifier:nfs-supra` (candidate), `unresolved:nfsx-supra` y los `ESS*` — **todos pendientes de
  los bloques E1b**, cuyo cross-bloque ya declara los homónimos morley↔unresolved
  (ESS*/NFS*-Supra).
- «VSN2-PLUS» en la FAQ de finales de línea encaja como la FAMILIA (serie VSN2 = Vision segunda
  generación, sufijo Plus), no como una central de 2 zonas: no existe ningún «NFS2-Supra» y las
  variantes de zonas vistas son 4/8/12.

## Qué se propone (y qué NO se hace en seco)

1. **No se crea ningún producto ni alias hoy.** Es la clase «rebrand/OEM, decisión entre marcas»
   (la misma que dejó fuera de bloque la fila `asd harsh environments_sp` de §1.A) + homónimos
   cross-bloque de E1b: la adjudicación es de Alberto, en la sentada E1b donde ya están los
   candidates Supra.
2. Para esa sentada, la propuesta preparada: **paraguas de familia** (término con las grafías de
   arriba como alias, `divergent: true`) → miembros = los Supra que confirmes en E1b; el token
   `VSN2-PLUS` de la FAQ de finales de línea se resuelve entonces vía paraguas, sin alta de
   producto nuevo.
3. El riesgo léxico se medirá en ese lote con el gate de siempre (los términos «2Plus»/«Plus 2»
   sueltos NO deben entrar al detector: son sufijos con riesgo de disparo en texto común; entrarían
   solo las formas ancladas VSN-2Plus/VSN2plus/Vision Plus2/ESS-2Plus).
