"""A risk-assessment row as a hazardous-event scene (render-tool-plan.md §3 to §5).

A row of the template (template.py) names a library environment, a condition and traffic, a motion preset (a scene
of ../blender/scenes.yaml whose motion it borrows, with an optional speed) and the method's own rating columns. This
module turns it into a scenes.yaml-shaped entry and hands it to ../blender/export_scene.py unchanged, so the motion,
events, contact, gap and TTC come from the plant or the preset's stated assumptions exactly as for a gallery scene.
The rating is carried to the dashboard's card as the row writes it; nothing here rates anything.

Column kinds, in sheet order:
  Row      Row ID, Title
  Scene    Environment: the road and its cross-section, so it can change the outcome (a barrier, a lane)
  Look     Condition, Traffic: the picture only (export_scene's variants test holds it)
  Motion   Motion preset, Speed km/h
  Rating   the adapter's columns (adapters/*.yaml), shown on the card
  Result   written back by run_sheet.py

A row the library cannot draw raises RowError with a plain reason for the Status column.
"""

from __future__ import annotations

import csv
import dataclasses
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
REPO = SIM.parent.parent
ADAPTERS = HERE / "adapters"
sys.path.insert(0, str(SIM / "blender"))

import export_scene as ex  # noqa: E402

# (header, kind, hint); the rating columns of an adapter go between Motion and Result
NEUTRAL = [
  ("Row ID", "Row", "your name for the row, unique in the sheet"),
  ("Title", "Row", "a few words"),
  ("Environment", "Scene", "library environment; sets the road, so it can change the outcome"),
  ("Condition", "Look", "W01..W06, TC-01: the picture only"),
  ("Traffic", "Look", "illustrative traffic, or default"),
  ("Motion preset", "Motion", "the scene whose motion the row uses"),
  ("Speed km/h", "Motion", "blank: the preset's own"),
]
RESULTS = [
  ("Status", "Result", "written by run_sheet.py"),
  ("Dashboard", "Result", "the picture"),
  ("Contact", "Result", "first contact, from the motion"),
  ("Smallest gap m", "Result", "to the critical road user"),
  ("Smallest TTC s", "Result", "to a road user in the ego's path"),
  ("Motion source", "Result", "plant or kinematic"),
  ("Render key", "Result", "rows with the same key share one render"),
]
DEFAULT = "default"
# preset fields a row takes over: its motion and what the motion is drawn against (road overrides, props, actors)
MOTION_KEYS = ("motion", "case", "case_overrides", "case_title", "assumptions", "ego", "actors", "window", "road",
               "props", "trigger_label", "events", "lane_change", "hide_plant_traffic", "critical", "env", "sg", "tc",
               "ks")


class RowError(Exception):
  """A row the library cannot draw; the message goes to the Status column as written."""


@dataclasses.dataclass
class Context:
  lib: dict
  hes: dict
  presets: dict

  @classmethod
  def load(cls) -> "Context":
    return cls(ex.load_library(), ex.hazardous_events(), {s["id"]: s for s in ex.load_raw_scenes()})


def load_adapters() -> list[dict]:
  return [yaml.safe_load(p.read_text()) for p in sorted(ADAPTERS.glob("*.yaml"))]


def columns(adapter: dict) -> list[tuple[str, str, str]]:
  return NEUTRAL + [(c["column"], "Rating", c.get("hint", "")) for c in adapter["rating"]] + RESULTS


def preset_label(sc: dict) -> str:
  if sc.get("motion", "plant") == "plant":
    return f"plant case {sc['case']}" + (f" {sc['case_overrides']}" if sc.get("case_overrides") else "")
  return "kinematic"


def _fill(text: str, row: dict) -> str:
  return re.sub(r"\{([^{}]+)\}", lambda m: str(row.get(m.group(1)) or "—"), text)


def _blank(v) -> bool:
  return v is None or str(v).strip() == ""


