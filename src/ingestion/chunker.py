"""
Intelligent chunker for PCI manuals (multi-manufacturer).
Splits documents into semantic chunks based on section hierarchy,
preserving procedural steps and technical specifications together.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from .pdf_parser import ParsedDocument, PageContent, detect_section_headers, get_page_combined_text


@dataclass
class Chunk:
    """A semantic chunk of content from a manual."""
    content: str
    product_model: str
    category: str  # Unified EN 54 taxonomy
    section_title: str
    content_type: str  # procedure, specification, troubleshooting, wiring, general
    manufacturer: str = ""
    protocol: str = ""  # analógico | convencional
    doc_type: str = ""  # instalación | usuario | mantenimiento | guía_rápida | nota_técnica
    has_diagram: bool = False
    diagram_pages: list[int] = field(default_factory=list)
    source_file: str = ""
    start_page: int = 0
    end_page: int = 0
    chunk_index: int = 0


# ---------------------------------------------------------------------------
# Product model detection patterns — grouped by manufacturer
# ---------------------------------------------------------------------------

# Detnov models
DETNOV_MODEL_PATTERNS = [
    re.compile(r"\b(CAD-\d+(?:-\d+)?[A-Z]?)\b"),
    re.compile(r"\b(CCD-\d+[A-Z]?)\b"),
    re.compile(r"\b(CMD-\d+[A-Z]?)\b"),
    re.compile(r"\b(MAD-\d+[A-Z]?(?:-[A-Z])?)\b"),
    re.compile(r"\b(DXD-\d+[A-Z]?)\b"),
    re.compile(r"\b(DOD-\d+[A-Z]?)\b"),
    re.compile(r"\b(DTD-\d+[A-Z]?)\b"),
    re.compile(r"\b(DBD-\d+[A-Z]?)\b"),
    re.compile(r"\b(DGD-\d+[A-Z]?)\b"),
    re.compile(r"\b(DMDX?-\d+[A-Z]?)\b"),
    re.compile(r"\b(SG\d+[A-Z]?)\b"),
    re.compile(r"\b(FAD-\d+[A-Z]?)\b"),
    re.compile(r"\b(TUL\d+[A-Z]?)\b"),
    re.compile(r"\b(PCD-\d+[A-Z]?)\b"),
    re.compile(r"\b(SCD-\d+[A-Z]?)\b"),
    re.compile(r"\b(TBUD-\d+[A-Z]?)\b"),
    re.compile(r"\b(PGD-\d+[A-Z]?)\b"),
    re.compile(r"\b(TRMD-\d+[A-Z]?)\b"),
    re.compile(r"\b(PA[X]?\s*\d+)\b"),
    re.compile(r"\b(S[23]-(?:T[12]|IR))\b"),
    re.compile(r"\b(ASD\d+[A-Z]?)\b"),
    re.compile(r"\b(ADW\d+[A-Z]?)\b"),
    re.compile(r"\b(CALYPSO[- ]?II[- ]?R?)\b"),
    re.compile(r"\b(Firebeam\s+\w+)\b", re.IGNORECASE),
]

# Notifier models
NOTIFIER_MODEL_PATTERNS = [
    # --- Centrales ---
    re.compile(r"\b(ID[- ]?3000)\b", re.IGNORECASE),
    re.compile(r"\b(ID[- ]?3004)\b", re.IGNORECASE),
    re.compile(r"\b(ID[- ]?3008)\b", re.IGNORECASE),
    re.compile(r"\b(ID[- ]?2net)\b", re.IGNORECASE),
    re.compile(r"\b(ID[- ]?50(?:/60)?)\b", re.IGNORECASE),
    re.compile(r"\b(ID[- ]?60)\b", re.IGNORECASE),
    re.compile(r"\b(INSPIRE(?:\s+E\d+)?)\b", re.IGNORECASE),
    re.compile(r"\b(PEARL)\b", re.IGNORECASE),
    re.compile(r"\b(NFS[2]?[- ]?8)\b", re.IGNORECASE),
    re.compile(r"\b(NFS[2]?[- ]?3030)\b", re.IGNORECASE),
    re.compile(r"\b(NFS[- ]?(?:Supra|320))\b", re.IGNORECASE),
    re.compile(r"\b(TG[- ]?Honeywell)\b", re.IGNORECASE),
    re.compile(r"\b(TG[- ]?IP[- ]?1(?:[- ]?SEC)?)\b", re.IGNORECASE),
    re.compile(r"\b(MN[- ]?DT[- ]?530)\b", re.IGNORECASE),
    # --- Detectores / sensores ---
    re.compile(r"\b(AM[- ]?8[12]00[A-Z]?)\b", re.IGNORECASE),
    re.compile(r"\b(NFG[- ]?\d+)\b", re.IGNORECASE),
    re.compile(r"\b(NFXI[- ]?\w+)\b", re.IGNORECASE),
    re.compile(r"\b(NFX[- ]?(?:OPT|SMT|TDIFF|TFIX|BEAM)(?:-?\w*)?)\b", re.IGNORECASE),
    re.compile(r"\b(M7[012]\d[A-Z]*(?:-\w+)?)\b"),
    re.compile(r"\b(IDX[- ]?\d+[A-Z]?)\b", re.IGNORECASE),
    re.compile(r"\b(B50\d[A-Z]*|B524[A-Z]*)\b", re.IGNORECASE),
    re.compile(r"\b(S20/?20MI)\b", re.IGNORECASE),
    re.compile(r"\b(LTS[- ]?2)\b", re.IGNORECASE),
    re.compile(r"\b(D2E)\b"),
    re.compile(r"\b(DNRE)\b"),
    re.compile(r"\b(VIEW)\b"),
    re.compile(r"\b(VGN)\b"),
    re.compile(r"\b(VGS[- ]?(?:EXP|TOXICOS)?)\b", re.IGNORECASE),
    re.compile(r"\b(FS[- ]?1[13]00)\b", re.IGNORECASE),
    re.compile(r"\b(HSF[- ]?280)\b", re.IGNORECASE),
    # --- Aspiración ---
    re.compile(r"\b(VESDA[- ]?E?[- ]?(?:VL[FIPS]|VE[APUS]|VES)[- ]?\w*)\b", re.IGNORECASE),
    re.compile(r"\b(FAAST[- ]?(?:FLEX|LT|XS|XM)?)\b", re.IGNORECASE),
    re.compile(r"\b(ICAM)\b", re.IGNORECASE),
    re.compile(r"\b(Li[- ]?ion\s+Tamer(?:\s+GEN3)?)\b", re.IGNORECASE),
    re.compile(r"\b(AgileIQ)\b", re.IGNORECASE),
    # --- Sirenas / balizas ---
    re.compile(r"\b(FSL[- ]?\d+\w*)\b", re.IGNORECASE),
    re.compile(r"\b(FS[- ]?(?:24|20)[XS]?)\b", re.IGNORECASE),
    re.compile(r"\b(S300[A-Z]*)\b", re.IGNORECASE),
    re.compile(r"\b(D1100)\b"),
    re.compile(r"\b(D1101)\b"),
    re.compile(r"\b(D1102)\b"),
    re.compile(r"\b(D1129)\b"),
    re.compile(r"\b(IS5001)\b"),
    re.compile(r"\b(HSR[- ]?E24)\b", re.IGNORECASE),
    re.compile(r"\b(HSR[- ]?INT24)\b", re.IGNORECASE),
    re.compile(r"\b(AVD2)\b", re.IGNORECASE),
    re.compile(r"\b(LCD[- ]?8200)\b", re.IGNORECASE),
    re.compile(r"\b(AM[- ]?LCD)\b", re.IGNORECASE),
    # --- Módulos / gateways ---
    re.compile(r"\b(SC[- ]?6)\b", re.IGNORECASE),
    re.compile(r"\b(CZ[- ]?6)\b", re.IGNORECASE),
    re.compile(r"\b(POL[- ]?200[- ]?TS?)\b", re.IGNORECASE),
    re.compile(r"\b(HLSPS\w*)\b", re.IGNORECASE),
    re.compile(r"\b(RP1[rR])\b"),
    re.compile(r"\b(PK[- ]?8200)\b", re.IGNORECASE),
    re.compile(r"\b(NRXI?[- ]?(?:GATE|WCP))\b", re.IGNORECASE),
    re.compile(r"\b(F3000M)\b", re.IGNORECASE),
    re.compile(r"\b(CR[- ]?6EA)\b", re.IGNORECASE),
    re.compile(r"\b(IM[- ]?10EA)\b", re.IGNORECASE),
    re.compile(r"\b(UCIP)\b", re.IGNORECASE),
    re.compile(r"\b(LIB[- ]?3000)\b", re.IGNORECASE),
    re.compile(r"\b(MI[- ]?DT[- ]?1500)\b", re.IGNORECASE),
    re.compile(r"\b(iBox[- ]?(?:BACnet|Modbus|MBS))\b", re.IGNORECASE),
    re.compile(r"\b(TCF[- ]?142[- ]?S?)\b", re.IGNORECASE),
    re.compile(r"\b(6500R)\b"),
    re.compile(r"\b(IRK[- ]?2E)\b", re.IGNORECASE),
    # --- Detectores lineales / térmicos ---
    re.compile(r"\b(40[- ]?40[ILURM])\b"),
    re.compile(r"\b(SMART[- ]?3[A-Z]*)\b", re.IGNORECASE),
    re.compile(r"\b(Multiscann\+?\+?)\b", re.IGNORECASE),
    re.compile(r"\b(SENTOX[- ]?\w*)\b", re.IGNORECASE),
    re.compile(r"\b(Testifire)\b", re.IGNORECASE),
    # --- Pulsadores ---
    re.compile(r"\b(PUL[- ]?(?:PEXT|DEXT))\b", re.IGNORECASE),
    re.compile(r"\b(D700)\b"),
    re.compile(r"\b(D1129)\b"),
    # --- Extinción ---
    re.compile(r"\b(WFDE?N)\b", re.IGNORECASE),
    re.compile(r"\b(FR2000EX)\b", re.IGNORECASE),
    # --- Productos descatalogados con modelo en filename tras código I56 ---
    # Pattern: I56-####-### <MODEL>   (e.g. "I56-0788-003 - CP-651E")
    # Captures the first alphanumeric token that follows the internal doc code.
    # Requires at least one digit in the capture to avoid spurious matches like "Sp", "pdf", "Manual".
    re.compile(r"I56[- ]\d{2,5}[- ]\d{2,3}[A-Z]?[\s_\-]+([A-Z][A-Z0-9\-]*\d[A-Z0-9\-]*)", re.IGNORECASE),
    # Explicit patterns for models commonly seen in descatalogados / I56- filenames
    re.compile(r"\b(CP[- ]?651[A-Z]?)\b", re.IGNORECASE),
    re.compile(r"\b(SD[- ]?651[A-Z]?)\b", re.IGNORECASE),
    re.compile(r"\b(SD[- ]?851[A-Z]*)\b", re.IGNORECASE),
    re.compile(r"\b(SDX[- ]?751[A-Z]*)\b", re.IGNORECASE),
    re.compile(r"\b(FD[- ]?851[A-Z]*)\b", re.IGNORECASE),
    re.compile(r"\b(LPB[- ]?\d{3}[A-Z]?)\b", re.IGNORECASE),
    re.compile(r"\b(6200R)\b"),
    re.compile(r"\b(DH500(?:ACDC[- ]?E?)?)\b", re.IGNORECASE),
    re.compile(r"\b(NFX[- ]?MM1M)\b", re.IGNORECASE),
    re.compile(r"\b(IM[- ]?10)\b", re.IGNORECASE),
    re.compile(r"\b(CR[- ]?6(?!EA))\b", re.IGNORECASE),
]

# Source-file-based model detection for Notifier internal document codes
# These files use codes like MIDT190, MADT190_05 etc. that don't contain the product name
NOTIFIER_SOURCE_FILE_TO_MODEL: dict[str, str] = {
    # Centrales ID3000
    "MCDT191": "ID3000", "MCDT191_1": "ID3000",
    "MFDT190": "ID3000", "MIDT190": "ID3000",
    "MADT190_02": "ID3000", "MADT190_02_1": "ID3000",
    "MADT190_05": "ID3000", "MADT190_06": "ID3000",
    "MADT190_07": "ID3000", "MADT190_07_1": "ID3000",
    "MADT190_09": "ID3000", "MADT190_10": "ID3000",
    "MADT190_11": "ID3000", "MADT190_12": "ID3000",
    "MADT190_13": "ID3000", "MADT190_14": "ID3000",
    "MADT190_15": "ID3000", "MADT190_15_1": "ID3000",
    "MADT190P_02": "ID3000", "MADT190P_02_1": "ID3000",
    "MPDT190": "ID3000", "MNDT950": "ID3000",
    "TIDT089": "ID3000", "TIDT089_1": "ID3000", "TIDT089_2": "ID3000",
    "TIDT089_copia": "ID3000", "TIDT089_copia_1": "ID3000", "TIDT089_copia_2": "ID3000",
    "LEER PRIMERO_MADT951_10": "ID3000",
    # Centrales ID50/60
    "MCDT156_A": "ID50/60", "MIDT156": "ID50/60", "MFDT156": "ID50/60",
    "MADT155_05_A": "ID50/60", "MADT155_07": "ID50/60", "MADT155_08": "ID50/60",
    # Central ID2net
    "MADT190_01": "ID2net",
    # Módulos / expansiones
    "MADT190_04": "LIB3000", "MADT190_04_1": "LIB3000",
    # NFS2-8
    "MIDT015": "NFS2-8", "MIDT015_1": "NFS2-8", "MIDT015_2": "NFS2-8",
    "MADT015_01": "NFS2-8", "MADT015_01_1": "NFS2-8", "MADT015_01_2": "NFS2-8",
    "MADT015_02": "NFS2-8",
    "MADT015_03": "NFS2-8", "MADT015_03_1": "NFS2-8", "MADT015_03_2": "NFS2-8",
    # PEARL (numeric doc codes)
    "997-669-005-3_Instal-Comm_ES": "PEARL",
    "997-671-005-3_Configuration_ES": "PEARL",
    "997-670-005-3_Operating_ES": "PEARL",
    "997-671-007-3_Configuration_PT": "PEARL",
    "997-670-007-3_Operating_PT": "PEARL",
    # Conv. 2-8 zonas
    "997-493-002-2": "Central conv. 2-8 zonas",
    "997-493-002-2_1": "Central conv. 2-8 zonas",
    "997-493-002-2_2": "Central conv. 2-8 zonas",
    # Detectores
    "MNDT600": "VGS", "MNDT696": "S20/20MI", "MADT696_01": "S20/20MI",
    "MADT609": "NAP-100", "MADT606": "FS-Series",
    "MNDT1025": "VIEW", "MNDT1071": "LTS2", "MNDT1071_1": "LTS2",
    # Electroimanes
    "MNDT1102": "Art.1330-1345", "MNDT1102_1": "Art.1330-1345",
    "MNDT1102_2": "Art.1330-1345", "MNDT1102_3": "Art.1330-1345",
    "MNDT1103": "Art.1350/1360",
    "MNDT1104": "Art.1370/1380", "MNDT1104_1": "Art.1370/1380",
    "MNDT1105": "Art.1369",
    # Accesorios
    "MNDT1100": "MNDT1100", "MNDT1100_1": "MNDT1100",
    "MNDT1100_2": "MNDT1100", "MNDT1100_3": "MNDT1100",
    "MNDT1200": "Aerosol CO", "MNDT1202": "Aerosol limpieza",
    "MNDT1003": "BA1", "MNDT1003P": "BA1",
    # Extinción
    "MADT765": "FR2000EX",
    # Gateways / convertidores
    "MNDT960I_iBox-BACnet": "iBox-BACnet",
    "MNDT958": "iBox-Modbus", "MN-DT-958I_iBox-MBS-NID3000": "iBox-Modbus",
    "MNDT200": "ID3000 Repetidor", "MNDT1420": "TCF-142-S",
    "MNDT516": "PL4", "MNDT516_PL4_ESP-PORT": "PL4",
    "MNDT530": "MN-DT-530", "MNDT530_1": "MN-DT-530",
    # --- Auto-classified via LLM pass (scripts/llm_classify_unknowns.py) ---
    "12484_Ezsense_Ops Manual_EN": "ezsense",
    "15037SP": "AM2020/AFP1010",
    "15088SP": "AM2020/AFP1010",
    "15090SP": "15090SP",
    "15092SP": "INA",
    "15888SP": "XP Series",
    "50253SP": "AFP-300/AFP-400",
    "997-528-000-1": "NAS-2",
    "ASD Cold Environments_SP": "FAAST LT",
    "ASD Harsh Environments_SP": "FAAST",
    "BTDT017": "LCD-80",
    "BTDT032": "AM2020/AFP1010",
    "BTDT074": "MINILASER 100",
    "D 1128-1": "WCP3A",
    "D838-1_kac sounders": "D838",
    "EMA24RS2R_NX2y5-R-R": "NX2/R/R y NX5/R/R",
    "ETDT312": "NAS-2",
    "ETDT314": "NAS-1u",
    "Enlace entre TG": "TG",
    "ExitPoint- WP ENG": "ExitPoint",
    "FS2-1": "FS2-1",
    "FS8": "EFS/EM 8",
    "HLSI-TI-006": "TG MODBUS",
    "I56-1756-000_400 Series Bases": "400 Series Bases",
    "I56-2961-000R_Sp": "PF24V",
    "IIG4+IIG4N-ITAa4": "IIG4N",
    "IRK-E-SI": "IRK-E-SI",
    "MA-DT-1160": "ExitPoint",
    "MADT020": "CFP-800",
    "MADT100_01": "RP1001E and RP1002E",
    "MADT120_01": "AFP-200",
    "MADT170": "AFP-300/AFP-400",
    "MADT171": "AFP-300/AFP-400",
    "MADT212": "ID1000",
    "MADT230_01": "AFP4000",
    "MADT231": "AFP4000",
    "MADT232": "MA-DT-232",
    "MADT233": "AFP4000",
    "MADT234": "ARP4000",
    "MADT235": "AFP4000",
    "MADT236": "AFP4000",
    "MADT236P": "AFP4000",
    "MADT280": "AM2020/AFP1010",
    "MADT281": "AM2020",
    "MADT282": "DIA (DIB)",
    "MADT283": "AM2020/AFP1010",
    "MADT284": "AM2020/AFP1010",
    "MADT285": "AM2020/AFP1010",
    "MADT285_01": "AM2020",
    "MADT370": "NOTI-FIRE-NET",
    "MADT380_01": "NAM-232",
    "MADT575_01": "SecurNet Plus",
    "MADT575_02": "SECURNET PLUS",
    "MADT608": "MA-DT-608",
    "MADT635_01": "LISA 2",
    "MADT731_02": "STRATOS",
    "MADT731_03_A": "LaserStar",
    "MADT731_04": "AIRSENSE",
    "MADT732_01": "R3-MICRA",
    "MADT742": "MA-DT-742",
    "MADT745_01": "SCU 2000",
    "MADT746_01": "CCM3000",
    "MADT951_01": "TG-NOTIFIER",
    "MADT951_02": "TG-NOTIFIER",
    "MCDT120": "PK-AFP200E",
    "MCDT150": "ID200",
    "MCDT170": "VeriFire-300/400",
    "MCDT280": "UPDL-2020",
    "MFDT1070": "LTS-240",
    "MFDT112P": "UDS-2N",
    "MFDT170": "AFP-300/AFP-400",
    "MFDT180": "ID2000",
    "MFDT180P": "ID2000",
    "MFDT212": "ID1000",
    "MFDT280": "AM2020",
    "MFDT745": "SCU 2000",
    "MFDT746_B": "SCU-800",
    "MI-DT-951_V7.2": "MI-DT-951",
    "MIDT020": "Serie 800",
    "MIDT1041": "DH500AC/DC",
    "MIDT1452_Inst_via radio": "VW2W100",
    "MIDT170": "AFP-300/AFP-400",
    "MIDT180": "ID2000",
    "MIDT212": "ID1000",
    "MIDT230": "AFP4000",
    "MIDT250_A": "AM-6000",
    "MIDT260": "AM-2000",
    "MIDT340": "MI-DT-340",
    "MIDT730": "LaserStar",
    "MIDT731": "LaserStar-HSSD-2",
    "MIDT732": "MINILÁSER25",
    "MIDT734": "MINILÁSER100",
    "MIDT750": "6424",
    "MIDT760_C": "F2000D",
    "MIDT951_v5-87": "MI-DT-951",
    "MN-DT-1150": "LPS-700",
    "MN-DT-951_v7.2": "DT-951",
    "MNDT012P": "EFS/EM 8",
    "MNDT020": "Serie 800",
    "MNDT021": "CFP-800",
    "MNDT040": "CFP-600-E",
    "MNDT040P": "CFP-600-E",
    "MNDT060": "Sistema 5000",
    "MNDT080": "MS-5210UD/MS-5210UDE",
    "MNDT100": "RP-1001",
    "MNDT1001": "CMX-10R",
    "MNDT1001P": "CMX-10R",
    "MNDT1002": "MMX-10",
    "MNDT1002P": "MMX-10",
    "MNDT1004": "CMX-10RM",
    "MNDT1005": "MCX-55M",
    "MNDT1006": "MMX-10M",
    "MNDT101": "RP1002E",
    "MNDT105P": "AM-200",
    "MNDT105_A": "AM-200",
    "MNDT1070": "LTS-240",
    "MNDT110": "UDS-1N",
    "MNDT1101": "1315/1316 Series",
    "MNDT1116": "5054/5064 (PAN-1)",
    "MNDT1117": "PAN-2",
    "MNDT112": "UDS-2N",
    "MNDT1160": "ExitPoint",
    "MNDT120": "AFP-200E",
    "MNDT1300I_E": "PS Series",
    "MNDT1300_E": "PS Series",
    "MNDT1400": "IC-485S",
    "MNDT150": "ID-200",
    "MNDT213": "Serie 1000",
    "MNDT250": "AM-6000",
    "MNDT250P": "AM-6000",
    "MNDT255": "LCD-6000",
    "MNDT260": "AM-2000",
    "MNDT285": "AM2020/AFP1010",
    "MNDT350": "Serie XP",
    "MNDT370": "NRT",
    "MNDT380": "NAM-232",
    "MNDT390": "DT-390",
    "MNDT400": "LCD-80",
    "MNDT402": "LCD-80",
    "MNDT410": "DT-410",
    "MNDT420": "LDM Series",
    "MNDT430": "RPT-485W/RPT-485WF",
    "MNDT440": "NIB-96",
    "MNDT500": "G-500",
    "MNDT503": "G-100",
    "MNDT506": "G-100-R",
    "MNDT510P": "NCO-10",
    "MNDT515": "PL4",
    "MNDT515P": "PL4",
    "MNDT520": "GALILEO",
    "MNDT530P": "PARK 2000 / PARK 5000",
    "MNDT575": "SECURNET PLUS",
    "MNDT605": "GD-520-CO, GA-520-CO, GD-500-EP, GA-500-EP",
    "MNDT606": "SMART TWIN",
    "MNDT607": "SMART 1",
    "MNDT615": "DT-615",
    "MNDT616": "S317AMDP",
    "MNDT617": "S613AMFP",
    "MNDT618": "S313HSAP and S319HSAP",
    "MNDT619": "S264O2GP / S290O2GP",
    "MNDT624": "LCR 3 PK",
    "MNDT635": "LISA 2",
    "MNDT650": "MN-DT-650",
    "MNDT651": "PARK",
    "MNDT655": "Serie DOMÉSTICA (CAT/220, CAT/12, COMBIX/220, COMBIX/12)",
    "MNDT655P": "CAT/220, CAT/12, COMBIX/220, COMBIX/12",
    "MNDT656": "S876xx / S877xx",
    "MNDT690": "MN-DT-690",
    "MNDT694": "S20/20SI",
    "MNDT700_C": "20/20I",
    "MNDT701": "IR3",
    "MNDT710": "20/20U, 20/20UB",
    "MNDT710_B": "20/20U, 20/20UB",
    "MNDT713": "20/20R",
    "MNDT720": "20/20L, 20/20LB",
    "MNDT730": "Stratos HSSD",
    "MNDT730P": "Stratos HSSD",
    "MNDT740P": "NAS",
    "MNDT741": "NAS",
    "MNDT741I": "NAS",
    "MNDT742P_F": "NAS-2",
    "MNDT742_G": "NAS-2",
    "MNDT744I_B": "NAS-1u",
    "MNDT744_B": "NAS-1u",
    "MNDT747": "NAS-10",
    "MNDT747P": "NAS-10",
    "MNDT748": "NAS-20",
    "MNDT748P": "NAS-20",
    "MNDT770": "F50R / F100R",
    "MNDT951I": "DT-951I",
    "MNDT951I_v7-1": "MN-DT-951I",
    "MNDT951_v5-87": "DT-951",
    "MNDT954": "TG-6000",
    "MNDT955": "TG-6000 Net",
    "MNDT960": "POL-1",
    "MNDT960I": "POL-1",
    "MP-DT-951_v7.2": "MP-DT-951",
    "MPDT170": "AFP-300/AFP-400",
    "MPDT180": "ID2000",
    "MPDT212": "ID1000",
    "MPDT230": "AFP4000",
    "MPDT280": "AM2020 and AFP1010",
    "MPDT281": "AM2020/AFP1010",
    "MPDT951I": "MP-DT-951I",
    "MPDT951_v5-87": "MP-DT-951",
    "Manual SIMEI-HLSI_SP-EN": "SIMEI",
    "Manual Unipoint Esp": "Unipoint",
    "NCO-10-multinglingual": "NCO-10",
    "NF30-50_Manuel_d'utilisation_lr": "NF30/NF50",
    "PAN_AVD1": "PAN-AVD1",
    "Serie PS": "Serie PS",
    "TG-1020-INT": "TG-1020",
    "TG-1020-TEC": "TG-1020",
    "TG-1020-USU": "TG-1020",
    "TIDT070": "LáserStar",
    "TIDT101": "TG",
    "TIDT105": "S40/40",
    "TIDT109": "ClassiFire",
    "TMP2_QRefnotiES_Rev_1_4_HLSI 2018": "TMP2",
    "manco-N": "G-10",
    # --- 2nd LLM pass over Vision-rescued zero-chunks ---
    "15274 RevB - RZA-4X_Eng": "RZA-4X",
    "15581": "System 5000",
    "15584": "Systema 5000",
    "156-0393-008R - OSY2_Eng": "OSY2",
    "156-0394-007R - PIBV2_Eng": "PIBV2",
    "156-0551-005R EPS10_Eng": "EPS10 Series",
    "2470-2480 Pulsador": "2470/2471/2480",
    "50478 RevA - MPS-24AE _Eng": "MPS-24AE",
    "AC1460R - CESI 03 ATEX 050": "EFD Series",
    "BANI-G-24_Eng": "IS 28 Mk 4",
    "D391 Issue 3 WW_WY_WR2001 ": "WW2001",
    "D427 Issue 2 WW_WY_WR4001 ": "4001",
    "D686 EMA1224B4R_W NS4R": "EMA1224B4R/W",
    "I56-17771-002_multi": "B324RL, B312RL, B312NL",
    "I56-699-15R 5451EIS_Eng": "5451EIS",
    "I56-720-13R 1151EIS_Eng": "1151EIS",
    "I560849010EMA24ALRANS4REng": "EMA24ALR and EMA24ALW",
    "MADT213": "PRN1000",
    "MT4508-CKDPLUS REV 0": "STS/CKD+",
    "NSRE24": "NSRE24",
    "NSRE24_EXTERNO": "ESTELA-1 / ESTELA-2",
    "PL4_MT574E_Eng": "PL4",
    "RIF_08791_01 - AC1469_It-eng": "1469",
    "S3466R_Eng_ital": "3466",
    "Smart 2_MT251_Ita-Eng": "SMART 2",
}

# Combined list for backward compatibility
MODEL_PATTERNS = DETNOV_MODEL_PATTERNS + NOTIFIER_MODEL_PATTERNS

# Content type detection
PROCEDURE_KEYWORDS = re.compile(
    r"\b(PASO\s+\d+|paso\s+\d+|procedimiento|instalación|instalar|montar|conectar|"
    r"desmontar|configurar|programar|verificar|comprobar)\b",
    re.IGNORECASE,
)
SPEC_KEYWORDS = re.compile(
    r"\b(especificaciones|características\s+técnicas|datos\s+técnicos|dimensiones|"
    r"peso|temperatura|humedad|tensión|corriente|consumo|grado\s+de\s+protección|IP\d+|"
    r"alimentación\s+\d+V|potencia|frecuencia|impedancia|capacidad|autonomía|"
    r"rango\s+de\s+medida|sensibilidad|resolución|precisión|"
    r"máximo|mínimo|nominal|rango|valor|"
    r"\d+\s*V(?:AC|DC|ac|dc|cc)|"  # voltage patterns: 230VAC, 24VDC, 12Vcc
    r"\d+\s*(?:mA|µA|A)\b|"        # current patterns: 300mA, 500µA, 2A
    r"\d+\s*(?:mm|cm|kg|[ºª°]C)|"  # physical: 533mm, 12.5kg, -5°C
    r"\d+\s*(?:Ω|ohm|ohmio)|"      # resistance
    r"\d+\s*(?:nF|µF|pF)|"         # capacitance
    r"\d+\s*(?:dB|Hz|kHz|MHz))\b",  # audio/frequency
    re.IGNORECASE,
)
# Source-file-based model detection for Morley
MORLEY_SOURCE_FILE_TO_MODEL: dict[str, str] = {
    # Centrales DX Connexion
    "DXc_Guia de instalacion_multiling": "DXc",
    "DXc_Guia de usuario_multiling": "DXc",
    "DXc_Manual de configuracion": "DXc",
    "DXc_Manual de usuario": "DXc",
    "DXc_Manual variaciones de mercado": "DXc",
    # Centrales F5000 (detector de haz óptico motorizado)
    "0044-033-01 Guia F5000": "F5000",
    "F5K-2H-UserGuide-SPANISH_Manual F5000": "F5000",
    "F5K-Additional-Information-Spanish": "F5000",
    # Centrales Vision Supra (convencional)
    "27012012 ETIQUETA INSTRUCCIONES VISION SUPRA REV A ": "Vision Supra",
    "30012012  TARJETAS IDIOMAS VISION SUPRA rev A": "Vision Supra",
    # Centrales ZX (convencional)
    "996-130-000-3 Manuel d'utilisation ZX_hlsi": "ZXe",
    "MIE-MI-431rv2": "ZXr",
    "MIE-MI-530rv001": "ZXe",
    "MIE-MI-600": "ZXSe",
    "MIE-MP-530rv001": "ZXe",
    "MIE-MP-535rv001": "ZXSe",
    "MIE-MU-530rv001": "ZXe",
    "MIE-MU-535rv001": "ZXSe",
    # Centrales Morley Lite/Plus/Max
    "Docs Morley-IAS Lite&Plus - QR": "Morley Lite/Plus",
    "Docs Morley-IAS Max - QR": "Morley Max",
    # Software TG
    "Tg-Honeywell_Introduccion": "TG-Honeywell",
    "Tg-Honeywell_Tecnico": "TG-Honeywell",
    "TG-Honeywell_Usuario": "TG-Honeywell",
    "MIE-MI-505rv01": "TG-Honeywell",
    "Enlace entre TG": "TG-Honeywell",
    "Actulización histórico TG": "TG-Honeywell",
    "LEER PRIMERO_MADT951_10": "TG-Honeywell",
    # Aspiración AutoSAT
    "MNDT1310": "AutoSAT-10",
    "MNDT1311": "AutoSAT-20",
    # Aspiración ASD (guías genéricas de aplicación)
    "ASD Cold Environments_SP": "ASD",
    "ASD Harsh Environments_SP": "ASD",
    # Detectores / bases
    "I56-1756-000_400 Series Bases": "B400 Series Bases",
    "D 1152-1 BGL Morley": "MI-BGL-PC-I",
    "I56-2954-000_prelim": "CZ6",
    "I56-2955-000_prelim": "M200E",
    # Módulos MI-D
    "I56-2128-003 MI-DCZM": "MI-DCZM",
    "I56-4406-001 MI-DMMIE MI-DMM2IE MI-D2ICMOE": "MI-DMMIE",
    "I56-4407-001 MI-DCMOE": "MI-DCMOE",
    "I56-4428-000 MI-D240CMOE": "MI-D240CMOE",
    "I56-2957-000_prelim": "MI-DZM",
    "MIE-MI-160rv03": "MI-RTC",
    # Módulos / Gateways
    "HLSI_MN1007": "ITAC",
    "I56-3879-000 MI-LPB2-S2I_EN": "MI-LPB2-S2I",
    "Manual SIMEI-HLSI_SP-EN": "SIMEI",
    "MIE-TI-001": "MI-LPB2",
    # Bases de relé
    "I56-1749-020 ECO1000BREL12L_12NL_24L": "ECO1000 BREL",
    # Sirenas / Strobe
    "I56-5002-000-Morley-Strobe": "WRL/WWL Strobe",
    # Pulsadores
    "Instrucciones_PUL-VSN_MULTI": "PUL-VSN",
    # Fuente de alimentación
    "MIE-MI-591": "PSU Morley",
    # Comunicaciones (MIE-MI-320/330/340/390 - contenido corrupto, incluir con nombre genérico)
    "MIE-MI-320": "Comunicador MIE-320",
    "MIE-MI-330": "Comunicador MIE-330",
    "MIE-MI-340": "Comunicador MIE-340",
    "MIE-MI-390": "Comunicador MIE-390",
    # Detectores ECO1000 series (filename regex no capta "ECOxxxx")
    "I56-1651-023 ECO1002": "ECO1002",
    "I56-1652-023 ECO1005_ECO1005T_ECO1004T": "ECO1005",
    "I56-1653-022 ECO1003": "ECO1003",
    # Bases con indicador
    "D 1150-1 BRH Morley": "MI-BRH",
    "D 1151-1 BRS Morley": "MI-BRS",
    # Centrales / dispositivos con códigos internos
    "D391 Issue 3 WR2001 ": "WR2001",
    "HLSI-TI-007_VSN-4REL": "VSN-4REL",
    # Módulos MI-D (analógico, no "-E")
    "I56-2006-004 MI-DMMI_DMM2I_D2ICMO": "MI-DMMI",
    "I56-4259-000 MI-Gate Gateway": "MI-Gate",
    # Sirena + baliza
    "I56-5003-000-Morley-Sounder-Strobe": "WRL/WWL Sounder Strobe",
    # Fuente alimentación multi-idioma
    "PSU User Manual_MLT LNG": "PSU Morley",
}

# Source-file-based category override for Morley (more reliable than keywords)
MORLEY_SOURCE_FILE_TO_CATEGORY: dict[str, str] = {
    # === Centrales de incendios ===
    "DXc_Guia de instalacion_multiling": "Centrales de incendios",
    "DXc_Guia de usuario_multiling": "Centrales de incendios",
    "DXc_Manual de configuracion": "Centrales de incendios",
    "DXc_Manual de usuario": "Centrales de incendios",
    "DXc_Manual variaciones de mercado": "Centrales de incendios",
    "HLSI-MA-025 Guia Rapida NFS_Supra_ES": "Centrales de incendios",
    "HLSI-MN-025-I_NFS Supra Series": "Centrales de incendios",
    "HLSI-MN-025_NFS Supra": "Centrales de incendios",
    "HLSI-MA-103-I_GuiaRapida_RP1r-Supra_EN_lr": "Centrales de incendios",
    "HLSI-MA-103_GuiaRapida_RP1r-Supra_ES_lr": "Centrales de incendios",
    "HLSI-MN-103I_RP1r-Supra_lr": "Centrales de incendios",
    "HLSI-MN-103_RP1r-Supra_lr": "Centrales de incendios",
    "27012012 ETIQUETA INSTRUCCIONES VISION SUPRA REV A ": "Centrales de incendios",
    "30012012  TARJETAS IDIOMAS VISION SUPRA rev A": "Centrales de incendios",
    "996-130-000-3 Manuel d'utilisation ZX_hlsi": "Centrales de incendios",
    "MIE-MI-431rv2": "Centrales de incendios",
    "MIE-MI-530rv001": "Centrales de incendios",
    "MIE-MI-600": "Centrales de incendios",
    "MIE-MP-530rv001": "Centrales de incendios",
    "MIE-MP-535rv001": "Centrales de incendios",
    "MIE-MU-530rv001": "Centrales de incendios",
    "MIE-MU-535rv001": "Centrales de incendios",
    "Docs Morley-IAS Lite&Plus - QR": "Centrales de incendios",
    "Docs Morley-IAS Max - QR": "Centrales de incendios",
    "D391 Issue 3 WR2001 ": "Centrales de incendios",
    # === Detectores puntuales ===
    "I56-1651-023 ECO1002": "Detectores puntuales",
    "I56-1652-023 ECO1005_ECO1005T_ECO1004T": "Detectores puntuales",
    "I56-1653-022 ECO1003": "Detectores puntuales",
    "D 1150-1 BRH Morley": "Detectores puntuales",
    "D 1151-1 BRS Morley": "Detectores puntuales",
    "D 1152-1 BGL Morley": "Detectores puntuales",
    # === Detectores lineales (haz óptico) ===
    "0044-033-01 Guia F5000": "Detectores lineales",
    "F5K-2H-UserGuide-SPANISH_Manual F5000": "Detectores lineales",
    "F5K-Additional-Information-Spanish": "Detectores lineales",
    "I56-3879-000 MI-LPB2-S2I_EN": "Detectores lineales",
    "MIE-TI-001": "Detectores lineales",
    # === Detectores de aspiración ===
    "MNDT1310": "Detectores de aspiración",
    "MNDT1311": "Detectores de aspiración",
    "ASD Cold Environments_SP": "Detectores de aspiración",
    "ASD Harsh Environments_SP": "Detectores de aspiración",
    "A05-7030-100_B_ES_Morley FAAST FLEX Addressable": "Detectores de aspiración",
    "I56-3888-010 FAAST LT-200 Adv Guide": "Detectores de aspiración",
    "I56-6574-005_EN-HS-Stand-Alone-FAAST-LT-200-QIG": "Detectores de aspiración",
    "I56-6574-005_ES -HS Stand Alone FAAST LT-200 QIG": "Detectores de aspiración",
    "I56-6575-005_EN-FAAST-LT-200-Loop-QIG": "Detectores de aspiración",
    "I56-6575-005_ES FAAST LT-200 Loop QIG": "Detectores de aspiración",
    "FAAST Area Coverage Planner_SP": "Detectores de aspiración",
    "FAAST Understanding EN54-20_SP": "Detectores de aspiración",
    # === Pulsadores ===
    "Instrucciones_PUL-VSN_MULTI": "Pulsadores",
    "Manual SIMEI-HLSI_SP-EN": "Pulsadores",
    # === Sirenas y balizas ===
    "I56-2081-012 6500R(S)_ES": "Sirenas y balizas",
    "I56-5002-000-Morley-Strobe": "Sirenas y balizas",
    "I56-5003-000-Morley-Sounder-Strobe": "Sirenas y balizas",
    "HSR-E24_Multi": "Sirenas y balizas",
    "HSR-INT24_Multi": "Sirenas y balizas",
    # === Módulos de lazo ===
    "HLSI-MN-192_UCIP": "Módulos de lazo",
    "HLSI-MA-192_05 Guia Rapida UCIP GPRS_SP": "Módulos de lazo",
    "HLSI-MA-192_05 Quick Start Guide UCIP GPRS_GB": "Módulos de lazo",
    "HLSI-TI-007_VSN-4REL": "Módulos de lazo",
    "HLSI_MN1007": "Módulos de lazo",
    "HLSI-MN-963_POL-200-TS": "Módulos de lazo",
    "I56-2128-003 MI-DCZM": "Módulos de lazo",
    "I56-2006-004 MI-DMMI_DMM2I_D2ICMO": "Módulos de lazo",
    "I56-2954-000_prelim": "Módulos de lazo",
    "I56-2955-000_prelim": "Módulos de lazo",
    "I56-2957-000_prelim": "Módulos de lazo",
    "I56-4406-001 MI-DMMIE MI-DMM2IE MI-D2ICMOE": "Módulos de lazo",
    "I56-4407-001 MI-DCMOE": "Módulos de lazo",
    "I56-4428-000 MI-D240CMOE": "Módulos de lazo",
    "I56-4259-000 MI-Gate Gateway": "Módulos de lazo",
    "I56-1749-020 ECO1000BREL12L_12NL_24L": "Módulos de lazo",
    "MIE-MI-160rv03": "Módulos de lazo",
    "MIE-MI-320": "Módulos de lazo",
    "MIE-MI-330": "Módulos de lazo",
    "MIE-MI-340": "Módulos de lazo",
    "MIE-MI-390": "Módulos de lazo",
    # === Fuentes de alimentación ===
    "PSU User Manual_MLT LNG": "Fuentes de alimentación",
    "MIE-MI-591": "Fuentes de alimentación",
    # === Software y programación ===
    "Tg-Honeywell_Introduccion": "Software y programación",
    "Tg-Honeywell_Tecnico": "Software y programación",
    "TG-Honeywell_Usuario": "Software y programación",
    "MIE-MI-505rv01": "Software y programación",
    "Enlace entre TG": "Software y programación",
    "Actulización histórico TG": "Software y programación",
    "LEER PRIMERO_MADT951_10": "Software y programación",
    # === Accesorios y cableado ===
    "I56-1756-000_400 Series Bases": "Accesorios y cableado",
    "IRK-2E": "Accesorios y cableado",
}

TROUBLESHOOT_KEYWORDS = re.compile(
    r"\b(averías?|problemas?|solución|diagnóstico|error|fallo|resolver|"
    r"troubleshoot|causa|remedio)\b",
    re.IGNORECASE,
)
WIRING_KEYWORDS = re.compile(
    r"\b(conexión|conexionado|cableado|esquema|borne|terminal|polaridad|"
    r"cable|hilo|conector|pin|lazo|bucle|circuito|relé|salida|entrada)\b",
    re.IGNORECASE,
)


def detect_product_model(text: str, filename: str = "", manufacturer: str = "") -> str:
    """Detect the product model from text content or filename.

    Uses three strategies in order:
    1. Source-file lookup for Notifier internal doc codes (most reliable)
    2. Regex patterns on filename + content (general)
    3. Falls back to "unknown"
    """
    # Strategy 1: Source-file lookup for known internal doc codes
    if filename:
        stem = Path(filename).stem
        if manufacturer == "Notifier" and stem in NOTIFIER_SOURCE_FILE_TO_MODEL:
            return NOTIFIER_SOURCE_FILE_TO_MODEL[stem]
        if manufacturer == "Morley" and stem in MORLEY_SOURCE_FILE_TO_MODEL:
            return MORLEY_SOURCE_FILE_TO_MODEL[stem]

    # Strategy 2: Regex patterns on filename + first 2000 chars of content
    clean_filename = filename.replace("_", " ").replace(".", " ")
    combined = clean_filename + " " + text[:2000]
    for pattern in MODEL_PATTERNS:
        match = pattern.search(combined)
        if match:
            return match.group(1).strip()
    return "unknown"


def detect_manufacturer(file_path: str, text: str = "") -> str:
    """Detect manufacturer from file path or content.

    Checks folder structure first (reliable), then falls back to model patterns and keywords.
    """
    path_str = str(file_path).lower()

    # Folder-based detection (most reliable)
    if "manuales_notifier" in path_str:
        return "Notifier"
    if "manuales_es" in path_str or "manuales_detnov" in path_str:
        return "Detnov"
    if "manuales_morley" in path_str:
        return "Morley"

    # Model pattern-based detection
    clean = Path(file_path).stem.replace("_", " ").replace("-", " ")
    combined = clean + " " + text[:2000]

    for pattern in NOTIFIER_MODEL_PATTERNS:
        if pattern.search(combined):
            return "Notifier"
    for pattern in DETNOV_MODEL_PATTERNS:
        if pattern.search(combined):
            return "Detnov"

    # Keyword fallback
    text_lower = (clean + " " + text[:500]).lower()
    if "notifier" in text_lower:
        return "Notifier"
    if "detnov" in text_lower:
        return "Detnov"
    if "morley" in text_lower:
        return "Morley"
    # Honeywell last (parent brand of both Notifier and Morley)
    if "honeywell" in text_lower:
        return "Morley"

    return "unknown"


# ---------------------------------------------------------------------------
# Unified category taxonomy (EN 54-aligned)
# ---------------------------------------------------------------------------

# Map old Detnov folder-based categories to new unified categories
_DETNOV_CATEGORY_MAP = {
    "Detección analógica": "Detectores puntuales",
    "Detección convencional": "Detectores puntuales",
    "Detección de gas": "Detectores puntuales",
    "Detección de monóxido": "Detectores puntuales",
    "Detectores especiales": "Detectores puntuales",
    "PA_VA Evacuación por voz": "Sirenas y balizas",
    "Sistema de extinción": "Sistemas de extinción",
    "Accesorios": "Accesorios y cableado",
}

# Keywords in content/filename for category detection
_CATEGORY_KEYWORDS = {
    "Centrales de incendios": [
        "central de incendios", "central de alarma", "central de detección",
        "centrales analógicas", "centrales analogicas",
        "centrales convencionales", "fire alarm control panel",
        "panel de control", "panel de incendios",
        "NFS", "NFS2-3030", "NFS-320", "NFS Supra",
        "AM-8200", "AM-8100", "AM 8200", "AM 8100",
        "CAD-150", "CCD-100", "ID3000",
        "Pearl", "INSPIRE", "PARK 2000", "PARK 5000",
        "monóxido de carbono",
        "TG-Honeywell", "TG - Honeywell", "MN-DT-951",
        "S-HSF", "CLSS",
    ],
    "Detectores puntuales": [
        "detector óptico", "detector térmico", "detector de humo",
        "smoke detector", "heat detector", "optical detector",
        "NFXI", "NFX-OPT", "NFX-SMT", "NFX-TDIFF", "NFX-TFIX",
        "IDX-751", "B501", "B524",
        "DOD-", "DTD-", "DXD-", "DGD-", "DMD",
        "detector de gas", "gas detector",
        "SENTOX", "SMART 3", "NFG-",
        "Li-ion Tamer", "calibración", "calibracion",
    ],
    "Detectores lineales": [
        "detector lineal", "beam detector", "barrera",
        "FSL100", "FSL-100", "FSL 100",
        "Firebeam", "BEAM",
        "40-40", "detector de llama", "flame detector",
        "FS24X", "FS20X", "FS24", "FS20",
        "SharpEye", "spectrex",
    ],
    "Detectores de aspiración": [
        "aspiración", "VESDA", "FAAST", "ICAM", "aspiration",
        "ASD", "Multiscann", "LaserSense",
    ],
    "Pulsadores": [
        "pulsador", "call point", "manual call", "M700KAC", "PUL-",
    ],
    "Sirenas y balizas": [
        "sirena", "baliza", "sounder", "beacon", "horn", "strobe",
        "evacuación", "PA/VA", "PA_VA", "AMSECO",
    ],
    "Módulos de lazo": [
        "módulo de lazo", "módulo monitor", "módulo de control",
        "loop module", "MAD-", "CMX", "CZX",
        "aislador", "isolator", "monitor module", "relay module",
        "M710", "M720", "M721", "M701",
        "SC6", "CZ6", "S300",
        "repetidor", "repeater", "IDR-",
        "transmisor", "transmitter", "GSM", "convertidor", "TG-IP",
        "tarjeta de relé", "tarjeta de rele", "relay board",
    ],
    "Fuentes de alimentación": [
        "fuente de alimentación", "power supply", "HLSPS", "PSU",
        "FAD-", "batería", "battery", "cargador",
    ],
    "Sistemas de extinción": [
        "extinción", "extinction", "suppression", "agente limpio",
        "SUPRA", "sprinkler", "descarga",
    ],
    "Software y programación": [
        "software", "VeriFire",
        "programa de configuración", "configuration tool",
        "UCIP", "ID3000 tool",
        "guía técnico", "technical guide",
    ],
    "Accesorios y cableado": [
        "accesorio", "zócalo", "socket", "cableado",
        "PK-8200", "Testifire", "LCD-8200", "AM-LCD",
        "indicador remoto", "remote indicator", "aerosol",
        "herramienta de diagnóstico", "diagnostic tool", "POL-200",
    ],
}


def detect_category(file_path: str, text: str = "", manufacturer: str = "") -> str:
    """Detect the product category using unified EN 54 taxonomy.

    Uses content/filename keyword matching as primary method, with
    legacy Detnov folder mapping as fallback for protocol detection.
    """
    # Strategy 0: Source-file override for known Morley files (most reliable)
    if manufacturer == "Morley":
        stem = Path(file_path).stem
        if stem in MORLEY_SOURCE_FILE_TO_CATEGORY:
            return MORLEY_SOURCE_FILE_TO_CATEGORY[stem]

    # Keyword-based detection from filename + content (most accurate)
    # Use up to 5000 chars of content to catch keywords beyond the first page
    filename = Path(file_path).stem.replace("_", " ").lower()
    search_text = (filename + " " + text[:5000]).lower()

    best_category = None
    best_score = 0

    for category, keywords in _CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in search_text)
        if score > best_score:
            best_score = score
            best_category = category

    if best_category and best_score >= 1:
        return best_category

    # Fallback: Legacy Detnov folder-based detection
    parts = Path(file_path).parts
    for part in parts:
        if part in _DETNOV_CATEGORY_MAP:
            return _DETNOV_CATEGORY_MAP[part]

    return "General"


def detect_protocol(text: str, file_path: str = "") -> str:
    """Detect protocol type: analógico or convencional."""
    search_text = (Path(file_path).stem + " " + text[:3000]).lower()

    # Folder-based (Detnov legacy)
    if "analógica" in str(file_path) or "analogica" in str(file_path).lower():
        return "analógico"
    if "convencional" in str(file_path).lower():
        return "convencional"

    # Content-based
    analog_kw = ["analógico", "analogico", "addressable", "direccionable", "lazo", "loop"]
    conv_kw = ["convencional", "conventional", "zona", "zone"]

    analog_score = sum(1 for kw in analog_kw if kw in search_text)
    conv_score = sum(1 for kw in conv_kw if kw in search_text)

    if analog_score > conv_score and analog_score >= 2:
        return "analógico"
    if conv_score > analog_score and conv_score >= 2:
        return "convencional"
    return ""


def detect_doc_type(file_path: str) -> str:
    """Detect document type from filename."""
    filename = Path(file_path).stem.replace("_", " ").replace("-", " ").lower()

    if any(kw in filename for kw in ["instalacion", "instalación", "installation", "instal", "commissioning", "comm"]):
        return "instalación"
    if any(kw in filename for kw in ["usuario", "user", "programacion", "programación", "programming",
                                       "operating", "configuration", "prog"]):
        return "usuario"
    if any(kw in filename for kw in ["mantenimiento", "maintenance", "servicio"]):
        return "mantenimiento"
    if any(kw in filename for kw in ["quick", "qref", "guia rapida", "guía rápida", "quick start"]):
        return "guía_rápida"
    if any(kw in filename for kw in ["nota", "technical note", "application", "bulletin"]):
        return "nota_técnica"
    # Default: try to detect from common patterns
    if any(kw in filename for kw in ["manual", "product guide", "handbook"]):
        return "usuario"
    return ""


def classify_content_type(text: str) -> str:
    """Classify the content type of a chunk based on keywords.

    Specification detection is boosted because spec keywords include numeric
    patterns (230VAC, 500mA, -5°C) that are highly specific indicators.
    """
    proc = len(PROCEDURE_KEYWORDS.findall(text))
    spec = len(SPEC_KEYWORDS.findall(text))
    trouble = len(TROUBLESHOOT_KEYWORDS.findall(text))
    wiring = len(WIRING_KEYWORDS.findall(text))

    # Spec matches with numeric values are stronger signals — boost by 50%
    # because wiring keywords ("salida", "entrada") also appear in spec sections
    scores = {
        "procedure": proc,
        "specification": int(spec * 1.5),
        "troubleshooting": trouble,
        "wiring": wiring,
    }
    best = max(scores, key=scores.get)
    if scores[best] >= 2:
        return best
    return "general"


def chunk_document(
    parsed: ParsedDocument,
    spanish_pages: list[PageContent],
    max_chunk_chars: int = 3000,
    min_chunk_chars: int = 100,
) -> list[Chunk]:
    """Split a parsed document into semantic chunks based on section headers.

    Strategy:
    1. Detect section headers
    2. Group text between headers into chunks
    3. If a chunk is too large, split at sub-section boundaries
    4. Track which pages have images (for diagram association)
    """
    if not spanish_pages:
        return []

    # Build a set of Spanish page numbers for filtering
    spanish_page_nums = {p.page_number for p in spanish_pages}

    # Get headers (only from Spanish pages)
    headers = detect_section_headers(parsed)
    headers = [h for h in headers if h["page_number"] in spanish_page_nums]

    # Remove TOC-style headers (those with dots/periods as separators)
    headers = [
        h for h in headers
        if not re.search(r"\.{3,}", h["text"])
    ]

    # Detect metadata — use first few pages for better keyword coverage
    first_page_text = parsed.pages[0].full_text if parsed.pages else ""
    # Concatenate first 5 pages for category/protocol detection
    multi_page_text = " ".join(
        p.full_text for p in parsed.pages[:5] if p.full_text
    )
    manufacturer = detect_manufacturer(parsed.file_path, first_page_text)
    product_model = detect_product_model(first_page_text, parsed.file_name, manufacturer)
    category = detect_category(parsed.file_path, multi_page_text, manufacturer)
    protocol = detect_protocol(multi_page_text, parsed.file_path)
    doc_type = detect_doc_type(parsed.file_path)

    # Build page text map (only Spanish pages) — uses combined text (PyMuPDF + pdfplumber + Vision)
    page_texts = {}
    pages_with_images = set()
    for page in spanish_pages:
        page_texts[page.page_number] = get_page_combined_text(page)
        if page.images:
            pages_with_images.add(page.page_number)

    # If no headers detected, chunk by page groups
    if not headers:
        return _chunk_by_pages(
            spanish_pages, product_model, category, parsed.file_name,
            pages_with_images, max_chunk_chars,
            manufacturer=manufacturer, protocol=protocol, doc_type=doc_type,
        )

    # Build sections from headers
    chunks = []
    sorted_pages = sorted(page_texts.keys())

    for i, header in enumerate(headers):
        start_page = header["page_number"]

        # End page is the page before the next header (same or higher level)
        if i + 1 < len(headers):
            end_page = headers[i + 1]["page_number"]
            # If next header is on the same page, still include this page
            if end_page == start_page:
                end_page = start_page
            else:
                end_page = end_page  # Include up to but content split at header
        else:
            end_page = sorted_pages[-1] if sorted_pages else start_page

        # Collect text for this section
        section_text = header["text"].strip() + "\n\n"
        section_pages = [p for p in sorted_pages if start_page <= p <= end_page]

        for pn in section_pages:
            text = page_texts.get(pn, "")
            if text.strip():
                section_text += text + "\n"

        section_text = section_text.strip()

        # Skip very short sections
        if len(section_text) < min_chunk_chars:
            continue

        # Check for diagrams in this section's pages
        diagram_pages = [p for p in section_pages if p in pages_with_images]

        # Split large sections
        if len(section_text) > max_chunk_chars:
            sub_chunks = _split_large_section(
                section_text, header["text"], max_chunk_chars
            )
            for j, sub_text in enumerate(sub_chunks):
                chunks.append(Chunk(
                    content=sub_text,
                    product_model=product_model,
                    category=category,
                    section_title=header["text"].strip(),
                    content_type=classify_content_type(sub_text),
                    manufacturer=manufacturer,
                    protocol=protocol,
                    doc_type=doc_type,
                    has_diagram=bool(diagram_pages),
                    diagram_pages=diagram_pages,
                    source_file=parsed.file_name,
                    start_page=start_page,
                    end_page=end_page,
                ))
        else:
            chunks.append(Chunk(
                content=section_text,
                product_model=product_model,
                category=category,
                section_title=header["text"].strip(),
                content_type=classify_content_type(section_text),
                manufacturer=manufacturer,
                protocol=protocol,
                doc_type=doc_type,
                has_diagram=bool(diagram_pages),
                diagram_pages=diagram_pages,
                source_file=parsed.file_name,
                start_page=start_page,
                end_page=end_page,
            ))

    # Assign indices
    for i, chunk in enumerate(chunks):
        chunk.chunk_index = i

    return chunks


def _split_large_section(text: str, title: str, max_chars: int) -> list[str]:
    """Split a large section into smaller chunks at paragraph boundaries."""
    paragraphs = re.split(r"\n\s*\n", text)

    chunks = []
    current = title + "\n\n"

    for para in paragraphs:
        if len(current) + len(para) > max_chars and len(current) > 200:
            chunks.append(current.strip())
            current = title + " (continuación)\n\n"

        current += para + "\n\n"

    if current.strip() and len(current.strip()) > 50:
        chunks.append(current.strip())

    return chunks if chunks else [text[:max_chars]]


def _chunk_by_pages(
    pages: list[PageContent],
    product_model: str,
    category: str,
    file_name: str,
    pages_with_images: set,
    max_chars: int,
    manufacturer: str = "",
    protocol: str = "",
    doc_type: str = "",
) -> list[Chunk]:
    """Fallback: chunk by grouping pages together."""
    chunks = []
    current_text = ""
    start_page = pages[0].page_number if pages else 1
    diagram_pages = []

    for page in pages:
        page_text = get_page_combined_text(page).strip()
        if not page_text:
            continue

        if len(current_text) + len(page_text) > max_chars and current_text:
            chunks.append(Chunk(
                content=current_text.strip(),
                product_model=product_model,
                category=category,
                section_title=f"Páginas {start_page}-{page.page_number - 1}",
                content_type=classify_content_type(current_text),
                manufacturer=manufacturer,
                protocol=protocol,
                doc_type=doc_type,
                has_diagram=bool(diagram_pages),
                diagram_pages=list(diagram_pages),
                source_file=file_name,
                start_page=start_page,
                end_page=page.page_number - 1,
            ))
            current_text = ""
            start_page = page.page_number
            diagram_pages = []

        current_text += page_text + "\n\n"
        if page.page_number in pages_with_images:
            diagram_pages.append(page.page_number)

    if current_text.strip():
        chunks.append(Chunk(
            content=current_text.strip(),
            product_model=product_model,
            category=category,
            section_title=f"Páginas {start_page}-{pages[-1].page_number}",
            content_type=classify_content_type(current_text),
            manufacturer=manufacturer,
            protocol=protocol,
            doc_type=doc_type,
            has_diagram=bool(diagram_pages),
            diagram_pages=list(diagram_pages),
            source_file=file_name,
            start_page=start_page,
            end_page=pages[-1].page_number,
        ))

    for i, chunk in enumerate(chunks):
        chunk.chunk_index = i

    return chunks


if __name__ == "__main__":
    import sys
    from .pdf_parser import parse_pdf
    from .language_filter import filter_spanish_pages

    if len(sys.argv) < 2:
        print("Usage: python -m src.ingestion.chunker <pdf_path>")
        sys.exit(1)

    parsed = parse_pdf(sys.argv[1])
    spanish_pages = filter_spanish_pages(parsed)
    chunks = chunk_document(parsed, spanish_pages)

    print(f"Document: {parsed.file_name}")
    print(f"Total pages: {parsed.total_pages}, Spanish pages: {len(spanish_pages)}")
    print(f"Total chunks: {len(chunks)}")
    if chunks:
        c0 = chunks[0]
        print(f"Product model: {c0.product_model}")
        print(f"Manufacturer: {c0.manufacturer}")
        print(f"Category: {c0.category}")
        print(f"Protocol: {c0.protocol or '(not detected)'}")
        print(f"Doc type: {c0.doc_type or '(not detected)'}")
    print()
    for c in chunks[:15]:
        diag = " [DIAGRAM]" if c.has_diagram else ""
        print(f"  [{c.chunk_index}] {c.content_type:15s} p.{c.start_page}-{c.end_page} "
              f"({len(c.content):5d} chars){diag} | {c.section_title[:60]}")
