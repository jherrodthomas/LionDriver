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
from html import escape
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE), str(ROOT / "opendbc_repo"), str(ROOT / "assurance" / "trace" / "tools")]

import b2b_plots as P
import toy_auth_model as M
from scenarios import ENGAGE_MS, Event, Scenario, scenarios
from check_state_machines import load

RECORD = ROOT / "assurance" / "05-software" / "state-machines" / "sm-toy-auth.yaml"
TOYOTA_H = ROOT / "opendbc_repo" / "opendbc" / "safety" / "modes" / "toyota.h"
T0_US = 1000000
SAFETY_PARAM = 73  # CFG-001: LKA torque control, openpilot longitudinal, EPS factor 73 (WP-W-09 CD-01)

# Divergences reviewed once and given a candidate-finding ID. Key: (scenario, build, cause). The ID is a proposal for
# the next review record, not a finding until a reviewer accepts it.
# Value: (candidate ID, the record transition the difference concerns, for the coverage view).
KNOWN: dict[tuple[str, str, str], tuple[str, str]] = {
  ("BB-08b", "upstream", "C only"): ("BB-C-01", "T1"),
  ("BB-08b", "reference", "C only"): ("BB-C-01", "T1"),
}

# Short labels for the coverage views
LABELS = {"T1": "cruise 0→1, RX checks valid", "T2": "cruise off", "T3": "brake", "T4": "checksum / quality",
          "T5": "RX check lagging", "T6": "heartbeat engaged=0", "T7": "safety mode set", "T9": "TX content rejected",
          "T10a": "no SoC heartbeat", "T10b": "command not fresh", "T10c": "cruise without MAIN_ON",
          "T10d": "platform fault", "T10e": "driver override", "T11": "TX rate exceeded", "T12": "driver torque",
          "T13": "SPI errors", "T14": "bus-off", "T15": "forwarding"}
EXAMPLE = ("BB-10a", "reference")  # a trace without a difference, drawn for reference


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
  free = M.ToyAuthModel(build)  # never re-aligned: drawn in the traces, so a difference shows for as long as it lasts
  trace = []
  not_impl = {t["id"] for t in record["transitions"] if str(t.get("code", "")).startswith("not implemented")}
  divs = []
  events = sc.events()
  for e in events:
    t_us = T0_US + e.t_ms * 1000
    n_fired = len(m.fired)
    m_tx = None
    corrupt = e.kind == "rx" and (e.corrupt or (e.name == "WHEEL_SPEEDS" and bool(e.values["wheel_fault"])))
    for mm in (free, m):
      if e.kind == "rx":
        mm.rx(t_us, e.name, e.values, corrupt)
      elif e.kind == "tx":
        tx_result = mm.tx(t_us, e.name, e.content_ok)
        if mm is m:
          m_tx = tx_result
      elif e.kind == "tick":
        mm.tick(t_us)
      elif e.kind == "mode":
        mm.mode_set(t_us)
    c_allowed, c_tx = c.step(e, t_us)
    fired = [tid for _, tid in m.fired[n_fired:] if tid != "T8" or e.kind != "rx"]
    m_allowed = m.state == M.ALLOWED
    trace.append({"t": e.t_ms, "k": e.kind, "n": e.name, "cor": corrupt, "ok": e.content_ok, "v": e.values,
                  "m": free.state == M.ALLOWED, "c": c_allowed, "f": fired})
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
                   "class": cls, "id": KNOWN.get((sc.id, build, cause), ("", ""))[0]})
      m.resync(t_us, M.ALLOWED if c_allowed else M.NOT_ALLOWED)
  fired_ids = sorted({tid for _, tid in m.fired}, key=lambda x: (len(x), x))
  return {"scenario": sc.id, "transitions": sc.transitions, "title": sc.title, "build": build,
          "events": len(events), "fired": fired_ids, "divergences": divs, "trace": trace}


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
  L += ["", "## Coverage on the state machine", "", "![Coverage](coverage.svg)", "", meta_mermaid(results), "",
        "## Traces", "", "Model line drawn without re-alignment. Overview of the whole scenario, then a zoom on the first " +
        "difference with every frame and safety-task tick.", ""]
  for r in results:
    if r.get("svg"):
      L += [f"### {r['scenario']} · {r['build']} — {r['title']}", ""] + [f"![{r['scenario']} {n}]({f})" for n, f in r["svg"]] + [""]
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


