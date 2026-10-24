"""Mock cyber dashboard (one threat scenario), step 2 of 3, in the layout of assurance/sim/blender/compose.py.

  python3 assurance/sim/cyber/mock/compose.py --ts TS-14   # after cyber_scene.py --ts TS-14; runs its plant cases (seconds)
  python3 assurance/sim/cyber/mock/compose.py --ts TS-06

Writes assurance/sim/cyber/figures/<slug>-mock.jpg. The TARA facts are read from the documents: threat text, STRIDE,
violated and asset properties, damage scenarios with impact and HARA link, feasibility factors, risk, treatment and goal
with CAL from WP-C-09 and WP-C-10 (through fig_c09_scenes, which checks §8 against §3, §6 and §7), gate states from
WP-S-07 §4 (through fig_cy_iso). The drawing choices per threat scenario are in scenarios.py.

Fuchsia = cyber (path, threat, impact/risk/feasibility scales); cyan = security properties and the chosen treatment;
red/amber only where safety comes in (hazards, ASILs) and for the shared barrier convention. Synthetic, no evidence.
"""
import json, math, re, sys
from functools import cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "figures"))
sys.path.insert(0, str(ROOT / "assurance" / "02-concept" / "figures"))
import fig_c09_scenes as fc  # noqa: E402
import fig_cy_iso as fi  # noqa: E402
from scenarios import SCENARIOS  # noqa: E402

TS = globals().get("TS") or (sys.argv[sys.argv.index("--ts") + 1] if "--ts" in sys.argv else "TS-14")
SC = SCENARIOS[TS]
HE = HERE.parents[1] / "blender" / "dashboards" / "he-01-2-hardover-adjacent.jpg"
CUT = HERE / "out" / TS.lower().replace("-", "")
DEST = HERE.parent / "figures" / f"{SC['slug']}-mock.jpg"


@cache
def plant(case_id: str) -> dict:
  """A layer-1 plant case (real panda code in the loop): time, position, offset, accelerations, torque, events."""
  sys.path.insert(0, str(HERE.parents[1] / "plant"))
  from cases import all_cases
  from simulate import simulate
  r = simulate(next(c for c in all_cases() if c.id == case_id))
  return {"t": r.t, "x": r.x, "e_y": r.e_y, "ax": r.ax, "torque": r.torque, "t0": r.t0, "events": r.events, "metrics": r.metrics}


# ------------------------------------------------------------------------------------------------- TARA facts
TA = fc.load()
DOC = fc.SOURCE.read_text(encoding="utf-8")
TS_ROW = {c[0]: c for c in fc._rows(fc._section(DOC, 4), r"TS-\d+")}[TS]
AS_ROW = {c[0]: c for c in fc._rows(fc._section(DOC, 2), r"AS-\d+")}
PROPS = ["C", "I", "A", "Auth", "Authz", "NR"]
PNAME = {"C": "confidentiality", "I": "integrity", "A": "availability", "Auth": "authenticity", "Authz": "authorization",
         "NR": "non-repudiation"}


def prop(word: str) -> str:
  w = word.strip().lower()
  for pre, k in (("authori", "Authz"), ("authz", "Authz"), ("auth", "Auth"), ("integ", "I"), ("avail", "A"), ("conf", "C"),
                 ("non-rep", "NR")):
    if w.startswith(pre):
      return k
  raise fc.ParseError(f"WP-C-09: property '{word}' not understood")


THREAT = re.sub(r"\s*\(added [^)]*\)", "", TA.ts[TS]["text"]).strip()
STRIDE = {k for k, pre in (("S", "Spoof"), ("T", "Tamper"), ("R", "Repud"), ("I", "Info"), ("D", "DoS"), ("E", "Elev"))
          if pre in TA.ts[TS]["stride"]}
ASSETS = fc._ids(TS_ROW[3], "AS")
VIOL = [prop(w) for w in TS_ROW[4].split(",")]
INTEREST = {}
for a in ASSETS:
  for w in AS_ROW[a][2].split(","):
    if prop(w) not in VIOL: INTEREST.setdefault(prop(w), []).append(a)
CIA_CAPTION = "violated: " + ", ".join(PNAME[k] for k in VIOL) + (
  "".join(f" · {PNAME[k]} of interest ({', '.join(v)})" for k, v in sorted(INTEREST.items(), key=lambda kv: PROPS.index(kv[0])))
  if INTEREST else f" ({', '.join(ASSETS)})")
RISK = TA.risk[TS]
LEVELS = [("Elapsed time", ["Hours", "Days", "Weeks", "Months"], ["Hours", "Days", "Weeks", "Months"]),
          ("Expertise", ["Layman", "Proficient", "Expert", "Multiple"], ["Layman", "Profic.", "Expert", "Multi"]),
          ("Knowledge", ["Public", "Restricted", "Confidential", "Strictly"], ["Public", "Restr.", "Conf.", "Strict"]),
          ("Window", ["Unlimited", "Easy", "Moderate", "Difficult"], ["Unlim.", "Easy", "Moder.", "Diff."]),
          ("Equipment", ["Standard", "Specialized", "Bespoke", "Multiple"], ["Stand.", "Spec.", "Besp.", "Multi"])]
