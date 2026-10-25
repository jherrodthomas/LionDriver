#!/usr/bin/env python3
"""Draw WP-S-03 Figure 4-5, the safety envelope's states (fig-s03-4-5-envelope-states.svg).

The system-level view of the two envelope state machines of WP-W-05 §5: the panda safety mode (SM-SAFETY-MODE) and,
inside the Toyota car mode, the authority controls_allowed (SM-TOY-AUTH). Below them, every transition that takes
authority away, sorted by whether it is in the code; beside them, what each host engagement state (SM-SELFDRIVED)
means for authority on the car. All of it is read from the state-machine records in
assurance/05-software/state-machines/; the implementation status of a transition is the one check_state_machines.py
derives from the WP-W-02 Baseline column of its SWSRs.

Hand-listed, and checked against the records so a change there fails the build until the figure is updated:
  MODE_TEXT   one line per safety mode
  REVOKE      a short name for every transition that clears authority
  HOST        what each host state means for the envelope, with the transitions that say so

    python3 fig_s03_envelope_states.py            # write the SVG
    python3 fig_s03_envelope_states.py --check    # fail if the records and the lists disagree or the SVG is stale

Standard library only (the records are read with check_state_machines' loader). Output is deterministic.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fig_s03_defence_in_depth import (INK, MUTED, FAINT, LINE, SAFETY, SAFETY_BG, SW, AMBER, AMBER_BG,  # noqa: E402
                                      RED, RED_BG, BLUE, BLUE_BG, GREY_BG, text, rect, line, svg, header, el, fmt)
sys.path.insert(0, str(HERE.parents[1] / "trace" / "tools"))
import check_state_machines as csm  # noqa: E402
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)
sys.path.insert(0, str(HERE.parents[1] / "02-concept" / "hara"))
from hara_figures import wrap  # noqa: E402

OUT = "fig-s03-4-5-envelope-states.svg"
SM_DIR = csm.SM_DIR

# One line per safety mode of SM-SAFETY-MODE.
MODE_TEXT = {
  "SILENT": "nothing sent to the car; the MCU's safe state",
  "NOOUTPUT": "receive only, nothing sent to the car",
  "ELM327": "diagnostic queries only, for the firmware query",
  "TOYOTA": "the car mode, parameter 73",
  "OTHER_CAR": "any other car mode; unreachable in the reference build (M4)",
}

# A short name for every transition of SM-TOY-AUTH that clears authority (to NOT_ALLOWED from ALLOWED or any state).
REVOKE = {
  "T2": "cruise off or cancelled", "T3": "brake pressed", "T4": "bad checksum, counter or length",
  "T5": "an RX message late or missing", "T6": "engaged mismatch, 1 Hz tick (2–3 s)",
  "T6a": "engaged mismatch (0.3 s)", "T7": "safety mode set again", "T9": "frame out of limits (today: dropped)",
  "T10a": "no SoC heartbeat (0.3 s)", "T10b": "commands stop arriving (50 / 100 ms)",
  "T10c": "cruise on with main off (150 ms)", "T10d": "MCU platform fault", "T10e": "driver steers against it",
  "T11": "TX rate exceeded", "T12": "driver torque above the limit", "T13": "SPI errors", "T14": "car CAN bus-off",
  "T15": "camera-side forwarding lost",
}

# What each host engagement state means for authority on the car (reference build). kind: agree, brief, gap.
HOST = [
  {"state": "disabled", "label": "Disabled", "env": "no authority", "ids": ["T1a", "T1c"], "kind": "agree",
   "note": "A cruise edge opens the 1 s window; with no engaged heartbeat it closes again (T1c)."},
  {"state": "disabled", "label": "Disabled, driver locked out", "env": "no authority", "ids": ["N1", "T1a", "T1c", "T1", "T6"],
   "kind": "agree", "note": "NO_ENTRY refuses (N1), so the engaged heartbeat never comes and the window closes (T1c). "
   "Upstream build: granted on the edge (T1) until the cruise drops or T6 revokes."},
  {"state": "preEnabled", "label": "Pre-enabled", "env": "authority, once granted", "ids": ["D1", "T1b", "T1c"],
   "kind": "agree", "note": "The engaged heartbeat grants in the window (T1b); a brake pressed while moving closes it (T1c)."},
  {"state": "enabled", "label": "Enabled", "env": "authority", "ids": ["D3", "T1b"], "kind": "agree",
   "note": "Granted by the engaged heartbeat inside the window (T1b)."},
  {"state": "overriding", "label": "Overriding: accelerator", "env": "authority, longitudinal blocked", "ids": ["E2"],
   "kind": "agree", "note": "Gas blocks longitudinal frames; authority is kept."},
  {"state": "overriding", "label": "Overriding: steering", "env": "authority", "ids": ["E2", "T10e", "T12"], "kind": "gap",
   "note": "The envelope does not see it: T10e and T12 are not in the code."},
  {"state": "softDisabling", "label": "Soft disabling", "env": "authority for up to 3 s", "ids": ["E1", "SD2"],
   "kind": "gap", "note": "The host winds down while the envelope still grants (GAP-16)."},
  {"state": "disabled", "label": "Just disabled (immediate)", "env": "authority ≤ 0.3 s, then none", "ids": ["X1", "T6a", "T6"],
   "kind": "brief", "note": "The engaged heartbeat drops; T6a revokes within 0.3 s (upstream build: T6, 2–3 s)."},
]
KIND = {"agree": (INK, "agree"), "brief": (AMBER, "briefly differ"), "gap": (RED, "disagree")}
STATUS = {"impl": ("in the code", BLUE, BLUE_BG), "partial": ("in the code, partly met or not assessed", AMBER, AMBER_BG),
          "missing": ("not in the code", RED, RED_BG)}


class EnvelopeError(ValueError):
  pass


def records() -> dict[str, dict]:
  return {sm["machine"]: sm for sm in (csm.load(p) for p in sorted(SM_DIR.glob("*.yaml")))}


def status(t: dict, sw: dict) -> str:
  if str(t.get("code", "")).lower().startswith("not implemented"):
    return "missing"
  return "impl" if csm.transition_state(t, sw) == "impl" else "partial"


def parse(sms: dict[str, dict], sw: dict) -> dict:
  mode, auth, host = sms["SM-SAFETY-MODE"], sms["SM-TOY-AUTH"], sms["SM-SELFDRIVED"]
  if set(MODE_TEXT) != set(mode["states"]):
    raise EnvelopeError(f"MODE_TEXT {sorted(MODE_TEXT)} does not match SM-SAFETY-MODE states {mode['states']}")
  if auth["states"] != ["NOT_ALLOWED", "ENGAGE_PENDING", "ALLOWED"]:
    raise EnvelopeError(f"SM-TOY-AUTH states changed: {auth['states']}; redraw the authority row")
  revokes = [t for t in auth["transitions"] if t["to"] == "NOT_ALLOWED" and t["from"] in ("ALLOWED", "any")]
  ids = [t["id"] for t in revokes]
  if set(ids) != set(REVOKE):
    raise EnvelopeError(f"REVOKE does not match the revoking transitions: missing {sorted(set(ids) - set(REVOKE))}, "
                        f"extra {sorted(set(REVOKE) - set(ids))}")
  known = {t["id"] for sm in sms.values() for t in sm["transitions"]}
  for h in HOST:
    if h["state"] not in host["states"]:
      raise EnvelopeError(f"HOST: {h['state']} is not an SM-SELFDRIVED state")
    for i in h["ids"]:
      if i not in known:
        raise EnvelopeError(f"HOST {h['label']}: {i} is not a transition of the records")
  missing = set(host["states"]) - {h["state"] for h in HOST}
  if missing:
    raise EnvelopeError(f"HOST does not cover SM-SELFDRIVED states {sorted(missing)}")
  mode_t = {t["id"]: t for t in mode["transitions"]}
  for need in ("M1", "M4", "M5", "M7"):
    if need not in mode_t:
      raise EnvelopeError(f"SM-SAFETY-MODE has no {need}; redraw the mode row")
  auth_t = {t["id"]: t for t in auth["transitions"]}
  for need in ("T1", "T1a", "T1b", "T1c"):
    if need not in auth_t:
      raise EnvelopeError(f"SM-TOY-AUTH has no {need}; redraw the authority row")
  rev = [{"id": t["id"], "name": REVOKE[t["id"]], "build": t.get("build", "all"), "status": status(t, sw)} for t in revokes]
  return {"modes": mode["states"], "revokes": rev,
          "keep": [(n["event"], n["reaction"]) for n in auth.get("non_revoking", [])]}


def arrow(pts, col=INK, w=1.5, dash="", marker="muted"):
  p = " ".join(f"{fmt(x)},{fmt(y)}" for x, y in pts)
  return el("polyline", None, points=p, fill="none", stroke=col, stroke_width=w, stroke_dasharray=dash,
            marker_end=f"url(#{marker})")


def state(x, y, w, h, name, sub, fill="#FFFFFF", stroke=SAFETY, tc=INK, sc=MUTED):
  out = [rect(x, y, w, h, fill=fill, stroke=stroke, sw=1.6, rx=10), text(x + 12, y + 22, name, size=13, fill=tc, weight=700)]
  for i, ln in enumerate(wrap(sub, w - 24, 10.5)):
    out.append(text(x + 12, y + 40 + i * 14, ln, size=10.5, fill=sc))
  return out


def figure(d: dict) -> str:
  W = 1440
  out = header(W, "4-5", "The safety envelope's states",
               "The panda's safety modes and, in the car mode, its authority to actuate; what takes authority away; and "
               "what each driving state of the host means on the car", "WP-S-03 §4.5 · records of WP-W-05 §5")
  # ---- safety modes
  out.append(text(40, 112, "Safety mode · sm-safety-mode (panda MCU)", size=13, fill=SAFETY, weight=700))
  out.append(el("circle", None, cx=56, cy=163, r=8, fill=INK))
  out.append(arrow([(64, 163), (98, 163)]))
  out.append(text(46, 196, "M1 reset", size=10, fill=MUTED))
  xs = {"SILENT": 100, "NOOUTPUT": 380, "ELM327": 660}
  for m, x in xs.items():
    out += state(x, 124, 220, 78, m, MODE_TEXT[m], SAFETY_BG)
  out.append(arrow([(320, 163), (378, 163)])); out.append(text(349, 156, "M4", size=10, weight=700, anchor="middle"))
  out.append(arrow([(600, 163), (658, 163)])); out.append(text(629, 156, "M4", size=10, weight=700, anchor="middle"))
  out.append(text(880, 112, "OTHER_CAR: " + MODE_TEXT["OTHER_CAR"].split("; ")[1], size=10, fill=MUTED, anchor="end"))
  # ---- car mode container
  cy, ch = 262, 238
  out.append(rect(100, cy, 800, ch, fill="#FFFBF7", stroke=SAFETY, sw=1.6, rx=12))
  out.append(text(116, cy + 24, "TOYOTA · 73: " + MODE_TEXT["TOYOTA"].split(", ")[0] + ", with authority · sm-toy-auth",
                  size=13, fill=SAFETY, weight=700))
  out.append(arrow([(770, 202), (770, cy - 2)]))
  out.append(text(780, 232, "M4: only TOYOTA · 73 accepted,", size=10))
  out.append(text(780, 245, "then only steps down (TSR-512)", size=10))
  out.append(arrow([(150, cy), (150, 204)], dash="5 4"))
  out.append(text(160, 226, "M7: no heartbeat for 5 s", size=10)); out.append(text(160, 239, "(siren if recently engaged)", size=10, fill=MUTED))
  out.append(arrow([(470, cy), (470, 204)], dash="5 4"))
  out.append(text(480, 232, "M5: back to NOOUTPUT", size=10)); out.append(text(480, 245, "or SILENT only", size=10, fill=MUTED))
  sy = cy + 52
  out += state(130, sy, 200, 82, "NOT_ALLOWED", "steering and acceleration frames blocked", "#FFFFFF")
  out += state(400, sy, 200, 82, "ENGAGE_PENDING", "the 1 s window after a cruise edge", AMBER_BG, AMBER)
  out += state(670, sy, 210, 82, "ALLOWED", "controls_allowed = 1: frames pass, each checked against the limits",
               SAFETY, SAFETY, "#FFFFFF", "#FFFFFF")
  out.append(arrow([(330, sy + 26), (398, sy + 26)], SW, 2, marker="grant"))
  out.append(text(364, sy + 18, "T1a", size=10, fill=SW, weight=700, anchor="middle"))
  out.append(arrow([(600, sy + 26), (668, sy + 26)], SW, 2, marker="grant"))
  out.append(text(634, sy + 18, "T1b", size=10, fill=SW, weight=700, anchor="middle"))
  out.append(arrow([(398, sy + 60), (332, sy + 60)], MUTED))
  out.append(text(364, sy + 54, "T1c", size=10, fill=MUTED, weight=700, anchor="middle"))
  out.append(arrow([(775, sy + 82), (775, sy + 110), (230, sy + 110), (230, sy + 84)], RED, 2, marker="red"))
  n_code = sum(1 for r in d["revokes"] if r["status"] != "missing")
  out.append(text(500, sy + 126, f"revoke: {n_code} transitions in the code, "
                  f"{len(d['revokes']) - n_code} not yet (below)", size=10.5, fill=RED, weight=700, anchor="middle"))
  out.append(text(116, cy + ch - 28, "T1a: cruise 0→1 with every RX check valid · T1b: the host's engaged heartbeat "
                  "within 1 s · T1c: 1 s without it, cruise off, brake.", size=10, fill=MUTED))
  out.append(text(116, cy + ch - 14, "Upstream build: T1 grants on the cruise edge, with no window.", size=10, fill=MUTED))
  # ---- revocations
  y0 = cy + ch + 24
  groups = [(k, [r for r in d["revokes"] if r["status"] == k]) for k in STATUS]
  rows = max(len(g) for _, g in groups)
  bh = 74 + rows * 19 + 36
  out.append(rect(40, y0, 890, bh, fill="#F8FAFC", stroke=LINE, sw=1, rx=10))
  out.append(text(56, y0 + 24, "What takes authority away (to NOT_ALLOWED)", size=13, weight=700))
  cx = [56, 352, 648]
  for (k, rs), x in zip(groups, cx):
    lab, col, bg = STATUS[k]
    out.append(rect(x, y0 + 36, 14, 14, fill=bg, stroke=col, sw=1.2, rx=4, dash="4 2" if k == "missing" else ""))
    out.append(text(x + 20, y0 + 47, f"{lab} ({len(rs)})", size=10.5, fill=col, weight=700))
    for i, r in enumerate(rs):
      yy = y0 + 70 + i * 19
      out.append(text(x, yy, r["id"], size=10.5, weight=700))
      nm = r["name"] + (" · ref." if r["build"] == "reference" else " · upstr." if r["build"] == "upstream" else "")
      out.append(text(x + 40, yy, nm, size=10.5, fill=INK if k != "missing" else MUTED))
  keep = " · ".join(f"{e.split(' (')[0]}: {r.split(';')[0]}" for e, r in d["keep"])
  out.append(text(56, y0 + bh - 26, "Kept, not revoked: " + keep + ".", size=10.5, fill=MUTED))
  out.append(text(56, y0 + bh - 11, "ref. = reference build only. Status from the WP-W-02 Baseline of the software safety "
                  "requirements each transition cites; nothing is verified on hardware, so it is blue, not green.", size=10, fill=MUTED))
  # ---- host panel
  x0, py = 966, 100
  ph = (y0 + bh) - py
  out.append(rect(x0, py, 434, ph, fill="#F8FAFC", stroke=LINE, sw=1, rx=10))
  out.append(text(x0 + 16, py + 24, "Host state → authority on the car", size=13, weight=700))
  out.append(text(x0 + 16, py + 42, "sm-selfdrived (QM) against sm-toy-auth, reference build", size=10.5, fill=MUTED))
  rh = (ph - 60) / len(HOST)
  for i, h in enumerate(HOST):
    yy = py + 56 + i * rh
    col = KIND[h["kind"]][0]
    out.append(rect(x0 + 16, yy, 148, 34, fill="#FFFFFF", stroke=FAINT, sw=1.2, rx=8))
    for j, ln in enumerate(wrap(h["label"], 136, 10.5, True)[:2]):
      out.append(text(x0 + 24, yy + (21 if len(wrap(h["label"], 136, 10.5, True)) == 1 else 14) + j * 13, ln, size=10.5, weight=700))
    out.append(arrow([(x0 + 166, yy + 17), (x0 + 206, yy + 17)], col, 1.6, "" if h["kind"] == "agree" else "5 3",
                     "muted" if h["kind"] == "agree" else "red"))
    auth = h["env"].startswith("authority")
    out.append(rect(x0 + 210, yy, 208, 34, fill=SAFETY if auth else SAFETY_BG, stroke=SAFETY, sw=1.2, rx=8))
    out.append(text(x0 + 220, yy + 21, h["env"], size=10.5, fill="#FFFFFF" if auth else INK, weight=600))
    note = ("⚠ " if h["kind"] == "gap" else "") + h["note"]
    for j, ln in enumerate(wrap(note, 400, 9.5)[:3]):
      out.append(text(x0 + 18, yy + 48 + j * 12.5, ln, size=9.5, fill=col if h["kind"] != "agree" else MUTED))
  # ---- footer
  y = y0 + bh + 24
  lx = 40
  for k, (col, lab) in KIND.items():
    out.append(line(lx, y - 4, lx + 28, y - 4, stroke=col, sw=1.6, dash="" if k == "agree" else "5 3"))
    out.append(text(lx + 34, y, f"host and envelope {lab}", size=10.5, fill=MUTED))
    lx += 34 + len(f"host and envelope {lab}") * 5.6 + 24
  out.append(text(lx, y, "Green arrows grant; red revokes; dashed mode arrows step down.", size=10.5, fill=MUTED))
  y += 18
  out.append(text(40, y, "Generated by fig_s03_envelope_states.py from the state-machine records of WP-W-05 §5 "
                  "(sm-safety-mode, sm-toy-auth, sm-selfdrived); the tables there stay normative and give the code "
                  "reference of every transition.", size=10.5, fill=MUTED))
  extra, y = terms.svg_footer(out, 40, y + 22, W - 80)
  out += extra
  h = int(y + 12)
  desc = ("Safety modes " + ", ".join(d["modes"]) + "; authority NOT_ALLOWED, ENGAGE_PENDING, ALLOWED. Revocations: " +
          "; ".join(f"{r['id']} {r['name']} ({STATUS[r['status']][0]})" for r in d["revokes"]) + ". Host states: " +
          "; ".join(f"{h['label']}: {h['env']} ({KIND[h['kind']][1]})" for h in HOST) + ".")
  extra_markers = "".join(
    f'<marker id="{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
    f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for k, c in (("red", RED), ("grant", SW)))
  return svg(W, h, "Figure 4-5. The safety envelope's states (WP-S-03 §4.5)", desc, out).replace("<defs>", "<defs>" + extra_markers, 1)


def build() -> dict[str, str]:
  return {OUT: figure(parse(records(), csm.swsr_records()))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except EnvelopeError as e:
    print(f"fig_s03_envelope_states: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"assurance/03-system/figures/{n} is stale; run fig_s03_envelope_states.py", file=sys.stderr)
    if not stale:
      print(f"fig_s03_envelope_states: {len(outputs)} figure current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote assurance/03-system/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