# ---------------------------------------------------------------- views

_STATUS: dict = {}


def meta_mermaid(results: list[dict]) -> str:
  return _STATUS.get("mermaid", "")


def write_views(results: list[dict], record: dict, out: Path) -> None:
  """Coverage diagram, and overview and zoom traces for every run with a difference plus the reference example."""
  status = P.transition_status(record, results, M.EXECUTED, KNOWN)
  (out / "coverage.svg").write_text(P.coverage_svg(record, status, LABELS), encoding="utf-8")
  _STATUS["mermaid"] = P.coverage_mermaid(record, status, LABELS)
  by_id = {sc.id: sc for sc in scenarios()}
  (out / "traces").mkdir(exist_ok=True)
  for r in results:
    if not r["divergences"] and (r["scenario"], r["build"]) != EXAMPLE:
      continue
    sc = by_id[r["scenario"]]
    classes = {d["class"] for d in r["divergences"]}
    colour = P.UNEXPECTED if "UNEXPECTED" in classes else P.CANDIDATE if "known" in classes else P.EXPECTED
    anchor = r["divergences"][0]["t_ms"] if r["divergences"] else \
      next((x["t"] for x in r["trace"] if x["t"] > ENGAGE_MS + 50 and any(f != "T8" for f in x["f"])), ENGAGE_MS)
    files = []
    for name, (t0, t1, width, zoom) in (("overview", (0, sc.duration_ms, 1000, False)),
                                         ("zoom", (max(anchor - 20, 0), anchor + 40, 1450, True))):
      f = f"traces/{r['scenario']}-{r['build']}-{name}.svg"
      (out / f).write_text(P.trace_svg(r, sc, t0, t1, width, zoom, colour), encoding="utf-8")
      files.append((name, f))
    r["svg"] = files


