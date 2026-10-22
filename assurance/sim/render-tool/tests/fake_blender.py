"""A stand-in for Blender in the engine tests: takes hazard_scene.py's arguments, writes small stills for the scene's
key events from three cameras, prints hazard_scene.py's progress lines, and writes render.json and screen.json.
FAKE_DELAY (seconds a still) slows it down so a test can stop it part way."""

import json
import os
import sys
import time
from pathlib import Path

from PIL import Image

args = [a for a in sys.argv[1:] if a != "--"]
scene = Path(next(a for a in args if a.endswith(".json")))
out = scene.parent
sc = json.loads(scene.read_text())
keys = [{"frame": 1, "t": sc["t"][0], "label": "start"}]
for e in sc["events"]:
  i = min(range(len(sc["t"])), key=lambda j: abs(sc["t"][j] - e["t"]))
  keys.append({"frame": i + 1, "t": e["t"], "label": e["label"]})
cams = ("chase", "top", "driver")
(out / "stills").mkdir(exist_ok=True)
man = {"scene": sc["id"], "vehicle": "stand-in", "stills": [], "video": {}}
for k in keys:
  for c in cams:
    p = out / "stills" / f"f{k['frame']:04d}_{c}.png"
    if not ("--resume" in args and p.exists()):
      time.sleep(float(os.environ.get("FAKE_DELAY", "0")))
      Image.new("RGB", (64, 36) if c == "chase" else (32, 18), (90, 90, 90)).save(p)
    man["stills"].append({**k, "camera": c, "file": str(p.relative_to(out))})
    print(f"still {len(man['stills'])}/{len(keys) * len(cams)} {c} {k['t']:+.2f} s", flush=True)
(out / "screen.json").write_text("{}")
(out / "render.json").write_text(json.dumps(man))
