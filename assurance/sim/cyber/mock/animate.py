"""Mock cyber dashboard clip, step 3 of 3: a dashboard of compose.py with the attack animated over it, in two passes.

  python3 assurance/sim/cyber/mock/animate.py --ts TS-14   # after cyber_scene.py and compose.py; needs ffmpeg
  python3 assurance/sim/cyber/mock/animate.py --ts TS-06

TS-14. Pass 1, as built (reference build): pulses leave the SoC and travel the path to the panda; at the gate they are
refused, the ring flashes and the panda revokes authority, so nothing reaches the EPS. Pass 2, without the
reference-build checks: the flood passes the gate, reaches the EPS, and the consequence plays from plant case F-01b at
real speed: the time cursor runs over the plots and the top view in the inset moves by the plant's lateral offset.

TS-06. Pass 1, the reference configuration: automatic updates are off by procedure (CSR-124), so the update pulses stop
at the update gate around the SoC board, and the clip notes that a manual install is not checked either (CSR-121
open). Pass 2, a tampered release is installed: the pulses pass the update gate, the SoC board lights as the new
software runs, its commands pass the envelope within its limits and reach the EPS (consequence from plant case F-01b),
and a firmware branch reaches the panda, which the plant cannot represent.

What is drawn, and from where: the path, the gates and the parts come from the cutaway render (out/<ts>/anchors.json);
the plots and the event times come from the plant runs with the real panda code. The pulses and the gates' reactions are
qualitative: no attack is run, and the clip says so on every frame. Synthetic (DSR-12), no evidence credit.

Writes assurance/sim/cyber/figures/<slug>-mock.mp4 (20 fps). The still is the dashboard picture.
"""
import json, math, runpy, shutil, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
TS = sys.argv[sys.argv.index("--ts") + 1] if "--ts" in sys.argv else "TS-14"
FPS = 20
T_A0, T_A1 = 0.3, 4.6            # pass 1
T_B0 = 5.2                       # pass 2 starts
SPEED = 520.0                    # pulse speed along the path in pass 2, px/s on the dashboard (qualitative)

G = runpy.run_path(str(HERE / "compose.py"), init_globals={"ANIM": True, "TS": TS}, run_name="cyber_mock")
SC = G["SC"]
DEST = HERE.parent / "figures" / f"{SC['slug']}-mock.mp4"
BASE = G["im"].copy()
F, CY, CY_TXT, CY_SOFT, WARN, AMBER, TEXT, TEXT2, MUTED, PANEL, EDGE, CRIT, BG, SERIES = (
  G[k] for k in ("F", "CY", "CY_TXT", "CY_SOFT", "WARN", "AMBER", "TEXT", "TEXT2", "MUTED", "PANEL", "EDGE", "CRIT", "BG", "SERIES"))
R = G["R"]; T0 = R["t0"]; TAGS = G["TAGS"]; cent = G["cent"]; tops = G["tops"]; zones = G["zones"]
CX, CY0, sx = G["CX"], G["CY0"], G["sx"]
RX, RW = G["RX"], G["RW"]
A = json.load(open(G["CUT"] / "anchors.json"))
to = lambda p: (CX + 1 + p[0] * sx, CY0 + 1 + p[1] * sx)


class Route:
  """A polyline on the dashboard with arc-length positions."""
  def __init__(self, pts):
    self.p = pts; self.s = [0.0]
    for a, b in zip(pts, pts[1:]): self.s.append(self.s[-1] + math.dist(a, b))
    self.L = self.s[-1]
  def at(self, s):
    s = max(0.0, min(s, self.L))
    i = next((k for k in range(1, len(self.s)) if self.s[k] >= s), len(self.s) - 1)
    a, b, la, lb = self.p[i - 1], self.p[i], self.s[i - 1], self.s[i]
    u = 0 if lb == la else (s - la) / (lb - la)
    return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
  def near(self, q):
    return self.s[min(range(len(self.p)), key=lambda i: math.dist(self.p[i], q))]
  def enters(self, c, r):
    return next(self.s[i] for i in range(len(self.p)) if math.dist(self.p[i], c) <= r)


def circle(key):
  pts = [to(p) for p in A[key]]; c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
  return c, sum(math.dist(p, c) for p in pts) / len(pts)


