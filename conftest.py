# -*- coding: utf-8 -*-
# (s317/#72) La suite ENTERA corre con el pool HTTP compartido en OFF: cada
# petición construye su cliente como siempre (misma forma de llamada), así los
# ~20 ficheros de tests que fingen la red parcheando `httpx.Client` siguen
# interceptando sin cambiar una línea — y lo que la suite verifica es la
# EQUIVALENCIA de conducta de los sitios migrados. El pool ON tiene sus tests
# dedicados (tests/test_s317_http_pool.py) y su medición real con recibo
# (evals/s317_perfil_retrieval_v2.md). En producción el default es ON.
import os

os.environ.setdefault("HTTP_POOL", "off")
