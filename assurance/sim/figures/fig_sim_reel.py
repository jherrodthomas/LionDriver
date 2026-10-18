#!/usr/bin/env python3
"""Cut a short looping 3D compilation for the simulation page from the committed Blender clips.

Three segments, each about 3 s around its key moment at real speed, cropped to the 3D view of the dashboard clip
(`../blender/dashboards/clips/`), each with a label naming the event and its rating, and a band on every frame:
synthetic (DSR-12), no evidence credit. Output: `sim-reel-3d.webp` (animated WebP: GitHub plays it inline as an
image, and *.webp is not routed to Git LFS).

Rebuilding needs ffmpeg (with libwebp) and Pillow, so `--check` does not re-encode: it fails when a source clip is
missing, when a label's rating no longer matches WP-C-03, or when the committed file is missing, not animated, the
wrong size or frame count, or over the size limit.

    python3 fig_sim_reel.py            # rebuild sim-reel-3d.webp
    python3 fig_sim_reel.py --check
"""

from __future__ import annotations

import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
CLIPS = SIM / "blender" / "dashboards" / "clips"
OUT = HERE / "sim-reel-3d.webp"
sys.path.insert(0, str(HERE))

# (clip, start s into the clip, duration s, event, rating as drawn or None for a SOTIF hazard, label)
# The clips start 1.5 s before the fault, so start 1.5 is the fault onset.
SEGMENTS = [
  ("he-02-1-eps-loss-curve", 1.4, 3.2, "HE-02.1", "C", "EPS assist lost in a curve · plant run"),
  ("he-01-1-rural-hardover-oncoming", 1.1, 2.9, "HE-01.1", "A", "hard-over toward oncoming traffic · plant run"),
  ("sh-11-pedestrian-occluded", 1.0, 3.0, "SH-11", None, "pedestrian behind a parked truck · kinematic"),
]
CROP = (386, 66, 1092, 613)   # x, y, w, h of the 3D view in a 1920 x 1080 dashboard clip
WIDTH = 480
FPS = 10
BAND = 26                     # px: the band under the picture
QUALITY = 35
MAX_BYTES = 500_000
BAND_TEXT = "Synthetic (DSR-12) · no evidence credit · Blender renders"
FONTS = ["/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def height() -> int:
  h = round(CROP[3] * WIDTH / CROP[2] / 2) * 2
  return h + BAND


def frames_expected() -> int:
  return sum(round(d * FPS) for _c, _s, d, *_ in SEGMENTS)


def label(event: str, rating: str | None, text: str) -> str:
  return f"{event} · " + (f"ASIL {rating}" if rating else "SOTIF hazard") + f" · {text}"


def build() -> None:
  from PIL import Image, ImageDraw, ImageFont
  font_path = next((f for f in FONTS if Path(f).exists()), None)
  big = ImageFont.truetype(font_path, 13) if font_path else ImageFont.load_default()
  small = ImageFont.truetype(font_path, 11) if font_path else ImageFont.load_default()
  h_pic = height() - BAND
  with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    n = 0
    for clip, start, dur, event, rating, text in SEGMENTS:
      seg = tmp / clip
      seg.mkdir()
      x, y, w, h = CROP
      subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start}", "-t", f"{dur}", "-i", str(CLIPS / f"{clip}.mp4"),
                      "-vf", f"crop={w}:{h}:{x}:{y},scale={WIDTH}:{h_pic}:flags=lanczos,fps={FPS}",
                      "-frames:v", str(round(dur * FPS)), str(seg / "%04d.png")], check=True)
      lab = label(event, rating, text)
      for f in sorted(seg.glob("*.png")):
        im = Image.new("RGB", (WIDTH, height()), (26, 26, 25))
        with Image.open(f) as fr:
          im.paste(fr.convert("RGB"), (0, 0))
        d = ImageDraw.Draw(im)
        tw = d.textlength(lab, font=big)
        d.rounded_rectangle((8, 8, 8 + tw + 16, 8 + 24), radius=6, fill=(26, 26, 25))
        d.text((16, 12), lab, font=big, fill=(240, 239, 236))
        d.text((10, h_pic + 7), BAND_TEXT, font=small, fill=(230, 103, 103))
        im.save(tmp / f"f{n:04d}.png")
        n += 1
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(tmp / "f%04d.png"),
                    "-c:v", "libwebp_anim", "-loop", "0", "-q:v", str(QUALITY), "-compression_level", "6",
                    "-preset", "picture", str(OUT)], check=True)


def webp_info(path: Path) -> tuple[int, int, bool, int] | None:
  """(canvas width, canvas height, animated, frame count) of an extended-format WebP, or None."""
  data = path.read_bytes()
  if data[:4] != b"RIFF" or data[8:12] != b"WEBP" or data[12:16] != b"VP8X":
    return None
  flags = data[20]
  w = 1 + int.from_bytes(data[24:27], "little")
  h = 1 + int.from_bytes(data[27:30], "little")
  frames, i = 0, 12
  while i + 8 <= len(data):
    tag, size = data[i:i + 4], struct.unpack("<I", data[i + 4:i + 8])[0]
    frames += tag == b"ANMF"
    i += 8 + size + (size & 1)
  return w, h, bool(flags & 0x02), frames


def problems() -> list[str]:
  import fig_sim_he
  errs = []
  hara = fig_sim_he.hara()
  for clip, _s, _d, event, rating, _t in SEGMENTS:
    if not (CLIPS / f"{clip}.mp4").exists():
      errs.append(f"source clip missing: blender/dashboards/clips/{clip}.mp4")
    if rating is not None and hara.get(event, {}).get("asil") != rating:
      errs.append(f"{event} is drawn as ASIL {rating}; WP-C-03 rates it {hara.get(event, {}).get('asil')}")
  if not OUT.exists():
    return errs + [f"{OUT.name} missing; run fig_sim_reel.py (needs ffmpeg and Pillow)"]
  if OUT.stat().st_size > MAX_BYTES:
    errs.append(f"{OUT.name} is {OUT.stat().st_size} bytes, over {MAX_BYTES}")
  info = webp_info(OUT)
  # libwebp merges frames that do not change, so the stored count may be a little below the frames cut
  if info is None or info[:3] != (WIDTH, height(), True) or not 0.8 * frames_expected() <= info[3] <= frames_expected():
    errs.append(f"{OUT.name} is (width, height, animated, frames) {info}, expected ({WIDTH}, {height()}, True, "
                f"about {frames_expected()}); rebuild it")
  return errs


def main(argv: list[str]) -> int:
  if "--check" not in argv:
    if not shutil.which("ffmpeg"):
      print("error: ffmpeg not found", file=sys.stderr)
      return 1
    build()
    print(f"wrote {OUT.name}: {OUT.stat().st_size} bytes, {frames_expected()} frames")
  errs = problems()
  for e in errs:
    print(f"error: {e}", file=sys.stderr)
  if not errs and "--check" in argv:
    print(f"fig_sim_reel: {OUT.name} present, {frames_expected()} frames, ratings match WP-C-03")
  return 1 if errs else 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
