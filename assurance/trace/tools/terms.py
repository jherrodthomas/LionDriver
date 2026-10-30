#!/usr/bin/env python3
"""Abbreviations and record codes: one list, defined the same way on every page and figure that uses them.

The standard (also stated on the generated page `assurance/terms.md`):

1. **One list.** Every abbreviation, and every record-code prefix such as `FSR-` or `TS-`, is defined once, in
   `TERMS` below. Nothing else defines them.
2. **Pages.** Each page in `PAGES` carries a "Terms on this page" block, generated from the list with only the terms
   that page uses. It sits right under the page's opening, folded, so it costs a phone reader one line. The prose
   still spells a term out where it first matters; the block is the backstop.
3. **Figures.** Each generated figure in `FIGURES` ends with a definitions line for the terms drawn in it, so a figure
   copied out of its page still explains itself. The generators call `svg_footer`.
4. **CI.** `terms.py --check` fails when a page block is stale, a figure lacks its definitions line, or a page or
   figure uses an abbreviation or code that is not in the list. Add it to `TERMS`, or, for an ordinary word written in
   capitals, to `NOT_TERMS`.

    python3 assurance/trace/tools/terms.py            # write the page blocks and assurance/terms.md
    python3 assurance/trace/tools/terms.py --check    # fail on a stale block, a missing footer or an undefined term

Standard library only.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

REPO = Path(__file__).resolve().parents[3]
A = REPO / "assurance"
TERMS_PAGE = A / "terms.md"

# Pages that carry a generated "Terms on this page" block, and generated figures that carry a definitions line.
PAGES = [
  A / "02-concept/item/README.md",
  A / "02-concept/ai/README.md",
  A / "03-system/hsi/README.md",
  A / "03-system/timing/README.md",
  A / "03-system/cybersecurity/README.md",
  A / "03-system/integration/README.md",
  A / "03-system/verification/README.md",
  A / "03-system/system-requirements/README.md",
  A / "03-system/production/README.md",
  A / "03-system/technical-safety-requirements/README.md",
  A / "02-concept/odd/README.md",
  A / "02-concept/cybersecurity/README.md",
  A / "02-concept/hara/README.md",
  A / "02-concept/fsc/README.md",
  A / "02-concept/sotif/README.md",
  A / "02-concept/tara/README.md",
  A / "03-system/tsc/README.md",
  A / "08-analyses/dfa/README.md",
  A / "models/autosar/README.md",
]
FIGURES = [
  A / "02-concept/figures/fig-c01-3-4-function-allocation.svg",
  A / "02-concept/figures/fig-c11-6-1-air-map.svg",
  A / "03-system/figures/fig-s03-3-3-functional-flow.svg",
  A / "03-system/figures/fig-s03-4-5-envelope-states.svg",
  A / "03-system/figures/fig-s03-7-1-ffi.svg",
  A / "03-system/figures/fig-s05-4-1-control-requests.svg",
  A / "03-system/figures/fig-s04-5-3-verdicts.svg",
  A / "03-system/figures/fig-s07-4-1-csr-status.svg",
  A / "03-system/figures/fig-s08-6-1-cases.svg",
  A / "03-system/figures/fig-s09-5-1-cases.svg",
  A / "03-system/figures/fig-s01-10-1-requirements.svg",
  A / "03-system/figures/fig-s06-3-1-lifecycle.svg",
  A / "03-system/figures/fig-s02-2-1-allocation.svg",
  A / "02-concept/figures/fig-c02-5-1-odd-exits.svg",
  A / "02-concept/figures/fig-c10-6-1-concept-view.svg",
  A / "02-concept/fsc/figures/fig-c04-10-1-safety-view.svg",
  A / "02-concept/fsc/figures/fig-c04-12-1-degradation-ladder.svg",
  A / "02-concept/hara/figures/fig-c03-3-1-situations.svg",
  A / "02-concept/hara/figures/fig-c03-4-9-function-hazard-view.svg",
  A / "02-concept/figures/fig-c05-6-1-sotif-lineup.svg",
  A / "02-concept/figures/fig-c06-4-1-odd-sotif-view.svg",
  A / "02-concept/figures/fig-c09-1-1-cybersecurity-view.svg",
  A / "03-system/figures/fig-s03-6-2-safety-mechanisms.svg",
  A / "08-analyses/dfa/fig-dfa-1-boundary.svg",
  A / "08-analyses/dfa/fig-dfa-2-method.svg",
  A / "08-analyses/dfa/fig-dfa-3-gaps.svg",
  A / "08-analyses/dfa/fig-dfa-4-gates.svg",
  A / "08-analyses/dfa/fig-dfa-5-example.svg",
]

# Term -> meaning. A key ending in "-" is a record-code prefix (FSR- matches FSR-01.05). A key ending in "#" is a
# class written as a letter and digits (S# matches S0…S3). Everything else is an abbreviation matched as a word.
TERMS = {
  # standards, methods and analyses
  "ASIL": "Automotive Safety Integrity Level, A (lowest) to D (highest), from ISO 26262",
  "QM": "quality managed: no ASIL; ordinary quality processes suffice",
  "HARA": "hazard analysis and risk assessment (ISO 26262-3)",
  "FSC": "functional safety concept",
  "TSC": "technical safety concept",
  "SOTIF": "safety of the intended functionality (ISO 21448): hazards with nothing failing",
  "TARA": "threat analysis and risk assessment (ISO/SAE 21434)",
  "HATARA": "the joint HARA and TARA view: where hazards and threats meet",
  "STPA": "system-theoretic process analysis",
  "FMEA": "failure mode and effects analysis",
  "FMEDA": "failure modes, effects and diagnostic analysis (hardware metrics)",
  "FTA": "fault tree analysis",
  "DFA": "dependent failure analysis",
  "FFI": "freedom from interference",
  "STRIDE": "spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege",
  "ISO": "International Organization for Standardization",
  "SAE": "SAE International (formerly the Society of Automotive Engineers)",
  "FRET": "NASA's Formal Requirements Elicitation Tool",
  "ODD": "operational design domain: where the system is meant to work",
  "ODD-H": "the claimed ODD: limited-access highways",
  "FTTI": "fault-tolerant time interval: fault to hazard, the time a safety mechanism has",
  "FDTI": "fault detection time interval",
  "FRTI": "fault reaction time interval",
  "FHTI": "fault handling time interval: FDTI + FRTI",
  "DC": "diagnostic coverage: the share of faults a safety mechanism detects",
  "CAL": "cybersecurity assurance level, 1 to 4 (ISO/SAE 21434)",
  "SC": "safety-critical (a guide-word pair that can cause a hazard)",
  "NSC": "not safety-critical",
  "NA": "not applicable",
  "HSI": "hardware-software interface",
  "CI": "continuous integration: the checks that run on every pull request",
  "ID": "identifier",
  # vehicle and item
  "LD-SDA": "LionDriver Supervised Driving Assistance, the item",
  "TSS": "Toyota Safety Sense (TSS 2.0: the car's stock lane assist, radar cruise and pre-collision package)",
  "VIN": "vehicle identification number",
  "US": "United States",
  "SoC": "system on chip: the comma device's main processor, running openpilot (QM)",
  "MCU": "microcontroller: the panda safety processor (STM32H7)",
  "E/E": "electrical and electronic (systems)",
  "ECU": "electronic control unit",
  "EPS": "electric power steering",
  "PCM": "powertrain control module (engine and drive)",
  "ECM": "engine control module",
  "CLU": "instrument cluster",
  "PCS": "pre-collision system: Toyota's stock collision warning and braking",
  "AEB": "automatic emergency braking",
  "ACC": "adaptive cruise control",
  "ADC": "analogue-to-digital converter (in the safety MCU: orientation, supply and health readings)",
  "LKA": "lane keeping assist",
  "LKAS": "lane keeping assist system",
  "HUD": "head-up display (here the cluster's lane-assist display)",
  "FCW": "forward collision warning",
  "DSU": "driving support unit (Toyota's radar cruise module)",
  "CAN": "controller area network: the vehicle's data bus",
  "FDCAN": "CAN with flexible data rate (the MCU's CAN controller)",
  "DBC": "CAN database file: the frames, signals, scaling and bit layout of a car's CAN messages (opendbc)",
  "PDU": "protocol data unit: the payload of a frame (AUTOSAR I-PDU)",
  "SecOC": "secure onboard communication: AUTOSAR's message authentication for in-vehicle buses",
  "MQB": "Volkswagen's transverse modular platform (Modularer Querbaukasten)",
  "AUTOSAR": "AUTomotive Open System ARchitecture: the automotive software standard; Classic Platform for ECUs",
  "ARXML": "AUTOSAR XML: the file format AUTOSAR tools exchange",
  "XML": "extensible markup language",
  "RTE": "AUTOSAR runtime environment: the layer that connects software components to each other and to basic software",
  "OEM": "original equipment manufacturer: the carmaker",
  "CSAR": "configuration, software and architecture repository: the project lead's Tier-1 toolchain term, not an AUTOSAR one",
  "OBD": "on-board diagnostics port",
  "OBD-II": "on-board diagnostics port",
  "ABS": "anti-lock braking system; on the Toyota, the ABS/VSC ECU that also runs stability control",
  "DTC": "diagnostic trouble code: a fault code an ECU stores, read with a scan tool or over UDS",
  "UDS": "unified diagnostic services (ISO 14229): the diagnostic protocol used to read ECU versions and fault codes",
  "TX": "transmit",
  "RX": "receive",
  "SPI": "serial peripheral interface (the link between SoC and MCU)",
  "IPC": "inter-process communication",
  "HMI": "human-machine interface: display, sounds, cluster",
  "DM": "driver monitoring",
  "DRV": "the driver",
  "ML": "machine learning",
  "ONNX": "Open Neural Network Exchange, the model file format",
  "SHA-256": "a cryptographic hash used to identify a file exactly",
  "TBC": "to be confirmed",
  "MDN": "mixture density network (how the model reports a spread of possible values)",
  "GPU": "graphics processor (runs the models)",
  "GPS": "global positioning system",
  "RTK": "real-time kinematic GPS, accurate to centimetres",
  "EV": "exposure value: one EV halves or doubles the light",
  "JPEG": "a compressed image format",
  "HEVC": "a compressed video format (H.265)",
  "OOD": "out of distribution: unlike the data the model learned from",
  "PAS": "publicly available specification (ISO/PAS 8800 is the AI safety one)",
  "AI": "artificial intelligence",
  "VSC": "vehicle stability control (Toyota's stability system)",
  "eGPU": "external graphics processor (the optional big-model hardware)",
  "LFS": "Git Large File Storage (where the model files live)",
  "GNSS": "global navigation satellite system (GPS)",
  "VRU": "vulnerable road user: pedestrian or cyclist",
  "AGNOS": "the comma device's operating system",
  "MPU": "memory protection unit",
  "RDP": "read-out protection of the MCU's flash (option bytes)",
  "WRP": "write protection of the MCU's flash (option bytes)",
  "RAM": "random-access memory",
  "ECC": "error-correcting code (memory)",
  "CRC": "cyclic redundancy check",
  "CSS": "clock security system (MCU clock monitor)",
  "BOR": "brown-out reset (MCU supply monitor)",
  "PVD": "programmable voltage detector (MCU supply monitor)",
  "RT": "real time",
  "FW": "firmware",
  "SW": "software",
  "HW": "hardware",
  "OTA": "over-the-air (software update)",
  "RPC": "remote procedure call",
  "SSH": "secure shell (remote login)",
  "JWT": "JSON web token (the device's login token to the back end)",
  "AoU": "assumption of use: what the analysis assumes about the car, the driver or the environment",
  "HIL": "hardware in the loop: the bench with the real panda and simulated car buses",
  "SysML": "Systems Modeling Language: the system model in models/sysml",
  "ECDSA": "elliptic-curve digital signature algorithm",
  "P-256": "the NIST elliptic curve used with ECDSA (128-bit security)",
  "ENV": "build and release environment (allocation class, WP-S-07 §2)",
  "USR": "owner, installer or maintainer acting under a procedure (allocation class)",
  "UI": "user interface: the device's screen",
  "TLS": "transport layer security: encrypted network connections",
  "SBOM": "software bill of materials: the list of every component and version",
  "PC": "personal computer",
  "NaN": "not a number: an invalid floating-point value",
  "IMU": "inertial measurement unit: accelerometers and gyroscopes",
  "SYS": "system requirement SYS-nnn of WP-S-01",
  "T-SIL": "verification by software test or process replay (WP-S-01 §1.1)",
  "R-DEV": "installation record block: device and harness (WP-O-01 §5)",
  "R-VEH": "installation record block: vehicle (WP-O-01 §5)",
  "R-INS": "installation record block: installation work (WP-O-01 §5)",
  "R-SW": "installation record block: software and firmware (WP-O-01 §5)",
  "R-CFG": "installation record block: configuration (WP-O-01 §5)",
  "R-CAL": "installation record block: calibration (WP-O-01 §5)",
  "R-FUN": "installation record block: function checks (WP-O-01 §5)",
  "R-USR": "installation record block: driver briefing (WP-O-01 §5)",
  "T-HIL": "verification by bench test with the real panda (hardware in the loop)",
  "T-VEH": "verification by vehicle test",
  "LOG": "verification by analysis of drive logs",
  "TBD": "to be determined: a value not yet set",
  "LDW": "lane departure warning",
  "GiB": "gibibyte (2³⁰ bytes)",
  "SIM": "verification by scenario simulation",
  "SILENT": "the panda's safety mode that sends nothing",
  "XOR": "exclusive or: a simple checksum that misses many multi-bit errors",
  "ACK": "acknowledge (NACK: not acknowledge)",
  "NACK": "not acknowledge",
  "ST": "STMicroelectronics, the maker of the safety MCU",
  "ROM": "read-only memory",
  "DMA": "direct memory access: hardware that copies data without the processor",
  "DTCM": "the MCU's tightly coupled data memory, where the safety state lives",
  "FD": "flexible data rate (CAN FD: CAN with a faster data phase and up to 64 bytes)",
  "GPIO": "general-purpose input/output pin",
  "IRQ": "interrupt request",
  "IR": "infrared",
  "UID": "unique identifier of the chip",
  "SHA-1": "secure hash algorithm 1, an outdated hash",
  "RSA-1024": "RSA signature with a 1024-bit key, too short today",
  "NRST": "the MCU's reset line (BOOT0 is its boot-mode line)",
  "ISR": "interrupt service routine",
  "IWDG": "independent watchdog of the MCU",
  "WCET": "worst-case execution time",
  "PCB": "printed circuit board",
  "EMC": "electromagnetic compatibility: interference between electrical parts and wiring",
  "HSE": "high-speed external oscillator: the crystal that clocks the panda MCU",
  "NOOUTPUT": "the panda's safety mode that receives but sends nothing",
  "TOYOTA": "the panda's Toyota car mode (parameter 73 in the reference build)",
  "ALLOWED": "the envelope's authority state with controls_allowed = 1 (NOT_ALLOWED: 0), WP-W-05 §5.2",
  # files and repository
  "CSV": "comma-separated values file",
  "SVG": "scalable vector graphics (the figure format)",
  "MB": "megabyte",
  "PR": "pull request",
  "URL": "web address",
  "NUL": "null byte",
  # record-code prefixes
  "CFG-": "vehicle configuration in the vehicle register (CFG-001 is the reference Corolla)",
  "PL-": "platform (PL-001 is LionDriver's)",
  "VF-": "vehicle family in the vehicle register",
  "WP-": "work product, e.g. WP-C-04; the letter is its area (M management, C concept, S system, H hardware, W software, V validation, P processes, A analyses, O operation, K safety case)",
  "F-": "function of the item (WP-C-01 §2.1), F-01…F-09",
  "E-": "element of the item (WP-C-01 §3.1), E-01…E-06",
  "EXT-": "external element credited only through an assumption of use (EXT-EPS, EXT-PCM, EXT-CLU)",
  "IF-": "interface of the item (WP-C-01 §3.4)",
  "S-": "safety-relevant signal across the hardware-software interface or the item boundary (WP-S-05 §11), S-01…S-29",
  "AOU-": "assumption of use (WP-C-01 §7); an R suffix marks the FSC's refined version",
  "H-": "hazard (HARA)",
  "HE-": "hazardous event (HARA)",
  "OS-": "operational situation (HARA §3)",
  "SG-": "safety goal (HARA §6)",
  "SN-": "stakeholder need (WP-S-01 §1.3), SN-01…SN-12",
  "UC-": "use case (WP-S-01 §1.4), UC-01…UC-11",
  "FSR-": "functional safety requirement (FSC)",
  "TSR-": "technical safety requirement (WP-S-02)",
  "SWSR-": "software safety requirement (WP-W-02)",
  "HWSR-": "hardware safety requirement (WP-H-01)",
  "SM-": "safety mechanism (TSC §6)",
  "T-": "code-derived detection or reaction time (WP-S-04 §4); in WP-M-01 and WP-S-06, a tailoring decision T-01…T-08 (WP-M-01 §5)",
  "M-": "timing measurement of the plan in WP-S-04 §6",
  "TB-": "trust boundary (WP-S-07 §3.2)",
  "ST-": "step of the start-up and engagement sequence (WP-S-03 Table 4-1), ST-01…ST-21",
  "CS-": "cybersecurity architecture decision CS-AD-nn (WP-S-07 §3.4)",
  "V-": "view of the SysML model (V-01…V-27)",
  "UPD-": "update procedure step (WP-O-02)",
  "I-": "integration step I-1…I-4 (WP-S-08 §3.1)",
  "GC-": "global pass criterion of every integration test (WP-S-08 §5)",
  "VS-": "verification case: VS-SI system integration, VS-HW hardware, VS-SWQ software, VS-FI fault injection, VS-SQ system qualification",
  "IND-": "independence claim (WP-S-03 §7)",
  "SS-": "safe state (FSC §6): SS-L lateral, SS-G longitudinal, SS-S envelope silent",
  "SH-": "SOTIF hazard (WP-C-05)",
  "FI-": "functional insufficiency (WP-C-06)",
  "TC-": "triggering condition (WP-C-06)",
  "FM-": "functional modification (WP-C-07)",
  "AC-": "acceptance criterion (WP-C-05 §5.3)",
  "VT-": "validation target (WP-V-02)",
  "KS-": "known scenario (WP-V-03)",
  "AS-": "asset (TARA §2)",
  "DS-": "damage scenario (TARA §3)",
  "TS-": "threat scenario (TARA §4)",
  "AP-": "attack path (TARA §5); in WP-S-03 and on the TSC page, an architectural principle (WP-S-03 §2)",
  "AI-": "AI component (WP-C-11 §2.1): AI-1 driving model, AI-2 big driving model (excluded), AI-3 driver monitoring model",
  "AIR-": "AI safety requirement (WP-C-11 §6)",
  "DSR-": "dataset requirement (WP-C-11 §7)",
  "AE-": "AI error type (WP-C-11 §5)",
  "RM-": "runtime monitor of the AI safety plan (WP-M-10)",
  "DMP-": "driver monitoring performance requirement (WP-C-08 §5)",
  "INS-": "installation check (WP-O-01)",
  "P-SW": "allocation to the panda firmware: the envelope on the safety MCU (E-03; WP-S-02 §2.2)",
  "P-HW": "allocation to the panda hardware: the safety MCU (E-04; WP-S-02 §2.2)",
  "HAR": "allocation to the harness and relay (E-05; WP-S-02 §2.2)",
  "OPS": "allocation to a production or operation process (WP-S-02 §2.2)",
  "EXT": "allocation to an existing vehicle element, credited only through an assumption of use (WP-S-02 §2.2)",
  "SPC-": "special characteristic of the installation (WP-O-01 §4)",
  "OPS-": "operation step: the driver's pre-drive and field checks (WP-O-02 §3)",
  "SVC-": "vehicle service action that needs a re-check of the item (WP-O-02 §4)",
  "PM-": "periodic maintenance check of the item (WP-O-02 §4)",
  "ITS-": "item service step: replacing a faulty device or harness (WP-O-02 §5)",
  "DEC-": "decommissioning step (WP-O-02 §7)",
  "LTA": "lane tracing assist: Toyota's stock lane-centring function",
  "LDA": "lane departure alert: Toyota's stock lane warning",
  "DRCC": "dynamic radar cruise control: Toyota's stock adaptive cruise",
  "CSG-": "cybersecurity goal (WP-C-10)",
  "CSR-": "cybersecurity requirement: CSR-C-nn at concept level (WP-C-10 §7), CSR-nnn refined (WP-S-07)",
  "CSC-": "cybersecurity claim: a risk retained, shared or avoided, with its condition (WP-C-10 §5)",
  "CA-": "cybersecurity assumption on an entity outside the item (WP-C-10 §2)",
  "IX-": "safety-security interaction (HATARA)",
  "DQ-": "decision of the project lead (decision register)",
  "D-": "design decision of the earlier decision list (D-01…D-12; D-08 is the Experimental Mode decision)",
  "GAP-": "gap found by the gap assessment",
  "GD-": "private record of an unfixed weakness's code locations and mechanism, held until its control is verified (WP-O-05 §4.4)",
  "OI-": "open item of the document it appears in",
  "DFI-": "dependent failure initiator (WP-A-03 §4): one cause that could defeat two elements at once",
  "IC-": "independence claim (WP-A-03 §2): two elements the safety concept relies on not failing together",
  "R-": "shared resource in the DFA map (08-analyses/dfa/shared-resources.yaml): something two elements both depend on",
  "BE-": "basic event of a WP-A-04 fault tree",
  "UE-": "undeveloped event of a WP-A-04 fault tree",
  "G-": "named gate of a WP-A-04 fault tree (G-SIREN, G-LATCUE); numbered gates read G1.1, G2.3 …",
  "RR-": "review record",
  "NF-": "finding of the onboard code review",
  "TL-": "tool entry in the tool register (WP-P-07)",
  # classes written as a letter and digits
  "S#": "severity class S0 (no injuries) to S3 (life-threatening)",
  "E#": "exposure class E0 (incredible) to E4 (high probability)",
  "C#": "controllability class C0 (controllable in general) to C3 (difficult or uncontrollable)",
  "M#": "guide word M01…M14 of the HARA (no function, unrequested, excessive, …); M1…M8 (one digit) a safety-mode transition (WP-W-05 §5.1)",
  "W#": "weather and surface condition W01…W06 (HARA §3.1)",
  "L#": "degradation level L0 (full function) to L5 (lockout), FSC §12.1",
  "P#": "priority of a functional modification: P1 before on-road use, P2 before release, P3 decide at G2",
  "G#": "gate G0…G6 of the project lifecycle",
  "I#": "independence level of a review, I0 (none, e.g. the author or an AI) to I3 (independent organisation)",
}

# Ordinary words that the pages or figures write in capitals, and names that are not abbreviations.
NOT_TERMS = {
  # code names quoted in requirement statements (build flags, params, modes)
  "RELEASE", "ALLOUTPUT", "SshEnabled", "UpdaterTargetBranch", "DisableUpdates",
  "ACCEPTANCE", "ACTION", "AGENT", "AND", "BOUNDARY", "BY", "CONDITIONS", "CONSTRAINT", "DRIVER", "ENTERED", "EXAMPLES",
  "EXPOSURE", "FUNCTION", "FUNCTIONS", "GOALS", "HAZARD", "HAZARDS", "HIGHEST", "HOW", "INFORMATION", "INSUFFICIENCIES",
  "IS", "IT", "ITEM", "LATERAL", "LEFT", "LEVEL", "LONGITUDINAL", "MODAL", "MODIFICATIONS", "OBJECT", "RANGE", "READ",
  "SAFE", "SITUATION", "SITUATIONS", "SPEED", "STATES", "SURFACE", "TO", "TRIGGER", "TRIGGERING", "VALIDATION",
  "WEATHER", "WHAT", "SAFETY", "GOAL", "SOTIF HAZARD", "ELEMENT", "STATE", "THE", "OF", "VIEW", "IN", "ON", "AT",
  "WAY", "OUT", "DOES", "NOTICE", "TODAY", "CLOSES", "BRAKE",
  "LionDriver", "GitHub", "LibreOffice", "README", "II", "IsDriverViewEnabled", "CarParams", "DisengageOnAccelerator",
}

WORD_RE = re.compile(r"(?<![\w-])([A-Za-z]*[A-Z][A-Za-z]*[A-Z][A-Za-z]*(?:-[A-Z]+)?)(?![\w])")
CODE_RE = re.compile(r"(?<![\w-])(WP|[A-Z]{1,4})(?:-[A-Z]{1,2})?-(?=\d|[A-Z]{2,})")
CLASS_RE = re.compile(r"(?<![\w-])([SECMWLPGI])\d{1,2}(?![\w.])")


def plain_markdown(s: str) -> str:
  """Page text a reader sees: no code, link targets, comments or generated term blocks."""
  s = re.sub(r"<!-- terms:start.*?<!-- terms:end -->", " ", s, flags=re.S)
  s = re.sub(r"```.*?```", " ", s, flags=re.S)
  s = re.sub(r"`[^`]*`", " ", s)
  s = re.sub(r"\]\([^)]*\)", "]", s)
  s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
  s = re.sub(r"https?://\S+", " ", s)
  return s


def svg_texts(svg: str, footer: bool = False) -> str:
  """The visible text of an SVG, without the definitions footer unless asked for."""
  if not footer:
    svg = re.sub(r'<g class="terms">.*?</g>', " ", svg, flags=re.S)
  return " ".join(html.unescape(m) for m in re.findall(r"<text[^>]*>([^<]*)</text>", svg))


def find(text: str) -> tuple[list[str], list[str]]:
  """(known terms in order of first use, unknown tokens) of a text."""
  found: list[str] = []
  unknown: list[str] = []

  def add(key):
    if key not in found:
      found.append(key)

  hits = []
  for m in CODE_RE.finditer(text):
    whole = re.match(r"[A-Z]+-[A-Z0-9]+\b", text[m.start():])
    hits.append((m.start(), whole.group(0) if whole and whole.group(0) in TERMS else m.group(1) + "-"))
  for m in CLASS_RE.finditer(text):
    hits.append((m.start(), m.group(1) + "#"))
  for m in re.finditer(r"(?<![\w/])E/E(?![\w/])", text):
    hits.append((m.start(), "E/E"))
  for m in WORD_RE.finditer(text):
    w = m.group(1)
    if text[m.end():m.end() + 1] == "-" and re.match(r"-[\dA-Z]", text[m.end():m.end() + 2]):
      continue                       # a code prefix, matched above
    hits.append((m.start(), w))
  for _, k in sorted(hits):
    if k in TERMS:
      add(k)
    elif k.endswith("-") and k[:-1] in TERMS:
      add(k[:-1])
    elif k in NOT_TERMS or k.split("-")[0] in NOT_TERMS:
      continue
    elif k[0].islower():               # a code identifier such as speedTooHigh, not an abbreviation
      continue
    elif k + "-" in TERMS:              # a record prefix written as a word: "FSR", "the SM catalogue"
      add(k + "-")
    elif k.endswith("s") and k[:-1] in TERMS:
      add(k[:-1])
    elif k.endswith("s") and k[:-1] + "-" in TERMS:
      add(k[:-1] + "-")
    elif "-" in k and k.split("-")[0] + "-" in TERMS:   # a code with a letter suffix: SS-L, EXT-EPS
      add(k.split("-")[0] + "-")
    elif "-" in k and k.split("-")[0] in TERMS:
      add(k.split("-")[0])
    elif k not in unknown:
      unknown.append(k)
  return found, unknown


def label(key: str) -> str:
  if key.endswith("#"):
    return {"S#": "S0–S3", "E#": "E0–E4", "C#": "C0–C3", "M#": "M01–M14, M1–M8", "W#": "W01–W06", "L#": "L0–L5",
            "P#": "P1–P3", "G#": "G0–G6", "I#": "I0–I3"}[key]
  return key + "nn" if key.endswith("-") else key


def page_block(keys: list[str]) -> str:
  keys = sorted(keys, key=lambda k: label(k).lower())
  rows = "\n".join(f"| {label(k)} | {TERMS[k]} |" for k in keys)
  return ("<!-- terms:start (generated by assurance/trace/tools/terms.py; do not edit by hand) -->\n"
          f"<details><summary>Terms on this page ({len(keys)})</summary>\n\n"
          "| Term | Meaning |\n|---|---|\n" + rows +
          "\n\nAll terms: [abbreviations and record codes](" + "{rel}" + ").\n\n</details>\n<!-- terms:end -->")


def svg_footer(body: list[str], x: float, y: float, width: float, size: float = 10.5) -> tuple[list[str], float]:
  """Definitions line for the terms in a figure body: returns (svg elements, new y). Call before the closing lines."""
  keys, _ = find(svg_texts("\n".join(body)))
  if not keys:
    return [], y
  text = "Terms: " + " · ".join(f"{label(k)} {TERMS[k]}" for k in sorted(keys, key=lambda k: label(k).lower()))
  per_line = int(width / (size * 0.53))
  lines, line = [], ""
  for word in text.split(" "):
    cand = (line + " " + word).strip()
    if len(cand) > per_line and line:
      lines.append(line)
      line = word
    else:
      line = cand
  lines.append(line)
  out = ['<g class="terms">']
  for i, ln in enumerate(lines):
    out.append(f'<text x="{x:g}" y="{y + i * (size + 4):g}" font-size="{size:g}" fill="#475569">{escape(ln)}</text>')
  out.append("</g>")
  return out, y + len(lines) * (size + 4)


def terms_page() -> str:
  words = sorted((k for k in TERMS if not k.endswith(("-", "#"))), key=str.lower)
  codes = sorted((k for k in TERMS if k.endswith("-")), key=str.lower)
  classes = [k for k in TERMS if k.endswith("#")]
  out = ["<!-- Generated by assurance/trace/tools/terms.py; do not edit by hand. -->", "", "# Abbreviations and record codes", "",
         "Every abbreviation and record code used on the assurance pages and figures is defined here, once. "
         "The list lives in [`trace/tools/terms.py`](trace/tools/terms.py); this page is written from it.", "",
         "## How terms are defined for readers", "",
         "1. **One list.** A term is defined only in `TERMS` in `terms.py`.",
         "2. **On every page.** Each page in the list carries a folded \"Terms on this page\" block under its opening, "
         "written from the list with only the terms that page uses. The prose still spells a term out where it first "
         "matters.",
         "3. **On every figure.** Each generated figure ends with a \"Terms:\" line for what it draws, so a figure read "
         "on its own still explains itself.",
         "4. **Checked.** CI fails if a block is stale, a figure lacks its line, or a page or figure uses a term that "
         "is not in the list. To add one, add it to `TERMS` and run `python3 assurance/trace/tools/terms.py`.", "",
         "Pages covered: " + ", ".join(f"[{p.parent.name}]({p.relative_to(A).as_posix()})" for p in PAGES) + ". "
         "Other pages and older figures join the list as they are reworked.", "",
         "## Abbreviations", "", "| Term | Meaning |", "|---|---|"]
  out += [f"| {k} | {TERMS[k]} |" for k in words]
  out += ["", "## Record codes", "", "A record code is a prefix and a number, for example `FSR-01.05`.", "",
          "| Code | Meaning |", "|---|---|"]
  out += [f"| {label(k)} | {TERMS[k]} |" for k in codes]
  out += ["", "## Classes", "", "| Class | Meaning |", "|---|---|"]
  out += [f"| {label(k)} | {TERMS[k]} |" for k in classes]
  return "\n".join(out) + "\n"


def updated_page(path: Path) -> tuple[str, list[str]]:
  s = path.read_text(encoding="utf-8")
  keys, unknown = find(plain_markdown(s))
  block = page_block(keys).replace("{rel}", _rel(path))
  m = re.search(r"<!-- terms:start.*?<!-- terms:end -->", s, flags=re.S)
  if m:
    s = s[:m.start()] + block + s[m.end():]
  else:
    # under the opening: after the first paragraph that follows the H1
    parts = s.split("\n\n")
    i = next(n for n, p in enumerate(parts) if p.startswith("# ")) + 1
    while i < len(parts) and not parts[i].strip():
      i += 1
    parts.insert(i + 1, block)
    s = "\n\n".join(parts)
  return s, unknown


def _rel(path: Path) -> str:
  depth = len(path.relative_to(A).parts) - 1
  return "/".join([".."] * depth + ["terms.md"])


def main(argv: list[str]) -> int:
  check = "--check" in argv
  problems = []
  page = terms_page()
  if check:
    if not TERMS_PAGE.exists() or TERMS_PAGE.read_text(encoding="utf-8") != page:
      problems.append("assurance/terms.md is stale")
  else:
    TERMS_PAGE.write_text(page, encoding="utf-8")
  for p in PAGES:
    new, unknown = updated_page(p)
    if unknown:
      problems.append(f"{p.relative_to(REPO)}: not in TERMS: {', '.join(unknown)}")
    if check:
      if new != p.read_text(encoding="utf-8"):
        problems.append(f"{p.relative_to(REPO)}: terms block missing or stale")
    else:
      p.write_text(new, encoding="utf-8")
  for f in FIGURES:
    svg = f.read_text(encoding="utf-8")
    _, unknown = find(svg_texts(svg))
    if unknown:
      problems.append(f"{f.relative_to(REPO)}: not in TERMS: {', '.join(unknown)}")
    if '<g class="terms">' not in svg:
      problems.append(f"{f.relative_to(REPO)}: no definitions line (the generator must call terms.svg_footer)")
  for pr in problems:
    print(f"terms: {pr}", file=sys.stderr)
  if problems:
    print("run: python3 assurance/trace/tools/terms.py, after adding any missing term to TERMS", file=sys.stderr)
    return 1
  print(f"terms: {len(TERMS)} terms; {len(PAGES)} pages and {len(FIGURES)} figures define what they use")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
