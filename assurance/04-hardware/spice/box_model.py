#!/usr/bin/env python3
"""ngspice pilot: passive-network faults of comma's harness box v3, as predictions for VS-HW-22...24.

The box netlist is transcribed by hand from comma's published v3 drawing (RR-2026-010 section 2), the same source as
`../wiring/e05-harness-box.yaml`. Each box node cites the wire-end ID of `../wiring/wire-ends.tsv` it stands for, or the
row of the wiring README section 3 for parts the wiring drawings do not show; `test_box_model.py` checks the citations.

What is modelled, and how far to trust it (README section 2 has the full list):
- U1/U2 DG419LE are IDEALISED: a closed channel is a resistor R_on, an open one 1 GOhm. No supply dependence, no input
  threshold, no behaviour outside V- ... V+. Switch state is set by the case, never computed from IN.
- Transceivers, the car-side termination, bus capacitance and the Schottky clamps use GENERIC parameters stated in
  ASSUMPTIONS below, not vendor models.
- Nothing here is a measurement and nothing earns FMEDA credit. Results are predictions that sharpen the VS-HW-22...24
  pass criteria (WP-H-06 section 3.1); the switch-level questions (unpowered switch, threshold at VL = VIN) wait for the
  bench and a licensable DG419LE model.

Tool: ngspice 41 (BSD-3-Clause, tool TL-58), from the environment of assurance/sim/supply/supply-linux-64.lock (the same
pin the supply study uses), run in batch mode through subprocess. Run this script with that environment's python.
PySpice was not used: its last release (1.5, 2021) needs the ngspice shared library and adds nothing a batch run lacks.

    python3 box_model.py           # run every case, write predictions.tsv, predictions.md and box-v3-nominal.cir
    python3 box_model.py --check   # fail if a committed output differs from a fresh run
"""

import csv
import io
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
NGSPICE_VERSION = "41"
OUT_TSV = HERE / "predictions.tsv"
OUT_MD = HERE / "predictions.md"
OUT_CIR = HERE / "box-v3-nominal.cir"

# Box nodes: spice name -> (signal on the v3 drawing, citation). A citation is a wire-end ID of ../wiring/wire-ends.tsv
# or "README 3: <part>" for a node only the wiring README section 3 table describes.
NODES = {
  "can0h": ("CAN0_H car (U1 NC, J3 A2)", "HB.U1.2-J3.A2"),
  "can0l": ("CAN0_L car (U2 COM, J3 A3)", "HB.U2.1-J3.A3"),
  "can2h": ("CAN2_H camera (U1 COM, J3 B2)", "HB.U1.1-J3.B2"),
  "can2l": ("CAN2_L camera (U2 NC, J3 B3)", "HB.U2.2-J3.B3"),
  "can2hp": ("CAN2_H' (U1 NO, R7/R8)", "README 3: R7"),
  "can0lp": ("CAN0_L' (U2 NO, R6)", "README 3: R6"),
  "can2lpp": ("CAN2_L'' (J1 P15, R8)", "README 3: R8"),
  "vin": ("VIN (box supply, U1/U2 V+ and VL)", "HB.D1.K-J3.A4"),
  "sbu1": ("SBU1 (U1/U2 IN, R2/R3)", "HB.R2/R3.1-J3.A8"),
}

