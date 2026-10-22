"""The engine of Hazard Scene Studio: a row in, its outcome and dashboard out, with progress, cancel and a queue
(windows-build-plan.md §2, phase 1). run_sheet.py (command line) and the Windows app both drive it; it adds no
physics: the scene comes from row_to_scene.py and export_scene.py, the picture from Blender and compose.py.

  outcome   seconds: the plant or kinematic export, and the Result columns but the dashboard
  render    minutes: Blender's stills, cached by render key (rows that look the same share them), resumable
  compose   seconds: the row's own dashboard over the cached stills, with its own card

Events go to a callback as dicts: {"row", "stage": exported | still | rendered | drawn | cancelled | error, ...};
a still event carries "done" and "total". Blender runs as a separate program, so Stop ends it at once and a later
run carries on from the stills already made (hazard_scene.py --resume).
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import json
import os
import queue
import re
import shlex
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

from PIL import Image

import row_to_scene as rs
import compose  # noqa: E402  (../blender, put on the path by row_to_scene)

BLENDER_DIR = rs.SIM / "blender"
OUT = rs.HERE / "out"
STILL = re.compile(r"^still (\d+)/(\d+) (\S+) ([+-][\d.]+) s")
Event = Callable[[dict], None]


class Cancelled(Exception):
  pass


def blender_command() -> list[str] | None:
  """How to run a Blender script: LIONDRIVER_BLENDER, `blender` on the PATH, or this Python if it has bpy."""
  if os.environ.get("LIONDRIVER_BLENDER"):
    return shlex.split(os.environ["LIONDRIVER_BLENDER"], posix=os.name != "nt")
  if shutil.which("blender"):
    return ["blender", "-b", "-P"]
  if importlib.util.find_spec("bpy"):
    return [sys.executable]
  return None


@dataclasses.dataclass
class Settings:
  out: Path = OUT
  blender: list[str] | None = None        # None: blender_command()
  samples: int = 16
  res: str = "1280x720"
  standin: bool = False
  vehicle: Path | None = None             # the ego GLB (the purchased Corolla); None: hazard_scene.py's default


@dataclasses.dataclass
class Result:
  row: str
  data: dict | None = None                # scene.json
  outcome: dict | None = None             # the Result columns but Status and Dashboard
  key: str | None = None
  notes: list[str] = dataclasses.field(default_factory=list)
  dashboard: Path | None = None
  vehicle: str | None = None
  error: str | None = None

  def status(self, rendered: bool) -> str:
    if self.error:
      return f"cannot draw: {self.error}"
    head = f"drawn ({self.vehicle})" if rendered else "exported, not rendered"
    return "; ".join([head] + self.notes)


class Engine:
  def __init__(self, settings: Settings | None = None, ctx: rs.Context | None = None):
    self.settings = settings or Settings()
    self.ctx = ctx or rs.Context.load()
    self._proc: subprocess.Popen | None = None

  # ------------------------------------------------------------------------------------------------- stages
  def outcome(self, row: dict, adapter: dict) -> Result:
    """Seconds: the scene and its outcome. A row the library cannot draw comes back with its reason."""
    res = Result(str(row.get("Row ID")))
    try:
      if not str(row.get("Motion preset") or "").strip() and str(row.get("Status") or "").startswith("cannot draw"):
        raise rs.RowError(str(row["Status"])[len("cannot draw: "):])
      sc, res.notes = rs.row_to_scene(row, adapter, self.ctx)
      res.data = rs.export(sc, self.ctx)
      res.key = rs.render_key(res.data)
      res.outcome = {**rs.outcome(res.data), "Render key": res.key}
    except rs.RowError as e:
      res.error = str(e)
    return res

  def render(self, res: Result, on_event: Event, cancel: threading.Event) -> tuple[Path, str]:
    """Minutes: the stills of a render key, made once. Stop keeps the stills made so far for the next run."""
    s = self.settings
    look = json.dumps([s.samples, s.res, s.standin, str(s.vehicle or "")])   # the same key at another quality
    d = s.out / "renders" / f"{res.key}-{hashlib.sha256(look.encode()).hexdigest()[:6]}"
    man = d / "render.json"
    if man.exists():
      return d, json.loads(man.read_text())["vehicle"]
    cmd = self.settings.blender or blender_command()
    if cmd is None:
      raise rs.RowError("no Blender: install it, pip install bpy, or set LIONDRIVER_BLENDER")
    d.mkdir(parents=True, exist_ok=True)
    # seeded by the preset, as a gallery variant is by its base scene: the same people and plants
    scene = {**res.data, "id": f"rt-{res.key}", "variant_of": res.data["row"]["preset"]}
    (d / "scene.json").write_text(json.dumps(scene, indent=1))
    args = ["--stills", "--resume", "--no-blend", "--samples", str(s.samples), "--res", s.res]
    args += ["--standin"] if s.standin else (["--vehicle", str(s.vehicle)] if s.vehicle else [])
    sep = [] if cmd[0] == sys.executable else ["--"]
    log = []
    self._proc = subprocess.Popen(cmd + [str(BLENDER_DIR / "hazard_scene.py")] + sep + [str(d / "scene.json")] + args,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                                  encoding="utf-8", errors="replace")
    try:
      for line in self._proc.stdout:
        log.append(line)
        m = STILL.match(line)
        if m:
          on_event({"row": res.row, "stage": "still", "done": int(m[1]), "total": int(m[2]), "camera": m[3],
                    "t": float(m[4]), "file": str(d / "stills")})
        if cancel.is_set():
          self._proc.terminate()
          self._proc.wait()
          raise Cancelled()
      code = self._proc.wait()
    finally:
      self._proc.stdout.close()
      self._proc = None
    if code or not man.exists():
      (d / "blender.log").write_text("".join(log))
      raise rs.RowError(f"Blender failed (log: {d / 'blender.log'})")
    return d, json.loads(man.read_text())["vehicle"]

  def compose(self, res: Result, rdir: Path, dest: Path) -> Path:
    """Seconds: the row's own dashboard over the shared stills, as a JPEG at the gallery's size and quality."""
    d = self.settings.out / "rows" / res.data["id"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "scene.json").write_text(json.dumps(res.data, indent=1))
    shutil.copy(rdir / "screen.json", d / "screen.json")
    man = json.loads((rdir / "render.json").read_text())
    for st in man["stills"]:                      # absolute paths into the cache: no links (Windows has none to spare)
      st["file"] = str((rdir / st["file"]).resolve())
    (d / "render.json").write_text(json.dumps(man, indent=1))
    if compose.main([str(d)]):
      raise rs.RowError("compose failed")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(d / "dashboard.png") as im:      # gallery.py's size and quality
      im.convert("RGB").resize((1600, 900), Image.LANCZOS).save(dest, quality=75, optimize=True)
    return dest

  # ------------------------------------------------------------------------------------------------- a row
  def run(self, row: dict, adapter: dict, dest_dir: Path | None, on_event: Event = lambda e: None,
          cancel: threading.Event | None = None) -> Result:
    """All three stages for one row; dest_dir None: the outcome only."""
    cancel = cancel or threading.Event()
    res = self.outcome(row, adapter)
    if res.error:
      on_event({"row": res.row, "stage": "error", "error": res.error})
      return res
    on_event({"row": res.row, "stage": "exported", "outcome": res.outcome, "key": res.key})
    if dest_dir is None:
      return res
    try:
      rdir, res.vehicle = self.render(res, on_event, cancel)
      on_event({"row": res.row, "stage": "rendered", "key": res.key})
      res.dashboard = self.compose(res, rdir, dest_dir / f"{res.data['id']}.jpg")
      on_event({"row": res.row, "stage": "drawn", "dashboard": str(res.dashboard), "vehicle": res.vehicle})
    except Cancelled:
      on_event({"row": res.row, "stage": "cancelled"})
      res.error = "stopped before the picture was finished"
    except rs.RowError as e:
      res.error = str(e)
      on_event({"row": res.row, "stage": "error", "error": res.error})
    return res


class RenderQueue:
  """Rows rendered one after another on a worker thread; the caller keeps working. stop() ends the current row at
  once (its stills are kept) and drops the rest."""

  def __init__(self, engine: Engine, on_event: Event, on_done: Callable[[Result], None] = lambda r: None):
    self.engine, self.on_event, self.on_done = engine, on_event, on_done
    self._q: queue.Queue = queue.Queue()
    self._cancel = threading.Event()
    self._thread = threading.Thread(target=self._work, daemon=True)
    self._thread.start()

  def add(self, row: dict, adapter: dict, dest_dir: Path) -> None:
    self._q.put((row, adapter, dest_dir))

  def stop(self) -> None:
    while not self._q.empty():
      try:
        self._q.get_nowait()
        self._q.task_done()
      except queue.Empty:
        break
    self._cancel.set()

  def join(self) -> None:
    self._q.join()

  def _work(self) -> None:
    while True:
      row, adapter, dest = self._q.get()
      self._cancel.clear()
      try:
        self.on_done(self.engine.run(row, adapter, dest, self.on_event, self._cancel))
      finally:
        self._q.task_done()
