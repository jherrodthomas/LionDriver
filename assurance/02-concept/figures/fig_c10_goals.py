#!/usr/bin/env python3
"""Draw WP-C-10 Figure 7-1: one card per cybersecurity goal CSG-01 … CSG-08, what its control stops and how far it has got.

Each card shows:

- the goal, its CAL proposal (§4) and the threat scenarios it addresses with their WP-C-09 §8 risk;
- a looping scene: the threat enters, meets the goal's control at its element and either stops there or reaches the
  car. The control is drawn as built: no barrier while every requirement under the goal is open, a dashed one when a
  part is built or built but not verified, a solid one only when every requirement is verified (SMIL, 6 s; a still
  viewer shows the end pose);
- every concept-level requirement CSR-C-nn under the goal (§7) with its status, read from the latest dated status in
  its Status cell;
- the elements the controls are allocated to (§6), the gaps named in §4 and §7, and the claims of §5 that rest on it.

Goals, CALs, threat scenarios, requirements, statuses, allocations, gaps and claims come from WP-C-10 and the risks from
WP-C-09 (through fig_c09_scenes, which checks §8 against §3, §6 and §7). The short titles, requirement paraphrases,
scene labels and captions below are drawings. Each paraphrase quotes a phrase of its requirement, and each caption
names the barrier state it was written for; the build fails if the phrase leaves the requirement or the state the
statuses give changes, so a changed row needs its card redrawn. No exploitation detail.

    python3 fig_c10_goals.py            # regenerate the SVG
    python3 fig_c10_goals.py --check    # fail if a table disagrees, a card is missing or the SVG is stale

Standard library only. Output is deterministic.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hara"))
import fig_c09_scenes as fc  # WP-C-09 risks, already checked against §3, §6 and §7
from hara_figures import HAIR, INK, MUTED, header, pill, svg_doc, t, text_w, wrap  # noqa: E402

ParseError = fc.ParseError
GOALS = fc.GOALS
NAME = "fig-c10-7-1-goal-cards.svg"

CW, GAP, M, COLS = 400, 20, 40, 3
PW = CW - 24
RISK = {5: ("#DC2626", "#FFFFFF"), 4: ("#F97316", "#FFFFFF"), 3: ("#FDE68A", "#78350F")}
CSR_ST = {"open": ("#FEE2E2", "#7F1D1D", "Not implemented"), "partial": ("#FEF3C7", "#78350F", "Partial"),
          "unverified": ("#E0F2FE", "#075985", "Implemented, not verified"), "unconfirmed": ("#F1F5F9", "#334155", "Not confirmed"),
          "done": ("#DCFCE7", "#14532D", "Verified")}
BARRIER = {"open": None, "partial": "#D97706", "unverified": "#0284C7", "done": "#16A34A"}
BARRIER_TEXT = {"open": "no barrier: not built", "partial": "dashed amber: part built", "unverified": "dashed blue: built, not verified",
                "done": "solid green: verified"}


# ============================================================================ sources
def _section(doc, num):
  m = re.search(rf"^## {num}\. .*?(?=^## |\Z)", doc, re.M | re.S)
  if not m:
    raise ParseError(f"WP-C-10 §{num} not found")
  return m.group(0)


def _plain(s):
  s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
  return re.sub(r"\s+", " ", s.replace("**", "").replace("`", "")).strip()


def csr_status(cell):
  """The latest dated status of a §7 Status cell (the last bold '**date: …**' part, else the cell), as a CSR_ST key."""
  dated = re.findall(r"\*\*\d{4}-\d{2}-\d{2}:([^*]+)\*\*", cell)
  s = _plain(dated[-1] if dated else cell).lower()
  for key, pat in (("done", r"^\s*(implemented and )?verified"), ("partial", r"^\s*partial"),
                   ("unverified", r"^\s*implemented\b.*not verified"), ("unconfirmed", r"^\s*not confirmed"),
                   ("open", r"^\s*not (implemented|met)")):
    if re.search(pat, s):
      return key
  raise ParseError(f"WP-C-10 §7 status not understood: '{s[:60]}'")


def barrier(states):
  """What the card draws for a goal, from the statuses of its requirements."""
  if all(s in ("open", "unconfirmed") for s in states):
    return "open"
  if all(s == "done" for s in states):
    return "done"
  if any(s in ("open", "partial", "unconfirmed") for s in states):
    return "partial"
  return "unverified"


class Goals:
  def __init__(self, doc: str, tara):
    self.csg = {}
    for c in fc._rows(_section(doc, 4), r"\*\*CSG-\d+\*\*"):
      cal = re.match(r"\*\*CAL (\d)\*\*\s*(?:\((.*)\))?", c[3])
      if not cal:
        raise ParseError(f"{_plain(c[0])}: CAL proposal '{c[3]}' not understood")
      ts = [(t_, int(r)) for t_, r in re.findall(r"(TS-\d+) \((\d)\)", c[2])]
      self.csg[_plain(c[0])] = dict(goal=_plain(c[1]), ts=ts, cal=int(cal.group(1)), cal_note=cal.group(2) or "",
                                    gaps=re.findall(r"GAP-\d+", c[4]))
    self.alloc = {_plain(c[0]): _plain(re.sub(r"\s*\([^)]*\)", "", c[2])) for c in fc._rows(_section(doc, 6), r"CSG-\d+")}
    self.csr = {}
    for c in fc._rows(_section(doc, 7), r"CSR-C-\d+"):
      self.csr[c[0]] = dict(text=_plain(c[1]), parents=re.findall(r"CSG-\d+", c[2]), status=csr_status(c[6]),
                            gaps=re.findall(r"GAP-\d+", c[6]))
    self.csc = {}
    for c in fc._rows(_section(doc, 5), r"\*\*CSC-\d+\*\*"):
      for g in set(re.findall(r"CSG-\d+", c[1] + " " + c[4])):
        self.csc.setdefault(g, []).append((_plain(c[0]), _plain(c[3])))
    if not (self.csg and self.alloc and self.csr):
      raise ParseError("WP-C-10 tables not found (§4 goals, §6 concept, §7 requirements)")
    for g, v in self.csg.items():
      for ts, r in v["ts"]:
        if ts not in tara.risk:
          raise ParseError(f"{g}: {ts} is not in WP-C-09 §8")
        if tara.risk[ts]["risk"] != r:
          raise ParseError(f"{g}: WP-C-10 §4 gives {ts} risk {r}, WP-C-09 §8 gives {tara.risk[ts]['risk']}")
      if g not in self.alloc:
        raise ParseError(f"{g} has no control in WP-C-10 §6")
    for r, v in self.csr.items():
      for g in v["parents"]:
        if g not in self.csg:
          raise ParseError(f"{r}: parent {g} is not a WP-C-10 §4 goal")

  def under(self, g):
    return [r for r, v in self.csr.items() if g in v["parents"]]


def load(tara=None) -> Goals:
  return Goals(GOALS.read_text(encoding="utf-8"), tara or fc.load())


# ============================================================================ the cards
# title, scene (entry, element, effect), (barrier state the caption was written for, caption), {CSR: (paraphrase, phrase)}
MODEL = {
  "CSG-01": ("Lock the panda's safety configuration", ("Root on the SoC", "panda FW: mode lock", "Permissive envelope"),
             ("partial", "Mode lock built (reference build, not verified); release key, RDP open"), {
               "CSR-C-01": ("Enforce the Toyota mode; reject unauthorized mode or parameter changes", "enforce the Toyota safety mode"),
               "CSR-C-02": ("No debug key or debug-only capabilities in release firmware", "shall not accept a debug signing key")}),
  "CSG-02": ("Only authorized firmware on the safety MCU", ("SoC boot pins / dev bootstub", "panda boot chain", "Envelope replaced"),
             ("partial", "Softloader refused in a car mode; signing, RDP/WRP, recovery open"), {
               "CSR-C-02": ("No debug key or debug-only capabilities in release firmware", "shall not accept a debug signing key"),
               "CSR-C-03": ("Boot only firmware verified with a current algorithm", "verified with a current cryptographic algorithm"),
               "CSR-C-04": ("RDP/WRP set so the firmware cannot be replaced or read out", "cannot be replaced or read out without authorization"),
               "CSR-C-05": ("The recovery path does not flash unauthenticated firmware", "shall not flash unauthenticated (development) firmware")}),
  "CSG-03": ("Protect what the control software reads", ("Local access to params / IPC", "SoC params, msgq", "Actuation or DM altered"),
             ("partial", "Debug and joystick modes left out (reference build); params, IPC open"), {
               "CSR-C-06": ("Params and IPC protected, or the envelope does not depend on them", "or the safety envelope shall not depend on them"),
               "CSR-C-07": ("No debug, maneuver or joystick modes in reference builds", "Developer process-replacement modes (debug, maneuver, joystick)")}),
  "CSG-04": ("Load only verified, non-executable models", ("Tampered model file", "modeld: model load", "Code runs on the SoC"),
             ("open", "No control yet: the model loader runs code, no hash check"), {
               "CSR-C-08": ("Models load without running code from them, after a manifest check", "without executing code from the artefact")}),
  "CSG-05": ("Protect the safety-relevant CAN messages", ("Bus tap or rooted SoC", "panda: CAN RX/TX checks", "Spoofed inputs or actuation"),
             ("open", "No control yet: no counter or CRC on received messages"), {
               "CSR-C-09": ("Counter and CRC on safety-relevant RX and TX messages", "freshness and integrity protection (counter + CRC)")}),
  "CSG-06": ("Minimal, authenticated remote access", ("Back end / network", "athenad, SSH", "Root, personal data"),
             ("partial", "Onroad streaming blocked; RPCs and the SSH key path still open"), {
               "CSR-C-10": ("SSH off by default, no embedded authorized key", "shall not ship with an embedded authorized key"),
               "CSR-C-11": ("No arbitrary upload, SSH tunnel or key read over RPC; onroad streaming blocked",
                            "shall not permit arbitrary-URL upload")}),
  "CSG-07": ("Install only verified updates", ("Update path / supply chain", "updated", "Unsigned code installed"),
             ("open", "No control yet: git-branch updater, in-tree hashes only"), {
               "CSR-C-12": ("Install updates only after end-to-end package verification", "end-to-end integrity and authenticity verification"),
               "CSR-C-13": ("Safety components under LionDriver control, commit-pinned, with SBOM and scanning", "pinned by commit, with an SBOM")}),
  "CSG-08": ("Keep personal data and device key private", ("Lost or sold device", "Data at rest, device key", "Video, location, key leak"),
             ("open", "No control confirmed: encryption at rest unverified, no wipe"), {
               "CSR-C-14": ("Personal data and the identity key confidential in transit and at rest", "confidentiality in transit and at rest"),
               "CSR-C-15": ("Decommissioning wipes personal data and retires the identity key", "wipe personal data and revoke/retire")}),
}
SUPPORT = {"CSR-C-16": ("A LionDriver vulnerability intake and incident-response process", "vulnerability intake and incident-response process")}


def cards(G, model=None):
  model = MODEL if model is None else model
  if missing := sorted(set(G.csg) - set(model)):
    raise ParseError(f"no card for {', '.join(missing)}")
  if extra := sorted(set(model) - set(G.csg)):
    raise ParseError(f"card for {', '.join(extra)}, which WP-C-10 §4 does not have")
  out = []
  for g in sorted(G.csg):
    v, (title, scene, (state, caption), para) = G.csg[g], model[g]
    under = G.under(g)
    if sorted(under) != sorted(para):
      raise ParseError(f"{g}: §7 lists {under} under it, the card draws {sorted(para)}")
    for r, (_, q) in para.items():
      if _plain(q).lower() not in G.csr[r]["text"].lower():
        raise ParseError(f"{g}: '{q}' is no longer in {r}; redraw the card")
    states = [G.csr[r]["status"] for r in under]
    if (now := barrier(states)) != state:
      raise ParseError(f"{g}: its requirements now give the barrier '{now}', the caption was written for '{state}'; redraw the card")
    gaps = sorted(set(v["gaps"] + [x for r in under for x in G.csr[r]["gaps"]]), key=lambda s: int(s[4:]))
    out.append(dict(id=g, title=title, goal=v["goal"], cal=v["cal"], cal_note=v["cal_note"], ts=v["ts"], scene=scene, state=state,
                    caption=caption, alloc=G.alloc[g], csr=[(r, para[r][0], G.csr[r]["status"]) for r in sorted(under)],
                    gaps=gaps, csc=G.csc.get(g, [])))
  return out


def scene(x, y, w, c):
  """Entry -> the control at its element -> effect. The threat stops at a built barrier and runs on where there is none."""
  h, bw, cy = 92, 84, y + 40
  entry, element, effect = c["scene"]
  col = BARRIER[c["state"]]
  b = [f'<rect x="{x}" y="{y:.1f}" width="{w}" height="{h}" rx="8" fill="#F8FAFC" stroke="{HAIR}"/>']
  xs = [x + 10, x + w / 2 - bw / 2, x + w - bw - 10]
  for a, z in ((xs[0] + bw, xs[1]), (xs[1] + bw, xs[2])):
    b.append(f'<line x1="{a:.1f}" y1="{cy:.1f}" x2="{z:.1f}" y2="{cy:.1f}" stroke="#CBD5E1" stroke-width="2"/>')
  for bx, lab, stroke in zip(xs, (entry, element, effect), ("#7C3AED", "#334155", "#334155")):
    b.append(f'<rect x="{bx:.1f}" y="{cy - 16:.1f}" width="{bw}" height="32" rx="6" fill="#FFFFFF" stroke="{stroke}" stroke-width="1.3"/>')
    ls = wrap(lab, bw - 8, 9, True)
    if len(ls) > 2:
      raise ParseError(f"{c['id']}: scene label '{lab}' runs over two lines")
    for i, ln in enumerate(ls):
      b.append(t(round(bx + bw / 2, 1), round(cy + 3.5 - 5.5 * (len(ls) - 1) + 11 * i, 1), ln, 9, INK, 600, "middle"))
  gx = xs[1] - 10
  if col:
    dash = "" if c["state"] == "done" else ' stroke-dasharray="4 3"'
    b.append(f'<rect x="{gx - 4:.1f}" y="{cy - 24:.1f}" width="8" height="48" rx="2" fill="{col}" fill-opacity="0.18" stroke="{col}" '
             f'stroke-width="1.6"{dash}/>')
  through = c["state"] in ("open", "partial")
  start, stop = xs[0] + bw / 2, (xs[2] - 7 if through else gx - 10)
  if c["state"] == "partial":  # one part of the threat is stopped, the rest gets through
    b.append(f'<circle cx="{gx - 10:.1f}" cy="{cy:.1f}" r="4" fill="#7C3AED" opacity="0.6">'
             f'<animate attributeName="cx" values="{start:.1f};{start:.1f};{gx - 10:.1f};{gx - 10:.1f}" keyTimes="0;0.1;0.45;1" dur="6s" '
             f'repeatCount="indefinite"/></circle>')
  b.append(f'<circle cx="{stop:.1f}" cy="{cy:.1f}" r="5" fill="{"#DC2626" if through else "#7C3AED"}">'
           f'<animate attributeName="cx" values="{start:.1f};{start:.1f};{stop:.1f};{stop:.1f}" keyTimes="0;0.1;0.6;1" dur="6s" '
           f'repeatCount="indefinite"/></circle>')
  if through:
    b.append(f'<rect x="{xs[2]:.1f}" y="{cy - 16:.1f}" width="{bw}" height="32" rx="6" fill="#DC2626" fill-opacity="0.12" stroke="#DC2626" '
             f'stroke-width="1.6"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.6;0.62;1" dur="6s" repeatCount="indefinite"/></rect>')
  if text_w(c["caption"], 9.5, True) > w - 20:
    raise ParseError(f"{c['id']}: caption too long for the scene")
  b.append(t(x + 10, round(y + h - 9, 1), c["caption"], 9.5, "#DC2626" if through else MUTED, 600))
  return b, h


def card(x, y, c):
  b = [None]  # the frame, sized once the row height is known
  px, yy = x + 12, y + 26
  b.append(f'<title>{c["id"]}: {c["title"]}</title>')
  b.append(t(px, yy, c["id"], 12, MUTED, 600))
  if text_w(c["title"], 13.5, True) > PW - 56:
    raise ParseError(f"{c['id']}: title runs over one line")
  b.append(t(px + 56, yy, c["title"], 13.5, INK, 700))
  yy += 12
  cx = px
  # a CAL with a note in §4 (e.g. "re-derive, OI-8") is a provisional proposal: drawn as an outline, not a solid chip
  cal = (f"CAL {c['cal']} provisional ({c['cal_note']})", "#FFFFFF", "#0F172A", "#0F172A") if c["cal_note"] else \
        (f"CAL {c['cal']}", "#0F172A", "#FFFFFF", None)
  for s, bg, fg, stroke in [cal] + [(f"{ts} · risk {r}", *RISK[r], None) for ts, r in c["ts"]]:
    w = text_w(s, 10, True) + 14
    if cx + w > px + PW:
      cx, yy = px, yy + 22
    b.append(pill(cx, yy, s, bg, fg, 18, 10, stroke)[0])
    cx += w + 6
  yy += 32
  gl = wrap(c["goal"], PW, 9.5)
  for i, ln in enumerate(gl[:3]):
    b.append(t(px, yy + 12 * i, ln + (" …" if i == 2 and len(gl) > 3 else ""), 9.5, MUTED))
  yy += 12 * min(len(gl), 3) + 8
  sb, sh = scene(px, yy, PW, c)
  b += sb
  yy += sh + 16
  b.append(t(px, yy, "Requirements", 9.5, MUTED, 700))
  b.append(t(px + PW, yy, "Allocated to " + c["alloc"], 9.5, MUTED, None, "end"))
  yy += 8
  for rid, text, st in c["csr"]:
    bg, fg, lab = CSR_ST[st]
    pw = text_w(lab, 9, True) + 12
    b.append(pill(px + PW - pw, yy, lab, bg, fg, 16, 9)[0])
    ls = wrap(f"{rid}  {text}", PW - pw - 10, 9.5)
    if len(ls) > 2:
      raise ParseError(f"{c['id']}: {rid} paraphrase runs over two lines")
    for i, ln in enumerate(ls):
      b.append(t(px, yy + 12 + 12 * i, ln, 9.5, INK))
    yy += 12 * len(ls) + 10
  yy += 4
  foot = [("Gaps", ", ".join(c["gaps"]) or "none named")]
  if c["csc"]:
    foot.append(("Claims", "; ".join(f"{k} ({typ.lower()})" for k, typ in c["csc"])))
  for k, v in foot:
    ls = wrap(v, PW - 60, 9.5)
    b.append(t(px, yy + 6, k, 9.5, MUTED))
    for i, ln in enumerate(ls[:2]):
      b.append(t(px + 60, yy + 6 + 12 * i, ln, 9.5, INK))
    yy += 12 * min(len(ls), 2) + 6
  return b, yy + 10 - y


def figure(G) -> str:
  cs = cards(G)
  w = 2 * M + COLS * CW + (COLS - 1) * GAP
  body = header(w, "Cybersecurity goals · what each control stops, and how far it has got",
                "Threat → the goal's control at its element → what reaches the car. The barrier is drawn as built, from the §7 statuses.",
                "WP-C-10 §4-§7 · WP-C-09 §8", "Schematic scenes")
  lx = M
  for k in ("open", "partial", "unverified", "unconfirmed", "done"):
    bg, fg, lab = CSR_ST[k]
    body.append(pill(lx, 92, lab, bg, fg, 18, 10)[0])
    lx += text_w(lab, 10, True) + 22
  body.append(t(lx + 6, 105, "Barrier: " + " · ".join(BARRIER_TEXT[k] for k in ("open", "partial", "unverified", "done")), 10.5, MUTED))
  y = 124
  for r in range(0, len(cs), COLS):
    built = [card(M + k * (CW + GAP), y, c) for k, c in enumerate(cs[r:r + COLS])]
    row_h = max(h for _, h in built)
    for k, (b, _) in enumerate(built):
      b[0] = f'<rect x="{M + k * (CW + GAP)}" y="{y}" width="{CW}" height="{row_h:.0f}" rx="12" fill="#FFFFFF" stroke="{HAIR}"/>'
      body += [f"<g>"] + b + ["</g>"]
    y += row_h + GAP
  for r, (text, q) in SUPPORT.items():
    if r not in G.csr or _plain(q).lower() not in G.csr[r]["text"].lower() or G.csr[r]["parents"]:
      raise ParseError(f"{r} is no longer the goal-less supporting requirement the footer names; redraw it")
    body.append(t(M, y + 6, f"{r} supports every goal: {text} ({CSR_ST[G.csr[r]['status']][2].lower()}).", 10.5, INK))
    y += 18
  body.append(t(M, y + 8, "Paraphrases quote their requirement, checked at build. Statuses, CALs, risks, allocations, gaps and claims "
                "from WP-C-10 §4-§7 and WP-C-09 §8. No exploitation detail.", 10.5, MUTED))
  body.append(t(w - M, y + 26, "Generated by fig_c10_goals.py", 10, MUTED, None, "end"))
  desc = ("Figure 7-1: one card per cybersecurity goal. " + " ".join(
    f"{c['id']} ({c['title']}; CAL {c['cal']}{' provisional' if c['cal_note'] else ''}; " + ", ".join(f"{ts} risk {r}" for ts, r in c["ts"]) + f"): {c['caption']}. " +
    " ".join(f"{r} {CSR_ST[s][2].lower()}." for r, _, s in c["csr"]) for c in cs))
  return svg_doc(w, int(y + 38), "Figure 7-1. Cybersecurity goals: what each control stops (WP-C-10 §4-§7)", desc, body)


def build(G=None) -> dict[str, str]:
  return {NAME: figure(G or load())}


def main(argv: list[str]) -> int:
  check = "--check" in argv
  try:
    out = build()
  except ParseError as e:
    print(f"fig_c10_goals: {e}", file=sys.stderr)
    return 1
  stale = []
  for name, content in out.items():
    p = HERE / name
    if check:
      if not p.exists() or p.read_text(encoding="utf-8") != content:
        stale.append(name)
    else:
      p.write_text(content, encoding="utf-8")
  if stale:
    print("stale goal cards; run fig_c10_goals.py: " + ", ".join(stale), file=sys.stderr)
    return 1
  print(f"fig_c10_goals: {len(out)} figure {'current' if check else 'written'}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