# Stated generic parameters. Changing one changes the predictions; each is named in predictions.md.
ASSUMPTIONS = {
  "VIN": (13.2, "V", "box VIN: 13.5 V ignition less the D1 drop"),
  "R_ON": (30.0, "ohm", "closed switch channel; swept 10 to 100 ohm in the signal-integrity cases; DG419LE value unconfirmed (DFM-ACT-015)"),
  "R_OFF": (1e9, "ohm", "open switch channel"),
  "VDOM_H": (4.5, "V", "transmitter CAN_H source when dominant"),
  "VDOM_L": (0.5, "V", "transmitter CAN_L source when dominant"),
  "R_OUT": (25.0, "ohm", "transmitter output resistance per line; with the two above gives about 2.2 V on a 60 ohm bus, inside ISO 11898-2's 1.5-3.0 V"),
  "V_REC": (2.5, "V", "recessive bias of each transceiver"),
  "R_IN": (25e3, "ohm", "receiver input resistance per line to the recessive bias"),
  "R_CAR": (60.0, "ohm", "car side of the camera bus: both ends lumped (the Toyota A loopback gives the camera side 60 ohm in intercept, so the car side is taken as terminated by the car)"),
  "C_LINE": (200e-12, "F", "capacitance of each line to ground per bus segment (cable, connectors, transceiver pins)"),
  "BIT": (2e-6, "s", "bit time at 500 kbit/s"),
  "SAMPLE": (1.5e-6, "s", "sample point, 75 % of the bit"),
  "I_LEAK": (1e-6, "A", "net leakage into the U1/U2 IN node, sign unknown"),
  "R_PULLDOWN": (240.0, "ohm", "R2 + R3, 2 x 120 ohm in series, SBU1 to GND (from the v3 drawing, HB-02; not an estimate)"),
}
SCHOTTKY = ".model dsch d(is=1e-8 n=1.05 rs=1 cjo=5p) ; generic small-signal Schottky, not the BAS40SDW vendor model"
ISO_REC_MAX = 0.5   # ISO 11898-2 receiver: recessive below 0.5 V
ISO_DOM_MIN = 0.9   # dominant above 0.9 V
ISO_CM = (-2.0, 7.0)  # receiver common-mode range of each line to ground
RX_LINES = {"dcar": ("carh", "carl"), "dcam": ("camh", "caml"), "ddev0": ("can0h", "can0l"), "ddev2": ("can2h", "can2l")}


def p(name):
  return ASSUMPTIONS[name][0]


def box(state, faults=(), r_on=None, cam_term=False):
  """Box netlist lines for one switch state ("pass" or "intercept") with a set of fault tags applied."""
  ron = r_on if r_on is not None else p("R_ON")
  closed, open_ = f"{ron:g}", f"{p('R_OFF'):g}"
  nc, no = (closed, open_) if state == "pass" else (open_, closed)
  f = set(faults)
  lines = [
    "* U1 on CAN_H: COM = CAN2_H camera, NC = CAN0_H car, NO = CAN2_H' (idealised: R_on or R_off)",
    f"RU1NC can2h can0h {nc}",
    f"RU1NO can2h can2hp {no}",
    "* U2 on CAN_L: COM = CAN0_L car, NC = CAN2_L camera, NO = CAN0_L'",
    f"RU2NC can0l can2l {nc}",
    f"RU2NO can0l can0lp {no}",
    "* terminations on the NO side; Toyota A loops J1 P13-P15 (CAN2_L to CAN2_L''), not P3-P5",
    f"R7 can2l can2hp {'1e9' if 'r7_open' in f else '120'}",
    "R8 can2lpp can2hp 120",
    f"RLOOP can2l can2lpp {'1e9' if 'loop_open' in f else '1m'}",
    "R6 can0lp can0hpp 120",
    "RHPP can0hpp 0 1e9",
    "* supply",
    f"VVIN vin 0 {p('VIN'):g}",
  ]
  # clamps D2 (CAN0) and D3 (CAN2): each line has a Schottky to VIN and one from GND
  for tag, line in (("d2", "can0h"), ("d2", "can0l"), ("d3", "can2h"), ("d3", "can2l")):
    up, dn = f"{tag}_{line}_vin", f"{tag}_{line}_gnd"
    lines.append(f"D{line}UP {line} vin dsch" if up not in f else f"R{line}UP {line} vin 0.1 ; fault: upper diode short")
    if dn in f:
      lines.append(f"R{line}DN {line} 0 0.1 ; fault: lower diode short")
    elif dn + "_leak" in f:
      lines.append(f"R{line}DN {line} 0 1k ; fault: lower diode leakage, 1 kohm")
    else:
      lines.append(f"D{line}DN 0 {line} dsch")
  if cam_term:
    lines.append("RCAMT camh caml 120 ; assumption variant: camera has its own 120 ohm")
  return lines


