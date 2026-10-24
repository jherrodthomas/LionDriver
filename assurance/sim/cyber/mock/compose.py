"""Mock cyber dashboard v4 (TS-14), step 2 of 2, in the layout of assurance/sim/blender/compose.py with cyber accents.

  python3 assurance/sim/cyber/mock/compose.py     # after cyber_scene.py; runs plant case F-01b itself (about 1 s)

Writes assurance/sim/cyber/figures/cy-ts-14-tx-flood-mock.jpg. The TARA values are written out here from WP-C-09 v0.8,
WP-C-10 v0.6, WP-C-03 and WP-S-07 v0.7; the path model of the design note will read them from the documents instead.

Fuchsia = cyber (path, threat, impact/risk/feasibility scales); cyan = security properties and the chosen treatment;
red/amber only where safety comes in (hazards, ASILs) and for the shared barrier convention. Synthetic, no evidence.
"""
import json, math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
HE = HERE.parents[1] / "blender" / "dashboards" / "he-01-2-hardover-adjacent.jpg"
CUT = HERE / "out"
DEST = HERE.parent / "figures" / "cy-ts-14-tx-flood-mock.jpg"


def plant_f01b() -> dict:
  """Layer-1 plant case F-01b (hard-over within the envelope, real panda code in the loop): time, offset, torque."""
  sys.path.insert(0, str(HERE.parents[1] / "plant"))
  from cases import all_cases
  from simulate import simulate
  r = simulate(next(c for c in all_cases() if c.id == "F-01b"))
  return {"t": r.t, "x": r.x, "e_y": r.e_y, "torque": r.torque, "t0": r.t0, "events": r.events}
W, H = 1600, 900
BG, PANEL, EDGE = "#111110", "#1a1a19", "#2c2c2a"
TEXT, TEXT2, MUTED, DIM = "#f0efec", "#c3c2b7", "#898781", "#5f5e59"
CRIT, WARN, AMBER, SERIES = "#d03b3b", "#fab219", "#d97706", "#3987e5"      # safety, thresholds, barrier, plotted signal
CY, CY_SOFT, CY_TXT, PROP = "#d946ef", "#2a1030", "#f0abfc", "#06b6d4"     # cyber accent, its soft fill and text; properties
LV = {"Severe": "#86198f", "Major": "#5b2157", "Moderate": "#3b3542", "Negligible": "#262624"}
RC = {5: "#86198f", 4: "#6b1d63", 3: "#4a2346", 2: "#2c2c2a", 1: "#222220"}

def font(size, w="Regular"): return ImageFont.truetype(f"/usr/share/fonts/opentype/inter/Inter-{w}.otf", size)
F = {k: font(*v) for k, v in {"h1": (19, "SemiBold"), "h2": (15, "SemiBold"), "b": (14, "Regular"), "bs": (14, "SemiBold"),
     "s": (12, "Regular"), "ss": (12, "SemiBold"), "big": (26, "SemiBold"), "xs": (10, "Regular"), "xss": (10, "SemiBold"),
     "x9": (9, "Regular"), "x9s": (9, "SemiBold")}.items()}
ANIM = globals().get("ANIM", False)   # animate.py: leave out what the clip brings in step by step
R = plant_f01b(); T_CORR = R["events"]["driver correction"] - R["t0"]
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
d.text((14, 8), "Scene cy-ts-14-tx-flood", font=F["h1"], fill=TEXT)
x = 14 + d.textlength("Scene cy-ts-14-tx-flood", font=F["h1"]) + 12
pill((x, 9), "TS-14  risk 5", CY, BG); pill((x + 112, 9), "MOCK", "#3b3542")
d.text((14, 32), "Compromised SoC sends in-limit steering frames far above their nominal rate through the panda (AP-14)",
       font=F["s"], fill=TEXT2)
fields = [("Path source", "WP-C-09 §5 · WP-S-07 §4"), ("Hand-off", "Plant F-01b (panda code in loop)"),
          ("Gate statuses", "as of 2026-10-12"), ("Lens", "credited | as built")]