UP = [to(p) for p in A["path_upper"]]; LO = [to(p) for p in A["path_lower"]]
CMD = Route(UP + LO[1:])                                   # SoC -> panda -> harness -> bus -> EPS
PANDA = to(A["px"]["panda"]); EPS = to(A["px"]["eps"]); SOC = to(A["px"]["soc"])
RING_C, RING_R = circle("ring")
S_GATE = CMD.near(PANDA)                                   # where the path meets the panda


def plant(tp, key):
  """Plant signal of case F-01b at plant time tp (s from the fault), clamped to the run."""
  ts = R["t"]; t = T0 + tp
  i = min(range(len(ts)), key=lambda k: abs(ts[k] - t)); return R[key][i]


T_LANE = next(t - T0 for t, e in zip(R["t"], R["e_y"]) if t > T0 and e < -(3.7 / 2 - 1.78 / 2))
T_CUE = R["events"]["driver cue (drift)"] - T0; T_CORR = R["events"]["driver correction"] - T0


def glow(ov, p, r, rgb, a):
  o = ImageDraw.Draw(ov)
  for k in range(4, 0, -1):
    rr = r * (1 + k * 0.6); o.ellipse((p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr), fill=rgb + (int(a * 0.12 * (5 - k)),))
  o.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=rgb + (a,))


def hexrgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ring_flash(ov, c, r, a):
  ImageDraw.Draw(ov).ellipse((c[0] - r - 6, c[1] - r - 6, c[0] + r + 6, c[1] + r + 6), outline=hexrgb(WARN) + (a,), width=6)


def banner(d, text, color, line=0, top=34):
  w = d.textlength(text, font=F["bs"]) + 24; x1 = CX + G["CW"] - 12; x0 = x1 - w; y = CY0 + top + line * 32
  d.rounded_rectangle((x0, y, x1, y + 28), 5, fill=PANEL, outline=color, width=2)
  d.text((x0 + 12, y + 6), text, font=F["bs"], fill=TEXT)


def topview(im, tp, pass_b):
  """The inset: a top view of the ego lane, with the car at the plant's lateral offset (pass 2) or centred (pass 1)."""
  x0, y0, w, h = RX + 10, 82, RW - 20, 124
  v = Image.new("RGB", (w, h), "#1f2023"); d = ImageDraw.Draw(v)
  K = 9.5; cy = h / 2 - 8; lw = 3.7 * K
  xs = plant(tp, "x") if pass_b else 0.0
  for lane_y in (cy - lw * 1.5, cy - lw / 2, cy + lw / 2, cy + lw * 1.5):
    solid = abs(lane_y - (cy - lw * 1.5)) < 1 or abs(lane_y - (cy + lw * 1.5)) < 1
    if solid: d.line((0, lane_y, w, lane_y), fill="#8a8a85", width=2)
    else:
      off = (xs * K) % 60
      for xx in range(-60, w + 60, 60): d.line((xx - off, lane_y, xx - off + 30, lane_y), fill="#cfcfc8", width=2)
  ey = plant(tp, "e_y") if (pass_b and tp > 0) else 0.0
  ycar = cy - ey * K; xcar = w * 0.42; L, Wc = 4.6 * K, 1.78 * K
  d.rounded_rectangle((xcar - L / 2, ycar - Wc / 2, xcar + L / 2, ycar + Wc / 2), 4, fill="#d95926" if pass_b else "#7b7b77")
  d.text((6, h - 13), "top view, plant F-01b offset" if pass_b else "car unaffected (expected, not run)", font=F["xs"], fill=TEXT2)
  if pass_b:
    d.text((w - 6, 4), f"{tp:+.2f} s  offset {ey:+.2f} m", font=F["xss"], fill=TEXT, anchor="ra")
  im.paste(v, (x0, y0))
  d2 = ImageDraw.Draw(im); d2.rectangle((RX + 8, 208, RX + RW - 8, 228), fill=PANEL)
  d2.text((RX + 10, 212), "schematic top view; offset and times from plant F-01b", font=F["xs"], fill=TEXT2)


