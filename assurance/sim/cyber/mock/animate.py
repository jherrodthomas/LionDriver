"""Mock cyber dashboard clip (TS-14), step 3 of 3: the v4 dashboard with the attack animated over it, in two passes.

  python3 assurance/sim/cyber/mock/animate.py     # after cyber_scene.py; about a minute; needs ffmpeg

Pass 1, as built (reference build): pulses leave the SoC and travel the TS-14 path to the panda; at the gate they are
refused, the ring flashes and the panda revokes authority, so nothing reaches the EPS. Pass 2, without the
reference-build checks: the flood passes the gate, reaches the EPS, and the consequence plays from plant case F-01b at
real speed: the time cursor runs over the plots and the top view in the inset moves by the plant's lateral offset.

What is drawn, and from where: the path, the gate and the parts come from the cutaway render (out/anchors.json); the
plots, the offset in the top view and the event times come from the F-01b plant run with the real panda code. The
pulses and the gate's reaction are qualitative: the rate-flood fault kind is not built, so neither pass is a run, and
the clip says so on every frame. Synthetic (DSR-12), no evidence credit.

Writes assurance/sim/cyber/figures/cy-ts-14-tx-flood-mock.mp4 (11 s, 20 fps). The still is the v4 picture.
"""
import json, math, runpy, shutil, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
DEST = HERE.parent / "figures" / "cy-ts-14-tx-flood-mock.mp4"
FPS, T_END = 20, 11.0
T_A0, T_A1 = 0.3, 4.6            # pass 1
T_B0 = 5.2                       # pass 2 starts
T_FAULT = 6.2                    # pass 2: the first flood frames reach the EPS (= plant fault onset, F-01b t = 0)
SPEED = 520.0                    # pulse speed along the path in pass 2, px/s on the dashboard (qualitative)
SPEED_A = 140.0                  # pass 1, slower so the refusal at the gate can be seen

G = runpy.run_path(str(HERE / "compose.py"), init_globals={"ANIM": True}, run_name="cyber_mock")
BASE = G["im"].copy()
F, CY, CY_TXT, CY_SOFT, WARN, AMBER, TEXT, TEXT2, MUTED, PANEL, EDGE, CRIT, BG, SERIES = (
  G[k] for k in ("F", "CY", "CY_TXT", "CY_SOFT", "WARN", "AMBER", "TEXT", "TEXT2", "MUTED", "PANEL", "EDGE", "CRIT", "BG", "SERIES"))
R = G["R"]; T0 = R["t0"]; TAGS = G["TAGS"]; cent = G["cent"]; tops = G["tops"]; zones = G["zones"]
CX, CY0, sx = G["CX"], G["CY0"], G["sx"]
RX, RW = G["RX"], G["RW"]
A = json.load(open(HERE / "out" / "anchors.json"))
to = lambda p: (CX + 1 + p[0] * sx, CY0 + 1 + p[1] * sx)
UP = [to(p) for p in A["path_upper"]]; LO = [to(p) for p in A["path_lower"]]; RING = [to(p) for p in A["ring"]]
PANDA = to(A["px"]["panda"]); EPS = to(A["px"]["eps"])
RING_C = (sum(p[0] for p in RING) / len(RING), sum(p[1] for p in RING) / len(RING))
RING_R = sum(math.dist(p, RING_C) for p in RING) / len(RING)


def cum(poly):
  out = [0.0]
  for a, b in zip(poly, poly[1:]): out.append(out[-1] + math.dist(a, b))
  return out
FULL = UP + LO[1:]; S_FULL = cum(FULL)
S_GATE = S_FULL[min(range(len(UP)), key=lambda i: math.dist(UP[i], PANDA))]   # where the path meets the panda


def at(s):
  """Point at arc length s along the full path."""
  s = max(0.0, min(s, S_FULL[-1]))
  i = next((k for k in range(1, len(S_FULL)) if S_FULL[k] >= s), len(S_FULL) - 1)
  a, b, la, lb = FULL[i - 1], FULL[i], S_FULL[i - 1], S_FULL[i]
  u = 0 if lb == la else (s - la) / (lb - la)
  return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)