def node(name, h, l, gnd="0", dominant=False, c=True):
  """A transceiver at lines h/l: recessive bias through R_IN, plus a dominant driver through R_OUT when dominant."""
  out = [f"R{name}HB {h} {name}b {p('R_IN'):g}", f"R{name}LB {l} {name}b {p('R_IN'):g}",
         f"V{name}B {name}b {gnd} {p('V_REC'):g}"]
  if dominant:
    out += [f"R{name}HD {h} {name}hd {p('R_OUT'):g}", f"V{name}HD {name}hd {gnd} {p('VDOM_H'):g}",
            f"R{name}LD {l} {name}ld {p('R_OUT'):g}", f"V{name}LD {name}ld {gnd} {p('VDOM_L'):g}"]
  if c:
    out += [f"C{name}H {h} 0 {p('C_LINE'):g}", f"C{name}L {l} 0 {p('C_LINE'):g}"]
  return out


def harness():
  """Ideal harness: camera lines camh/caml on CAN2, car lines carh/carl on CAN0, car termination lumped."""
  return ["RHCH camh can2h 1m", "RHCL caml can2l 1m", "RHAH carh can0h 1m", "RHAL carl can0l 1m",
          f"RCART carh carl {p('R_CAR'):g}"]


def ngspice() -> str:
  """The pinned ngspice: the one beside this Python (the supply-linux-64.lock environment) first, then PATH."""
  env_exe = Path(sys.executable).parent / "ngspice"
  return str(env_exe) if env_exe.exists() else (shutil.which("ngspice") or "")


def run(netlist):
  """Run one netlist in ngspice batch mode; return {name: value} from its 'name = value' prints."""
  with tempfile.TemporaryDirectory() as tmp:
    cir = Path(tmp) / "case.cir"
    cir.write_text(netlist, encoding="utf-8")
    res = subprocess.run([ngspice(), "-b", str(cir)], capture_output=True, text=True, timeout=60)
  out = {}
  for m in re.finditer(r"^\s*(\w+)\s*=\s*([-+0-9.eE]+)", res.stdout, re.M):
    out[m.group(1).lower()] = float(m.group(2))
  if not out:
    raise RuntimeError(f"ngspice gave no result:\n{res.stdout[-2000:]}\n{res.stderr[-2000:]}")
  return out


def deck(title, body, control):
  return "\n".join([f"* {title}", SCHOTTKY, *body, ".control", *control, ".endc", ".end", ""])


def dc_case(state, faults=(), tx="camera", r_on=None, cam_gnd=0.0, cam_term=False):
  """DC levels: one transmitter dominant or all recessive; differential at every receiver on that bus."""
  vals = {}
  for bit in ("rec", "dom"):
    dom = bit == "dom"
    body = box(state, faults, r_on, cam_term) + harness()
    camg = "camg" if cam_gnd else "0"
    if cam_gnd:
      body.append(f"VCAMG camg 0 {cam_gnd:g}")
    body += node("cam", "camh", "caml", camg, dominant=dom and tx == "camera", c=False)
    body += node("car", "carh", "carl", dominant=dom and tx == "car", c=False)
    body += node("dv0", "can0h", "can0l", dominant=dom and tx == "device0", c=False)
    body += node("dv2", "can2h", "can2l", dominant=dom and tx == "device2", c=False)
    ctrl = ["op", "let dcar = v(carh)-v(carl)", "let dcam = v(camh)-v(caml)",
            "let ddev0 = v(can0h)-v(can0l)", "let ddev2 = v(can2h)-v(can2l)", "print dcar dcam ddev0 ddev2"]
    for ln in ("carh", "carl", "camh", "caml", "can0h", "can0l", "can2h", "can2l"):
      ctrl.append(f"let l{ln} = v({ln})")
    ctrl.append("print " + " ".join(f"l{ln}" for ln in ("carh", "carl", "camh", "caml", "can0h", "can0l", "can2h", "can2l")))
    r = run(deck(f"{state} {bit} {sorted(faults)}", body, ctrl))
    for k, v in r.items():
      vals[f"{bit}_{k}"] = v
  return vals