fx = W - 14
for k, v in reversed(fields):
  wv = max(d.textlength(v, font=F["bs"]), d.textlength(k, font=F["s"])); fx -= wv
  d.text((fx, 9), k, font=F["s"], fill=MUTED); d.text((fx, 27), v, font=F["bs"], fill=TEXT); fx -= 26
d.line((0, 50, W, 50), fill=EDGE)

# ================================================================ left: threat card with feasibility gauges and CAL (widgets 4, 5)
panel((10, 56, 310, 334), edge=CY)
d.text((20, 64), "Threat scenario TS-14", font=F["h1"], fill=CY_TXT)
y = para(20, 90, "Compromised SoC injects PCS/DSU frames or floods whitelisted actuation IDs through the panda", "bs", TEXT, 278, 17)
y = para(20, y + 3, "Entry: root on the SoC, assumed (AP-14 is rated given SoC code execution) · GAP-42", "s", TEXT2, 280)
y += 6; d.text((20, y), "Attack feasibility", font=F["ss"], fill=TEXT); d.text((300, y), "High", font=F["ss"], fill=CY_TXT, anchor="ra"); y += 18
facts = [("Elapsed time", ["Hours", "Days", "Weeks", "Months"], 0), ("Expertise", ["Layman", "Profic.", "Expert", "Multi"], 1),
         ("Knowledge", ["Public", "Restr.", "Conf.", "Strict"], 0), ("Window", ["Unlim.", "Easy", "Moder.", "Diff."], 2),
         ("Equipment", ["Stand.", "Spec.", "Besp.", "Multi"], 0)]
for name, lv, k in facts:
  d.text((20, y + 2), name, font=F["xs"], fill=TEXT2)
  for i, l_ in enumerate(lv):
    xx = 96 + i * 51; on = i <= k
    d.rounded_rectangle((xx, y, xx + 48, y + 15), 2, fill=("#a21caf" if k == 0 else "#6b1d63" if k == 1 else "#4a2346") if on else "#222220")
    d.text((xx + 24, y + 2), l_, font=F["x9s"] if i == k else F["x9"], fill=TEXT if i == k else (TEXT2 if on else DIM), anchor="ma")
  y += 18
y += 4
d.text((20, y + 3), "Goal", font=F["xs"], fill=MUTED); chip(54, y, "CSG-05 · CAL 2", fill="#2a2a28", fg=TEXT, f="xss")
chip(156, y, "CAL 2 → 3?  OI-8", fill=CY_SOFT, fg=CY_TXT, outline=CY, f="xss")
d.text((20, 318), "longer bar = harder to attack · ratings are proposals", font=F["xs"], fill=MUTED)

# ================================================================ left: risk matrix and treatment (widgets 2, 3)
panel((10, 340, 310, 640), "Risk and treatment")
M = [[5, 4, 3, 2], [4, 3, 2, 1], [3, 2, 2, 1], [2, 1, 1, 1]]
gx, gy, cw, ch = 64, 382, 44, 23
for i, f_ in enumerate(["High", "Med.", "Low", "V. low"]): d.text((gx + i * cw + cw / 2, gy - 14), f_, font=F["x9"], fill=MUTED, anchor="ma")
for r in range(4):
  d.text((gx - 6, gy + r * ch + 6), f"imp. {4 - r}", font=F["x9"], fill=MUTED, anchor="ra")
  for c in range(4):
    v = M[r][c]; box = (gx + c * cw + 1, gy + r * ch + 1, gx + (c + 1) * cw - 1, gy + (r + 1) * ch - 1)
    d.rounded_rectangle(box, 2, fill=RC[v]); d.text((box[0] + 5, box[1] + 4), str(v), font=F["xss"], fill=TEXT2)
    if v >= 3: d.rounded_rectangle(box, 2, outline="#a8a29e")