FACTORS = []
for (name, full, short), val in zip(LEVELS, TA.feas[SC["ap"]]["factors"]):
  k = next((i for i, f in enumerate(full) if val.strip().startswith(f)), None)
  if k is None:
    raise fc.ParseError(f"WP-C-09 §6 {SC['ap']}: {name} '{val}' not on the scale")
  FACTORS.append((name, short, k))
CSG, CAL_NOTE = TA.csg[TS][0]
CAL = re.match(r"CAL \d", CAL_NOTE).group(0)
DS = TA.ts[TS]["damage"]
CAT = ["safety", "financial", "operational", "privacy"]
IMP = TA.impact(TS)
TOP = max(fc.LEVEL[v] for v in IMP)
IMPACT_SUB = f"{IMP[0] if fc.LEVEL[IMP[0]] == TOP else next(v for v in IMP if fc.LEVEL[v] == TOP)} (" + \
  ", ".join(c for c, v in zip(CAT, IMP) if fc.LEVEL[v] == TOP) + ")"

S07 = {}
for line in fi.S07.read_text(encoding="utf-8").splitlines():
  m = re.match(r"^\| (CSR-\d{3}) \|", line)
  if m: S07[m.group(1)] = line.rstrip().rstrip("|").split("|")[-1]
def state(csr): return fi.csr_state(S07[csr])
WALL_REQS = [c for _, ids in SC["walls"] for c in ids] + (list(SC["branch"][1]) if SC["branch"] else [])

# ------------------------------------------------------------------------------------------------- drawing
W, H = 1600, 900
BG, PANEL, EDGE = "#111110", "#1a1a19", "#2c2c2a"
TEXT, TEXT2, MUTED, DIM = "#f0efec", "#c3c2b7", "#898781", "#5f5e59"
CRIT, WARN, AMBER, SERIES, BLUE, GREEN = "#d03b3b", "#fab219", "#d97706", "#3987e5", "#38bdf8", "#4ade80"
CY, CY_SOFT, CY_TXT, PROP = "#d946ef", "#2a1030", "#f0abfc", "#06b6d4"     # cyber accent, its soft fill and text; properties
LV = {"Severe": "#86198f", "Major": "#5b2157", "Moderate": "#3b3542", "Negligible": "#262624"}
RC = {5: "#86198f", 4: "#6b1d63", 3: "#4a2346", 2: "#2c2c2a", 1: "#222220"}
STATE_LOOK = {"partial": (AMBER, "dashed amber"), "open": (MUTED, "no barrier"), "unverified": (BLUE, "dashed blue"),
              "done": (GREEN, "solid green")}

def font(size, w="Regular"): return ImageFont.truetype(f"/usr/share/fonts/opentype/inter/Inter-{w}.otf", size)
F = {k: font(*v) for k, v in {"h1": (19, "SemiBold"), "h2": (15, "SemiBold"), "b": (14, "Regular"), "bs": (14, "SemiBold"),
     "s": (12, "Regular"), "ss": (12, "SemiBold"), "big": (26, "SemiBold"), "xs": (10, "Regular"), "xss": (10, "SemiBold"),
     "x9": (9, "Regular"), "x9s": (9, "SemiBold")}.items()}
ANIM = globals().get("ANIM", False)   # animate.py: leave out what the clip brings in step by step
R = plant("F-01b"); T_CORR = R["events"]["driver correction"] - R["t0"]
im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)

def redraw():
  global d; d = ImageDraw.Draw(im)
def panel(box, title=None, edge=EDGE):
  d.rounded_rectangle(box, 6, fill=PANEL, outline=edge, width=1)
  if title: d.text((box[0] + 10, box[1] + 8), title, font=F["h2"], fill=TEXT)
def pill(xy, text, fill, fg=TEXT, f="ss", anchor="la", outline=None):
  x, y = xy; tw = d.textlength(text, font=F[f])
  if anchor == "ma": x -= tw / 2 + 7
  d.rounded_rectangle((x, y, x + tw + 14, y + 21), 4, fill=fill, outline=outline); d.text((x + 7, y + 3), text, font=F[f], fill=fg)
  return x, y, x + tw + 14, y + 21
def chip(x, y, txt, fill=None, fg=TEXT, outline=None, f="xss", w=None, h=19):
  tw = w or d.textlength(txt, font=F[f]) + 14
  d.rounded_rectangle((x, y, x + tw, y + h), 4, fill=fill, outline=outline or (None if fill else EDGE))
  d.text((x + tw / 2, y + (h - 12) / 2), txt, font=F[f], fill=fg, anchor="ma"); return x + tw + 4
def dashed(p0, p1, color, w=3, dash=7, gap=5):
  (x0, y0), (x1, y1) = p0, p1; L = math.hypot(x1 - x0, y1 - y0); n = 0
  while n < L:
    a, b = n / L, min(n + dash, L) / L
    d.line((x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, x0 + (x1 - x0) * b, y0 + (y1 - y0) * b), fill=color, width=w); n += dash + gap
