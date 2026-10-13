#!/usr/bin/env python3
"""Back-to-back test: the SM-TOY-AUTH reference model against the C safety code (libsafety).

Every scenario in scenarios.py runs through both, in the upstream build and in the reference build
(LIONDRIVER_REFERENCE=1). After every event, controls_allowed of the C code is compared with the model state, and the
accept/reject result of every TX frame is compared too. A divergence is reported, then the model is re-aligned with
the C state so that later divergences are found independently.

Each divergence is classified:
  expected   the model fired a transition whose record entry says "not implemented": it confirms an open SWSR
  known      listed in KNOWN below with a candidate-finding ID, awaiting engineering review
  UNEXPECTED anything else; the run exits 1

The run is not verification evidence (modelling plan MD-01, WP-P-07 OI-8): the harness and the model are unreviewed
and unclassified. A run without divergences shows agreement between the record and the code for the stimuli used,
nothing more.

Usage (from the superproject root, opendbc_repo checked out, opendbc test dependencies installed):
  python3 assurance/models/b2b/run_b2b.py <output dir>
Writes b2b-report.md and b2b-report.json to the output directory.

Drafting origin: ai-assisted (Claude), not reviewed.
"""
from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE), str(ROOT / "opendbc_repo"), str(ROOT / "assurance" / "trace" / "tools")]

import toy_auth_model as M
from scenarios import Event, Scenario, scenarios
from check_state_machines import load

RECORD = ROOT / "assurance" / "05-software" / "state-machines" / "sm-toy-auth.yaml"
TOYOTA_H = ROOT / "opendbc_repo" / "opendbc" / "safety" / "modes" / "toyota.h"
T0_US = 1000000
SAFETY_PARAM = 73  # CFG-001: LKA torque control, openpilot longitudinal, EPS factor 73 (WP-W-09 CD-01)

# Divergences reviewed once and given a candidate-finding ID. Key: (scenario, build, cause). The ID is a proposal for
# the next review record, not a finding until a reviewer accepts it.
KNOWN: dict[tuple[str, str, str], str] = {
  ("BB-08b", "upstream", "C only"): "BB-C-01",
  ("BB-08b", "reference", "C only"): "BB-C-01",
  ("BB-06b", "reference", "T1"): "BB-C-02",
}


# ---------------------------------------------------------------- preconditions

def record_check(record: dict) -> list[str]:
  ids = [t["id"] for t in record["transitions"]]
  errs = [f"record transition {i} is neither executed nor listed as not executable by the model"
          for i in ids if i not in M.EXECUTED and i not in M.NOT_EXECUTED]
  errs += [f"model handles {i}, which is not in the record" for i in [*M.EXECUTED, *M.NOT_EXECUTED] if i not in ids]
  return errs


def code_constants_check() -> list[str]:
  src = TOYOTA_H.read_text(encoding="utf-8")
  errs = []
  for name, (addr, freq, _) in M.CODE_CONSTANTS["rx_checks"].items():
    if not re.search(rf"\{{\s*0x0*{addr:x}, 0, 8, {freq}U", src, re.I):
      errs.append(f"RX check {name} 0x{addr:X} at {freq} Hz not found in toyota.h")
  for name, (addr, freq, burst) in M.CODE_CONSTANTS["tx_rate"].items():
    if not re.search(rf"\.addr = 0x{addr:X}U, \.bus = 0U, \.frequency = {freq}U, \.burst = {burst}U", src, re.I):
      errs.append(f"TX rate row {name} 0x{addr:X} {freq} Hz burst {burst} not found in toyota.h")
  return errs


# ---------------------------------------------------------------- C side

_LIBS: dict[bool, object] = {}


