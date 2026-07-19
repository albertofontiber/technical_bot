"""S271c — filtro determinista de contenido-informativo del serving visual.

Contrato verificado aquí (offline, funciones puras):
    * analizador de tablas markdown: celdas de datos vs cabecera/separador,
      filas de celdas VACÍAS cuentan como datos (no como separador), dedupe
      de chunks idénticos;
    * S1 blank_table_template: rejilla real (>=6 celdas de datos, cero
      informativas) + prosa mínima → señal; una tabla CON valores o celdas
      vacías SUELTAS (clase FP de árboles/UI) jamás la disparan;
    * S2 low_density: <120 alfanuméricos + corroboración de IMAGEN
      (bytes/píxel < 0.05); sin stats del render NO se evalúa (fail-open —
      clase FP de falsos-vacíos de extracción); 'wiring' EXENTA;
    * página con contenido real → cero señales.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "s271_content_filter", ROOT / "scripts" / "s271_content_filter.py"
)
cf = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("s271_content_filter", cf)
_spec.loader.exec_module(cf)


BLANK_LOG_TEMPLATE = """# Registro de mantenimiento

| Fecha | Técnico | Firma | Observaciones |
|-------|---------|-------|---------------|
|       |         |       |               |
|       |         |       |               |
|       |         |       |               |
"""

REAL_SPEC_TABLE = """## Especificaciones eléctricas

La central admite los siguientes rangos de operación en el lazo.

| Parámetro | Valor |
|-----------|-------|
| Tensión de lazo | 21-28 VDC |
| Consumo en reposo | 15 mA |
| Resistencia final de línea | 3.9 kOhm |
"""

BLANK_PAGE_STATS = {"bytes": 40_000, "width": 1169, "height": 1653}   # ~0.021 b/px
DENSE_PAGE_STATS = {"bytes": 240_000, "width": 1169, "height": 1653}  # ~0.124 b/px


def test_blank_template_es_rejilla_de_datos_vacios_y_dispara_s1():
    blank = cf.analyze_page_text([BLANK_LOG_TEMPLATE])
    assert blank["has_table"] is True
    # 3 filas vacías x 4 columnas = 12 celdas de DATOS (no separadores).
    assert blank["data_cells"] == 12
    assert blank["informative_data_cells"] == 0
    assert cf.page_signals(blank, "table") == ["blank_table_template"]
    # Con render casi vacío corroborado, S2 también.
    assert cf.page_signals(blank, "table", BLANK_PAGE_STATS) == [
        "blank_table_template",
        "low_density",
    ]


def test_tabla_real_con_valores_no_dispara_nada():
    real = cf.analyze_page_text([REAL_SPEC_TABLE])
    assert real["has_table"] is True
    assert real["informative_data_cells"] == 6
    assert cf.page_signals(real, "table", DENSE_PAGE_STATS) == []


def test_celdas_vacias_sueltas_no_son_plantilla():
    # Clase FP verificada en dry-run: LlamaParse vuelca un árbol/ventana de
    # UI como "tabla" con 2-3 celdas vacías sueltas. Eso NO es una rejilla.
    ui_dump = (
        "Prosa breve.\n| Estacion 1 | |\n| --- | --- |\n| | |\n"
    )
    metrics = cf.analyze_page_text([ui_dump])
    assert metrics["has_table"] is True
    assert 0 < metrics["data_cells"] < cf.MIN_BLANK_DATA_CELLS_S1
    assert cf.page_signals(metrics, "ui") == []


def test_cabecera_sola_sin_rejilla_no_es_s1_pero_s2_con_render_vacio():
    header_only = "| Fecha | Firma | Zona probada |\n|---|---|---|\n"
    metrics = cf.analyze_page_text([header_only])
    assert metrics["has_table"] is True
    assert metrics["data_cells"] == 0  # sin rejilla de datos → S1 no aplica
    assert cf.page_signals(metrics, "procedure") == []  # sin stats: fail-open
    assert cf.page_signals(metrics, "procedure", BLANK_PAGE_STATS) == ["low_density"]


def test_low_density_exige_corroboracion_de_imagen_y_exime_wiring():
    sparse = cf.analyze_page_text(["L1  L2\nIN  OUT\n24V"])
    assert sparse["total_alnum"] < cf.MIN_TOTAL_ALNUM
    # Clase FP verificada en dry-run: página DENSA cuyo texto cayó en el
    # chunk de otra página — el render denso la salva.
    assert cf.page_signals(sparse, "table", DENSE_PAGE_STATS) == []
    # Sin stats del render (legacy bridge): no evaluable, fail-open.
    assert cf.page_signals(sparse, "table") == []
    # Render corroborado casi vacío: señal.
    assert cf.page_signals(sparse, "table", BLANK_PAGE_STATS) == ["low_density"]
    # Wiring es gráfico-primero: exenta siempre.
    assert cf.page_signals(sparse, "wiring", BLANK_PAGE_STATS) == []


def test_prosa_densa_no_dispara_nada():
    prose = cf.analyze_page_text([
        "El módulo supervisa la zona convencional frente a circuitos "
        "abiertos, cortocircuitos y estados de alarma. " * 5
    ])
    assert cf.page_signals(prose, "table", BLANK_PAGE_STATS) == []


def test_plantilla_con_prosa_sustancial_no_es_s1():
    # Conservador: si la página lleva prosa real (>=200 alnum fuera de tabla),
    # la tabla vacía no basta para degradar.
    text = BLANK_LOG_TEMPLATE + (
        "\nInstrucciones: registre cada intervención trimestral del sistema "
        "indicando la zona probada, el resultado de la prueba de detectores "
        "y las incidencias observadas durante la revisión periódica según "
        "la norma UNE 23007-14 vigente para mantenimiento de instalaciones."
    )
    metrics = cf.analyze_page_text([text])
    assert metrics["informative_data_cells"] == 0
    assert cf.page_signals(metrics, "table") == []


def test_dedupe_de_chunks_identicos_y_conteo_de_celdas():
    metrics = cf.analyze_page_text(["hola mundo 123", "hola mundo 123"])
    assert metrics["total_alnum"] == cf.analyze_page_text(["hola mundo 123"])["total_alnum"]
    table = "| Modelo | Zonas |\n| --- | --- |\n| CAD-150-1 | 1 |\n| CAD-150-8 | 8 |\n"
    m = cf.analyze_page_text([table])
    assert m["has_table"] is True
    assert m["data_cells"] == 4
    assert m["informative_data_cells"] == 4
    # Una línea suelta con UN pipe no es tabla (prosa con pipe): fail-open.
    m2 = cf.analyze_page_text(["entrada | salida"])
    assert m2["has_table"] is False
