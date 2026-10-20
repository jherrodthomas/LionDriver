#!/usr/bin/env python3
"""Draw the "reading a scene dashboard" guide of the simulation page (README §1.1) from one committed dashboard.

Handbook style: the HE-02.1 dashboard (`../blender/dashboards/he-02-1-eps-loss-curve.jpg`) with its ten panels
outlined and numbered (`sim-guide-0-overview.jpg`), and four spotlights that light the panels answering one question
and dim the rest (`sim-guide-1-what.jpg` … `sim-guide-4-time.jpg`).

The panel boxes are pixel positions in that dashboard, so the source is pinned by its SHA-256: when the Blender
session changes the dashboard, `--check` fails and the boxes are redrawn instead of pointing at the wrong panels.
Rebuilding needs Pillow; `--check` needs only the standard library and also fails when an output is missing, the
wrong size or over the size limit.

    python3 fig_sim_guide.py            # rebuild the five JPEGs
    python3 fig_sim_guide.py --check
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
SOURCE = SIM / "blender" / "dashboards" / "he-02-1-eps-loss-curve.jpg"
SOURCE_SHA256 = "300778f1b44cfe6e8d7c01c2c38e6b421c130c4555ec684d0134fd2d8988d2af"
sys.path.insert(0, str(HERE))

# panel number -> (name, box x0, y0, x1, y1 in the 1600 x 900 dashboard)
PANELS = {
  1: ("Header strip", (2, 2, 1598, 46)),
  2: ("Hazardous-event card", (10, 54, 311, 344)),
  3: ("Ego state", (10, 350, 311, 641)),
  4: ("3D view", (320, 54, 1234, 568)),
  5: ("Forward and top views", (1242, 54, 1591, 496)),
  6: ("Outcome tiles", (320, 573, 1234, 641)),
  7: ("Event list", (1242, 503, 1591, 641)),
  8: ("Plots", (10, 648, 1591, 786)),
  9: ("Filmstrip", (10, 792, 1591, 877)),
  10: ("Footer", (2, 879, 1598, 898)),
}
BADGE_AT = {1: (700, 24), 10: (1400, 889)}   # thin strips: badge in a gap of the text; others at the top-right corner

# output name -> (panels lit, title, subtitle); None lights all panels without dimming
IMAGES = {
  "sim-guide-0-overview.jpg": (None, "How to read a dashboard: the ten panels",
                               "HE-02.1 (ASIL C), EPS assist lost in a highway curve · synthetic (DSR-12), no evidence credit"),
  "sim-guide-1-what.jpg": ([1, 2], "1 · What is this scene?",
                           "Event and ASIL, motion source (plant or kinematic), road, time from the fault; the HARA entry"),
  "sim-guide-2-happens.jpg": ([4, 5, 9], "2 · What happens?",
                              "The 3D view at the time shown, the driver's view, the path with event ghosts, stills of each event"),
  "sim-guide-3-close.jpg": ([3, 6, 7], "3 · How close did it get?",
                            "Ego state and margin to the lane line, outcome tiles, the panda's and driver's events with times"),
  "sim-guide-4-time.jpg": ([8], "4 · How does it unfold?",
                           "Red dashed: the fault · white: the time shown · yellow dashed: lane-line thresholds"),
}
WIDTH = 960
SOURCE_SIZE = (1600, 900)
HEAD = 96          # px of the title bar above the dashboard, at source scale
MAX_BYTES = 200_000
ACCENT = (255, 176, 32)
FONTS = ["/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def out_size() -> tuple[int, int]:
  w, h = SOURCE_SIZE
  return WIDTH, round((h + HEAD + 12) * WIDTH / w)


def badge_at(n: int) -> tuple[int, int]:
  if n in BADGE_AT:
    return BADGE_AT[n]
  x0, y0, x1, _y1 = PANELS[n][1]
  return x1 - 26, y0 + 4


def build() -> None:
  from PIL import Image, ImageDraw, ImageEnhance, ImageFont
  font = next((f for f in FONTS if Path(f).exists()), None)

  def ttf(size):
    return ImageFont.truetype(font, size) if font else ImageFont.load_default()

  fb, fh, fs = ttf(24), ttf(30), ttf(22)
  with Image.open(SOURCE) as im:
    src = im.convert("RGB")
  for name, (lit, title, sub) in IMAGES.items():
    ids = list(PANELS) if lit is None else lit
    im = src.copy() if lit is None else ImageEnhance.Brightness(src).enhance(0.28)
    for n in ids:
      box = PANELS[n][1]
      im.paste(src.crop(box), box[:2])
    d = ImageDraw.Draw(im)
    for n in ids:
      d.rounded_rectangle(PANELS[n][1], radius=8, outline=ACCENT, width=5)
    for n in ids:
      x, y = badge_at(n)
      d.ellipse((x - 18, y - 18, x + 18, y + 18), fill=ACCENT, outline=(20, 20, 20), width=3)
      d.text((x, y + 1), str(n), font=fb, fill=(20, 20, 20), anchor="mm")
    w, h = SOURCE_SIZE
    can = Image.new("RGB", (w, h + HEAD + 12), (26, 26, 25))
    can.paste(im, (0, HEAD + 6))
    d2 = ImageDraw.Draw(can)
    d2.text((24, 18), title, font=fh, fill=(240, 239, 236))
    d2.text((24, 58), sub, font=fs, fill=(195, 194, 183))
    can.resize(out_size(), Image.LANCZOS).save(HERE / name, "JPEG", quality=82, optimize=True, progressive=True)


def problems() -> list[str]:
  from fig_sim_readme import jpeg_size
  errs = []
  if not SOURCE.exists():
    return [f"source dashboard missing: {SOURCE.relative_to(SIM)}"]
  sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
  if sha != SOURCE_SHA256:
    errs.append(f"{SOURCE.relative_to(SIM)} changed (sha256 {sha[:12]}…): check the panel boxes against the new "
                "layout, rebuild, and update SOURCE_SHA256")
  for name in IMAGES:
    p = HERE / name
    if not p.exists():
      errs.append(f"{name} missing; run fig_sim_guide.py (needs Pillow)")
      continue
    if p.stat().st_size > MAX_BYTES:
      errs.append(f"{name} is {p.stat().st_size} bytes, over {MAX_BYTES}")
    if jpeg_size(p) != out_size():
      errs.append(f"{name} is {jpeg_size(p)}, expected {out_size()}")
  return errs


def main(argv: list[str]) -> int:
  if "--check" not in argv:
    build()
    print(f"wrote {len(IMAGES)} images: " + ", ".join(f"{n} {(HERE / n).stat().st_size // 1000} KB" for n in IMAGES))
  errs = problems()
  for e in errs:
    print(f"error: {e}", file=sys.stderr)
  if not errs and "--check" in argv:
    print(f"fig_sim_guide: {len(IMAGES)} images present; source dashboard unchanged")
  return 1 if errs else 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