cx, cy = gx + cw - 9, gy + ch / 2
d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=TEXT, outline=CY, width=2)
d.ellipse((cx - 20, cy - 6, cx - 8, cy + 6), outline=CY_TXT, width=2)
lx = gx + 4 * cw + 10
d.text((lx, gy - 2), "● as rated:", font=F["xs"], fill=TEXT); d.text((lx, gy + 11), "4 × High = 5", font=F["xss"], fill=CY_TXT)
d.text((lx, gy + 30), "○ treated:", font=F["xs"], fill=CY_TXT); d.text((lx, gy + 43), "not re-rated", font=F["xs"], fill=CY_TXT)
d.text((lx, gy + 56), "(OI-5)", font=F["xs"], fill=CY_TXT)
d.text((20, gy + 4 * ch + 4), "outlined: risk ≥ 3, treatment required", font=F["x9"], fill=MUTED)
y = gy + 4 * ch + 20; x = 20
for k in ("Reduce", "Retain", "Share", "Avoid"): x = chip(x, y, k, fill=PROP if k == "Reduce" else None, fg=BG if k == "Reduce" else DIM, w=66)
y += 26
for lab, txt, c in [("Direction", "Remove PCS/DSU IDs from the TX allow-list (TSR-705); supervise the TX rate per ID (TSR-518)", TEXT2),
                    ("Status", "Both built in the reference build only; not verified on hardware", WARN),
                    ("Residual", "In-limit actuation within the rate budget, bounded by the envelope limits", CY_TXT)]:
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
tag("soc", "SoC board, exploded (Z2)", 120, -10)
tag("panda", "panda safety MCU, exploded (Z1)", -20, 70)
tag("device", "comma device on the windshield", 150, -20)
tag("harness", "harness box + relay (TB-5)", -150, 30)
tag("fcam", "forward camera, stock PCS (bus 2)", 140, -60)
tag("eps", "EPS motor + ECU (Z5)", 150, -40, CY, BG)
tag("abs", "brake ECU", 40, -50)
tag("obd", "OBD-II port", 95, -38)
gx_, gy_ = P["gate"]
gb = pill((gx_ - 185, gy_ - 20), "Gate CSR-092: TX allow-list + per-ID rate", "#3a2a0a", WARN)
d.text((gb[0] + 7, gb[3] + 2), "partial: reference build only, not verified", font=F["xs"], fill=WARN)
bt = "TS-14 path: SoC → TB-1 → panda (gate) → harness relay → car bus 0 → EPS"
bw = d.textlength(bt, font=F["bs"]) + 20
d.rounded_rectangle((CX + 12, CY0 + CHh - 40, CX + 12 + bw, CY0 + CHh - 12), 4, fill=PANEL, outline=CY)
d.text((CX + 22, CY0 + CHh - 34), bt, font=F["bs"], fill=TEXT)
d.text((CX + CW - 10, CY0 + 8), "parts: generic CC-BY stand-ins, not the real hardware", font=F["xs"], fill=MUTED, anchor="ra")

# ================================================================ TARA strip (tiles)
tiles = [("Impact level", "4", "Severe (safety)", CY_TXT), ("Attack feasibility", "High", "", CY_TXT),
         ("Risk value", "5", "highest band", CY), ("Treatment", "Reduce", "not verified", PROP),
         ("Gates verified", "0 of 3", "3 partial", TEXT)]
tw = (CW - 4 * 8) / 5
for i, (k, v, sub, c) in enumerate(tiles):
  x0 = CX + i * (tw + 8); panel((x0, 573, x0 + tw, 640))
  d.text((x0 + 10, 580), k, font=F["s"], fill=TEXT2)
  d.text((x0 + 10, 598), v, font=F["big"], fill=c)
  d.text((x0 + tw - 10, 620), sub, font=F["xs"], fill=MUTED, anchor="ra")

# ================================================================ right column
RX, RW = 1242, 348
panel((RX, 56, RX + RW, 236), "Physical consequence (plant F-01b)")
he = Image.open(HE).convert("RGB").crop((322, 56, 1232, 565)); he = he.resize((RW - 20, round((RW - 20) * he.height / he.width)))
he = he.crop((0, 30, he.width, 30 + 124)); im.paste(he, (RX + 10, 82)); redraw()
d.text((RX + 10, 212), "HE-01.2 render reused: hard-over within the envelope", font=F["xs"], fill=TEXT2)