def wrap(text, f, width):
  out, line = [], ""
  for w_ in text.split():
    t = (line + " " + w_).strip()
    if d.textlength(t, font=F[f]) > width and line: out.append(line); line = w_
    else: line = t
  return out + [line]
def para(x, y, text, f="s", fill=TEXT2, width=280, lh=15):
  for ln in wrap(text, f, width): d.text((x, y), ln, font=F[f], fill=fill); y += lh
  return y

# ================================================================ header
d.text((14, 8), f"Scene {SC['slug']}", font=F["h1"], fill=TEXT)
x = 14 + d.textlength(f"Scene {SC['slug']}", font=F["h1"]) + 12
pill((x, 9), f"{TS}  risk {RISK['risk']}", CY, BG); pill((x + 112, 9), "MOCK", "#3b3542")
d.text((14, 32), SC["subtitle"], font=F["s"], fill=TEXT2)
fields = [("Path source", "WP-C-09 §5 · WP-S-07 §4"), ("Hand-off", SC["handoff"]),
          ("Gate statuses", "as of 2026-10-12"), ("Lens", "credited | as built")]
fx = W - 14
for k, v in reversed(fields):
  wv = max(d.textlength(v, font=F["bs"]), d.textlength(k, font=F["s"])); fx -= wv
  d.text((fx, 9), k, font=F["s"], fill=MUTED); d.text((fx, 27), v, font=F["bs"], fill=TEXT); fx -= 26
d.line((0, 50, W, 50), fill=EDGE)

# ================================================================ left: threat card with feasibility gauges and CAL (widgets 4, 5)
panel((10, 56, 310, 334), edge=CY)
d.text((20, 64), f"Threat scenario {TS}", font=F["h1"], fill=CY_TXT)
y = para(20, 90, THREAT, "bs", TEXT, 278, 17)
y = para(20, y + 3, SC["entry"], "s", TEXT2, 280)
y += 6; d.text((20, y), "Attack feasibility", font=F["ss"], fill=TEXT); d.text((300, y), RISK["feas"], font=F["ss"], fill=CY_TXT, anchor="ra"); y += 18
for name, lv, k in FACTORS:
  d.text((20, y + 2), name, font=F["xs"], fill=TEXT2)
  for i, l_ in enumerate(lv):
    xx = 96 + i * 51; on = i <= k
    d.rounded_rectangle((xx, y, xx + 48, y + 15), 2, fill=("#a21caf" if k == 0 else "#6b1d63" if k == 1 else "#4a2346") if on else "#222220")
    d.text((xx + 24, y + 2), l_, font=F["x9s"] if i == k else F["x9"], fill=TEXT if i == k else (TEXT2 if on else DIM), anchor="ma")
  y += 18
y += 4
d.text((20, y + 3), "Goal", font=F["xs"], fill=MUTED); xg = chip(54, y, f"{CSG} · {CAL}", fill="#2a2a28", fg=TEXT, f="xss")
if SC["cal_flag"] and "OI-8" in CAL_NOTE:
  chip(156, y, SC["cal_flag"], fill=CY_SOFT, fg=CY_TXT, outline=CY, f="xss")
d.text((20, 318), "longer bar = harder to attack · ratings are proposals", font=F["xs"], fill=MUTED)

# ================================================================ left: risk matrix and treatment (widgets 2, 3)
panel((10, 340, 310, 640), "Risk and treatment")
M = [TA.matrix[i] for i in (4, 3, 2, 1)]
gx, gy, cw, ch = 64, 382, 44, 23
for i, f_ in enumerate(["High", "Med.", "Low", "V. low"]): d.text((gx + i * cw + cw / 2, gy - 14), f_, font=F["x9"], fill=MUTED, anchor="ma")
for r in range(4):
  d.text((gx - 6, gy + r * ch + 6), f"imp. {4 - r}", font=F["x9"], fill=MUTED, anchor="ra")
  for c in range(4):
    v = M[r][c]; box = (gx + c * cw + 1, gy + r * ch + 1, gx + (c + 1) * cw - 1, gy + (r + 1) * ch - 1)
    d.rounded_rectangle(box, 2, fill=RC[v]); d.text((box[0] + 5, box[1] + 4), str(v), font=F["xss"], fill=TEXT2)
    if v >= 3: d.rounded_rectangle(box, 2, outline="#a8a29e")
