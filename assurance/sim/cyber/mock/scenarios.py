"""What the mock dashboards draw for each threat scenario that is not read from the documents.

compose.py reads the TARA facts itself: the threat text, STRIDE, the violated and the asset properties, the damage
scenarios with their impact and HARA link, the feasibility factors, the risk value, the treatment decision and the goal
with its CAL (WP-C-09 and WP-C-10, through ../../../02-concept/figures/fig_c09_scenes.py), and the gate states
(WP-S-07 §4, through ../figures/fig_cy_iso.py). This file holds the drawing: short labels, which requirements sit on
which boundary, where the labels go on the cutaway, which plant cases stand for the consequence, and the paraphrased
treatment lines, each of which names its source. Synthetic (DSR-12), no evidence credit.
"""

SCENARIOS = {
  "TS-14": dict(
    slug="cy-ts-14-tx-flood", ap="AP-14",
    subtitle="Compromised SoC sends in-limit steering frames far above their nominal rate through the panda (AP-14)",
    entry="Entry: root on the SoC, assumed (AP-14 is rated given SoC code execution) · GAP-42",
    handoff="Plant F-01b (panda code in loop)",
    cal_flag="CAL 2 → 3?  OI-8",                                   # WP-C-10 OI-8: re-derive the CAL of CSG-05
    treatment=[("Direction", "Remove PCS/DSU IDs from the TX allow-list (TSR-705); supervise the TX rate per ID (TSR-518)"),
               ("Status", "Both built in the reference build only; not verified on hardware"),
               ("Residual", "In-limit actuation within the rate budget, bounded by the envelope limits")],  # WP-C-09 §8
    treatment_sub="not verified",
    cut_tags=[("soc", "SoC board, exploded (Z2)", 120, -10, False), ("panda", "panda safety MCU, exploded (Z1)", -20, 70, False),
              ("device", "comma device on the windshield", 150, -20, False), ("harness", "harness box + relay (TB-5)", -150, 30, False),
              ("fcam", "forward camera, stock PCS (bus 2)", 140, -60, False), ("eps", "EPS motor + ECU (Z5)", 150, -40, True),
              ("abs", "brake ECU", 40, -50, False), ("obd", "OBD-II port", 95, -38, False)],
    gate_pills=[("gate", -185, -20, "Gate CSR-092: TX allow-list + per-ID rate", "partial: reference build only, not verified")],
    banner="TS-14 path: SoC → TB-1 → panda (gate) → harness relay → car bus 0 → EPS",
    gates=[("CSR-092", "TX allow-list + per-ID rate"), ("CSR-061", "envelope independent of SoC values"),
           ("CSR-093", "relay check on intercepted IDs"), ("CSR-063", "one publisher per topic (foothold)")],
    lens=["Credited: none verified, so the path reaches the car.", "As built (ref. build): expected to stop at S4; not yet run."],
    consequence="image",
    plots="f01b",
    iso_title="Attack path, isometric (WP-C-09 AP-14 at the §5 level)",
    precursors=[("TS-06", "malicious update"), ("TS-08", "SSH access"), ("TS-09", "tampered model"), ("TS-10", "supply chain")],
    zones=[("S3", "SoC host · Z2", "root, assumed"), ("S4", "Envelope · Z1", "panda filters TX"),
           ("S5", "Vehicle · Z5", "frames on bus 0"), ("G", "DS-01 → H-01", "hard-over (plant)")],
    walls=[(0, ("CSR-092", "CSR-061")), (1, ("CSR-093",))],      # wall after zone i, and the requirements on it
    branch=None,
    tags=["item sees: nothing", "item sees: TX refused (ref.)", "credited: reaches EPS", "driver corrects +{corr} s"],
    footer="the consequence reuses layer-1 case F-01b (real panda code), because the flood fault kind is not built.",
  ),
  "TS-06": dict(
    slug="cy-ts-06-update", ap="AP-06",
    subtitle="A malicious update is installed through the git-branch OTA path (AP-06); the installed software then drives the car",
    entry="Entry: control of the update source or branch, or an on-path position (outside the item) · GAP-26",
    handoff="Plant F-01b, L-01, L-03, F-04b",
    cal_flag=None,
    treatment=[("Direction", "Replace the git-branch updater with a signed release manifest checked on the device (CSR-121; DQ-075)"),
               ("Status", "Not implemented; until then automatic updates are off and installs are manual (CSR-124, WP-O-02 UPD-02)"),
               ("Residual", "Not stated for TS-06 in WP-C-09 §8; not re-rated (OI-5)")],
    treatment_sub="not built",
    cut_tags=[("src", "update source / on-path (Z4, outside the item)", 20, 66, False),
              ("soc", "SoC board: updater and openpilot (Z2/Z3)", -10, 58, False),
              ("panda", "panda safety MCU, exploded (Z1)", -150, 40, False),
              ("device", "comma device on the windshield", 150, -20, False), ("harness", "harness box + relay (TB-5)", -150, 30, False),
              ("eps", "EPS motor + ECU (Z5)", 150, -40, True), ("abs", "brake ECU", 40, -50, False), ("obd", "OBD-II port", 95, -38, False)],
    gate_pills=[("gateA", 60, 22, "Update gate CSR-124 · 122", "partial: updates off by procedure; origin not fixed"),
                ("gate", -185, -20, "Envelope CSR-061 · 011", "partial: in-limit commands pass"),
                ("branch", 30, 30, "Firmware branch CSR-031 · 051", "no barrier: beyond the plant")],
    parts_note="bottom",
    banner="TS-06 path: update source → network → updater on the SoC → panda → car bus 0 → EPS, and the firmware branch",
    gates=[("CSR-124", "automatic updates off (procedure)"), ("CSR-122", "update origin fixed"), ("CSR-121", "signed release manifest"),
           ("CSR-123", "anti-rollback"), ("CSR-061", "envelope independent of SoC values"), ("CSR-031", "firmware signed, modern scheme")],
    lens=["Credited: none verified, so the path reaches the car.", "As configured: automatic updates off; a manual install is not checked."],
    consequence="cases",
    cases=[("F-01b", "Hard-over within the envelope", "H-01"), ("L-01", "Acceleration at the envelope max", "H-03"),
           ("L-03", "Deceleration step at the envelope min", "H-04"), ("F-04b", "SoC stalls (bricked update)", "H-02")],
    plots="cases",
    iso_title="Attack path, isometric (WP-C-09 AP-06 at the §5 level)",
    precursors=None,
    zones=[("S1", "Update source · Z4", "outside the item"), ("S2", "Updater · Z3", "accepts the tree"),
           ("S3", "SoC host · Z2", "new software runs"), ("S4", "Envelope · Z1", "panda filters TX"),
           ("S5", "Vehicle · Z5", "frames on bus 0"), ("G", "DS-01…07, 11", "fleet: ×N cars")],
    walls=[(0, ("CSR-124", "CSR-122")), (1, ("CSR-121", "CSR-123")), (2, ("CSR-061", "CSR-011"))],
    branch=(2, ("CSR-031", "CSR-051")),                           # firmware branch from zone 2 over the envelope
    tags=["item sees: nothing", "item sees: nothing (no signature)", "item sees: nothing", "item sees: out-of-limit only",
          "credited: reaches EPS", "every device on the channel"],
    footer="the consequence reuses layer-1 cases F-01b, L-01, L-03 and F-04b (real panda code); firmware replacement is not simulated.",
  ),
}