def edge_case(state, faults=(), cam_term=False):
  """Camera bus in intercept: camera sends one dominant bit; time for the device receiver to fall below 0.5 V."""
  body = box(state, faults, cam_term=cam_term) + harness()
  body += node("cam", "camh", "caml", dominant=False)
  body += node("car", "carh", "carl")
  body += node("dv0", "can0h", "can0l")
  body += node("dv2", "can2h", "can2l")
  # camera driver switched on for one bit by a pulse-controlled switch
  bit = p("BIT")
  body += [".model txsw sw vt=0.5 vh=0.1 ron=1m roff=1e12",
           f"VTX tx 0 pulse(0 1 0.5u 1n 1n {bit:g} 1)",
           f"SCH camh camhd tx 0 txsw", f"RCHD camhd camhs {p('R_OUT'):g}", f"VCHD camhs 0 {p('VDOM_H'):g}",
           f"SCL caml camld tx 0 txsw", f"RCLD camld camls {p('R_OUT'):g}", f"VCLD camls 0 {p('VDOM_L'):g}"]
  rx = ("can2h", "can2l") if state == "intercept" else ("carh", "carl")
  t_end = 0.5e-6 + bit
  ctrl = [f"tran 10n {t_end + 6 * bit:g}", f"let d = v({rx[0]})-v({rx[1]})",
          f"meas tran tdom find d at={0.5e-6 + bit * 0.9:g}",
          f"meas tran trec when d=0.5 fall=1 td={t_end:g}",
          "if trec < 0", "let trec = 1", "end",
          f"let tfall = trec - {t_end:g}", "print tdom tfall"]
  r = run(deck(f"edge {state} {sorted(faults)}", body, ctrl))
  return {"dom_level": r.get("tdom"), "rec_time": r.get("tfall")}


def sbu1_case(pulldown=True, leak=1e-6, src=None, r_src=None):
  """Voltage at the U1/U2 IN node: R2+R3 to GND (or open), an input leakage, and an optional source on SBU1.
  The IN pins are given generic ESD clamps to VL (= VIN) and GND, as CMOS inputs have."""
  body = [f"VVIN vin 0 {p('VIN'):g}",
          f"RPD sbu1 0 {format(p('R_PULLDOWN'), 'g') if pulldown else '1e12'}",
          f"ILEAK 0 sbu1 {leak:g}", "DESDUP sbu1 vin dsch", "DESDDN 0 sbu1 dsch"]
  if src is not None:
    body += [f"VSRC srcn 0 {src:g}", f"RSRC srcn sbu1 {r_src:g}"]
  ctrl = ["op", "let vin_node = v(sbu1)", "let isrc = 0"]
  if src is not None:
    ctrl[-1] = "let isrc = -i(vsrc)"
  ctrl.append("print vin_node isrc")
  return run(deck("sbu1", body, ctrl))


def line_range(r, rk):
  """Lowest and highest line voltage at receiver rk over both bit states."""
  vs = [r[f"{bit}_l{ln}"] for bit in ("rec", "dom") for ln in RX_LINES[rk]]
  return min(vs), max(vs)


def verdict(rec, dom, lines=None):
  if rec is None or dom is None:
    return "n/a"
  if lines and (lines[0] < ISO_CM[0] or lines[1] > ISO_CM[1]):
    return f"line at {lines[1] if lines[1] > ISO_CM[1] else lines[0]:.3g} V: outside the receiver common-mode range"
  if rec >= ISO_REC_MAX:
    return "bus reads dominant when idle"
  if dom <= ISO_DOM_MIN:
    return "dominant lost"
  return "levels OK"