col, row = fc.FEAS.index(RISK["feas"]), 4 - RISK["impact"]
cx, cy = gx + col * cw + cw - 9, gy + row * ch + ch / 2
d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=TEXT, outline=CY, width=2)
d.ellipse((cx - 20, cy - 6, cx - 8, cy + 6), outline=CY_TXT, width=2)
lx = gx + 4 * cw + 10
d.text((lx, gy - 2), "● as rated:", font=F["xs"], fill=TEXT)
d.text((lx, gy + 11), f"{RISK['impact']} × {dict(Medium='Med.').get(RISK['feas'], RISK['feas'])} = {RISK['risk']}", font=F["xss"], fill=CY_TXT)
d.text((lx, gy + 30), "○ treated:", font=F["xs"], fill=CY_TXT); d.text((lx, gy + 43), "not re-rated", font=F["xs"], fill=CY_TXT)
d.text((lx, gy + 56), "(OI-5)", font=F["xs"], fill=CY_TXT)
d.text((20, gy + 4 * ch + 4), "outlined: risk ≥ 3, treatment required", font=F["x9"], fill=MUTED)
y = gy + 4 * ch + 20; x = 20
TREAT = RISK["treat"].split("/")[0].strip()
for k in ("Reduce", "Retain", "Share", "Avoid"): x = chip(x, y, k, fill=PROP if k == TREAT else None, fg=BG if k == TREAT else DIM, w=66)
y += 26
for (lab, txt), c in zip(SC["treatment"], (TEXT2, WARN, CY_TXT)):
  d.text((20, y), lab, font=F["xss"], fill=MUTED); y = para(76, y, txt, "xs", c, 224, 13) + 4

# ================================================================ centre: cutaway
CX, CY0, CW, CHh = 320, 56, 912, 510
panel((CX, CY0, CX + CW, CY0 + CHh))
cut = Image.open(CUT / "cutaway.png").convert("RGB")
sx = (CW - 2) / cut.width; cut = cut.resize((CW - 2, round(cut.height * sx)), Image.LANCZOS)
im.paste(cut.crop((0, 0, CW - 2, CHh - 2)), (CX + 1, CY0 + 1)); redraw()
A = json.load(open(CUT / "anchors.json"))["px"]
P = {k: (CX + 1 + v[0] * sx, CY0 + 1 + v[1] * sx) for k, v in A.items()}
def tag(key, text, dx, dy, color="#2a2a28", fg=TEXT):
  ax, ay = P[key]; bx, by = ax + dx, ay + dy
  pill((bx, by), text, color, fg, anchor="ma")
  d.line((ax, ay, bx, by + (21 if dy < 0 else 0)), fill=color if color != "#2a2a28" else "#9a9a94", width=1)
  d.ellipse((ax - 3, ay - 3, ax + 3, ay + 3), fill=fg if color == "#2a2a28" else color)
for key, text, dx, dy, hot in SC["cut_tags"]:
  tag(key, text, dx, dy, CY, BG) if hot else tag(key, text, dx, dy)
for key, dx, dy, text, sub in SC["gate_pills"]:
  gx_, gy_ = P[key]
  hot = WARN if not sub.startswith("no barrier") else CY_TXT
  gb = pill((gx_ + dx, gy_ + dy), text, "#3a2a0a" if hot == WARN else CY_SOFT, hot)
  d.text((gb[0] + 7, gb[3] + 2), sub, font=F["xs"], fill=hot)
bt = SC["banner"]
bw = d.textlength(bt, font=F["bs"]) + 20
d.rounded_rectangle((CX + 12, CY0 + CHh - 40, CX + 12 + bw, CY0 + CHh - 12), 4, fill=PANEL, outline=CY)
d.text((CX + 22, CY0 + CHh - 34), bt, font=F["bs"], fill=TEXT)
d.text((CX + CW - 10, CY0 + (CHh - 56 if SC.get("parts_note") == "bottom" else 8)), "parts: generic CC-BY stand-ins, not the real hardware",
       font=F["xs"], fill=MUTED, anchor="ra")

# ================================================================ TARA strip (tiles)
wall_states = [state(c) for c in WALL_REQS]
n_open, n_part = wall_states.count("open"), wall_states.count("partial")
tiles = [("Impact level", str(RISK["impact"]), IMPACT_SUB, CY_TXT), ("Attack feasibility", RISK["feas"], "", CY_TXT),
         ("Risk value", str(RISK["risk"]), "highest band" if RISK["risk"] == 5 else "≥ 3: treat", CY),
         ("Treatment", TREAT, SC["treatment_sub"], PROP),
         ("Gates verified", f"{wall_states.count('done')} of {len(wall_states)}", f"{n_open} open" if n_open else f"{n_part} partial", TEXT)]
tw = (CW - 4 * 8) / 5
for i, (k, v, sub, c) in enumerate(tiles):
  x0 = CX + i * (tw + 8); panel((x0, 573, x0 + tw, 640))
  d.text((x0 + 10, 580), k, font=F["s"], fill=TEXT2)
  d.text((x0 + 10, 598), v, font=F["big"], fill=c)
  d.text((x0 + tw - 10, 620), sub, font=F["xs"], fill=MUTED, anchor="ra")

# ================================================================ right column
RX, RW = 1242, 348
if SC["consequence"] == "image":
  panel((RX, 56, RX + RW, 236), "Physical consequence (plant F-01b)")
  he = Image.open(HE).convert("RGB").crop((322, 56, 1232, 565)); he = he.resize((RW - 20, round((RW - 20) * he.height / he.width)))
  he = he.crop((0, 30, he.width, 30 + 124)); im.paste(he, (RX + 10, 82)); redraw()
  d.text((RX + 10, 212), "HE-01.2 render reused: hard-over within the envelope", font=F["xs"], fill=TEXT2)
