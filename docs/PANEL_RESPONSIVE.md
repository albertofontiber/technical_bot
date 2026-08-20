# El panel en el móvil — decisiones y cómo extenderlo

> **De dónde sale.** Alberto (19-ago): «optimiza la web de Vercel para verla desde el móvil,
> apoyándote en lo que ya hemos desarrollado para el war room, para no reinventar la rueda».
> Este doc es el equivalente de [`war-room/docs/RESPONSIVE.md`](https://github.com/albertofontiber/war-room/blob/main/docs/RESPONSIVE.md)
> para un panel que **no tiene Tailwind, ni React, ni una línea de JavaScript** — así que lo que
> se reutiliza son sus DECISIONES, no su código.

## Qué se tomó del war room, y qué no

| Del war room | Aquí | Por qué |
|---|---|---|
| Pivot `sm` = 640 px | ✅ único breakpoint del panel | Con cuatro pantallas y sin sidebar, un solo pivot basta; añadir `md`/`lg` sería mantener reglas que nadie necesita |
| Tap targets 44 px (Apple HIG) | ✅ `min-height:44px` en nav y botones | Idéntico |
| Regla anti-zoom iOS (`font-size:16px` en inputs) | ✅ literal | Safari hace zoom al enfocar un input de <16 px y deja la página descuadrada. Es el bug que más se nota y el más barato de evitar |
| Tabla → cards por debajo del pivot | ✅ `tabla(cards=True)` | Su `TablaEmpresas` en `<md`; aquí el Explorador (8 columnas) y las tablas de métricas |
| `<MobileDrawer>` / `<BottomSheet>` / `<ResponsiveModal>` | ❌ | Son componentes React con estado. El panel tiene 5 enlaces de navegación: un `flex-wrap` los pone en dos líneas y se ven los cinco. Un drawer escondería lo que cabe |
| Constantes TS de breakpoints + hooks | ❌ | No hay JS donde consultarlos |

## Las decisiones propias

1. **Una sola regla de rejilla, sin media queries**: `repeat(auto-fit, minmax(280px, 1fr))`.
   La portada pasa de 1 a 2 a 3 columnas según lo que quepa. No hay breakpoint que recordar
   ni que mantener sincronizado con nada.
2. **SVG fluido**: los gráficos llevan `viewBox` y NINGUNA medida en píxeles; el tamaño lo pone
   el CSS. Con las medidas fijas de antes (410 px) el gráfico se salía de la pantalla.
3. **La navegación envuelve, no se esconde**: cinco pestañas en dos líneas. Un scroll horizontal
   de tabs oculta pestañas y nadie las busca.
4. **El header reordena con `flex:1 0 100%`, no con `width:100%`** — el `nav` hereda
   `flex:1 1 0%` de escritorio y una base de 0 % gana a cualquier `width`. Medido con el
   navegador, no supuesto.
5. **En las tarjetas el valor ENVUELVE** (`overflow-wrap:anywhere`): en una tarjeta sobra alto,
   que es justo lo que no había en una fila de tabla.

## Cómo se verifica (y cómo repetirlo)

Sin Playwright en la suite —el panel se prueba en proceso, sin navegador—, pero la verificación
visual se hizo con Chromium real y es reproducible:

```python
# renderiza las páginas con datos reales a /tmp/*.html y luego:
p.goto("file:///tmp/portada.html")
p.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
# ⇒ 0 en 390×844 (iPhone 12 Pro), 768×1024 (iPad mini) y 1440×900
```

**Resultado registrado (20-ago)**: 0 px de desborde horizontal en las tres anchuras para
portada, detalle y explorador. El desborde horizontal es el fallo que hay que vigilar: es el
que hace que una página «no se vea» en un móvil.

Lo que sí vigila la suite (`tests/test_s327_panel_portada_movil.py`): que el SVG no lleve
medidas fijas, que existan la media query del pivot, la regla anti-zoom y los 44 px, que la
rejilla sea `auto-fit`, y que las tablas anchas emitan `data-etiqueta`.

## Al añadir una pantalla nueva

- Tabla de más de 4 columnas → `render.tabla(..., cards=True)`.
- Gráfico → `render.barras(..., leyenda="qué mide, en qué unidad y qué ventana")`.
- Nada de `width`/`height` en píxeles dentro de un SVG.
- Verifica el desborde con el snippet de arriba antes de dar por buena la pantalla.