def pill(d, xy, text, fill, fg):
  x, y = xy; tw = d.textlength(text, font=F["ss"])
  d.rounded_rectangle((x, y, x + tw + 14, y + 21), 4, fill=fill); d.text((x + 7, y + 3), text, font=F["ss"], fill=fg)


def mtag(d, x, y, text, c):
  tw = d.textlength(text, font=F["xs"]); d.rounded_rectangle((x - tw / 2 - 5, y, x + tw / 2 + 5, y + 15), 3, fill="#141413", outline=c)
  d.text((x, y + 2), text, font=F["xs"], fill=c, anchor="ma")


def stage_hi(d, i, color):
  T = tops[i]; d.polygon(T, outline=color, width=3)


def composite(im, ov):
  box = (CX + 1, CY0 + 1, CX + G["CW"] - 1, CY0 + G["CHh"] - 1)          # keep the pulses inside the cutaway panel
  clip = Image.new("RGBA", im.size, (0, 0, 0, 0)); clip.paste(ov.crop(box), box[:2])
  im.paste(Image.alpha_composite(im.convert("RGBA"), clip).convert("RGB")); return ImageDraw.Draw(im)


def plots(im, d, pass_b, tp, label):
  for box in ((960, 648, 1270, 862), (1280, 648, 1590, 862)):
    x0, y0, x1, y1 = box[0] + 44, box[1] + 56, box[2] - 12, box[3] - 22
    if not pass_b:
      dim = Image.new("RGBA", (box[2] - box[0] - 2, box[3] - box[1] - 30), (17, 17, 16, 170))
      im.paste(Image.alpha_composite(im.crop((box[0] + 1, box[1] + 29, box[2] - 1, box[3] - 1)).convert("RGBA"), dim).convert("RGB"),
               (box[0] + 1, box[1] + 29)); d = ImageDraw.Draw(im)
      d.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2 + 10), label, font=F["s"], fill=TEXT2, anchor="ma")
    elif tp >= -1.5:
      xc = x0 + (min(tp, 2.7) + 1.5) / 4.2 * (x1 - x0); d.line((xc, y0, xc, y1), fill=TEXT, width=1)
  return d


def clock(d, t, y=22):
  d.text((CX + G["CW"] - 10, CY0 + y), f"clip {t:4.1f} s", font=F["xs"], fill=MUTED, anchor="ra")


# ================================================================ TS-14
SPEED_A14 = 140.0                # pass 1, slower so the refusal at the gate can be seen
T_HIT14 = T_A0 + S_GATE / SPEED_A14
T_REVOKE = T_HIT14 + 0.1        # TSR-518 unit-test bound, drawn at the bound
T_FAULT14 = 6.2                 # pass 2: the first flood frames reach the EPS (= plant fault onset, F-01b t = 0)
PULSE_B14 = T_FAULT14 - CMD.L / SPEED


