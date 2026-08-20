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
2. **El gráfico es HTML, no SVG — y por eso la letra no escala** (s328b). Fue SVG dos veces y las
   dos salió mal: con medidas fijas se salía del móvil; fluido, escalaba **todo**, así que en una
   tarjeta estrecha los rótulos caían a ~8 px y en una ancha el gráfico se pintaba a ×2,29 (lo que
   Alberto llamó «zoom»). No hay ajuste que lo arregle: **una escala uniforme mueve el texto por
   definición**. En HTML el texto es texto —12 px son 12 px a cualquier anchura— y lo único que
   estira es la barra, con la altura en porcentaje. De paso desaparece la clase de fallo entera de
   s328: no hay dos sistemas de coordenadas que puedan desalinearse, porque el rótulo y su columna
   son hijos del **mismo** `<li>`.
   · **Columnas, no barras horizontales** (adjudicación de Alberto): «que salgan de izquierda a
   derecha, no de arriba a abajo». Para una serie temporal es además lo correcto — el tiempo avanza
   hacia la derecha, y las vistas temporales ya venían invertidas para eso.
   · **La altura viaja en una CLASE** (`.h0`…`.h100`, tabla fija de 101 reglas en la hoja): un
   atributo de estilo sería «inline style» y obligaría a abrir la CSP con `unsafe-inline`.
   · **El rótulo va vertical** (`writing-mode`, que a diferencia de `transform:rotate` sí ocupa
   sitio en el layout): bajo una columna de 44 px no cabe una fecha en horizontal.
3. **La navegación envuelve, no se esconde**: cinco pestañas en dos líneas. Un scroll horizontal
   de tabs oculta pestañas y nadie las busca.
4. **El header reordena con `flex:1 0 100%`, no con `width:100%`** — el `nav` hereda
   `flex:1 1 0%` de escritorio y una base de 0 % gana a cualquier `width`. Medido con el
   navegador, no supuesto.
5. **En las tarjetas el valor ENVUELVE** (`overflow-wrap:anywhere`): en una tarjeta sobra alto,
   que es justo lo que no había en una fila de tabla.

## Cómo se verifica: ahora lo mide CI, no yo

Hasta s327 esto se comprobaba a mano con un navegador y se anotaba el resultado. Duró un día: la
única métrica que miré fue el **desborde**, y el bug que llegó no desbordaba —se ampliaba—, así que
mi verificación pasó sobre un layout roto. La lección es que **la geometría no está en el HTML**:
la calcula el navegador, y un test que lee cadenas no puede verla.

**`tests/test_s328_panel_geometria.py`** (workflow `s328-panel-geometria.yml`) levanta la app ASGI
de verdad con `scripts/s328_panel_servidor_de_medida.py` —transporte doblado; lo que se mide es el
layout, no los datos— y la recorre con Chromium en **390 / 768 / 1440** afirmando tres cosas:

| Invariante | Cómo se mide | Por qué |
|---|---|---|
| No desborda | `scrollWidth == clientWidth` | el scroll lateral esconde columnas sin decirlo |
| **La letra no escala** | todo el texto del gráfico y la leyenda, al mismo tamaño computado | lo que pidió Alberto, y lo que ningún SVG escalado puede dar |
| Rótulo centrado bajo su columna | centros horizontales a < 3 px | heredero del invariante de s328 |
| Ningún rótulo **cortado** | `scrollHeight == clientHeight` del rótulo | el recorte lo hace Python con «…»; si además el CSS corta, el gráfico miente |
| Ningún SVG se amplía | `ancho pintado / viewBox ≤ 1` | hoy no hay SVG; la sonda se conserva armada |

**Controles VERSIONADOS, en las dos direcciones** — el gate incluye páginas sintéticas con el fallo
(un SVG que se amplía; unas columnas descentradas y con otra letra) y exige que la sonda las marque,
más una con el render vigente y la hoja de estilo real que exige que **no** la marque. Sin la
segunda mitad, una sonda que dijera «roto» siempre pasaría la primera.

Y el arnés (`scripts/s328_panel_servidor_de_medida.py`) siembra **los rótulos reales más hostiles**
(`catalogo_especificaciones`) y respeta el ORDEN de cada vista: con etiquetas cortas el gate del
recorte pasaba en vacío, y con fechas ascendentes el gráfico salía del revés y parecía un fallo del
código. Un doble perezoso no verifica, tranquiliza.

**Gaps declarados**: mide **Chromium** (Safari/iOS no entra, y el técnico en obra puede llevar un
iPhone) y mide **geometría, no estética** — que nada desborde ni se amplíe no dice que se vea bien.

Lo que además vigila la suite en proceso (`tests/test_s327_panel_portada_movil.py`): que el SVG no
lleve medidas fijas, que el tope del CSS sea el mismo número que el `viewBox`, que el rótulo vaya
dentro del SVG, que existan la media query del pivot, la regla anti-zoom y los 44 px, que la
rejilla sea `auto-fit`, y que las tablas anchas emitan `data-etiqueta`.

## Al añadir una pantalla nueva

- Tabla de más de 4 columnas → `render.tabla(..., cards=True)`.
- Gráfico → `render.barras(..., leyenda="qué mide, en qué unidad y qué ventana")`.
- Nada de `width`/`height` en píxeles dentro de un SVG — y nada de rótulos FUERA de él: una
  gráfica, un sistema de coordenadas.
- Corre `python -m pytest tests/test_s328_panel_geometria.py` antes de dar por buena la pantalla.
  Si la pantalla nueva no sale en `RUTAS`, añádela ahí: un gate que no la visita no la cubre.

## La puerta va aparte (s328)

`/entrar` NO usa el design system del war room: lleva la identidad **Fontiber** del Data Room
(navy `#0c1932`, cobre `#c75b39`, arena `#f5f3ef`), por petición de Alberto. Todo cuelga de
`body.entrada`, así que ninguna regla de la puerta alcanza al resto del panel — la puerta es la
cara de la casa y la herramienta es la herramienta.

Del original se dejaron fuera tres cosas, ninguna por olvido, y están escritas junto al CSS que las
implementa (`render._ESTILO`, bloque «LA PUERTA»): el botón «Mostrar» de la contraseña (necesita
JavaScript, y la CSP dice `default-src 'none'`), «¿Olvidaste tu contraseña?» y «verificación en dos
pasos» (describen cosas que el Data Room tiene y este panel no), y la fuente Playfair Display
(cargarla obligaría a abrir la CSP a dos dominios de Google en un panel que hoy no pide nada de
fuera; va la pila serif del sistema).

Ojo al tocar los campos de la puerta: pintan a 14 px con más especificidad que la regla anti-zoom
de iOS, así que el `font-size:16px` se REPITE dentro de la media query para ellos. Quitarlo hace
que iOS haga zoom al tocar el campo de usuario.