class CSide:
  def __init__(self, reference: bool):
    from opendbc.safety.tests.libsafety import libsafety_py
    from opendbc.safety.tests.common import CANPackerSafety
    from opendbc.car.structs import CarParams
    if reference not in _LIBS:  # one compilation per build; set_safety_hooks resets the state between scenarios
      os.environ["LIONDRIVER_REFERENCE"] = "1" if reference else "0"
      _LIBS[reference] = libsafety_py.ffi.dlopen(libsafety_py._build_libsafety())
    self.L = libsafety_py
    self.lib = _LIBS[reference]
    self.packer = CANPackerSafety("toyota_nodsu_pt_generated")
    self.mode = CarParams.SafetyModel.toyota
    self.lib.set_safety_hooks(self.mode, SAFETY_PARAM)
    self.lib.init_tests()
    self.lib.set_timer(T0_US)

  def _msg(self, name: str, v: dict, corrupt: bool):
    if name == "WHEEL_SPEEDS":
      vals = {f"WHEEL_SPEED_{w}": v["speed"] * 3.6 for w in ("FR", "FL", "RR", "RL")}
      if v["wheel_fault"]:
        vals |= {f"WHEEL_SPEED_{w}_FAULT": 1 for w in ("FR", "FL", "RR", "RL")}
    elif name == "STEER_TORQUE_SENSOR":
      vals = {"STEER_TORQUE_EPS": v["STEER_TORQUE_EPS"] / SAFETY_PARAM * 100.,
              "STEER_TORQUE_DRIVER": v["STEER_TORQUE_DRIVER"]}
    elif name == "EPS_STATUS":
      vals = {"LKA_STATE": v["LKA_STATE"]}
    elif name == "PCM_CRUISE":
      vals = {"CRUISE_ACTIVE": v["CRUISE_ACTIVE"], "GAS_RELEASED": v["GAS_RELEASED"]}
    elif name == "PCM_CRUISE_2":
      vals = {"MAIN_ON": v["MAIN_ON"]}
    elif name == "BRAKE_MODULE":
      vals = {"BRAKE_PRESSED": v["BRAKE_PRESSED"]}
    elif name == "STEERING_LKA":
      vals = {"STEER_TORQUE_CMD": v.get("STEER_TORQUE_CMD", 0), "STEER_REQUEST": v.get("STEER_REQUEST", 0)}
    elif name == "ACC_CONTROL":
      vals = {"ACCEL_CMD": 0, "CANCEL_REQ": 0}
    else:
      raise ValueError(name)
    addr, dat, bus = self.packer.make_can_msg(name, 0, vals)
    if corrupt:
      dat = dat[:-1] + bytes([dat[-1] ^ 0xFF])  # wrong checksum byte
    return self.L.make_CANPacket(addr, bus, dat)

  def step(self, e: Event, t_us: int):
    self.lib.set_timer(t_us)
    tx_ok = None
    if e.kind == "rx":
      self.lib.safety_rx_hook(self._msg(e.name, e.values, e.corrupt))
    elif e.kind == "tx":
      tx_ok = bool(self.lib.safety_tx_hook(self._msg(e.name, e.values, False)))
    elif e.kind == "tick":
      self.lib.safety_tick()
    elif e.kind == "mode":
      self.lib.set_safety_hooks(self.mode, SAFETY_PARAM)
    return bool(self.lib.get_controls_allowed()), tx_ok


# ---------------------------------------------------------------- run

def describe(e: Event) -> str:
  if e.kind in ("rx", "tx"):
    return f"{e.kind} {e.name}" + (" (corrupt)" if e.corrupt else "") + ("" if e.content_ok else " (content over limit)")
  return e.kind


def run_one(sc: Scenario, build: str, record: dict) -> dict:
  c = CSide(build == "reference")
  m = M.ToyAuthModel(build)
  not_impl = {t["id"] for t in record["transitions"] if str(t.get("code", "")).startswith("not implemented")}
  divs = []
  events = sc.events()
  for e in events:
    t_us = T0_US + e.t_ms * 1000
    n_fired = len(m.fired)
    m_tx = None
    if e.kind == "rx":
      corrupt = e.corrupt or (e.name == "WHEEL_SPEEDS" and bool(e.values["wheel_fault"]))
      m.rx(t_us, e.name, e.values, corrupt)
    elif e.kind == "tx":
      m_tx = m.tx(t_us, e.name, e.content_ok)
    elif e.kind == "tick":
      m.tick(t_us)
    elif e.kind == "mode":
      m.mode_set(t_us)
    c_allowed, c_tx = c.step(e, t_us)
    fired = [tid for _, tid in m.fired[n_fired:] if tid != "T8" or e.kind != "rx"]
    m_allowed = m.state == M.ALLOWED
    kinds = []
    if c_allowed != m_allowed:
      kinds.append("state")
    if m_tx is not None and c_tx != m_tx:
      kinds.append("tx")
    if kinds:
      cause = ",".join(fired) if fired else "C only"
      if fired and any(t in not_impl for t in fired):
        cls = "expected"
      elif (sc.id, build, cause) in KNOWN:
        cls = "known"
      else:
        cls = "UNEXPECTED"
      divs.append({"t_ms": e.t_ms, "event": describe(e), "kind": "+".join(kinds), "model": m.state,
                   "c": M.ALLOWED if c_allowed else M.NOT_ALLOWED, "model_tx": m_tx, "c_tx": c_tx, "cause": cause,
                   "class": cls, "id": KNOWN.get((sc.id, build, cause), "")})
      m.resync(t_us, M.ALLOWED if c_allowed else M.NOT_ALLOWED)
  fired_ids = sorted({tid for _, tid in m.fired}, key=lambda x: (len(x), x))
  return {"scenario": sc.id, "transitions": sc.transitions, "title": sc.title, "build": build,
          "events": len(events), "fired": fired_ids, "divergences": divs}