else:
  panel((RX, 56, RX + RW, 236), "What new software can command (plant)")
  y = 88
  for cid, what, hz in SC["cases"]:
    e = plant(cid); t0 = e["t0"]; ev = {k: v - t0 for k, v in e["events"].items()}; tl = e["metrics"].get("t_line")
    bits = []
    if tl is not None: bits.append(f"lane line +{tl:.2f} s")
    if "panda siren" in ev: bits.append(f"siren +{ev['panda siren']:.2f} s")
    if "driver correction" in ev: bits.append(f"driver +{ev['driver correction']:.2f} s")
    d.text((RX + 10, y), cid, font=F["ss"], fill=TEXT); d.text((RX + 56, y), what, font=F["s"], fill=TEXT2)
    d.text((RX + RW - 10, y), hz, font=F["xss"], fill=CRIT, anchor="ra")
    d.text((RX + 56, y + 15), " · ".join(bits[:3]), font=F["xs"], fill=CY_TXT); y += 34

panel((RX, 242, RX + RW, 404), "Gates on this path")
if len(SC["gates"]) <= 4:
  y = 268
  for cid, what in SC["gates"]:
    st = state(cid); c, look = STATE_LOOK[st]
    if st == "open": d.line((RX + 12, y + 7, RX + 44, y + 7), fill=EDGE, width=1)
    else: dashed((RX + 12, y + 7), (RX + 44, y + 7), c, 3, 6, 4)
    d.text((RX + 52, y), cid, font=F["ss"], fill=TEXT); d.text((RX + 116, y), what, font=F["s"], fill=TEXT2)
    d.text((RX + 116, y + 14), f"{st} · {look}", font=F["xs"], fill=c); y += 27
else:
  y = 268
  for cid, what in SC["gates"]:
    st = state(cid); c, look = STATE_LOOK[st]
    if st == "open": d.line((RX + 12, y + 6, RX + 40, y + 6), fill=EDGE, width=1)
    else: dashed((RX + 12, y + 6), (RX + 40, y + 6), c, 3, 5, 4)
    d.text((RX + 48, y), cid, font=F["ss"], fill=TEXT); d.text((RX + 108, y), what, font=F["xs"], fill=TEXT2)
    d.text((RX + RW - 12, y), st, font=F["xss"], fill=c, anchor="ra"); y += 18
  y -= 1
d.text((RX + 12, y + 1), SC["lens"][0], font=F["xs"], fill=CY_TXT)
d.text((RX + 12, y + 13), SC["lens"][1], font=F["xs"], fill=WARN)

# STRIDE, properties and the impact heat strip (widget 1)
panel((RX, 410, RX + RW, 640), "STRIDE · CIA · impact")
x = RX + 12; y = 436
for letter, word in (("S", "Spoof"), ("T", "Tamper"), ("R", "Repud."), ("I", "Info"), ("D", "DoS"), ("E", "Elev.")):
  on = letter in STRIDE; x = chip(x, y, f"{letter} {word}", fill=CY if on else None, fg=BG if on else DIM, w=51)
x = RX + 12; y = 460
for k in PROPS:
  if k in INTEREST: x = chip(x, y, k, fg=PROP, outline=PROP, w=51)
  else: x = chip(x, y, k, fill=PROP if k in VIOL else None, fg=BG if k in VIOL else DIM, w=51)
d.text((RX + 12, 482), CIA_CAPTION, font=F["x9"], fill=MUTED)


def hazard_label(ids):
  """'H-01 · ASIL C' for one damage scenario; a short form for a group or for the fleet scenario."""
  hs, asils = [], []
  for i in ids:
    text = TA.ds[i]["hara"]
    if "×N" in text: return "H-01…08 ×N fleet", CRIT
    hs.append(re.match(r"H-\d\d", text).group(0)); asils.append(re.search(r"ASIL ([A-D])", text).group(1))
  a = sorted(set(asils)); asil = f"ASIL {a[0]}" if len(a) == 1 else f"{a[0]}–{a[-1]}"
  if len(hs) == 1: lab = f"{hs[0]} · {asil}"
  elif [int(h[2:]) for h in hs] == list(range(int(hs[0][2:]), int(hs[-1][2:]) + 1)): lab = f"{hs[0]}–{hs[-1][2:]} · {asil}"
  else: lab = hs[0] + "/" + "/".join(h[2:] for h in hs[1:]) + f" · {asil}"
  return lab, CRIT if "C" in a else AMBER


rows = [[i] for i in DS]
if len(rows) > 4:                                                # group neighbours with the same ratings
  rows = []
  for i in DS:
    if rows and TA.ds[rows[-1][-1]]["imp"] == TA.ds[i]["imp"] and int(i[3:]) == int(rows[-1][-1][3:]) + 1: rows[-1].append(i)
    else: rows.append([i])