def cases():
  """Every case: (id, group, description, prediction for, function returning result columns)."""
  out = []
  # 1. clamp faults, both switch states
  for tag, bus in (("d2", "CAN0 car"), ("d3", "CAN2 camera")):
    lines = ("can0h", "can0l") if tag == "d2" else ("can2h", "can2l")
    for line in lines:
      for kind, desc in (("gnd", "lower diode short (line to GND)"), ("vin", "upper diode short (line to VIN)"),
                         ("gnd_leak", "lower diode leakage, 1 kohm to GND")):
        fault = f"{tag}_{line}_{kind}"
        out.append((f"C-{tag.upper()}-{line[-1].upper()}-{kind}", "clamp",
                    f"{tag.upper()} {desc} on {line[:4].upper()}_{line[-1].upper()} ({bus})", "VS-HW-24 (d)", fault))
  # 2. terminations on the camera bus in intercept
  out += [("T-nominal", "termination", "Nominal: R7 and R8 through the P13-P15 loopback (60 ohm)", "VS-HW-24 (c)", ()),
          ("T-loop-open", "termination", "Loopback P13-P15 open in the plug (R7 only, 120 ohm)", "VS-HW-24 (c)", ("loop_open",)),
          ("T-r7-open", "termination", "R7 open (R8 only, 120 ohm)", "VS-HW-24 (c)", ("r7_open",)),
          ("T-both-open", "termination", "R7 open and loopback open (camera bus unterminated in intercept)", "VS-HW-24 (c)", ("r7_open", "loop_open")),
          ("T-camterm", "termination", "Assumption variant: camera has its own 120 ohm (40 ohm in intercept)", "VS-HW-24 (c)", "camterm")]
  return out


def compute() -> list[dict]:
  rows = []
  for cid, group, desc, vs, fault in cases():
    if group == "clamp":
      bus_tx = "car" if fault.startswith("d2") else "camera"
      for state in ("pass", "intercept"):
        # the faulted bus's own node transmits; the far receiver is read: in pass-through the other end of the joined
        # bus, in intercept the device on that bus
        tx = bus_tx
        r = dc_case(state, (fault,), tx=tx)
        if state == "pass":
          rk = "dcar" if tx == "camera" else "dcam"
        else:
          rk = "ddev2" if bus_tx == "camera" else "ddev0"
        rec, dom = r[f"rec_{rk}"], r[f"dom_{rk}"]
        rows.append({"id": f"{cid}/{state}", "group": group, "case": desc, "state": state, "for": vs,
                     "recessive_V": rec, "dominant_V": dom, "edge_us": None,
                     "verdict": verdict(rec, dom, line_range(r, rk))})
    else:
      faults = () if fault == "camterm" else fault
      e = edge_case("intercept", faults, cam_term=(fault == "camterm"))
      t = e["rec_time"]
      v = verdict(0.0, e["dom_level"])
      if t is None or t > p("SAMPLE") - 0.5e-6:
        v = "recessive edge too slow for the sample point"
      rows.append({"id": f"{cid}/intercept", "group": group, "case": desc, "state": "intercept", "for": "VS-HW-24 (c)",
                   "recessive_V": None, "dominant_V": e["dom_level"], "edge_us": None if t is None else t * 1e6,
                   "verdict": v})
  # 3. signal integrity: R_on sweep and camera ground offset, pass-through, camera to car
  for ron in (10.0, 30.0, 50.0, 70.0, 100.0):
    r = dc_case("pass", r_on=ron, tx="camera")
    rows.append({"id": f"S-ron-{ron:g}/pass", "group": "signal", "case": f"Pass-through, R_on {ron:g} ohm per channel, camera to car",
                 "state": "pass", "for": "VS-HW-24 (c)", "recessive_V": r["rec_dcar"], "dominant_V": r["dom_dcar"],
                 "edge_us": None, "verdict": verdict(r["rec_dcar"], r["dom_dcar"], line_range(r, "dcar"))})
  for off in (-1.0, 1.0):
    r = dc_case("pass", tx="camera", cam_gnd=off)
    rows.append({"id": f"S-gnd{off:+g}/pass", "group": "signal", "case": f"Pass-through, camera ground {off:+g} V from box ground, camera to car",
                 "state": "pass", "for": "VS-HW-24 (c)", "recessive_V": r["rec_dcar"], "dominant_V": r["dom_dcar"],
                 "edge_us": None, "verdict": verdict(r["rec_dcar"], r["dom_dcar"], line_range(r, "dcar"))})
  # 4. SBU1 / IN node
  sb = [("I-intact+", "R2/R3 intact, leakage +1 uA into IN", dict(pulldown=True, leak=p("I_LEAK")), "VS-HW-23 (reference)"),
        ("I-intact-", "R2/R3 intact, leakage -1 uA out of IN", dict(pulldown=True, leak=-p("I_LEAK")), "VS-HW-23 (reference)"),
        ("I-open+", "R2/R3 open, SBU1 undriven, leakage +1 uA into IN", dict(pulldown=False, leak=p("I_LEAK")), "VS-HW-23 steps 2-4"),
        ("I-open-", "R2/R3 open, SBU1 undriven, leakage -1 uA out of IN", dict(pulldown=False, leak=-p("I_LEAK")), "VS-HW-23 steps 2-4"),
        ("I-bench-1k", "Bench drive of WP-H-06 3.1: 5 V through 1 kohm, R2/R3 intact", dict(pulldown=True, leak=0.0, src=5.0, r_src=1000.0), "VS-HW-23 step 1, VS-HW-24 (b)"),
        ("I-stiff-5V", "Stiff 5 V drive (10 ohm source), R2/R3 intact", dict(pulldown=True, leak=0.0, src=5.0, r_src=10.0), "VS-HW-23 step 1, VS-HW-24 (b)")]
  for cid, desc, kw, vs in sb:
    r = sbu1_case(**kw)
    vin_node = r["vin_node"]
    if "open" in cid:
      v = "IN pulled to a rail by leakage alone: switch state undefined"
    elif "bench" in cid:
      v = "IN reaches only about 1 V: intercept not reached on an intact box"
    elif "stiff" in cid:
      v = f"IN near 5 V; the drive must source about {r['isrc'] * 1e3:.0f} mA"
    else:
      v = "IN held near 0 V: pass-through default holds"
    rows.append({"id": f"{cid}/sbu1", "group": "release", "case": desc, "state": "-", "for": vs,
                 "recessive_V": None, "dominant_V": vin_node, "edge_us": None, "verdict": v})
  return rows