def frame_ts14(t):
  im = BASE.copy(); ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(im)
  pass_b = t >= T_B0; tp = t - T_FAULT14
  if not pass_b:
    for k in range(200):
      ts = T_A0 + k * 0.12
      if ts > min(t, T_A1 - 0.4): break                      # the attacker keeps sending; the panda keeps refusing
      s = (t - ts) * SPEED_A14
      if s >= S_GATE:                                       # refused at the gate: a short fade on the ring
        fade = 1 - (s - S_GATE) / 60
        if fade > 0: glow(ov, CMD.at(S_GATE), 5, hexrgb(WARN), int(220 * fade))
        continue
      glow(ov, CMD.at(s), 5, hexrgb(CY), 235)
    if t >= T_HIT14:                                        # the ring flashes on every refused frame
      ring_flash(ov, RING_C, RING_R, int(160 * (0.55 + 0.45 * math.cos((t - T_HIT14) * 14))) if t < T_REVOKE + 0.6 else 70)
  else:
    for k in range(400):
      ts = PULSE_B14 + k * 0.05
      if ts > t: break
      s = (t - ts) * SPEED
      if s <= CMD.L: glow(ov, CMD.at(s), 4, hexrgb(CY), 230)
    if tp >= 0:                                             # the EPS lights with the commanded torque
      a = min(1.0, abs(plant(tp, "torque")) / 1500.0)
      glow(ov, EPS, 10 + 10 * a, hexrgb(CY), int(90 + 150 * a))
  d = composite(im, ov)
  if not pass_b and t >= T_REVOKE:
    pill(d, (RING_C[0] - RING_R - 262, RING_C[1] - 4), "authority revoked (≤ 0.1 s bound)", "#3a2a0a", WARN)
  if t < T_A1: banner(d, "Pass 1 of 2 · as built (reference build) · expected, not run", WARN)
  elif t < T_B0: banner(d, "Pass 2 of 2 · without the reference-build checks", CY)
  else: banner(d, "Pass 2 of 2 · no reference checks · consequence: plant F-01b", CY)
  if t >= T_A0 and (not pass_b or t >= T_B0): stage_hi(d, 0, CY); mtag(d, *TAGS[0])
  if not pass_b and t >= T_HIT14: stage_hi(d, 1, WARN); mtag(d, *TAGS[1])
  if pass_b and tp >= -0.4: stage_hi(d, 1, CY)
  if pass_b and tp >= 0: stage_hi(d, 2, CY); mtag(d, *TAGS[2])
  if pass_b and tp >= T_LANE: stage_hi(d, 3, CRIT)
  if pass_b and tp >= T_CORR: mtag(d, *TAGS[3])
  d = plots(im, d, pass_b, tp, "plays in pass 2 (plant F-01b)")
  topview(im, max(tp, -1.0), pass_b and t >= T_B0)
  d = ImageDraw.Draw(im)
  if pass_b and tp >= T_CUE: d.text((RX + 12, 86), f"driver cue (drift) +{T_CUE:.2f} s", font=F["xs"], fill=TEXT2)
  if pass_b and tp >= T_LANE: d.text((RX + 12, 99), f"body at the lane line +{T_LANE:.2f} s", font=F["xs"], fill="#ef5b5b")
  if pass_b and tp >= T_CORR: d.text((RX + 12, 112), f"driver corrects +{T_CORR:.2f} s", font=F["xs"], fill=TEXT2)
  clock(d, t)
  return im


# ================================================================ TS-06
if TS == "TS-06":
  NET = [to(p) for p in A["path_net"]]; DS = [to(p) for p in A["path_dev_soc"]]
  UPD = Route(NET + DS[1:])                                # update source -> network -> device -> SoC board
  BR = Route([to(p) for p in A["branch"]])                 # firmware branch SoC -> panda
  RA_C, RA_R = circle("ringA")
  S_GA = UPD.enters(RA_C, RA_R)                            # where the update meets the update gate
  SPEED_A06 = 320.0
  T_HIT06 = T_A0 + S_GA / SPEED_A06
  T_ARR = T_B0 + S_GA / SPEED                              # pass 2: the release reaches the update gate (and passes)
  T_INST = T_B0 + 0.8 + UPD.L / SPEED                      # the last part of the release is on the SoC: it runs
  T_FAULT06 = T_INST + 0.3 + CMD.L / SPEED                 # its first commands reach the EPS (= plant fault onset)
  T_BR0 = T_INST + 0.3; T_BR = T_BR0 + BR.L / 300.0        # the firmware branch reaches the panda