if len(rows) > 4:
  raise fc.ParseError(f"{TS}: more than four impact rows after grouping")
hx0, cw2 = RX + 58, 46
y = 500
for i, c_ in enumerate("SFOP"): d.text((hx0 + i * cw2 + cw2 / 2, y), c_, font=F["xss"], fill=MUTED, anchor="ma")
d.text((hx0 + 4 * cw2 + 12, y), "max", font=F["xss"], fill=MUTED, anchor="ma"); d.text((RX + RW - 12, y), "hazard", font=F["xss"], fill=MUTED, anchor="ra")
AB = {"Severe": "Severe", "Major": "Major", "Moderate": "Moder.", "Negligible": "Neglig."}
for j, ids in enumerate(rows):
  vals, mx = TA.ds[ids[0]]["imp"], TA.ds[ids[0]]["level"]
  label = ids[0] if len(ids) == 1 else f"{ids[0]}–{ids[-1][3:]}"
  hz, hzc = hazard_label(ids)
  yy = y + 15 + j * 23; d.text((RX + 12, yy + 4), label, font=F["ss"] if len(ids) == 1 else F["xss"], fill=TEXT)
  for i, v in enumerate(vals):
    d.rounded_rectangle((hx0 + i * cw2 + 1, yy, hx0 + (i + 1) * cw2 - 1, yy + 20), 2, fill=LV[v])
    d.text((hx0 + i * cw2 + cw2 / 2, yy + 5), AB[v], font=F["x9"], fill=TEXT if v != "Negligible" else DIM, anchor="ma")
  d.text((hx0 + 4 * cw2 + 12, yy + 3), str(mx), font=F["ss"], fill=CY_TXT if mx == 4 else TEXT2, anchor="ma")
  d.text((RX + RW - 12, yy + 4), hz, font=F["xss"] if len(hz) < 15 else F["x9s"], fill=hzc, anchor="ra")
d.text((RX + 12, 622), "WP-C-09 §2–§4; ASILs from WP-C-03 (proposals)", font=F["x9"], fill=MUTED)

# ================================================================ bottom: isometric walk (widget 9: with precursors where they exist)
panel((10, 648, 950, 862), SC["iso_title"])
d.text((940, 660), "credited lens: no solid green wall, so the path reaches the car", font=F["xs"], fill=MUTED, anchor="ra")
if SC["precursors"]:
  for j, (ts, txt) in enumerate(SC["precursors"]):
    y = 690 + j * 36; d.rounded_rectangle((20, y, 152, y + 30), 4, fill="#222220", outline=EDGE)
    d.text((28, y + 3), ts, font=F["ss"], fill=TEXT); d.text((28, y + 17), txt, font=F["x9"], fill=TEXT2)
    chip(112, y + 6, f"r{TA.risk[ts]['risk']}", fill="#6b1d63", fg=TEXT, f="x9s", w=32, h=17)
    d.line((152, y + 15, 184, 755), fill=MUTED)
  d.ellipse((182, 744, 210, 766), fill="#2a2a28", outline=MUTED); d.text((196, 749), "OR", font=F["x9s"], fill=TEXT, anchor="ma")
  d.text((20, 836), "foothold precursors, risk 4 each; no", font=F["x9"], fill=MUTED)
  d.text((20, 847), "combined feasibility (TARA defines none)", font=F["x9"], fill=MUTED)
  K, OX, OY = 80, 300, 770
else:
  d.text((20, 676), "TS-06 is itself a foothold: WP-C-09 §5 routes AP-09 through it, and AP-14 starts from root on the SoC",
         font=F["x9"], fill=MUTED)
  K, OX, OY = 62, 78, 770

ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); o = ImageDraw.Draw(ov)
C30, S30 = math.cos(math.pi / 6), 0.5
def iso(x, y, z): return (OX + (x - y) * C30 * K, OY + (x + y) * S30 * K - z * K)
def hexrgb(h, a=255): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)
def shade(h, f): r, g, b, a = hexrgb(h); return (int(r * f), int(g * f), int(b * f), a)
def slab(u, w, h, top, edge):
  x0, y0 = u, -u
  pts = lambda z: [iso(x0, y0, z), iso(x0 + w, y0, z), iso(x0 + w, y0 + w, z), iso(x0, y0 + w, z)]
  T, B = pts(h), pts(0)
  o.polygon([T[1], T[2], B[2], B[1]], fill=shade(top, 0.55)); o.polygon([T[2], T[3], B[3], B[2]], fill=shade(top, 0.75))
  o.polygon(T, fill=hexrgb(top), outline=hexrgb(edge))
  return (sum(p[0] for p in T) / 4, sum(p[1] for p in T) / 4), T
STEP, Wd = 1.32, 0.78
LOOK = {"S1": ("#2a2a2e", "#6b6b75", 0.22), "S2": ("#2b3a4f", "#5b7aa6", 0.3), "S3": ("#2b3a4f", "#5b7aa6", 0.3),
        "S4": ("#33303d", "#8a7fa8", 0.42), "S5": ("#2b3a4f", "#5b7aa6", 0.3), "G": ("#4a1f1f", "#d03b3b", 0.22)}
