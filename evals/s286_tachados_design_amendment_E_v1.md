# s286 — ENMIENDA §E al brief de tachados (descubierta durante la ronda de dúo; se consolida en v1.1)

## El P2 no es un chunk corrupto único: es un PAR duplicado con una copia fiel

Auditando los chunks hermanos de HLSI-MA-103 p2 (§GAPS del brief) apareció `18691365-b867-4c39`
(p2, 1987 chars): la MISMA sección (rS · rearme-inhibido · Ft · EL · nota) en versión FIEL al
píxel del render:
- rS: «defecto 00 min, variable 00 a 10 min» ✓ (el corrupto decía 01-30)
- rearme inhibido: apartado **4.12.2** ✓ · tabla correcta con «**00 = Rearme permitido en
  cualquier momento (por defecto)**» ✓ (el corrupto INVERTÍA el default)
- Ft/EL ✓ · nota real del punto intermitente ✓

La página está DOBLE-INGESTADA (13 chunks para media guía rápida; 4 chunks «Guía rápida -
Opciones de configuración» casi idénticos; footers citando v.03 y v.05). `2113ac69` = pasada
mala; `18691365` = pasada buena.

## Cambio de diseño §E (más simple y con mejor provenance)
1. **RETIRAR el duplicado corrupto `2113ac69`** vía lifecycle (needs_review, motivo
   `s286_p2_duplicado_corrupto`, no servible) — NO re-escribir contenido a mano. Reversible
   (flag de status), before-image trivial.
2. **Patch mínimo de 2 etiquetas 7-segmentos en el chunk fiel `18691365`** (clase
   feedback_7segment, respaldo = píxel + manual completo HLSI-MN-103 p56 ya verificado en el
   gold hp011): «r.t» → «r.I» y «parámetro LA (LA → 0 seg.)» → «parámetro t.A (t.A → 0 seg.)».
3. **Auditoría de los 11 chunks restantes de p2** por pares duplicados (misma técnica hash/
   similitud + píxel): si hay más pares mala-vs-buena, retirar las malas EN EL MISMO paquete
   (inventario en el applier).
4. El REPLACE-manual del §E original queda DESCARTADO (era la alternativa peor: texto de autor
   donde existe extracción fiel).

Interacción con dedup s64: los 220 superseded del dedup histórico no cazaron este par (contenido
divergente por corrupción = no-duplicado exacto). El retiro usa el mismo lifecycle.
