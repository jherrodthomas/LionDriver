"""Hazardous-event dashboard frames (assurance/sim/blender, step 3 of 3).

Lays the Blender renders of a scene out as a review dashboard, one 1920x1080 frame per moment: the chase view in the
middle with tags on the road users, the forward and top views on the right, the HARA entry of the hazardous event and
the ego state on the left, metric tiles, strip charts of the plant signals with the fault and the current time marked,
the panda and driver event log, and a strip of the key-event stills along the bottom.

  python3 assurance/sim/blender/compose.py assurance/sim/blender/out/<scene>   # dashboards for the key-event stills
  python3 assurance/sim/blender/compose.py assurance/sim/blender/out/<scene> --video   # and a clip, if frames exist

Writes out/<scene>/dashboard/f<frame>.png, out/<scene>/dashboard.png (the frame of the decisive event) and, with
--video, out/<scene>/<scene>.mp4 (ffmpeg). Every number on a frame is read from scene.json, i.e. from the plant;
nothing is drawn that the plant does not compute (there is no perception layer in layer 1, so there is no
perception panel).
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
BG = "#111110"
PANEL = "#1a1a19"
EDGE = "#2c2c2a"
TEXT = "#f0efec"
TEXT2 = "#c3c2b7"
MUTED = "#898781"
SERIES = "#3987e5"        # the plotted signal (one series per chart)
CRITICAL = "#d03b3b"      # fault onset, hazardous event, contact
WARNING = "#fab219"       # thresholds
EGO = "#d95926"

FONT_DIRS = [Path("/usr/share/fonts/opentype/inter"), Path("/usr/share/fonts/truetype/dejavu")]


def font(size: int, weight: str = "Regular"):
  for name in (f"Inter-{weight}.otf", "DejaVuSans-Bold.ttf" if weight in ("Bold", "SemiBold") else "DejaVuSans.ttf"):
    for d in FONT_DIRS:
      if (d / name).exists():
        return ImageFont.truetype(str(d / name), size)
  return ImageFont.load_default(size)


F = {k: font(*v) for k, v in {
  "h1": (20, "SemiBold"), "h2": (16, "SemiBold"), "b": (15, "Regular"), "bs": (15, "SemiBold"),
  "s": (13, "Regular"), "ss": (13, "SemiBold"), "big": (30, "SemiBold"), "xs": (11, "Regular")}.items()}


# ------------------------------------------------------------------------------------------------- helpers
def panel(d: ImageDraw.ImageDraw, box, title: str | None = None, edge: str = EDGE):
  d.rounded_rectangle(box, 6, fill=PANEL, outline=edge, width=1)
  if title:
    d.text((box[0] + 12, box[1] + 8), title, font=F["h2"], fill=TEXT)


def fit(img: Image.Image, w: int, h: int) -> Image.Image:
  s = max(w / img.width, h / img.height)
  img = img.resize((max(w, round(img.width * s)), max(h, round(img.height * s))), Image.LANCZOS)
  x, y = (img.width - w) // 2, (img.height - h) // 2
  return img.crop((x, y, x + w, y + h))


def wrap(d, xy, text: str, f, fill, width_px: int, gap: int = 4) -> int:
  x, y = xy
  avg = max(1, f.getlength("abcdefghijklmnopqrstuvwxyz") / 26)
  for line in textwrap.wrap(text, max(10, int(width_px / avg))):
    d.text((x, y), line, font=f, fill=fill)
    y += f.size + gap
  return y


def clip(text: str, f, width: float) -> str:
  if f.getlength(text) <= width:
    return text
  while text and f.getlength(text + "…") > width:
    text = text[:-1]
  return text.rstrip() + "…"


def nearest(ts: list[float], t: float) -> int:
  return min(range(len(ts)), key=lambda i: abs(ts[i] - t))


def chart(d, box, title: str, unit: str, t: list[float], v: list[float], i: int, bands=(), zero=False, span=1.0):
  """One signal against time: recessive grid, the signal, the fault at t = 0 and a cursor at the current time."""
  panel(d, box)
  x0, y0, x1, y1 = box
  d.text((x0 + 12, y0 + 8), title, font=F["ss"], fill=TEXT)
  d.text((x1 - 12, y0 + 8), f"{v[i]:+.2f} {unit}" if zero else f"{v[i]:.1f} {unit}", font=F["ss"], fill=TEXT,
         anchor="ra")
  px0, py0, px1, py1 = x0 + 44, y0 + 34, x1 - 12, y1 - 24
  lo, hi = min(v + [b for b in bands]), max(v + [b for b in bands])
  if zero:
    lo, hi = min(lo, 0.0), max(hi, 0.0)
  if hi - lo < span:                            # a near-constant signal stays flat, not magnified noise
    mid = 0.5 * (hi + lo)
    lo, hi = mid - span / 2, mid + span / 2
  pad = 0.08 * (hi - lo)
  lo, hi = lo - pad, hi + pad
  t0, t1 = t[0], t[-1]
  X = lambda tt: px0 + (tt - t0) / (t1 - t0) * (px1 - px0)
  Y = lambda vv: py1 - (vv - lo) / (hi - lo) * (py1 - py0)
  for k in range(3):
    vv = lo + (hi - lo) * k / 2
    d.line([(px0, Y(vv)), (px1, Y(vv))], fill=EDGE, width=1)
    d.text((px0 - 6, Y(vv)), f"{vv:.0f}" if abs(hi - lo) > 6 else f"{vv:.1f}", font=F["xs"], fill=MUTED, anchor="rm")
  for tt in range(math.ceil(t0), math.floor(t1) + 1):
    d.text((X(tt), py1 + 5), f"{tt:d}", font=F["xs"], fill=MUTED, anchor="ma")
  for b in bands:
    for xa in range(int(px0), int(px1), 10):
      d.line([(xa, Y(b)), (min(xa + 5, px1), Y(b))], fill=WARNING, width=1)
  if t0 <= 0 <= t1:
    for ya in range(int(py0), int(py1), 8):
      d.line([(X(0), ya), (X(0), min(ya + 4, py1))], fill=CRITICAL, width=2)
  d.line([(X(tt), Y(vv)) for tt, vv in zip(t, v)], fill=SERIES, width=2, joint="curve")
  d.line([(X(t[i]), py0), (X(t[i]), py1)], fill=TEXT2, width=1)
  r = 4
  d.ellipse([X(t[i]) - r, Y(v[i]) - r, X(t[i]) + r, Y(v[i]) + r], fill=SERIES, outline=PANEL, width=2)


def tile(d, box, label: str, value: str, colour: str = TEXT):
  panel(d, box)
  d.text((box[0] + 14, box[1] + 10), label, font=F["s"], fill=TEXT2)
  d.text((box[0] + 14, box[1] + 32), value, font=F["big"], fill=colour)


def tag(d, xy, text: str, colour: str, img_box):
  """A callout box above a road user in the main view, with a leader line down to it."""
  x0, y0, x1, y1 = img_box
  x = x0 + xy[0] * (x1 - x0)
  y = y0 + xy[1] * (y1 - y0)
  if not (x0 <= x <= x1 and y0 <= y <= y1):
    return
  w = F["ss"].getlength(text) + 16
  bx, by = min(max(x - w / 2, x0 + 4), x1 - w - 4), max(y - 54, y0 + 4)
  d.line([(x, by + 26), (x, y)], fill=colour, width=2)
  d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=colour)
  d.rounded_rectangle([bx, by, bx + w, by + 26], 4, fill=colour)
  d.text((bx + 8, by + 5), text, font=F["ss"], fill="#ffffff")


# ------------------------------------------------------------------------------------------------- frame
def frame(sc: dict, screen: dict, keys: list[dict], views: dict[str, Path], i: int, thumbs: dict[int, Path]):
  img = Image.new("RGB", (W, H), BG)
  d = ImageDraw.Draw(img)
  t = sc["t"]
  he, hz, case = sc["he"], sc["hazard"], sc["case"]

  # top bar
  d.rectangle([0, 0, W, 56], fill=PANEL)
  d.line([(0, 56), (W, 56)], fill=EDGE)
  d.text((16, 9), f"Scene {sc['id']}", font=F["h1"], fill=TEXT)
  d.text((16, 33), f"Plant case {case['id']}: {case['title']}", font=F["s"], fill=TEXT2)
  bx = 16 + F["h1"].getlength(f"Scene {sc['id']}") + 16
  badge = f"{he['id']}  ASIL {he['asil']}"
  d.rounded_rectangle([bx, 8, bx + F["ss"].getlength(badge) + 16, 32], 4, fill=CRITICAL)
  d.text((bx + 8, 12), badge, font=F["ss"], fill="#ffffff")
  fields = [("Road", case["road"]), ("Set speed", f"{case['speed_kph']:.0f} km/h"), ("EPS assumption", case["eps"]),
            ("Safety goal", case["sg"]), ("Time from fault", f"{t[i]:+.2f} s  ({t[0]:+.1f} to {t[-1]:+.1f})")]
  x = W - 16
  for k, v in reversed(fields):
    w = max(F["s"].getlength(k), F["bs"].getlength(v)) + 28
    x -= w
    d.line([(x - 8, 10), (x - 8, 46)], fill=EDGE)
    d.text((x, 9), k, font=F["s"], fill=MUTED)
    d.text((x, 29), v, font=F["bs"], fill=TEXT)

  # main view
  mb = (384, 64, 384 + 1095, 64 + 616)
  if views.get("chase"):
    img.paste(fit(Image.open(views["chase"]).convert("RGB"), mb[2] - mb[0], mb[3] - mb[1]), mb[:2])
  d.rectangle(mb, outline=EDGE)
  past = [e for e in sc["events"] if e["t"] <= t[i] + 1e-6]
  for a in sc["actors"]:
    name = "ego" if a["kind"] == "ego" else a["name"]
    pos = screen.get(name, [None] * len(t))[i]
    if pos is None:
      continue
    if a["kind"] == "ego":
      dev = sc["lateral"][i]
      label = f"Ego (plant)  {abs(dev):.2f} m {'right' if dev < 0 else 'left'} of lane centre"
      tag(d, pos, label, EGO, mb)
    else:
      contact = any("contact" in e["label"] and a["name"] in e["label"] for e in past)
      src = "plant" if a["source"] == "plant" else "illustrative, not simulated"
      tag(d, pos, f"{a['name'].capitalize()} ({src})" + ("  CONTACT" if contact else ""),
          CRITICAL if contact else "#4b5563", mb)
  if past:
    last = past[-1]
    msg = f"{last['label']}  at {last['t']:+.2f} s"
    w = F["bs"].getlength(msg) + 24
    d.rounded_rectangle([mb[0] + 12, mb[3] - 44, mb[0] + 12 + w, mb[3] - 12], 5, fill="#000000c0", outline=CRITICAL)
    d.text((mb[0] + 24, mb[3] - 37), msg, font=F["bs"], fill=TEXT)

  # left: hazardous event (HARA) and ego state
  hb = (12, 64, 372, 412)
  panel(d, hb, edge=CRITICAL)
  d.text((24, 74), f"Hazardous event {he['id']}", font=F["h1"], fill=CRITICAL)
  y = wrap(d, (24, 102), f"{hz['id']}: {hz['title']}", F["bs"], TEXT, 330)
  y = wrap(d, (24, y + 6), "Situation: " + he["situation"], F["s"], TEXT2, 330, 3)
  y = wrap(d, (24, y + 4), "Effect: " + he["effect"], F["s"], TEXT2, 330, 3)
  rows = [("Severity", f"S{he['s']}"), ("Exposure", f"E{he['e']}"), ("Controllability", f"C{he['c']}"),
          ("ASIL", he["asil"])]
  y = max(y + 8, 300)
  for k, v in rows:
    d.text((24, y), k, font=F["s"], fill=TEXT2)
    d.text((200, y), v, font=F["ss"], fill=CRITICAL if k == "ASIL" else TEXT)
    y += 20
  d.text((24, hb[3] - 22), "Ratings are WP-C-03 proposals, not approved", font=F["xs"], fill=MUTED)

  eb = (12, 420, 372, 768)
  panel(d, eb, "Ego state (plant)")
  rows = [("Speed", f"{sc['speed'][i] * 3.6:.1f} km/h"), ("Longitudinal accel.", f"{sc['ax'][i]:+.2f} m/s²"),
          ("Lateral accel.", f"{sc['ay'][i]:+.2f} m/s²"), ("Lateral offset", f"{sc['lateral'][i]:+.2f} m"),
          ("Margin to lane line", f"{sc['lane_threshold'] - abs(sc['lateral'][i]):+.2f} m"),
          ("EPS LKA torque", f"{sc['eps_torque'][i]:.0f}")]
  if sc.get("gap"):
    rows += [("Gap to lead", f"{sc['gap']['lead'][i]:.1f} m"), ("Gap to follower", f"{sc['gap']['follower'][i]:.1f} m")]
  y = 452
  for k, v in rows:
    d.text((28, y), k, font=F["b"], fill=TEXT2)
    neg = k == "Margin to lane line" and v.startswith("-")
    d.text((356, y), v, font=F["bs"], fill=CRITICAL if neg else TEXT, anchor="ra")
    y += 36 if not sc.get("gap") else 34

  # right: forward and top views, event log
  for title, name, top in (("Forward view", "driver", 64), ("Top view", "top", 333)):
    vb = (1491, top, 1908, top + 261)
    panel(d, vb, title)
    if views.get(name):
      img.paste(fit(Image.open(views[name]).convert("RGB"), 417 - 2, 261 - 34), (vb[0] + 1, vb[1] + 33))
  lb = (1491, 602, 1908, 768)
  panel(d, lb, "Panda and driver events (plant)")
  ev = sc["events"]
  y = 632
  for e in ev[-6:] if len(ev) > 6 else ev:
    done = e["t"] <= t[i] + 1e-6
    col = CRITICAL if ("contact" in e["label"] or e["label"] == "fault") and done else (TEXT if done else MUTED)
    r = 5
    if done:
      d.ellipse([1505, y + 4, 1505 + 2 * r, y + 4 + 2 * r], fill=col)
    else:
      d.ellipse([1505, y + 4, 1505 + 2 * r, y + 4 + 2 * r], outline=MUTED, width=2)
    d.text((1524, y), f"{e['t']:+.2f} s", font=F["ss"], fill=col)
    d.text((1590, y), clip(e["label"], F["s"], lb[2] - 1600), font=F["s"], fill=col)
    y += 22

  # tiles under the main view
  m = sc["metrics"]
  tiles = [("Time from fault", f"{t[i]:+.2f} s", TEXT)]
  if sc.get("gap"):
    g = sc["gap"]["follower"]
    tg = g[i] / max(sc["speed"][i], 0.1)
    tiles += [("Gap to follower", f"{g[i]:.1f} m", TEXT), ("Minimum follower gap", f"{min(g):.1f} m", TEXT),
              ("Follower time gap", f"{tg:.2f} s", WARNING if tg < 1.0 else TEXT)]
  else:
    tl = m.get("t_line")
    tiles += [("Lateral offset", f"{sc['lateral'][i]:+.2f} m", TEXT),
              ("Body at lane line", f"{tl:.2f} s" if tl is not None else "not reached", WARNING if tl else TEXT),
              ("Peak offset (whole run)", f"{m['max_offset']:.2f} m", TEXT)]
  contact = next((e for e in sc["events"] if "contact" in e["label"] or "barrier" in e["label"]), None)
  tiles.append(("Contact", f"{contact['t']:+.2f} s" if contact else "none", CRITICAL if contact else TEXT))
  tw = (1095 - 4 * 8) / 5
  for k, (label, value, col) in enumerate(tiles):
    x0 = 384 + k * (tw + 8)
    tile(d, (x0, 688, x0 + tw, 768), label, value, col)

  # strip charts
  series = [("Speed", "km/h", [v * 3.6 for v in sc["speed"]], (), False, 20.0),
            ("Longitudinal acceleration", "m/s²", sc["ax"], (), True, 2.0),
            ("Lateral offset from lane centre", "m", sc["lateral"], (sc["lane_threshold"], -sc["lane_threshold"]),
             True, 2.0),
            ("Lateral acceleration", "m/s²", sc["ay"], (), True, 2.0)]
  if sc.get("gap"):
    series.append(("Gap to follower", "m", sc["gap"]["follower"], (), False, 10.0))
  else:
    series.append(("EPS LKA torque", "", sc["eps_torque"], (), True, 300.0))
  cw = (W - 24 - 4 * 8) / 5
  for k, (title, unit, v, bands, zero, span) in enumerate(series):
    x0 = 12 + k * (cw + 8)
    chart(d, (x0, 776, x0 + cw, 942), title, unit, t, v, i, bands, zero, span)

  # key-event strip
  n = len(keys)
  sw = (W - 24 - (n - 1) * 8) / n
  for k, key in enumerate(keys):
    x0 = 12 + k * (sw + 8)
    box = (x0, 950, x0 + sw, 1050)
    cur = key["frame"] - 1 <= i and (k == n - 1 or keys[k + 1]["frame"] - 1 > i)
    panel(d, box, edge=SERIES if cur else EDGE)
    if key["frame"] in thumbs:
      th = fit(Image.open(thumbs[key["frame"]]).convert("RGB"), int(sw) - 2, 66)
      img.paste(th, (int(x0) + 1, 951))
    d.text((x0 + 8, 1020), f"{key['t']:+.1f} s", font=F["ss"], fill=TEXT)
    d.text((x0 + 56, 1021), clip(key["label"], F["xs"], sw - 64), font=F["xs"], fill=TEXT2)
    if cur:
      d.rounded_rectangle(box, 6, outline=SERIES, width=2)

  d.text((12, 1056), clip(sc["provenance"] + ". " + sc["caption"], F["xs"], W - 260), font=F["xs"], fill=MUTED)
  d.text((W - 12, 1056), "LionDriver assurance/sim/blender", font=F["xs"], fill=MUTED, anchor="ra")
  return img


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("scene_dir", type=Path)
  ap.add_argument("--video", action="store_true", help="also compose every rendered frame and encode an MP4")
  args = ap.parse_args(argv)
  out = args.scene_dir
  sc = json.loads((out / "scene.json").read_text())
  screen = json.loads((out / "screen.json").read_text()) if (out / "screen.json").exists() else {}
  man = json.loads((out / "render.json").read_text())
  stills = {}
  for s in man["stills"]:
    stills.setdefault(s["frame"], {})[s["camera"]] = out / s["file"]
  keys, seen = [], set()
  for s in man["stills"]:
    if s["frame"] not in seen:
      seen.add(s["frame"])
      keys.append({"frame": s["frame"], "t": s["t"], "label": s["label"]})
  thumbs = {f: v["chase"] for f, v in stills.items() if "chase" in v}

  (out / "dashboard").mkdir(exist_ok=True)
  for f, views in stills.items():
    frame(sc, screen, keys, views, f - 1, thumbs).save(out / "dashboard" / f"f{f:04d}.png", optimize=True)
  decisive = next((k for k in keys if "contact" in k["label"] or "barrier" in k["label"]), None) \
    or next((k for k in keys if "correction" in k["label"]), None) or keys[len(keys) // 2]
  shutil.copy(out / "dashboard" / f"f{decisive['frame']:04d}.png", out / "dashboard.png")
  print(f"{sc['id']}: {len(stills)} dashboards; {out / 'dashboard.png'} ({decisive['label']})")

  if args.video:
    if not man["video"].get("chase"):
      print("no clip frames: run hazard_scene.py with --video first", file=sys.stderr)
      return 1
    tmp = out / "dashboard_frames"
    tmp.mkdir(exist_ok=True)
    for f in range(1, len(sc["t"]) + 1):
      views = {c: out / "frames" / c / f"{f:04d}.png" for c in man["video"]}
      frame(sc, screen, keys, views, f - 1, thumbs).save(tmp / f"{f:04d}.png")
    mp4 = out / f"{sc['id']}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(sc["fps"]), "-i", str(tmp / "%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(mp4)], check=True)
    print(f"{sc['id']}: {mp4}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