zones = [(sid, name, note) + LOOK[sid] for sid, name, note in SC["zones"]]
cent, tops = [], []
for i, (sid, name, note, top, edge, h) in enumerate(zones):
  (cx_, cy_), T = slab(i * STEP, Wd, h, top, edge); cent.append((cx_, cy_)); tops.append(T)
WALL_RGB = {"partial": ((217, 119, 6, 55), (250, 178, 25, 255)), "unverified": ((56, 189, 248, 45), (56, 189, 248, 255)),
            "done": ((74, 222, 128, 45), (74, 222, 128, 255))}
def wall(u, st):
  x, y = u, -u
  q = [iso(x, y, 0.0), iso(x, y + Wd, 0.0), iso(x, y + Wd, 0.5), iso(x, y, 0.5)]
  if st == "open":
    return q
  fill, line = WALL_RGB[st]
  o.polygon(q, fill=fill)
  for a_, b_ in zip(q, q[1:] + q[:1]):
    L = math.dist(a_, b_); n = 0
    while n < L:
      t0, t1 = n / L, min(n + 6, L) / L
      o.line((a_[0] + (b_[0] - a_[0]) * t0, a_[1] + (b_[1] - a_[1]) * t0, a_[0] + (b_[0] - a_[0]) * t1, a_[1] + (b_[1] - a_[1]) * t1),
             fill=line, width=2); n += 10 if st != "done" else 6
  return q
walls = []
for i, ids in SC["walls"]:
  st = fi.barrier([state(c) for c in ids])
  walls.append((wall((i + 1) * STEP - (STEP - Wd) / 2, st), ids, st))