def fmt(x, nd=3):
  if x is None:
    return ""
  if abs(x) < 5e-4:
    return "0"
  return f"{x:.{nd}g}"


def to_tsv(rows) -> str:
  buf = io.StringIO()
  w = csv.writer(buf, delimiter="\t", lineterminator="\n")
  w.writerow(["id", "group", "case", "state", "prediction for", "recessive Vdiff (V)", "dominant Vdiff or IN (V)",
              "recessive edge (us)", "verdict"])
  for r in rows:
    w.writerow([r["id"], r["group"], r["case"], r["state"], r["for"], fmt(r["recessive_V"]), fmt(r["dominant_V"]),
                fmt(r["edge_us"]), r["verdict"]])
  return buf.getvalue()


def to_md(rows) -> str:
  head = {
    "clamp": "## 1. Clamp diode faults (D2 on CAN0, D3 on CAN2)\n\nDifferential at the far receiver of the faulted bus: in pass-through the other end of the joined bus, in intercept the device. ISO 11898-2 receiver: recessive below 0.5 V, dominant above 0.9 V, each line within -2 ... +7 V of ground.",
    "termination": "## 2. Camera-bus termination in intercept\n\nCamera sends one dominant bit to the device. Dominant level at the device, and the time from the end of the bit until the differential falls below 0.5 V. A time beyond about 1 us (sample point 1.5 us of a 2 us bit, edge already 0.5 us late) puts the next bit at risk.",
    "signal": "## 3. Pass-through signal integrity\n\nCamera to car through U1/U2. The switch is idealised: below-ground signals and the analog range V- ... V+ are not modelled, so the ground-offset rows show only the clamp diodes' effect.",
    "release": "## 4. Release default: the U1/U2 IN node (SBU1)\n\nVoltage at IN. Generic ESD clamps to VIN and GND stand for the CMOS input protection.",
  }
  cols = {
    "clamp": (["Case", "State", "Recessive (V)", "Dominant (V)", "Prediction", "For"], lambda r: [r["case"], r["state"], fmt(r["recessive_V"]), fmt(r["dominant_V"]), r["verdict"], r["for"]]),
    "termination": (["Case", "Dominant (V)", "Recessive edge (us)", "Prediction", "For"], lambda r: [r["case"], fmt(r["dominant_V"]), fmt(r["edge_us"]), r["verdict"], r["for"]]),
    "signal": (["Case", "Recessive (V)", "Dominant (V)", "Prediction", "For"], lambda r: [r["case"], fmt(r["recessive_V"]), fmt(r["dominant_V"]), r["verdict"], r["for"]]),
    "release": (["Case", "IN (V)", "Prediction", "For"], lambda r: [r["case"], fmt(r["dominant_V"]), r["verdict"], r["for"]]),
  }
  out = ["<!-- Generated by assurance/04-hardware/spice/box_model.py; do not edit by hand. -->", "",
         "# Harness box v3: ngspice pilot predictions", "",
         "**Predictions from an idealised model, not measurements. No FMEDA credit.** Each row names the bench case whose pass criterion it informs. Model limits and the reasons are in the [README](README.md).", ""]
  for g in ("clamp", "termination", "signal", "release"):
    out += [head[g], ""]
    h, f = cols[g]
    out.append("| " + " | ".join(h) + " |")
    out.append("|" + "---|" * len(h))
    for r in rows:
      if r["group"] == g:
        out.append("| " + " | ".join(str(c).replace("|", "/") for c in f(r)) + " |")
    out.append("")
  out += ["## Parameters", "", "| Name | Value | Meaning |", "|---|---|---|"]
  for k, (v, unit, why) in ASSUMPTIONS.items():
    out.append(f"| `{k}` | {v:g} {unit} | {why} |")
  out += ["", f"Diode model: `{SCHOTTKY.split(';')[0].strip()}` (generic small-signal Schottky, not the BAS40SDW vendor model).", ""]
  return "\n".join(out)