def plant(tp, key):
  """Plant signal at plant time tp (s from the fault), clamped to the run."""
  ts = R["t"]; t = T0 + tp
  i = min(range(len(ts)), key=lambda k: abs(ts[k] - t)); return R[key][i]


T_HIT = T_A0 + S_GATE / SPEED_A                              # pass 1: first pulse reaches the gate
T_REVOKE = T_HIT + 0.1                                     # TSR-518 unit-test bound, drawn at the bound
T_LANE = next(t - T0 for t, e in zip(R["t"], R["e_y"]) if t > T0 and e < -(3.7 / 2 - 1.78 / 2))
T_CUE = R["events"]["driver cue (drift)"] - T0; T_CORR = R["events"]["driver correction"] - T0
PULSE_B = T_FAULT - S_FULL[-1] / SPEED                     # pass 2: spawn so the first pulse lands at T_FAULT


def glow(ov, p, r, rgb, a):
  o = ImageDraw.Draw(ov)
  for k in range(4, 0, -1):
    rr = r * (1 + k * 0.6); o.ellipse((p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr), fill=rgb + (int(a * 0.12 * (5 - k)),))
  o.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=rgb + (a,))


def hexrgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def banner(d, text, color):
  w = d.textlength(text, font=F["bs"]) + 24; x1 = CX + G["CW"] - 12; x0 = x1 - w
  d.rounded_rectangle((x0, CY0 + 34, x1, CY0 + 62), 5, fill=PANEL, outline=color, width=2)
  d.text((x0 + 12, CY0 + 40), text, font=F["bs"], fill=TEXT)


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