def report_html(results: list[dict], meta: dict, out: Path) -> str:
  css = ("body{margin:0;background:#F4F6F9;color:#0E1A2B;font:14px/1.45 'IBM Plex Sans',Helvetica,Arial,sans-serif}" +
         "header{background:#0B1B33;color:#fff;padding:18px 28px;border-bottom:3px solid #C9A227}h1{margin:0;font-size:22px}" +
         ".note{margin:14px 28px;padding:9px 14px;border:1px solid #E3C77A;background:#FBF5E4;border-radius:6px;color:#6B5108}" +
         "main{padding:0 28px 28px}section{background:#fff;border:1px solid #D9DEE6;border-radius:10px;padding:14px 16px;margin:14px 0}" +
         "a{color:inherit}h2{margin:0 0 8px;font-size:15px;color:#9A7414}h3{font-size:14px;margin:14px 0 6px}svg{max-width:100%;height:auto}" +
         "table{border-collapse:collapse;font-size:12.5px;width:100%}td,th{border-bottom:1px solid #E7EAF0;padding:5px 6px;text-align:left}" +
         ".legend{display:flex;gap:16px;flex-wrap:wrap;color:#5A6778;font-size:12px;margin:6px 0}" +
         ".agree{background:#EAF0F5;color:#3D6B8C}.expected{background:#FBF1D9;color:#7A5A06}" +
         ".known{background:#F8E5E5;color:#B23A3A;font-weight:600}.UNEXPECTED{background:#EFE3F5;color:#7A1F9E;font-weight:700}")
  h = [f"<!doctype html><html><head><meta charset='utf-8'><title>B2B SM-TOY-AUTH</title><style>{css}</style></head><body>",
       "<header><h1>Back-to-back run · SM-TOY-AUTH model vs C safety code</h1></header>",
       "<div class='note'>Generated by assurance/models/b2b/run_b2b.py. Not verification evidence: model and harness are " +
       "AI-drafted and unreviewed. A difference is a question for an engineer, not a defect until reviewed. " +
       "'agrees' is not a pass.</div><main>"]
  h.append("<section><h2>Run</h2><table>" + "".join(f"<tr><th>{escape(k)}</th><td>{escape(str(v).strip('`'))}</td></tr>"
                                                     for k, v in meta.items()) + "</table></section>")
  grid = ["<table><tr><th>Scenario</th><th>Stimulus</th><th>Upstream</th><th>Reference</th></tr>"]
  for sid in dict.fromkeys(r["scenario"] for r in results):
    rr = {r["build"]: r for r in results if r["scenario"] == sid}
    cells = []
    for b in ("upstream", "reference"):
      cl = {d["class"] for d in rr[b]["divergences"]}
      k = "UNEXPECTED" if "UNEXPECTED" in cl else "known" if "known" in cl else "expected" if cl else "agree"
      txt = {"agree": "agrees", "expected": "expected", "UNEXPECTED": "UNEXPECTED"}.get(k) or \
        ", ".join(sorted({d["id"] for d in rr[b]["divergences"] if d["id"]}))
      link = f"#{sid}-{b}" if rr[b].get("svg") else ""
      cells.append(f"<td class='{k}'>" + (f"<a href='{link}'>{escape(txt)}</a>" if link else escape(txt)) + "</td>")
    grid.append(f"<tr><td>{escape(sid)}</td><td>{escape(rr['upstream']['title'])}</td>{''.join(cells)}</tr>")
  grid.append("</table>")
  legend = "<div class='legend'>" + "".join(f"<span style='color:{c}'>━━ {escape(t)}</span>" for c, t in P.STATUS.values()) + "</div>"
  h.append("<section><h2>Coverage on the state machine</h2>" + (out / "coverage.svg").read_text(encoding="utf-8") + legend +
           "</section><section><h2>Scenario × build</h2>" + "".join(grid) + "</section>")
  for r in results:
    if r.get("svg"):
      h.append(f"<section id='{escape(r['scenario'])}-{r['build']}'><h2>{escape(r['scenario'])} · {r['build']} — {escape(r['title'])}</h2>")
      for d in r["divergences"]:
        h.append(f"<p>{d['t_ms']} ms, {escape(d['event'])}: model {d['model']}, C {d['c']}; cause {escape(d['cause'])}; " +
                 f"<b>{escape(d['class'])}</b> {escape(d['id'])}</p>")
      for name, f in r["svg"]:
        h.append(f"<h3>{name}</h3>" + (out / f).read_text(encoding="utf-8"))
      h.append(P.trace_legend_html() + "</section>")
  return "".join(h) + "</main></body></html>\n"


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
  write_views(results, record, out)
  (out / "b2b-report.md").write_text(report_md(results, meta), encoding="utf-8")
  (out / "b2b-report.html").write_text(report_html(results, meta, out), encoding="utf-8")
  slim = [{k: v for k, v in r.items() if k not in ("trace", "svg")} for r in results]
  (out / "b2b-report.json").write_text(json.dumps({"meta": meta, "results": slim}, indent=2) + "\n", encoding="utf-8")
  counts = {c: sum(d["class"] == c for r in results for d in r["divergences"]) for c in ("expected", "known", "UNEXPECTED")}
  for r in results:
    print(f"{r['scenario']:<26} {r['build']:<9} fired={','.join(r['fired']) or '-':<22} {result_label(r)}")
  print(f"divergences: {counts}; report: {out / 'b2b-report.md'}")
  print("FAILED: unexpected divergence" if counts["UNEXPECTED"] else "OK: no unexpected divergence (not verification)")
  return 1 if counts["UNEXPECTED"] else 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