def nominal_cir() -> str:
  body = box("pass")
  head = ["* Harness box v3, nominal, pass-through. Generated by box_model.py; do not edit by hand.",
          "* Hand-transcribed from comma.ai Harness_Box.pdf v3 (commaai/hardware 530b7da; RR-2026-010 section 2).",
          "* Node citations (wire-end IDs of ../wiring/wire-ends.tsv, or the wiring README section 3 row):"]
  head += [f"*   {n:8s} {sig}  [{cite}]" for n, (sig, cite) in NODES.items()]
  return "\n".join(head + [SCHOTTKY] + body + [".end", ""])


def ngspice_version() -> str:
  try:
    out = subprocess.run([ngspice(), "-v"], capture_output=True, text=True, timeout=30).stdout
  except (OSError, subprocess.SubprocessError):
    return ""
  m = re.search(r"ngspice-(\d+)", out)
  return m.group(1) if m else ""


def build() -> dict[str, str]:
  rows = compute()
  return {OUT_TSV.name: to_tsv(rows), OUT_MD.name: to_md(rows), OUT_CIR.name: nominal_cir()}


def main(argv: list[str]) -> int:
  if not ngspice():
    print("ngspice not found: create the environment from assurance/sim/supply/supply-linux-64.lock")
    return 1
  ver = ngspice_version()
  if ver != NGSPICE_VERSION:
    print(f"ngspice {NGSPICE_VERSION} required, found {ver or 'unknown'}")
    return 1
  out = build()
  if "--check" in argv:
    errs = [f"{n} is stale; run box_model.py" for n, t in out.items()
            if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != t]
    print("\n".join(errs) if errs else f"spice pilot outputs current ({len(out)} files, ngspice {ver})")
    return 1 if errs else 0
  for n, t in out.items():
    (HERE / n).write_text(t, encoding="utf-8")
  print(f"wrote {len(out)} files")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