panel((RX, 242, RX + RW, 404), "Gates on this path")
gates = [("CSR-092", "TX allow-list + per-ID rate", "partial", AMBER, "dashed amber"),
         ("CSR-061", "envelope independent of SoC values", "partial", AMBER, "dashed amber"),
         ("CSR-093", "relay check on intercepted IDs", "partial", AMBER, "dashed amber"),
         ("CSR-063", "one publisher per topic (foothold)", "open", MUTED, "no barrier")]
y = 268
for cid, what, st, c, look in gates:
  if st == "open": d.line((RX + 12, y + 7, RX + 44, y + 7), fill=EDGE, width=1)
  else: dashed((RX + 12, y + 7), (RX + 44, y + 7), c, 3, 6, 4)
  d.text((RX + 52, y), cid, font=F["ss"], fill=TEXT); d.text((RX + 116, y), what, font=F["s"], fill=TEXT2)
  d.text((RX + 116, y + 14), f"{st} · {look}", font=F["xs"], fill=c); y += 27
d.text((RX + 12, y + 1), "Credited: none verified, so the path reaches the car.", font=F["xs"], fill=CY_TXT)
d.text((RX + 12, y + 13), "As built (ref. build): expected to stop at S4; not yet run.", font=F["xs"], fill=WARN)

# STRIDE, properties and the impact heat strip (widget 1)
panel((RX, 410, RX + RW, 640), "STRIDE · CIA · impact")
x = RX + 12; y = 436
for letter, word in (("S", "Spoof"), ("T", "Tamper"), ("R", "Repud."), ("I", "Info"), ("D", "DoS"), ("E", "Elev.")):
  on = letter in "TD"; x = chip(x, y, f"{letter} {word}", fill=CY if on else None, fg=BG if on else DIM, w=51)
x = RX + 12; y = 460
for k, st in (("C", 0), ("I", 1), ("A", 1), ("Auth", 2), ("Authz", 0), ("NR", 0)):
  if st == 2: x = chip(x, y, k, fg=PROP, outline=PROP, w=51)
  else: x = chip(x, y, k, fill=PROP if st else None, fg=BG if st else DIM, w=51)
d.text((RX + 12, 482), "violated: integrity, availability · authenticity of interest (AS-01)", font=F["x9"], fill=MUTED)
hx0, cw2 = RX + 58, 46
y = 500
for i, c_ in enumerate("SFOP"): d.text((hx0 + i * cw2 + cw2 / 2, y), c_, font=F["xss"], fill=MUTED, anchor="ma")
d.text((hx0 + 4 * cw2 + 12, y), "max", font=F["xss"], fill=MUTED, anchor="ma"); d.text((RX + RW - 12, y), "hazard", font=F["xss"], fill=MUTED, anchor="ra")
AB = {"Severe": "Severe", "Major": "Major", "Moderate": "Moder.", "Negligible": "Neglig."}
for j, (ds, vals, mx, hz) in enumerate([("DS-01", ("Severe", "Major", "Major", "Negligible"), 4, "H-01 · ASIL C"),
                                        ("DS-03", ("Severe", "Major", "Major", "Negligible"), 4, "H-03 · ASIL C"),
                                        ("DS-04", ("Major", "Moderate", "Major", "Negligible"), 3, "H-04 · ASIL B"),
                                        ("DS-07", ("Severe", "Major", "Major", "Negligible"), 4, "H-08 · ASIL B")]):
  yy = y + 15 + j * 23; d.text((RX + 12, yy + 4), ds, font=F["ss"], fill=TEXT)
  for i, v in enumerate(vals):
    d.rounded_rectangle((hx0 + i * cw2 + 1, yy, hx0 + (i + 1) * cw2 - 1, yy + 20), 2, fill=LV[v])
    d.text((hx0 + i * cw2 + cw2 / 2, yy + 5), AB[v], font=F["x9"], fill=TEXT if v != "Negligible" else DIM, anchor="ma")
  d.text((hx0 + 4 * cw2 + 12, yy + 3), str(mx), font=F["ss"], fill=CY_TXT if mx == 4 else TEXT2, anchor="ma")
  hzc = CRIT if "ASIL C" in hz else AMBER
  d.text((RX + RW - 12, yy + 4), hz, font=F["xss"], fill=hzc, anchor="ra")