im.paste(Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")); redraw()
def arc(p, q, lift, color, w):
  pts = [(p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t - lift * 4 * t * (1 - t)) for t in (k / 24 for k in range(25))]
  d.line(pts, fill=color, width=w, joint="curve"); return pts
if SC["precursors"]:
  d.line((210, 755, cent[0][0], cent[0][1]), fill="#6b1d63", width=3)          # precursors feed the foothold
for i in range(len(cent) - 1):
  p, q = cent[i], cent[i + 1]
  arc(p, q, 30, "#5b1460", 9); pts = arc(p, q, 30, CY, 4)
  (x1, y1), (x2, y2) = pts[-3], pts[-1]; ang = math.atan2(y2 - y1, x2 - x1)
  d.polygon([(x2, y2), (x2 - 11 * math.cos(ang - 0.45), y2 - 11 * math.sin(ang - 0.45)),
             (x2 - 11 * math.cos(ang + 0.45), y2 - 11 * math.sin(ang + 0.45))], fill=CY)
for (cx_, cy_) in cent: d.ellipse((cx_ - 4, cy_ - 4, cx_ + 4, cy_ + 4), fill=CY)
for i, (sid, name, note, top, edge, h) in enumerate(zones):
  T = tops[i]; by = max(p[1] for p in T) + h * K
  d.text((cent[i][0], by + 6), f"{sid}  {name}", font=F["ss"], fill=CRIT if sid == "G" else TEXT, anchor="ma")
  d.text((cent[i][0], by + 21), note, font=F["xs"], fill=TEXT2, anchor="ma")
WALL_SUB = {"partial": "partial · not verified", "open": "no barrier", "unverified": "built · not verified", "done": "verified"}
for q, ids, st in walls:
  lab = "Gate " + ids[0] + "".join(" · " + c[4:] for c in ids[1:])
  c = {"partial": WARN, "open": MUTED, "unverified": BLUE, "done": GREEN}[st]
  tx = (q[2][0] + q[3][0]) / 2; ty = min(p[1] for p in q) - 6
  d.text((tx, ty - 24), lab, font=F["xss"], fill=c, anchor="ma"); d.text((tx, ty - 11), WALL_SUB[st], font=F["xs"], fill=c, anchor="ma")
BRANCH_END = None
if SC["branch"]:
  i, ids = SC["branch"]
  p = cent[i]; q = (cent[i + 1][0] + 30, cent[i + 1][1] - 78)
  pts = [(p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t - 40 * 4 * t * (1 - t)) for t in (k / 24 for k in range(25))]
  for a_, b_ in zip(pts[::2], pts[1::2]): d.line((a_, b_), fill=CY_TXT, width=2)
  BRANCH_END = q
  d.rounded_rectangle((q[0] - 4, q[1] - 12, q[0] + 196, q[1] + 18), 4, fill=CY_SOFT, outline=CY_TXT)
  d.text((q[0] + 4, q[1] - 9), "firmware branch · " + ids[0] + "".join(" · " + c[4:] for c in ids[1:]), font=F["xss"], fill=CY_TXT)
  d.text((q[0] + 4, q[1] + 4), "no barrier: no envelope left to simulate", font=F["x9"], fill=CY_TXT)
px_, py_ = cent[0]; pin = 52 if SC["precursors"] else 70
d.line((px_, py_, px_, py_ - pin), fill=CY, width=2)
pill((px_, py_ - pin - 22), f"{TS} · risk {RISK['risk']}", CY, BG, anchor="ma")
def mtag(x, y, text, c):
  tw_ = d.textlength(text, font=F["xs"]); d.rounded_rectangle((x - tw_ / 2 - 5, y, x + tw_ / 2 + 5, y + 15), 3, fill="#141413", outline=c)
  d.text((x, y + 2), text, font=F["xs"], fill=c, anchor="ma")
def tag_colour(text):
  return WARN if "refused" in text or "out-of-limit" in text else CY_TXT if text.startswith(("credited", "every")) else \
    TEXT2 if text.startswith("driver") else MUTED
TAGS = [(cent[i][0] - 8, cent[i][1] + (16 if zones[i][0] == "S4" else 14), t_.format(corr=f"{T_CORR:.2f}"), tag_colour(t_))
        for i, t_ in enumerate(SC["tags"])]
if not ANIM:
  for tg in TAGS: mtag(*tg)

# ================================================================ bottom: plots from the plant runs
def chart(box, title, series, unit, lo, hi, thr=None):
  """series: [(run, key, colour)]; the value at the right is the first series' last point."""
  panel(box, title)
  x0, y0, x1, y1 = box[0] + 44, box[1] + 56, box[2] - 12, box[3] - 22
  X = lambda a: x0 + (a + 1.5) / 4.2 * (x1 - x0); Y = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
  for v in (lo, (lo + hi) / 2, hi): d.text((x0 - 6, Y(v) - 6), f"{v:g}", font=F["xs"], fill=MUTED, anchor="ra")
  for a in (-1, 0, 1, 2): d.text((X(a), y1 + 5), f"{a:g}", font=F["xs"], fill=MUTED, anchor="ma")
  for v in thr or []: dashed((x0, Y(v)), (x1, Y(v)), WARN, 1, 5, 4)
  dashed((X(0), y0), (X(0), y1), CY, 1, 5, 4)
  first = None
  for run, key, colour in reversed(series):
    t = [x - run["t0"] for x in run["t"]]
    win = [(a, b) for a, b in zip(t, run[key]) if -1.5 <= a <= 2.7]
    d.line([(X(a), Y(max(lo, min(hi, b)))) for a, b in win], fill=colour, width=2); first = win
  last = first[-1][1]; d.text((box[2] - 12, box[1] + 8), f"{last:.2f} {unit}" if abs(last) < 100 else f"{last:.0f}", font=F["ss"], fill=TEXT, anchor="ra")
LANE = -(3.7 / 2 - 1.78 / 2)
if SC["plots"] == "f01b":
  chart((960, 648, 1270, 862), "EPS LKA torque (plant)", [(R, "torque", SERIES)], "", -1600, 400)
  chart((1280, 648, 1590, 862), "Lateral offset (plant)", [(R, "e_y", SERIES)], "m", -4.0, 0.5, thr=[LANE])
  d.text((970, 678), "fuchsia: flood starts (F-01b fault onset)", font=F["xs"], fill=CY_TXT)
  d.text((1290, 678), "yellow: body at the lane line", font=F["xs"], fill=WARN)
else:
  GREY = "#a3a29b"
  chart((960, 648, 1270, 862), "Lateral offset (plant)", [(R, "e_y", SERIES), (plant("F-04b"), "e_y", GREY)], "m", -4.0, 0.5, thr=[LANE])
  chart((1280, 648, 1590, 862), "Longitudinal accel. (plant)", [(plant("L-01"), "ax", SERIES), (plant("L-03"), "ax", GREY)], "m/s²", -4.0, 3.0)
  d.text((970, 678), "blue F-01b hard-over · grey F-04b stall (curve)", font=F["xs"], fill=TEXT2)
  d.text((1290, 678), "blue L-01 accel. max · grey L-03 decel. step", font=F["xs"], fill=TEXT2)

# ================================================================ footer
d.line((0, 868, W, 868), fill=EDGE)
d.text((12, 872), "MOCK for review · synthetic (DSR-12), no evidence credit. Path, ratings and gate states from WP-C-09 v0.8, WP-C-10 v0.6 and WP-S-07 v0.7; "
       + SC["footer"], font=F["xs"], fill=MUTED)
d.text((12, 885), "3D stand-ins (CC BY, Sketchfab): ADAS+DMS device, ZackyRomiz · CM4, Vacui · STM32 PCB, Aravind Vallaban · relay, ecramirez · "
       "enclosure, AnsysLearn · IMCU, mkonstadakis · ECU, Ryn.Works · Pi Cam, F2A. Car: TurboSquid 1450755 (editorial).", font=F["xs"], fill=MUTED)
d.text((W - 12, 885), "LionDriver assurance/sim/cyber", font=F["xs"], fill=MUTED, anchor="ra")
if __name__ == "__main__":
  DEST.parent.mkdir(exist_ok=True); im.save(DEST, quality=90); print("wrote", DEST)