def frame(t):
  im = BASE.copy(); ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(im)
  pass_b = t >= T_B0; tp = t - T_FAULT
  # ---------------------------------------------------------------- pulses on the cutaway
  if not pass_b:
    for k in range(200):
      ts = T_A0 + k * 0.12
      if ts > min(t, T_A1 - 0.4): break                      # the attacker keeps sending; the panda keeps refusing
      s = (t - ts) * SPEED_A
      if s >= S_GATE:                                       # refused at the gate: a short fade on the ring
        fade = 1 - (s - S_GATE) / 60
        if fade > 0: glow(ov, at(S_GATE), 5, hexrgb(WARN), int(220 * fade))
        continue
      glow(ov, at(s), 5, hexrgb(CY), 235)
    if t >= T_HIT:                                          # the ring flashes on every refused frame
      a = int(160 * (0.55 + 0.45 * math.cos((t - T_HIT) * 14))) if t < T_REVOKE + 0.6 else 70
      o = ImageDraw.Draw(ov); o.ellipse((RING_C[0] - RING_R - 6, RING_C[1] - RING_R - 6, RING_C[0] + RING_R + 6, RING_C[1] + RING_R + 6),
                                        outline=hexrgb(WARN) + (a,), width=6)
  else:
    for k in range(400):
      ts = PULSE_B + k * 0.05
      if ts > t: break
      s = (t - ts) * SPEED
      if s <= S_FULL[-1]: glow(ov, at(s), 4, hexrgb(CY), 230)
    if tp >= 0:                                             # the EPS lights with the commanded torque
      a = min(1.0, abs(plant(tp, "torque")) / 1500.0)
      glow(ov, EPS, 10 + 10 * a, hexrgb(CY), int(90 + 150 * a))
  box = (CX + 1, CY0 + 1, CX + G["CW"] - 1, CY0 + G["CHh"] - 1)          # keep the pulses inside the cutaway panel
  clip = Image.new("RGBA", im.size, (0, 0, 0, 0)); clip.paste(ov.crop(box), box[:2])
  im.paste(Image.alpha_composite(im.convert("RGBA"), clip).convert("RGB")); d = ImageDraw.Draw(im)
  if not pass_b and t >= T_REVOKE:
    pill(d, (RING_C[0] - RING_R - 262, RING_C[1] - 4), "authority revoked (≤ 0.1 s bound)", "#3a2a0a", WARN)
  # ---------------------------------------------------------------- banners
  if t < T_A1:
    banner(d, "Pass 1 of 2 · as built (reference build) · expected, not run", WARN)
  elif t < T_B0:
    d.rectangle((CX + 1, CY0 + 1, CX + G["CW"] - 1, CY0 + G["CHh"] - 1), fill=None)
    banner(d, "Pass 2 of 2 · without the reference-build checks", CY)
  else:
    banner(d, "Pass 2 of 2 · no reference checks · consequence: plant F-01b", CY)
  # ---------------------------------------------------------------- isometric panel: the active stage and what the item sees
  if t >= T_A0 and (not pass_b or t >= T_B0): stage_hi(d, 0, CY); mtag(d, *TAGS[0])
  if not pass_b and t >= T_HIT: stage_hi(d, 1, WARN); mtag(d, *TAGS[1])
  if pass_b and tp >= -0.4: stage_hi(d, 1, CY)
  if pass_b and tp >= 0: stage_hi(d, 2, CY); mtag(d, *TAGS[2])
  if pass_b and tp >= T_LANE: stage_hi(d, 3, CRIT)
  if pass_b and tp >= T_CORR: mtag(d, *TAGS[3])
  # ---------------------------------------------------------------- plots: dimmed in pass 1, a time cursor in pass 2
  for box in ((960, 648, 1270, 862), (1280, 648, 1590, 862)):
    x0, y0, x1, y1 = box[0] + 44, box[1] + 56, box[2] - 12, box[3] - 22
    if not pass_b:
      dim = Image.new("RGBA", (box[2] - box[0] - 2, box[3] - box[1] - 30), (17, 17, 16, 170))
      im.paste(Image.alpha_composite(im.crop((box[0] + 1, box[1] + 29, box[2] - 1, box[3] - 1)).convert("RGBA"), dim).convert("RGB"),
               (box[0] + 1, box[1] + 29)); d = ImageDraw.Draw(im)
      d.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2 + 10), "plays in pass 2 (plant F-01b)", font=F["s"], fill=TEXT2, anchor="ma")
    elif tp >= -1.5:
      xc = x0 + (min(tp, 2.7) + 1.5) / 4.2 * (x1 - x0); d.line((xc, y0, xc, y1), fill=TEXT, width=1)
  # ---------------------------------------------------------------- inset
  topview(im, max(tp, -1.0), pass_b and t >= T_B0)
  d = ImageDraw.Draw(im)
  if pass_b and tp >= T_CUE: d.text((RX + 12, 86), f"driver cue (drift) +{T_CUE:.2f} s", font=F["xs"], fill=TEXT2)
  if pass_b and tp >= T_LANE: d.text((RX + 12, 99), f"body at the lane line +{T_LANE:.2f} s", font=F["xs"], fill="#ef5b5b")
  if pass_b and tp >= T_CORR: d.text((RX + 12, 112), f"driver corrects +{T_CORR:.2f} s", font=F["xs"], fill=TEXT2)
  # ---------------------------------------------------------------- clock
  d.text((CX + G["CW"] - 10, CY0 + 22), f"clip {t:4.1f} s", font=F["xs"], fill=MUTED, anchor="ra")
  return im


def main():
  tmp = HERE / "out" / "frames"; shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
  n = int(T_END * FPS)
  for i in range(n):
    frame(i / FPS).save(tmp / f"f{i:04d}.png", compress_level=1)
  DEST.parent.mkdir(exist_ok=True)
  subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%04d.png"),
                  "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "24", "-preset", "slow", "-movflags", "+faststart",
                  str(DEST)], check=True)
  print("wrote", DEST, f"({n} frames)")


if __name__ == "__main__":
  main()