d.text((RX + 12, 622), "WP-C-09 §2–§4; ASILs from WP-C-03 (proposals)", font=F["x9"], fill=MUTED)

# ================================================================ bottom: precursor tree + isometric walk (widget 9)
panel((10, 648, 950, 862), "Attack path, isometric (WP-C-09 AP-14 at the §5 level)")
d.text((940, 660), "credited lens: no solid green wall, so the path reaches the car", font=F["xs"], fill=MUTED, anchor="ra")
pre = [("TS-06", "malicious update"), ("TS-08", "SSH access"), ("TS-09", "tampered model"), ("TS-10", "supply chain")]
for j, (ts, txt) in enumerate(pre):
  y = 690 + j * 36; d.rounded_rectangle((20, y, 152, y + 30), 4, fill="#222220", outline=EDGE)
  d.text((28, y + 3), ts, font=F["ss"], fill=TEXT); d.text((28, y + 17), txt, font=F["x9"], fill=TEXT2)
  chip(112, y + 6, "r4", fill="#6b1d63", fg=TEXT, f="x9s", w=32, h=17)
  d.line((152, y + 15, 184, 755), fill=MUTED)
d.ellipse((182, 744, 210, 766), fill="#2a2a28", outline=MUTED); d.text((196, 749), "OR", font=F["x9s"], fill=TEXT, anchor="ma")
d.text((20, 836), "foothold precursors, risk 4 each; no", font=F["x9"], fill=MUTED)
d.text((20, 847), "combined feasibility (TARA defines none)", font=F["x9"], fill=MUTED)

ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); o = ImageDraw.Draw(ov)
K = 80; C30, S30 = math.cos(math.pi / 6), 0.5
OX, OY = 300, 770
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
zones = [("S3", "SoC host · Z2", "root, assumed", "#2b3a4f", "#5b7aa6", 0.3),
         ("S4", "Envelope · Z1", "panda filters TX", "#33303d", "#8a7fa8", 0.42),
         ("S5", "Vehicle · Z5", "frames on bus 0", "#2b3a4f", "#5b7aa6", 0.3),
         ("G", "DS-01 → H-01", "hard-over (plant)", "#4a1f1f", "#d03b3b", 0.22)]
cent, tops = [], []
for i, (sid, name, note, top, edge, h) in enumerate(zones):
  (cx_, cy_), T = slab(i * STEP, Wd, h, top, edge); cent.append((cx_, cy_)); tops.append(T)
def wall(u):
  x, y = u, -u
  q = [iso(x, y, 0.0), iso(x, y + Wd, 0.0), iso(x, y + Wd, 0.5), iso(x, y, 0.5)]
  o.polygon(q, fill=(217, 119, 6, 55))
  for a_, b_ in zip(q, q[1:] + q[:1]):
    L = math.dist(a_, b_); n = 0
    while n < L:
      t0, t1 = n / L, min(n + 6, L) / L
      o.line((a_[0] + (b_[0] - a_[0]) * t0, a_[1] + (b_[1] - a_[1]) * t0, a_[0] + (b_[0] - a_[0]) * t1, a_[1] + (b_[1] - a_[1]) * t1),
             fill=(250, 178, 25, 255), width=2); n += 10
  return q
