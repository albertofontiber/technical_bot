# s336 · Lote de clasificación del catálogo (vista Notifier) — RESULTADO (21/22-ago-2026)

> Diseño vinculante: `evals/s336_clasificacion_notifier_propuesta_v3.md` (2 rondas de dúo,
> 20 hallazgos adjudicados). Recibos JSON: censo/GT/población/elegibles/gate/escritura
> (`s336_*_v1.json`). GO de Alberto («clasificación por categoría de producto → GO»).

## Veredicto del lote: **PASS** (cobertura 71,9% ≥ 60%; efecto verificado)

| métrica | antes | después |
|---|---|---|
| vista Notifier clasificados | 3 (los 3 software) | **364** |
| ciegos | 502 | **141** |
| centrales clasificadas | 0 | **32** |
| replay «¿Qué centrales de Notifier tienes?» | «ninguno de los 3 casa» | **32 centrales servidas** (suelo pre-registrado 11, ×3) |

Escritas 361 filas (§0 alta + cita FULL-TEXT atribuida a su doc): 92 modulo · 85 detector ·
54 accesorio · 32 central · 21 fuente · 18 repetidor · 15 aspiracion · 14 sirena · 11 barrera ·
10 pasarela · 5 software · 4 pulsador. Todas con `clasificacion.doc` (Sol2-2) y provenance
s336. Escritura ATÓMICA (shadow 7 jsonl → validate → backup → os.replace).
**No-regresión: suite 4955 passed + MT 52/52 CON el catálogo escrito.**

## El gate hizo su trabajo (traza honesta)

1. **v1 FAIL 92,9% (13/14)** — el único fallo fue LA trampa que el GT pinnó: `pl4-e`
   (tarjeta de ampliación clasificada como su central anfitriona — clase R16 doc-de-otro).
   El writer se negó a escribir.
2. Arreglo de RAÍZ: regla R16 al prompt (v2) + re-pasada QUIRÚRGICA de las 65 filas
   `categoria=central` (población mecánica del fallo, ~$1,5). GT congelado e intacto.
3. **v2 PASS 100% (14/14)**; pl4-e→modulo·alta; centrales-alta 54→32 (clase falso-central
   desinflada). Mezcla v1/v2 declarada en el recibo de población.

## Pasada (números)

502/502 con fable-5 + repesca dirigida: 1,70M tokens in / 251k out (~96 min) + re-pasada v2
(268k in) + fix de instrumento. Confianzas finales: 366 alta / 33 media / 103 baja.
**El prompt es DERIVADO de s322 (+divergencia multi-doc, +sounders→sirena, +R16)** —
el sha propio va al recibo; el control que lo valida es el gate, no la herencia textual.

## Packet §1 — residuo DECLARADO (141 ciegos + capacidad), para adjudicación

- **98 parse-fail = fallo de INSTRUMENTO, no de evidencia**: `max_tokens=500` se agotaba en
  razonamiento sin emitir texto (raw VACÍO). Arreglado (1200) y `--solo-parse-fail` listo;
  la recuperación (~$2, ~25 min) quedó BLOQUEADA por crédito de API agotado (2ª vez del
  día). Al recargar: `--solo-parse-fail` → full-text → gate → writer (incremental) — la
  cobertura subiría de 71,9% hacia ~85%.
- 33 media + 5 baja legítima (evidencia floja o dudosa) · 5 alta sin full-text (cita no
  localizable en el doc entero) · 2 sin chunks en ningún doc.
- **31 capacidades a packet (Sol2-1 en acción)**: docs con mención de lazos/zonas sin
  entrada atribuida o max divergente — JAMÁS write-fusión; 1 sola capacidad escrita
  (la completa y no divergente). Los 4 `docs_sin_chunks` (clase GT-09/20-20UB) listados
  en el recibo de población.
- **Huecos de ENUM que Notifier destapa** (de las 8 dudas del GT + razones de baja):
  anunciador (LED-10), unidad de EXTINCIÓN (UDS-2N), audio/EVAC (ATG-2), impresora
  (PRN-4), barrera-IS Zener (Z978, colisión con «barrera»=haz), kit/paquete (BE-XP).
  Ampliar el enum es adjudicación de Alberto (packet).

## #76b — estado honesto (NO se declara cerrado)

Cableado: `alcance` {eje: idioma_doc} validado en el store · gate de completitud
multi-doc (write-fusión IMPOSIBLE por construcción: divergencia o incompletitud → packet)
· display POR FUENTE en `_casa` (byte-idéntico hoy; fixture AFP1010 con test dirigido).
Ejes mercado/variante quedan ABIERTOS y el cierre contra producción espera la primera
divergencia real escrita. TECH_DEBT #76b pasa de LATENTE a MITIGADO-por-construcción.

## Colas

(1) Recuperar los 98 parse-fail al recargar crédito (§1) · (2) resto de vistas de marca
(morley, systemsensor, xtralis, kidde…, mismo pipeline, dedupe por id) · (3) packet de
enum + capacidades a Alberto · (4) los 18 «sin docs» de mi censo v1 eran artefacto
redirect — no existen (lección G3 ×2 en un día).
