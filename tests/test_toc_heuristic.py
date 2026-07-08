"""Tests de la heurística de páginas de ÍNDICE (scripts/toc_heuristic.py, s102).

Consumidor vivo: el crédito de soporte del instrumento fact-level (cierre H4).
Cubren TOCs es/en con y sin dot-leaders (el caso HOP-138-8ES p.2: '# ÍNDICE' markdown +
OCR sin puntos) y los falsos positivos que NO debe marcar: packing-list, tabla de specs,
tabla de capacidad, árbol de menús.
"""

from scripts.toc_heuristic import is_toc_page

TOC_ES_DOTS = """Índice
1. Introducción ......... 3
2. Instalación ........... 12
3. Cableado del lazo ........ 18
4. Programa de Configuración de CLSS ......... 24
5. Detalles de la licencia ....... 28
6. Mantenimiento ........ 35
"""

TOC_EN_NO_DOTS = """Table of contents
Introduction 3
Panel overview 5
Loop wiring 11
CLSS configuration tool 18
License details 28
Import license file (.bin) 28
Commissioning 31
Maintenance 40
Troubleshooting 44
"""

# El caso real que motivó el lever: cabecera markdown '# ÍNDICE' + OCR sin dot-leaders.
TOC_MARKDOWN_HEADING = """# ÍNDICE

Documentos relacionados 3
Notas 3
Introducción 4
Comprobaciones preliminares 5
Módulos y ubicaciones de ranuras 6
Circuitos de lazo 7
Pruebas de cableado de lazo 8
Conexión de dispositivos OPAL/CLIP 11
Configuración inicial y primer encendido 13
"""

TOC_CONTINUATION = """7. Puesta en marcha ......... 41
8. Averías típicas .......... 47
9. Códigos de error ........ 52
10. Especificaciones ........ 58
11. Anexo A ......... 63
"""

PACKING_LIST = """Contenido del embalaje
Central de incendios ......... 1
Baterías 12V ......... 2
Manual de instalación ......... 1
Kit de tornillería ......... 1
Resistencia final de línea ......... 2
"""

SPEC_TABLE = """Especificaciones técnicas
Tensión de alimentación 230
Consumo en reposo 45
Corriente máxima por lazo 750
Temperatura de funcionamiento 40
Peso 5
Dimensiones alto 400
"""

CAPACITY_TABLE = """Capacidad por lazo
Protocolo OPAL: hasta 159 detectores y 159 módulos
Protocolo CLIP: hasta 99 detectores y 99 módulos
Corriente máxima 750 mA
Con 4 lazos: hasta 792 dispositivos en total
"""

MENU_TREE = """MENU PROGRAMMAZIONE
  Punti
    Moduli
    Rivelatori
  Zone
  Uscite
  Password di livello 2
"""


def test_toc_es_con_dot_leaders():
    assert is_toc_page(TOC_ES_DOTS)


def test_toc_en_sin_puntos_con_cabecera():
    assert is_toc_page(TOC_EN_NO_DOTS)


def test_toc_cabecera_markdown_sin_puntos():
    assert is_toc_page(TOC_MARKDOWN_HEADING)


def test_toc_continuacion_sin_cabecera():
    assert is_toc_page(TOC_CONTINUATION)


def test_packing_list_no_es_toc():
    # También usa dot-leaders, pero las cantidades (1,2,1,1,2) no son una
    # secuencia de páginas no-decreciente con máximo ≥5.
    assert not is_toc_page(PACKING_LIST)


def test_tabla_specs_no_es_toc():
    # Líneas acabadas en número pero sin dot-leaders ni cabecera de índice.
    assert not is_toc_page(SPEC_TABLE)


def test_tabla_capacidad_no_es_toc():
    assert not is_toc_page(CAPACITY_TABLE)


def test_menu_tree_no_es_toc():
    assert not is_toc_page(MENU_TREE)


def test_vacio_y_prosa_no_son_toc():
    assert not is_toc_page("")
    assert not is_toc_page("El lazo se cablea en bucle cerrado desde la salida.")