g1 = wall(1 * STEP - (STEP - Wd) / 2); g2 = wall(2 * STEP - (STEP - Wd) / 2)
im.paste(Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")); redraw()
def arc(p, q, lift, color, w):
  pts = [(p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t - lift * 4 * t * (1 - t)) for t in (k / 24 for k in range(25))]
  d.line(pts, fill=color, width=w, joint="curve"); return pts
d.line((210, 755, cent[0][0], cent[0][1]), fill="#6b1d63", width=3)          # precursors feed the foothold
for i in range(3):
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
for q, lab in ((g1, "Gate CSR-092 · 061"), (g2, "Gate CSR-093")):
  tx = (q[2][0] + q[3][0]) / 2; ty = min(p[1] for p in q) - 6
  d.text((tx, ty - 24), lab, font=F["xss"], fill=WARN, anchor="ma"); d.text((tx, ty - 11), "partial · not verified", font=F["xs"], fill=WARN, anchor="ma")
px_, py_ = cent[0]; d.line((px_, py_, px_, py_ - 52), fill=CY, width=2)
pill((px_, py_ - 74), "TS-14 · risk 5", CY, BG, anchor="ma")
def mtag(x, y, text, c):
  tw_ = d.textlength(text, font=F["xs"]); d.rounded_rectangle((x - tw_ / 2 - 5, y, x + tw_ / 2 + 5, y + 15), 3, fill="#141413", outline=c)
  d.text((x, y + 2), text, font=F["xs"], fill=c, anchor="ma")
TAGS = [(cent[0][0] - 8, cent[0][1] + 14, "item sees: nothing", MUTED),
        (cent[1][0] - 8, cent[1][1] + 16, "item sees: TX refused (ref.)", WARN),
        (cent[2][0] - 8, cent[2][1] + 14, "credited: reaches EPS", CY_TXT),
        (cent[3][0] - 8, cent[3][1] + 14, f"driver corrects +{T_CORR:.2f} s", TEXT2)]
if not ANIM:
  for tg in TAGS: mtag(*tg)

# ================================================================ bottom: plots from the plant run
r = R; t0 = r["t0"]; t = [x - t0 for x in r["t"]]
def chart(box, title, ys, unit, lo, hi, thr=None):
  panel(box, title)
  x0, y0, x1, y1 = box[0] + 44, box[1] + 56, box[2] - 12, box[3] - 22
  win = [(a, b) for a, b in zip(t, ys) if -1.5 <= a <= 2.7]
  X = lambda a: x0 + (a + 1.5) / 4.2 * (x1 - x0); Y = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
  for v in (lo, (lo + hi) / 2, hi): d.text((x0 - 6, Y(v) - 6), f"{v:g}", font=F["xs"], fill=MUTED, anchor="ra")
  for a in (-1, 0, 1, 2): d.text((X(a), y1 + 5), f"{a:g}", font=F["xs"], fill=MUTED, anchor="ma")
  for v in thr or []: dashed((x0, Y(v)), (x1, Y(v)), WARN, 1, 5, 4)
  dashed((X(0), y0), (X(0), y1), CY, 1, 5, 4)
  d.line([(X(a), Y(max(lo, min(hi, b)))) for a, b in win], fill=SERIES, width=2)
  last = win[-1][1]; d.text((box[2] - 12, box[1] + 8), f"{last:.2f} {unit}" if abs(last) < 100 else f"{last:.0f}", font=F["ss"], fill=TEXT, anchor="ra")
chart((960, 648, 1270, 862), "EPS LKA torque (plant)", r["torque"], "", -1600, 400)
chart((1280, 648, 1590, 862), "Lateral offset (plant)", r["e_y"], "m", -4.0, 0.5, thr=[-(3.7 / 2 - 1.78 / 2)])
d.text((970, 678), "fuchsia: flood starts (F-01b fault onset)", font=F["xs"], fill=CY_TXT)
d.text((1290, 678), "yellow: body at the lane line", font=F["xs"], fill=WARN)

# ================================================================ footer
d.line((0, 868, W, 868), fill=EDGE)
d.text((12, 872), "MOCK for review · synthetic (DSR-12), no evidence credit. Path, ratings and gate states from WP-C-09 v0.8, WP-C-10 v0.6 and WP-S-07 v0.7; "
       "the consequence reuses layer-1 case F-01b (real panda code), because the flood fault kind is not built.", font=F["xs"], fill=MUTED)
d.text((12, 885), "3D stand-ins (CC BY, Sketchfab): ADAS+DMS device, ZackyRomiz · CM4, Vacui · STM32 PCB, Aravind Vallaban · relay, ecramirez · "
       "enclosure, AnsysLearn · IMCU, mkonstadakis · ECU, Ryn.Works · Pi Cam, F2A. Car: TurboSquid 1450755 (editorial).", font=F["xs"], fill=MUTED)
d.text((W - 12, 885), "LionDriver assurance/sim/cyber", font=F["xs"], fill=MUTED, anchor="ra")
if __name__ == "__main__":
  DEST.parent.mkdir(exist_ok=True); im.save(DEST, quality=90); print("wrote", DEST)