def make_card(row: dict, adapter: dict, lib: dict, code: str) -> dict:
  c, cond = adapter["card"], lib["conditions"][code]
  rows = [[k, _fill(v, row)] for k, v in c["rows"]]
  rows.append(["Condition", f"{code}" + (f" {cond['exposure']}" if cond["exposure"] else "") + f", {cond['odd']} ODD"])
  return {"kind": adapter["method"], "id": str(row["Row ID"]), "heading": _fill(adapter["heading"], row),
          "badge": _fill(c["badge"], row), "title": _fill(c["title"], row), "situation": _fill(c["situation"], row),
          "effect": _fill(c["effect"], row), "rows": rows, "note": c["note"], "tc": [], "ks": []}


def slug(text: str) -> str:
  return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "row"


def situation_code(row: dict, adapter: dict) -> str | None:
  col = next((c["column"] for c in adapter["rating"] if c["source"] == adapter["prefill"]["situation"]), None)
  m = re.match(r"\s*(OS-\d+)", str(row.get(col) or ""))
  return m.group(1) if m else None


def _plant_road(sc: dict) -> str:
  return ex.plant_case(sc)[1].road if sc.get("motion", "plant") == "plant" else sc.get("road", {}).get("geometry",
                                                                                                         "straight")


def _geometry_fits(sc: dict, env: dict) -> bool:
  want = env["geometry"]
  return want == "any" or (_plant_road(sc) != "straight") == (want == "curve")


def row_to_scene(row: dict, adapter: dict, ctx: Context) -> tuple[dict, list[str]]:
  """The scenes.yaml entry for a row, and notes for the Status column."""
  notes = []
  if _blank(row.get("Row ID")):
    raise RowError("no Row ID")
  pid = str(row.get("Motion preset") or "").strip()
  if not pid:
    raise RowError("pick a motion preset (Lists sheet)")
  if pid not in ctx.presets:
    raise RowError(f"motion preset {pid} is not a scene of scenes.yaml (see the Lists sheet)")
  pre = ctx.presets[pid]
  env_id = str(row.get("Environment") or "").strip() or pre["environment"]
  if env_id not in ctx.lib["environments"]:
    raise RowError(f"environment {env_id} is not in the library (see the Lists sheet)")
  env = ctx.lib["environments"][env_id]
  code = str(row.get("Condition") or "").strip() or pre.get("conditions", "W01")
  if code not in ctx.lib["conditions"]:
    raise RowError(f"condition {code} is not in the library (W01..W06, TC-01, TC-01-NB)")
  if code not in env["conditions"]:
    raise RowError(f"environment {env_id} is not drawn under {code} (it allows {', '.join(env['conditions'])})")
  traffic = str(row.get("Traffic") or "").strip() or DEFAULT
  if traffic == DEFAULT:
    traffic = pre.get("traffic", env.get("traffic", "none")) if env_id == pre["environment"] else env.get("traffic",
                                                                                                           "none")
  if traffic not in ctx.lib["traffic"]:
    raise RowError(f"traffic {traffic} is not in the library (see the Lists sheet)")

  sc = {k: pre[k] for k in MOTION_KEYS if k in pre}
  sc.update({"id": f"row-{slug(row['Row ID'])}", "environment": env_id, "conditions": code, "traffic": traffic})
  speed = row.get("Speed km/h")
  moved = False
  if not _blank(speed):
    try:
      v = float(speed)
    except ValueError:
      raise RowError(f"Speed km/h {speed!r} is not a number") from None
    if not 5 <= v <= 160:
      raise RowError(f"Speed km/h {v:g} is outside 5 to 160")
    if sc.get("motion", "plant") == "plant":
      if v != ex.plant_case(sc)[1].speed_kph:
        sc["case_overrides"] = {**sc.get("case_overrides", {}), "speed_kph": v}
        moved = True
    elif v != ex.value(sc["ego"]["speed_kph"]):
      sc["ego"] = {**sc["ego"], "speed_kph": v}
      moved = True
  if not _geometry_fits(sc, env):
    raise RowError(f"the motion of {pid} drives a {_plant_road(sc)} road; environment {env_id} is {env['geometry']}")
  os_code = situation_code(row, adapter)
  if os_code and os_code not in env["os"]:
    notes.append(f"{env_id} does not list {os_code}")
  if env_id != pre["environment"]:
    notes.append(f"environment changed from the preset's {pre['environment']}: the road can change the outcome")

  # the same look as a gallery variant of the preset draws the same illustrative traffic (export_scene.expand)
  if not moved and env_id == pre["environment"] and (code != pre.get("conditions", "W01")
                                                       or traffic != pre.get("traffic", env.get("traffic", "none"))):
    sc["jitter_seed"] = f"{pid}--{code.lower()}"
  sc["card"] = make_card(row, adapter, ctx.lib, code)
  head = f"{adapter['method']} row {row['Row ID']}" + (f" ({row['Title']})" if not _blank(row.get("Title")) else "")
  how = f"drawn with the motion of {pid}" + (f" at {float(speed):g} km/h, set by the row" if moved else "")
  sc["caption"] = (f"{head}, {how}. " + ("" if moved else " ".join(pre["caption"].split()))).strip()
  sc["preset"] = pid
  return sc, notes