def git(*args, cwd=ROOT) -> str:
  try:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False).stdout.strip()
  except OSError:
    return ""


def result_label(r: dict) -> str:
  classes = {d["class"] for d in r["divergences"]}
  if not classes:
    return "No divergence"
  if "UNEXPECTED" in classes:
    return "**UNEXPECTED divergence**"
  return ", ".join(sorted({"expected": "Expected (open SWSR)", "known": "Known candidate finding"}[c] for c in classes))


def report_md(results: list[dict], meta: dict) -> str:
  L = ["# Back-to-back run: SM-TOY-AUTH model vs C safety code", "",
       "Generated by `assurance/models/b2b/run_b2b.py`. **Not verification evidence**: the model and harness are " +
       "AI-drafted, unreviewed and unclassified (modelling plan MD-01). A divergence is a question for an engineer, " +
       "not a defect until reviewed.", "",
       "| Field | Value |", "|---|---|"]
  L += [f"| {k} | {v} |" for k, v in meta.items()]
  L += ["", "## Results", "", "| Scenario | Transitions | Stimulus | Build | Events | Model fired | Divergences | Result |",
        "|---|---|---|---|---|---|---|---|"]
  for r in results:
    L.append(f"| {r['scenario']} | {r['transitions']} | {r['title']} | {r['build']} | {r['events']} | " +
             f"{', '.join(r['fired']) or '—'} | {len(r['divergences'])} | {result_label(r)} |")
  L += ["", "## Divergences", "", "Model re-aligned with the C state after each one.", "",
        "| Scenario | Build | t (ms) | Event | Kind | Model | C | Cause (model transition) | Class | Candidate |",
        "|---|---|---|---|---|---|---|---|---|---|"]
  n = 0
  for r in results:
    for d in r["divergences"]:
      n += 1
      kind = d["kind"] + (f" (model {d['model_tx']}, C {d['c_tx']})" if "tx" in d["kind"] else "")
      L.append(f"| {r['scenario']} | {r['build']} | {d['t_ms']} | {d['event']} | {kind} | {d['model']} | {d['c']} | " +
               f"{d['cause']} | {d['class']} | {d['id'] or '—'} |")
  if not n:
    L.append("| — | | | | | | | | | |")
  L += ["", "## Model assumptions (record silent)", "", "| ID | Assumption |", "|---|---|"]
  L += [f"| {a} | {t} |" for a, t in M.ASSUMPTIONS]
  L += ["", "## Record transitions not executed at the libsafety boundary", "", "| Transition | Reason |", "|---|---|"]
  L += [f"| {t} | {why} |" for t, why in M.NOT_EXECUTED.items()]
  return "\n".join(L) + "\n"


def main(argv: list[str]) -> int:
  if len(argv) != 2:
    print(__doc__)
    return 2
  out = Path(argv[1])
  out.mkdir(parents=True, exist_ok=True)
  record = load(RECORD)
  errs = record_check(record) + code_constants_check()
  if errs:
    for e in errs:
      print("ERROR " + e)
    return 1
  results = [run_one(sc, b, record) for b in ("upstream", "reference") for sc in scenarios()]
  meta = {
    "Superproject": f"`{git('rev-parse', '--short', 'HEAD')}`",
    "opendbc": f"`{git('rev-parse', '--short', 'HEAD', cwd=ROOT / 'opendbc_repo')}`",
    "Record": "`assurance/05-software/state-machines/sm-toy-auth.yaml`",
    "Configuration": f"CFG-001, Toyota safety param {SAFETY_PARAM} (LKA, openpilot longitudinal, non-SecOC)",
    "Builds": "upstream (no flag), reference (`LIONDRIVER_REFERENCE=1`); libsafety host build, UBSan",
    "Environment": f"{platform.system()} {platform.machine()}, Python {platform.python_version()}, " +
                   subprocess.run(["cc", "--version"], capture_output=True, text=True, check=False).stdout.split("\n")[0],
    "Scenarios": f"{len(results) // 2} per build, {sum(r['events'] for r in results)} events in total",
  }
  (out / "b2b-report.md").write_text(report_md(results, meta), encoding="utf-8")
  (out / "b2b-report.json").write_text(json.dumps({"meta": meta, "results": results}, indent=2) + "\n", encoding="utf-8")
  counts = {c: sum(d["class"] == c for r in results for d in r["divergences"]) for c in ("expected", "known", "UNEXPECTED")}
  for r in results:
    print(f"{r['scenario']:<26} {r['build']:<9} fired={','.join(r['fired']) or '-':<22} {result_label(r)}")
  print(f"divergences: {counts}; report: {out / 'b2b-report.md'}")
  print("FAILED: unexpected divergence" if counts["UNEXPECTED"] else "OK: no unexpected divergence (not verification)")
  return 1 if counts["UNEXPECTED"] else 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
