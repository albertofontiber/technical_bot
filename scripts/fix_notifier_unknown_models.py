"""
Fix product_model='unknown' for Notifier chunks.

Maps source_file names to their actual product models based on content analysis.
Updates chunks in Supabase via PATCH requests.

Usage:
    python -m scripts.fix_notifier_unknown_models             # Dry run
    python -m scripts.fix_notifier_unknown_models --apply      # Apply changes
"""

import argparse
import logging
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.supabase_client import get_supabase

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Source file → Product model mapping
# Built from content analysis of first chunk of each source_file
# ---------------------------------------------------------------------------

SOURCE_FILE_TO_MODEL: dict[str, str] = {
    # === Centrales de incendios ===
    "MCDT191_1": "ID3000",                          # Manual programa configuración PK-ID3000
    "MCDT156_A": "ID50/60",                          # Centrales ID5x/6x configuración fuera de línea
    "TG-Honeywell_Usuario": "TG-Honeywell",          # Panel TG-Honeywell manual usuario
    "Tg-Honeywell_Introduccion": "TG-Honeywell",     # Panel TG-Honeywell introducción
    "TG-Honeywell_Usuario_PT": "TG-Honeywell",       # Panel TG-Honeywell manual usuario (PT)
    "Tg-Honeywell_Tecnico": "TG-Honeywell",          # Panel TG-Honeywell manual técnico
    "HLSI-MN-192_UCIP": "UCIP",                      # Universal Command and Information Point
    "HLSI-MA-192_05 Guia Rapida UCIP GPRS_SP": "UCIP",
    "Guia basica instalacion_PEARL": "PEARL",         # Central PEARL
    "MIDT190": "ID3000",                              # Manual instalación ID3000
    "MADT190_01": "ID2net",                           # Manual instalación ID2net
    "MADT190_05": "ID3000",                           # Manual instalación ID3000 (caja posterior)
    "MADT190_12": "ID3000",                           # ID3000 características nuevas v4.51
    "MPDT190": "ID3000",                              # Manual programación ID3000 (extinción)
    "TIDT089": "ID3000",                              # Aisladores galvánicos con equipos Notifier
    "TIDT089_1": "ID3000",
    "TIDT089_copia": "ID3000",
    "TIDT089_copia_1": "ID3000",
    "TIDT089_2": "ID3000",
    "TIDT089_copia_2": "ID3000",
    "HOP-138-9ES issue 5_11-2025_In": "INSPIRE",     # Central INSPIRE E10/E15
    "MADT190_06": "ID3000",                           # Tabla compatibilidad ID3000
    "MADT190_04": "LIB3000",                          # Placa interfaz ampliación lazo ID3000
    "MADT190_04_1": "LIB3000",

    # === Detectores de aspiración ===
    "33037_05_VESDA-E_VEA-040-A10_Product_Guide_A4_Spanish_lores": "VESDA-E VEA",
    "33036_05_VESDA-E_VEA-040-A00_Product_Guide_A4_Spanish_lores": "VESDA-E VEA",
    "33976_13_VESDA-E_VEP-A00-P_Product_Guide_A4_Spanish_lores": "VESDA-E VEP",
    "33977_13_VESDA-E_VEP-A10-P_Product_Guide_A4_Spanish_lores": "VESDA-E VEP",
    "33978_12_VESDA-E_VEU-A00_Product_Guide_A4_Spanish_lores": "VESDA-E VEU",
    "19152_00_ICAM_Maintenance_Guide_A4_Spanish_lores": "ICAM",
    "19150_00_ICAM_Commissioning_Guide_A4_Spanish_lores": "ICAM",
    "32849_05_VESDA-E_VEA_Installation_Sheet_A3_Spanish_lores": "VESDA-E VEA",

    # === Detectores lineales ===
    # Note: VESDA-E VEA is aspiration, not linear — category may be wrong in some chunks.
    # The model assignment is still correct.

    # === Detectores puntuales ===
    "37444_A1_Xtralis_Li-ion_Tamer_GEN3_User_Manual_A4_Spanish": "Li-ion Tamer GEN3",
    "Li-ion_Tamer_User_Manual": "Li-ion Tamer",
    "MNDT1025": "VIEW",                               # Detector humo analógico cámara láser VIEW
    "I56-3536-003R D2E_SP": "D2E",                    # Detector D2E
    "MNDT600": "VGS",                                  # Desarrollo detector gas (VGS related)
    "I56-5004-000-Notifier-Strobe": "Notifier Strobe",
    "I56-3538-002R DNRE_SP": "DNRE",                   # Detector DNRE
    "HLSI-MN-601": "KIT-GAS",                          # Kit calibración gas
    "I56-1756-000_400 Series Bases": "400 Series Base",
    "MANUAL DETECTOR DE GAS VGN _SP rev 0": "VGN",     # Detector gas VGN
    "MADT609": "NAP-100",                               # Tabla aproximaciones gas NAP-100

    # === Sirenas y balizas ===
    "MIDT015": "NFS2-8",                               # Manual instalación central NFS 2-8 (sirenas/balizas section)
    "MIDT015_1": "NFS2-8",
    "MIDT015_2": "NFS2-8",
    "170020 21122011 TARJETAS IDIOMAS EXTINCION SUPRA REV A": "SUPRA",
    "170019 02012012 ETIQUETA INSTRUCCIONES EXTINCION SUPRA REV A ": "SUPRA",
    "HLSI-MA-202_01_Guia-MiniVista": "MiniVista",
    "S-287.1-DSE-ESP Rev. A.1 ": "DSE",
    "MADT015_01": "NFS2-8",                            # Instalación central (sirenas section)
    "MADT015_01_1": "NFS2-8",
    "MADT015_01_2": "NFS2-8",
    "MADT015_03": "NFS2-8",
    "MADT015_03_1": "NFS2-8",
    "MADT015_03_2": "NFS2-8",
    "D 1100-4 Sounder": "D1100",                       # Sounder
    "D 1101-7 Sounder Beacon": "D1101",                 # Sounder Beacon
    "D 1102-7 Beacon_Multi": "D1102",                   # Beacon
    "IS5001-F_IS-mA1_EN": "IS5001",                     # Sirena IS intrínseca
    "PAN AVD2_SPANISH": "AVD2",                         # Panel AVD2
    "HSR-E24_Multi": "HSR-E24",                         # Horn/Strobe
    "HSR-INT24_Multi": "HSR-INT24",                     # Horn/Strobe intrinsic
    "MADT155_08": "ID50/60",                            # Notas ID50/60

    # === Módulos de lazo ===
    "I56-4207-001 NRXI-GATE Gateway Web": "NRXI-GATE",
    "F3000M_Spanish User Guide_0044-047-02-ES": "F3000M",
    "HLSI_MNDT1410_B": "TG-IP-1",                      # Convertidor RS232 a IP
    "MNDT200": "ID3000 Repetidor",                      # Repetidor ID3000
    "I56-3920-001 CR-6EA_multi": "CR-6EA",              # Módulo control
    "I56-3918-001 IM-10EA_multi": "IM-10EA",            # Módulo
    "MNDT950": "ID3000",                                # Conexión PC ID3000
    "MADT155_05_A": "ID50/60",                          # Extinción central ID50/60
    "MADT765": "FR2000EX",                              # Central extinción FR2000EX
    "MNDT1420": "TCF-142-S",                            # Convertidor RS485

    # === Pulsadores ===
    "I56-4209-001 NRX-WCP Call Point Web": "NRX-WCP",
    "PUL-PEXT_Instrucciones multi": "PUL-PEXT",
    "PUL-DEXT_Instrucciones multi": "PUL-DEXT",
    "HLSI_MA102": "Extinción Central",                  # Pulsador disparo/espera extinción
    "D700-3-Sp": "D700",
    "D700-3-Sp_1": "D700",
    "D 1129-1": "D1129",

    # === Fuentes de alimentación ===
    "MADT190_15_1": "ID3000",                           # Cabina FA y baterías ID3000
    "MADT190_15": "ID3000",
    "VGS EXPLOSIVOS _SP rev 1": "VGS-EXP",             # Detector gas explosivos
    "VGS TOXICOS _SP rev 1": "VGS-TOXICOS",            # Detector gas tóxicos
    "997-267-000-6_Eng": "DTP Booster",                 # Kit DTP/Booster
    "08895_04-multiling_1": "Art.1555/5055/5555",       # Fuente genérica
    "08895_04-multiling": "Art.1555/5055/5555",
    "MNDT516": "PL4",                                   # Programming mode PL4
    "MNDT516_PL4_ESP-PORT": "PL4",
    "HLSI_MA-DT-1412_01_TG-IP1-SEC_QG": "TG-IP1-SEC",

    # === Software y programación ===
    "4188-1124-ES issue 6_01-2026_To": "INSPIRE",       # Software central INSPIRE
    "MADT155_07": "ID50/60",                            # Compatibilidad software ID50/60

    # === Accesorios y cableado ===
    "MN-HON-POL-200-TS_EN_V03": "POL-200-TS",
    "HLSI-MN-963_POL-200-TS": "POL-200-TS",
    "I56-2081-001ES 6500R(S) Manual": "6500R",
    "I56-2081-001ES 6500R(S) Manual_1": "6500R",
    "IRK-2E": "IRK-2E",
    "MNDT1100": "MNDT1100",                             # Fuente 12/24Vcc (doc code = product)
    "MNDT1100_1": "MNDT1100",
    "MNDT1100_2": "MNDT1100",
    "MNDT1100_3": "MNDT1100",
    "MNDT1202": "Aerosol limpieza",

    # === Sistemas de extinción ===
    "WFDEN_Manual_I56-4051": "WFDEN",

    # === General ===
    "MNDT1003": "BA1",                                  # Adaptador tubo BA1
    "MNDT1003P": "BA1",
    "Actulizacion historico TG": "TG-Honeywell",
    "Indicator Honeywell Manual SP": "Honeywell Indicator",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry run)")
    args = parser.parse_args()

    sb = get_supabase()

    # Get all unknown Notifier chunks grouped by source_file
    logger.info("Fetching unknown Notifier chunks...")

    total_mapped = 0
    total_unmapped = 0
    unmapped_files = []

    # Process each source_file in the mapping
    for source_file, model in SOURCE_FILE_TO_MODEL.items():
        # Count chunks for this source_file
        import httpx
        from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Prefer": "count=exact",
        }

        resp = sb.client.get(
            f"{sb.url}/rest/v1/chunks",
            headers=headers,
            params={
                "select": "id",
                "limit": "0",
                "source_file": f"eq.{source_file}",
                "manufacturer": "eq.Notifier",
                "product_model": "eq.unknown",
            },
        )

        content_range = resp.headers.get("Content-Range", "")
        count = int(content_range.split("/")[1]) if "/" in content_range else 0

        if count == 0:
            continue

        total_mapped += count
        logger.info(f"  {source_file}: {count} chunks → {model}")

        if args.apply:
            # Batch update: PATCH all chunks with this source_file
            update_headers = {
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            }

            resp = sb.client.patch(
                f"{sb.url}/rest/v1/chunks",
                headers=update_headers,
                params={
                    "source_file": f"eq.{source_file}",
                    "manufacturer": "eq.Notifier",
                    "product_model": "eq.unknown",
                },
                json={"product_model": model},
            )

            if resp.status_code in (200, 204):
                logger.info(f"    ✓ Updated {count} chunks")
            else:
                logger.error(f"    ✗ Failed: {resp.status_code} {resp.text[:200]}")

    # Check for unmapped source_files
    resp = sb.client.get(
        f"{sb.url}/rest/v1/chunks",
        headers={
            "apikey": sb.service_key,
            "Authorization": f"Bearer {sb.service_key}",
        },
        params={
            "select": "source_file",
            "manufacturer": "eq.Notifier",
            "product_model": "eq.unknown",
            "limit": "1000",
        },
    )
    remaining = resp.json()
    remaining_files = Counter(r["source_file"] for r in remaining)

    if remaining_files:
        total_unmapped = sum(remaining_files.values())
        logger.warning(f"\nUnmapped source_files ({total_unmapped} chunks):")
        for sf, cnt in remaining_files.most_common():
            logger.warning(f"  {cnt:5d} | {sf}")

    mode = "APPLIED" if args.apply else "DRY RUN"
    logger.info(f"\n{'='*60}")
    logger.info(f"  Mode: {mode}")
    logger.info(f"  Mapped: {total_mapped} chunks across {len(SOURCE_FILE_TO_MODEL)} source_files")
    logger.info(f"  Remaining unknown: {total_unmapped}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()