def export(sc: dict, ctx: Context) -> dict:
  """scene.json for the row: export_scene's own resolve and build, as for any scene."""
  data = ex.build(ex.resolve(sc, ctx.lib), ctx.hes, ctx.lib)
  data["row"] = {"preset": sc["preset"], "method": sc["card"]["kind"]}
  return data


def render_key(data: dict) -> str:
  """Rows whose 3D picture is the same share one render: everything but the card, caption and ID."""
  keep = {k: v for k, v in data.items() if k not in ("id", "caption", "card", "row")}
  keep["preset"] = data["row"]["preset"]            # seeds the people and plants, as a variant's base scene does
  return hashlib.sha256(json.dumps(keep, sort_keys=True).encode()).hexdigest()[:12]


def outcome(data: dict) -> dict:
  c = data["contact"]
  gap = min(data["gap"]) if data.get("gap") else None
  ttc = min(data["ttc"]) if data.get("ttc") else None
  return {"Contact": f"yes: {c['who']} at {c['t']:+.2f} s, {c['rel_kph']:.0f} km/h relative" if c else "no",
          "Smallest gap m": round(gap, 2) if gap is not None else "—",
          "Smallest TTC s": round(ttc, 2) if ttc is not None and ttc < 99 else "none",
          "Motion source": (f"plant, case {data['case']['id']}" if data["motion"] == "plant" else "kinematic")
                           + " (synthetic, no evidence credit)"}


# ----------------------------------------------------------------------------------------------------- prefill
def source_rows(adapter: dict) -> dict[str, dict]:
  p = adapter["prefill"]
  with open(REPO / p["source"], newline="") as f:
    return {r[p["key"]]: r for r in csv.DictReader(f)}


def prefill(adapter: dict, key: str, ctx: Context, src: dict | None = None) -> dict:
  """A template row from one of the method's own rows: its rating columns as written, an environment that draws its
  situation, its condition, and the motion preset that pictures its hazard there."""
  src = src if src is not None else source_rows(adapter)
  if key not in src:
    raise RowError(f"{key} is not a row of {adapter['prefill']['source']}")
  r, p = src[key], adapter["prefill"]
  row = {"Row ID": key}
  row.update({c["column"]: r[c["source"]] for c in adapter["rating"]})
  os_code, code = r[p["situation"]], r[p["condition"]]
  hz = r[p["hazard"]].split()[0]
  envs = ctx.lib["environments"]
  if not any(os_code in e["os"] for e in envs.values()):
    raise RowError(f"no library environment draws {os_code} yet")
  best = None
  for pid, sc in ctx.presets.items():
    he = ctx.hes.get(sc.get("he", ""))
    if not he or hz not in he["parents"]:
      continue
    env = envs[sc["environment"]]
    score = (os_code in env["os"]) * 2 + (os_code in he["situation"]) + (code in env["conditions"])
    if score and (best is None or score > best[0]):
      best = (score, pid)
  if best is None:
    raise RowError(f"no motion preset pictures {hz} yet")
  pid = best[1]
  pre_env = ctx.presets[pid]["environment"]
  env_id = pre_env if os_code in envs[pre_env]["os"] else next(
    (k for k, e in envs.items() if os_code in e["os"] and _geometry_fits(ctx.presets[pid], e)), pre_env)
  row.update({"Title": f"{r.get('Function name', '')}, {r.get('Guide word name', '')}".strip(", "),
              "Environment": env_id, "Condition": code, "Traffic": DEFAULT, "Motion preset": pid})
  return row
