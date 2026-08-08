
# L2a/s310: activa el puente de imports de la isla para TODA la suite. Los ficheros
# CONGELADOS (tests y scripts pineados por sha en los preregs s210-s212) importan por
# las rutas pre-move (`src.rag.query_evidence_compiler`) — el finder de harness los
# redirige al fichero vivo sin tocar sus bytes («version, don't relax»).
import harness  # noqa: F401