def frame_ts06(t):
  im = BASE.copy(); ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(im)
  pass_b = t >= T_B0; tp = t - T_FAULT06
  if not pass_b:
    for k in range(60):                                     # update attempts; the updater is not running
      ts = T_A0 + k * 0.3
      if ts > min(t, T_A1 - 0.5): break
      s = (t - ts) * SPEED_A06
      if s >= S_GA:
        fade = 1 - (s - S_GA) / 60
        if fade > 0: glow(ov, UPD.at(S_GA), 5, hexrgb(WARN), int(220 * fade))
        continue
      glow(ov, UPD.at(s), 5, hexrgb(CY), 235)
    if t >= T_HIT06:
      ring_flash(ov, RA_C, RA_R, int(150 * (0.55 + 0.45 * math.cos((t - T_HIT06) * 10))))
  else:
    for k in range(40):                                     # the release arrives
      ts = T_B0 + k * 0.08
      if ts > min(t, T_B0 + 0.8): break
      s = (t - ts) * SPEED
      if s <= UPD.L: glow(ov, UPD.at(s), 5, hexrgb(CY), 235)
    if t >= T_ARR:                                          # the new software runs on the SoC
      a = min(1.0, (t - T_ARR) / 0.8); glow(ov, SOC, 16 + 8 * a, hexrgb(CY), int(70 + 120 * a))
    for k in range(400):                                    # its commands, within the envelope's limits
      ts = T_INST + 0.3 + k * 0.06
      if ts > t: break
      s = (t - ts) * SPEED
      if s <= CMD.L: glow(ov, CMD.at(s), 4, hexrgb(CY), 230)
    if t >= T_INST + 0.3 + S_GATE / SPEED:                  # the envelope passes them: a steady amber ring, no flash
      ring_flash(ov, RING_C, RING_R, 60)
    for k in range(60):                                     # the firmware branch
      ts = T_BR0 + k * 0.18
      if ts > t: break
      s = (t - ts) * 300.0
      if s <= BR.L: glow(ov, BR.at(s), 4, hexrgb(CY_TXT), 220)
    if tp >= 0:
      a = min(1.0, abs(plant(tp, "torque")) / 1500.0)
      glow(ov, EPS, 10 + 10 * a, hexrgb(CY), int(90 + 150 * a))
  d = composite(im, ov)
  if not pass_b and t >= T_HIT06:
    pill(d, (RA_C[0] + RA_R + 26, RA_C[1] + 44), "updater not running (CSR-124)", "#3a2a0a", WARN)
  if pass_b and t >= T_ARR:
    pill(d, (SOC[0] + 30, SOC[1] + 90), "new software installed: no signature check", CY_SOFT, CY_TXT)
  if pass_b and t >= T_BR and int((t - T_BR) * 3) % 2 == 0:
    pill(d, (PANDA[0] - 110, PANDA[1] + 86), "panda firmware replaced? beyond the plant", CY_SOFT, CY_TXT)
  if t < T_A1:
    banner(d, "Pass 1 of 2 · reference configuration · automatic updates off", WARN, top=6)
    if t >= T_HIT06 + 1.0: banner(d, "a manual install is not checked either (CSR-121 open)", WARN, 1, top=6)
  elif t < T_B0: banner(d, "Pass 2 of 2 · a tampered release is installed", CY, top=6)
  else: banner(d, "Pass 2 of 2 · tampered release installed · consequence: plant F-01b", CY, top=6)
  if t >= T_A0 and (not pass_b or t >= T_B0): stage_hi(d, 0, CY); mtag(d, *TAGS[0])
  if not pass_b and t >= T_HIT06:
    stage_hi(d, 1, WARN); x, y, _, _ = TAGS[1]; mtag(d, x, y, "updater off (procedure)", WARN)
  if pass_b and t >= T_ARR: stage_hi(d, 1, CY); mtag(d, *TAGS[1])
  if pass_b and t >= T_INST: stage_hi(d, 2, CY); mtag(d, *TAGS[2])
  if pass_b and tp >= -0.3: stage_hi(d, 3, CY); mtag(d, *TAGS[3])
  if pass_b and tp >= 0: stage_hi(d, 4, CY); mtag(d, *TAGS[4])
  if pass_b and tp >= T_LANE: stage_hi(d, 5, CRIT); mtag(d, *TAGS[5])
  d = plots(im, d, pass_b, tp, "plays in pass 2 (plant)")
  if pass_b and tp >= 0:                                    # the case the clip plays, in the table of what it could command
    d.rounded_rectangle((RX + 6, 86, RX + RW - 6, 117), 4, outline=CY, width=2)
  clock(d, t, 100 if t < T_A1 and t >= T_HIT06 + 1.0 else 68)
  return im


FRAME, T_END = (frame_ts14, 11.0) if TS == "TS-14" else (frame_ts06, round(T_FAULT06 + 3.8, 1))


def main():
  tmp = HERE / "out" / "frames"; shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
  n = int(T_END * FPS)
  for i in range(n):
    FRAME(i / FPS).save(tmp / f"f{i:04d}.png", compress_level=1)
  DEST.parent.mkdir(exist_ok=True)
  subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%04d.png"),
                  "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "24", "-preset", "slow", "-movflags", "+faststart",
                  str(DEST)], check=True)
  print("wrote", DEST, f"({n} frames, {T_END} s)")


if __name__ == "__main__":
  main()
