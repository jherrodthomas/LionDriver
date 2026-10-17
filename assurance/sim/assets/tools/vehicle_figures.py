#!/usr/bin/env python3
"""Mock-up figures for how the Corolla E210 mesh will be used in the simulation track.

Every figure here is a MOCK-UP: it shows the layout and the quantities a future figure will carry, with illustrative
numbers. None of it is a result, and the SVGs say so in their title, description and footer. The car outline is read
from the purchased GLB (vertex positions only, as a top-down and a side silhouette); the outline is rendered output of
the model and may be published, the model files may not (assurance/sim/assets/README.md).

  python3 assurance/sim/assets/tools/vehicle_figures.py            # writes the SVGs next to the other sim figures
  python3 assurance/sim/assets/tools/vehicle_figures.py --check    # fail if the committed SVGs differ

The silhouette is taken from assurance/sim/assets/1450755-gltf-extended.glb when present (ignored, licensed);
otherwise from the committed figures/corolla-e210-silhouette.json, so CI can run the check without the model.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[1]
GLB = SIM / "assets" / "1450755-gltf-extended.glb"
FIGDIR = SIM / "figures"
SIL = FIGDIR / "corolla-e210-silhouette.json"

STYLE = """<style>
svg { --bg:#ffffff; --ink:#0b0b0b; --ink2:#52514e; --ink3:#8a8984; --grid:#e3e2de; --lane:#3d3c39; --band:#fbe3d6;
      --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#c98500; --s5:#6250d6; --s8:#e34948; --car:#d9d7d1; --mock:#fff3c4; }
@media (prefers-color-scheme: dark) {
  svg { --bg:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --ink3:#8d8c85; --grid:#33322f; --lane:#c3c2b7; --band:#4a2a1c;
        --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#eda100; --s5:#9085e9; --s8:#e66767; --car:#3a3936; --mock:#4a4020; }
}
.bg { fill:var(--bg); } .t { font:12px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.t2 { font:11px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink2); }
.th { font:600 15px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.tb { font:600 12.5px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.tm { font:600 11px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--s4); letter-spacing:.06em; }
.grid { stroke:var(--grid); stroke-width:1; } .axis { stroke:var(--ink3); stroke-width:1; }
.lane { stroke:var(--lane); stroke-width:1.5; } .laned { stroke:var(--lane); stroke-width:1.2; stroke-dasharray:8 6; }
.thr { stroke:var(--s8); stroke-width:1.3; stroke-dasharray:6 4; } .thrn { stroke:var(--s4); stroke-width:1.3; stroke-dasharray:2 3; }
.band { fill:var(--band); } .path { fill:none; stroke:var(--s1); stroke-width:2.2; }
.car { fill:var(--car); stroke:var(--ink2); stroke-width:1.2; } .carl { fill:none; stroke:var(--ink2); stroke-width:1.2; }
.ghost { fill:none; stroke:var(--ink3); stroke-width:1; stroke-dasharray:3 3; }
.fault { stroke:var(--s2); stroke-width:1.5; } .fov { fill:var(--s1); fill-opacity:.12; stroke:var(--s1); stroke-width:1.2; }
.mock { fill:var(--mock); stroke:var(--s4); stroke-width:1; }
.m1 { fill:var(--s2); } .m2 { fill:var(--s5); } .m3 { fill:var(--s3); } .m4 { fill:var(--s4); } .m5 { fill:var(--s1); } .m6 { fill:var(--s8); }
</style>"""

W, H = 1100, 800
MOCK = "MOCK-UP: layout and quantities only, illustrative numbers, not a result"


# ---------------------------------------------------------------------------------------------- silhouette
def _glb_json_and_buffer(p: Path):
  with p.open("rb") as f:
    f.read(12)
    clen, _ = struct.unpack("<II", f.read(8))
    g = json.loads(f.read(clen).decode("utf-8"))
    blen, _ = struct.unpack("<II", f.read(8))
    return g, f.read(blen)


def _positions(g, buf, mesh_idx, edge_step=0.02):
  """Points on the mesh surface: its vertices plus samples along every triangle edge (flat panels such as the roof
  have vertices only at their corners, so vertices alone miss the silhouette). Uses numpy when regenerating."""
  import numpy as np
  pts = []
  for pr in g["meshes"][mesh_idx]["primitives"]:
    a = g["accessors"][pr["attributes"]["POSITION"]]
    bv = g["bufferViews"][a["bufferView"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", 12)
    raw = np.frombuffer(buf, dtype=np.uint8, count=stride * a["count"], offset=off).reshape(a["count"], stride)[:, :12]
    v = raw.copy().view("<f4").reshape(-1, 3).astype(np.float64)
    pts.append(v)
    if "indices" not in pr:
      continue
    ia = g["accessors"][pr["indices"]]
    ibv = g["bufferViews"][ia["bufferView"]]
    ioff = ibv.get("byteOffset", 0) + ia.get("byteOffset", 0)
    dt = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32}[ia["componentType"]]
    idx = np.frombuffer(buf, dtype=dt, count=ia["count"], offset=ioff).astype(np.int64).reshape(-1, 3)
    edges = np.concatenate([idx[:, [0, 1]], idx[:, [1, 2]], idx[:, [2, 0]]])
    edges = np.unique(np.sort(edges, axis=1), axis=0)
    p0, p1 = v[edges[:, 0]], v[edges[:, 1]]
    length = np.linalg.norm(p1 - p0, axis=1)
    n = np.minimum((length / (edge_step * 100)).astype(int), 400)  # positions are in cm here
    for k in range(1, int(n.max()) + 1):
      m = n >= k
      f = (k / (n[m] + 1))[:, None]
      pts.append(p0[m] + (p1[m] - p0[m]) * f)
  return [tuple(p) for p in np.concatenate(pts)]


def _profile(pts, along, across, step=0.02):
  lo: dict[int, float] = {}
  hi: dict[int, float] = {}
  for p in pts:
    k = int(p[along] // step)
    v = p[across]
    lo[k] = min(lo.get(k, v), v)
    hi[k] = max(hi.get(k, v), v)
  ks = sorted(lo)
  return ([[round((k + 0.5) * step, 3), round(lo[k], 3)] for k in ks], [[round((k + 0.5) * step, 3), round(hi[k], 3)] for k in ks])


def extract_silhouette(glb: Path) -> dict:
  """Top-down and side outlines (metres, car frame: x right, y forward is -y in the file, z up) from vertex data."""
  g, buf = _glb_json_and_buffer(glb)
  byname = {n.get("name"): n["mesh"] for n in g["nodes"] if "mesh" in n}
  groups = {
    "body": ["body", "molding", "headlights_plastic", "windows", "window_1", "window_2", "window_3", "window_4", "bottom", "chassis"],
    "mirrors": ["mirror_1", "mirror_2", "mirror_3", "mirror_plastic_left", "mirror_plastic_right"],
    "wheels": ["wheel_1", "wheel_2", "wheels_forward", "tire_1", "tire_2", "tires_forward"],
  }
  P = {k: [tuple(c / 100.0 for c in p) for n in v if n in byname for p in _positions(g, buf, byname[n])] for k, v in groups.items()}
  top_l, top_r = _profile(P["body"] + P["mirrors"], 1, 0)
  body_l, body_r = _profile(P["body"], 1, 0)
  side_b, side_t = _profile(P["body"] + P["wheels"], 1, 2)
  wheels = []
  for name in ("wheels_forward", "wheel_1", "wheel_2"):
    w = [tuple(c / 100.0 for c in p) for p in _positions(g, buf, byname[name])]
    parts = [("L", [p for p in w if p[0] < 0]), ("R", [p for p in w if p[0] > 0])] if name == "wheels_forward" else [("", w)]
    for side, q in parts:
      ys = [p[1] for p in q]; zs = [p[2] for p in q]; xs = [p[0] for p in q]
      wheels.append({"name": (f"front_{side}" if side else ("rear_R" if sum(xs) > 0 else "rear_L")),
                     "x": round((min(xs) + max(xs)) / 2, 3), "y": round((min(ys) + max(ys)) / 2, 3),
                     "z": round((min(zs) + max(zs)) / 2, 3), "r_rim": round((max(zs) - min(zs)) / 2, 3)})
  tz = [p[2] / 100.0 for p in _positions(g, buf, byname["tire_1"])]
  allp = P["body"] + P["mirrors"] + P["wheels"]
  return {
    "source": "3d_molier Toyota Corolla 2020 Simple Interior (TurboSquid 1450755); vertex positions only; metres; "
              "file frame: x right, car faces -y, z up. Rendered output of the model; the model files are licensed.",
    "extent_m": {"min": [round(min(p[i] for p in allp), 3) for i in range(3)], "max": [round(max(p[i] for p in allp), 3) for i in range(3)]},
    "top_outline_with_mirrors": {"left": top_l, "right": top_r},
    "top_outline_body": {"left": body_l, "right": body_r},
    "side_outline": {"bottom": side_b, "top": side_t},
    "wheels": wheels,
    "r_tire": round((max(tz) - min(tz)) / 2, 3),
  }


def load_silhouette() -> dict:
  if GLB.is_file():
    s = extract_silhouette(GLB)
    SIL.write_text(json.dumps(s, separators=(",", ":")) + "\n", encoding="utf-8")
    return s
  return json.loads(SIL.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------------------------- drawing helpers
def _t(x, y, s, cls="t", anchor=None, extra=""):
  a = f' text-anchor="{anchor}"' if anchor else ""
  return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}"{a}{extra}>{escape(s)}</text>'


def _poly(points, cls):
  return f'<polygon class="{cls}" points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in points)}"/>'


def car_top(sil, cx, cy, scale, heading_deg=0.0, mirrors=True, cls="car"):
  """Top-down car outline centred on (cx, cy) in px, car pointing up the page when heading 0, scale px per metre."""
  import math
  o = sil["top_outline_with_mirrors" if mirrors else "top_outline_body"]
  pts = [(x, -y) for y, x in o["left"]] + [(x, -y) for y, x in reversed(o["right"])]  # car frame: forward = +Y page-up
  a = math.radians(heading_deg)
  out = []
  for x, y in pts:
    xr, yr = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
    out.append((cx + xr * scale, cy - yr * scale))
  return _poly(out, cls)


def car_side(sil, x0, ground_y, scale, cls="car"):
  """Side outline, car facing left, rear at x0 px; returns svg and the wheel circles."""
  o = sil["side_outline"]
  top = [(x0 + (2.4 - (-y)) * 0 + (y - sil["extent_m"]["min"][1]) * scale, ground_y - z * scale) for y, z in o["top"]]
  bot = [(x0 + (y - sil["extent_m"]["min"][1]) * scale, ground_y - z * scale) for y, z in o["bottom"]]
  # the file's -y is the front; draw front on the left: mirror by mapping y -> (y - ymin) and flipping around the span
  span = sil["extent_m"]["max"][1] - sil["extent_m"]["min"][1]
  top = [(x0 + (span - (p[0] - x0) / scale) * scale, p[1]) for p in top]
  bot = [(x0 + (span - (p[0] - x0) / scale) * scale, p[1]) for p in bot]
  body = _poly(top + list(reversed(bot)), cls)
  wheels = ""
  for w in sil["wheels"]:
    if w["name"].endswith("_R"):
      continue
    wx = x0 + (span - (w["y"] - sil["extent_m"]["min"][1])) * scale
    wheels += f'<circle class="carl" cx="{wx:.1f}" cy="{ground_y - w["z"] * scale:.1f}" r="{sil["r_tire"] * scale:.1f}"/>'
    wheels += f'<circle class="carl" cx="{wx:.1f}" cy="{ground_y - w["z"] * scale:.1f}" r="{w["r_rim"] * scale:.1f}"/>'
  return body + wheels


def frame(title, desc):
  return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">',
          f"<title id=\"t\">{escape(title)}</title>", f"<desc id=\"d\">{escape(MOCK + '. ' + desc)}</desc>", STYLE,
          f'<rect class="bg" width="{W}" height="{H}"/>',
          f'<rect class="mock" x="20" y="14" width="{W - 40}" height="26" rx="4"/>', _t(W / 2, 32, MOCK, "tm", "middle"),
          _t(30, 66, title, "th")]


def footer(out, text):
  out.append(_t(30, H - 18, text, "t2"))
  out.append("</svg>")
  return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------------------------- figure 1: fault case, top-down
def fig_fault_topdown(sil) -> str:
  out = frame("Mock-up 1: fault-injection case with the reference-car outline (layer 1, replaces the ego rectangle)",
              "Top-down lane view of a loss-of-assist case in a highway curve: the Corolla outline at fault onset, at the "
              "0.5 s SG-01 FTTI, at the driver cue and at the correction, with the lane lines, the body-edge thresholds and "
              "the lateral-deviation plot below. Quantities come from the plant results tables when the figure is generated "
              "for real.")
  # lane view: 48 m of road, 3.7 m lane, 20 px per metre; illustrative drift capped near the 3.7 m threshold
  sx, sy, s = 60, 110, 20.0
  roadw = 3.7 * s
  lane_y = sy + 1.6 * roadw
  def drift(x):
    if x < 8: return 0.0
    if x <= 34: return min(1.05, 0.0016 * (x - 8) ** 2)
    return max(0.0, 1.05 - 0.009 * (x - 34) ** 2)
  out.append(f'<rect class="band" x="{sx}" y="{lane_y - roadw / 2:.1f}" width="{48 * s:.1f}" height="{roadw:.1f}" fill-opacity=".35"/>')
  for k in (-1.5, -0.5, 0.5, 1.5):
    cls = "lane" if abs(k) == 1.5 else "laned"
    out.append(f'<line class="{cls}" x1="{sx}" y1="{lane_y + k * roadw:.1f}" x2="{sx + 48 * s:.1f}" y2="{lane_y + k * roadw:.1f}"/>')
  out.append(_t(sx + 48 * s + 8, lane_y + 4, "ego lane 3.7 m", "t2"))
  pts = [(sx + x * s, lane_y - drift(x) * s) for x in range(0, 49)]
  out.append('<polyline class="path" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + '"/>')
  out.append(f'<line class="fault" x1="{sx + 8 * s:.1f}" y1="{lane_y - roadw * 1.55:.1f}" x2="{sx + 8 * s:.1f}" y2="{lane_y + roadw * .6:.1f}"/>')
  out.append(_t(sx + 8 * s + 4, lane_y - roadw * 1.55 + 10, "fault onset t = 0", "t2"))
  stations = [(8, "t = 0", False), (20, "0.5 s FTTI", False), (34, "driver cue 1.5 s", True), (45, "correction", True)]
  for x, label, ghost in stations:
    out.append(car_top(sil, sx + x * s, lane_y - drift(x) * s, s, heading_deg=-90 + (5 if 8 < x <= 34 else -4 if x > 34 else 0), cls="ghost" if ghost else "car"))
    out.append(_t(sx + x * s, lane_y + roadw * 0.85, label, "t2", "middle"))
  out.append(_t(sx, sy - 10, "Lane view, 48 m, speed 110 km/h (ODD-H bound); outline from the purchased mesh, 1.78 m body, 2.07 m with mirrors", "tb"))
  # deviation plot
  px, py, pw, ph = 60, 470, 980, 240
  out.append(f'<rect class="band" x="{px}" y="{py}" width="{0.5 / 4.5 * pw:.1f}" height="{ph}"/>')
  for v, cls, lab in ((0.61, "thr", "body edge at lane line, 3.0 m lane: 0.61 m"), (0.96, "thrn", "3.7 m lane: 0.96 m")):
    y = py + ph - v / 1.4 * ph
    out.append(f'<line class="{cls}" x1="{px}" y1="{y:.1f}" x2="{px + pw}" y2="{y:.1f}"/>'); out.append(_t(px + pw - 4, y - 4, lab, "t2", "end"))
  out.append(f'<line class="axis" x1="{px}" y1="{py + ph}" x2="{px + pw}" y2="{py + ph}"/><line class="axis" x1="{px}" y1="{py}" x2="{px}" y2="{py + ph}"/>')
  curve = []
  for i in range(0, 451):
    t = i / 100
    d = 0.0 if t < 0.1 else min(1.3, 0.55 * (t - 0.1) ** 2)
    if t > 1.6:
      d = min(1.3, 0.55 * 1.5 ** 2) - 0.9 * (t - 1.6) ** 2
    curve.append((px + t / 4.5 * pw, py + ph - max(0, d) / 1.4 * ph))
  out.append('<polyline class="path" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in curve) + '"/>')
  for t, lab in ((0, "0"), (0.5, "0.5 FTTI"), (1, "1"), (1.5, "1.5"), (2, "2"), (3, "3"), (4, "4 s")):
    x = px + t / 4.5 * pw
    out.append(f'<line class="grid" x1="{x:.1f}" y1="{py}" x2="{x:.1f}" y2="{py + ph}"/>'); out.append(_t(x, py + ph + 16, lab, "t2", "middle"))
  out.append(_t(px - 6, py + 10, "m", "t2", "end")); out.append(_t(px - 6, py + ph, "0", "t2", "end"))
  out.append(_t(px, py - 10, "Lateral deviation of the body edge against time; the orange band is the 0.5 s FTTI of SG-01", "tb"))
  out.append(_t(px + 0.5 / 4.5 * pw + 6, py + 16, "deviation at FTTI: the number the result table reports", "t2"))
  return footer(out, "Generated by assurance/sim/assets/tools/vehicle_figures.py. Mock-up of the layer-1 figure once plant/report.py "
                     "draws the mesh outline instead of a rectangle; the trajectory shown is illustrative. Synthetic data, no evidence credit.")


# ---------------------------------------------------------------------------------------------- figure 2: layer-3 frame
def fig_metadrive_frame(sil) -> str:
  out = frame("Mock-up 2: a layer-3 MetaDrive clip frame (third-person view, instrumented)",
              "What one frame of a MetaDrive closed-loop clip would show: the scenario in plan view with the Corolla and a lead "
              "vehicle, and an instrument strip with scenario ID, time, speed, engaged state, lateral error, alert state and the "
              "outcome class the WP-V-03 pass criteria use. openpilot never sees the mesh; it is drawn for the viewer.")
  # plan view panel
  vx, vy, vw, vh = 60, 95, 620, 420
  out.append(f'<rect class="bg" x="{vx}" y="{vy}" width="{vw}" height="{vh}" stroke="var(--grid)"/>')
  s = 14.0; lane = 3.7 * s; cy = vy + vh / 2
  for k in (-1.5, -0.5, 0.5, 1.5):
    cls = "lane" if abs(k) == 1.5 else "laned"
    out.append(f'<line class="{cls}" x1="{vx}" y1="{cy + k * lane:.1f}" x2="{vx + vw}" y2="{cy + k * lane:.1f}"/>')
  out.append(car_top(sil, vx + 170, cy, s, heading_deg=-90))
  out.append(_t(vx + 170, cy + lane * 0.75, "ego: Corolla E210 mesh", "t2", "middle"))
  # lead vehicle as a plain box (not the licensed mesh)
  out.append(f'<rect class="carl" x="{vx + 470:.1f}" y="{cy - 0.9 * s:.1f}" width="{4.5 * s:.1f}" height="{1.8 * s:.1f}" rx="6"/>')
  out.append(_t(vx + 470 + 2.25 * s, cy + lane * 0.75, "lead vehicle (KS-05 cut-in / braking)", "t2", "middle"))
  out.append(f'<line class="thr" x1="{vx + 170 + 2.33 * s:.1f}" y1="{cy - lane * 1.2:.1f}" x2="{vx + 470:.1f}" y2="{cy - lane * 1.2:.1f}"/>')
  out.append(_t((vx + 170 + 2.33 * s + vx + 470) / 2, cy - lane * 1.2 - 6, "gap 23.4 m (time gap 0.77 s)", "t2", "middle"))
  out.append(_t(vx, vy - 10, "Plan view of KS-05 at t = 12.4 s from MetaDrive's state (camera path unchanged)", "tb"))
  # instrument strip
  ix, iy, iw, ih = 700, 95, 340, 420
  out.append(f'<rect class="bg" x="{ix}" y="{iy}" width="{iw}" height="{ih}" stroke="var(--grid)"/>')
  rows = [("Scenario", "KS-05 lead brakes 4 m/s²"), ("Configuration", "CFG-001, Chill mode"), ("t", "12.40 s"), ("v", "27.8 m/s (100 km/h)"),
          ("Engaged", "yes, lateral + long."), ("Lateral error", "0.12 m"), ("Accel request", "−2.9 m/s²"), ("Lead gap", "23.4 m, 0.77 s"),
          ("Alert", "none"), ("Panda", "all frames allowed"), ("Outcome class", "pending")]
  for i, (k, v) in enumerate(rows):
    y = iy + 28 + i * 34
    out.append(_t(ix + 12, y, k, "t2")); out.append(_t(ix + iw - 12, y, v, "tb", "end"))
  out.append(_t(ix, iy - 10, "Instrument strip", "tb"))
  # outcome classes legend
  ly = 560
  out.append(_t(60, ly, "Outcome classes a clip is scored against at its end (WP-V-03 §4 pass criteria, per scenario family)", "tb"))
  classes = [("m3", "A pass", "stays in lane, min gap ≥ 1.0 s, no driver intervention"), ("m4", "B degraded", "alert raised and driver takes over inside the FTTI"),
             ("m1", "C fail", "lane departure, gap < 0.5 s, or late/no alert"), ("m5", "D excluded", "sim artefact or outside ODD; listed, not scored")]
  for i, (cls, name, text) in enumerate(classes):
    y = ly + 28 + i * 26
    out.append(f'<circle class="{cls}" cx="70" cy="{y - 4}" r="6"/>'); out.append(_t(86, y, name, "tb")); out.append(_t(190, y, text, "t2"))
  out.append(_t(60, ly + 150, "Credit only per scenario family after the WP-V-02 §5.3 fidelity case (DQ-139); until then clips rank risks and guide tests.", "t2"))
  return footer(out, "Generated by assurance/sim/assets/tools/vehicle_figures.py. Layer 3 is planned (backlog item 3); numbers are illustrative. "
                     "The lead vehicle is a box on purpose: only the ego uses the licensed mesh. Synthetic data, no evidence credit.")


# ---------------------------------------------------------------------------------------------- figure 3: camera geometry
def fig_camera_geometry(sil) -> str:
  out = frame("Mock-up 3: device camera geometry on the reference car (side silhouette)",
              "Side silhouette of the Corolla from the mesh with the comma device at the windshield, its vertical field of view, "
              "the hood occlusion distance on flat ground, and a following vehicle's sight line. Device position and angles are "
              "to be measured on the reference car; the values shown are placeholders.")
  s = 62.0; gy = 400; x0 = 340
  span = sil["extent_m"]["max"][1] - sil["extent_m"]["min"][1]
  out.append(f'<line class="axis" x1="60" y1="{gy}" x2="{W - 60}" y2="{gy}"/>')
  out.append(car_side(sil, x0, gy, s))
  # device: near the top of the windshield, about 1.0 m back from the front, 1.25 m high (placeholders)
  dx = x0 + (1.95) * s; dz = gy - 1.26 * s
  out.append(f'<rect class="m5" x="{dx - 6:.1f}" y="{dz - 5:.1f}" width="12" height="10" rx="2"/>')
  out.append(_t(dx + 12, dz - 8, "comma device (position: placeholder, to measure)", "t2"))
  # vertical FOV cone, pitched slightly down; hood occlusion where lower ray meets ground
  import math
  pitch = math.radians(-4); half = math.radians(29)
  L_up = 4.5
  ux, uy = dx - L_up * s * math.cos(pitch + half), dz - L_up * s * math.sin(pitch + half)
  L_dn = abs((dz - gy) / (s * math.sin(pitch - half)))
  lx, ly_ = dx - L_dn * s * math.cos(pitch - half), gy
  out.append(f'<polygon class="fov" points="{dx:.1f},{dz:.1f} {ux:.1f},{uy:.1f} {lx:.1f},{ly_:.1f}"/>')
  out.append(_t(ux + 6, uy + 4, "vertical field of view (placeholder 58°, pitch −4°)", "t2"))
  gx = dx - ((dz - gy) / (s * math.sin(pitch - half))) * s * math.cos(pitch - half) * -1
  gx = dx - abs((dz - gy) / (s * math.sin(pitch - half))) * s * math.cos(pitch - half)
  out.append(f'<line class="thr" x1="{gx:.1f}" y1="{gy}" x2="{gx:.1f}" y2="{gy - 30}"/>')
  front_x = x0 + span * s * 0 + 0  # front of car is at x0 (car faces left)
  out.append(f'<line class="thrn" x1="{x0:.1f}" y1="{gy + 26}" x2="{gx:.1f}" y2="{gy + 26}"/>')
  out.append(_t((x0 + gx) / 2, gy + 44, "ground first seen at d_hood ≈ 4.2 m ahead of the bumper (placeholder)", "t2", "middle"))
  out.append(_t(60, 95, "Side view, front to the left, 1 m grid; silhouette from the purchased mesh (18-inch wheels: sport trim)", "tb"))
  for m in range(0, 16):
    x = 60 + m * s
    out.append(f'<line class="grid" x1="{x:.1f}" y1="{gy - 2.2 * s:.1f}" x2="{x:.1f}" y2="{gy}"/>')
  # following vehicle sight line (rear camera / driver mirror): box behind
  bx = x0 + span * s + 2.5 * s
  out.append(f'<rect class="carl" x="{bx:.1f}" y="{gy - 1.45 * s:.1f}" width="{2.6 * s:.1f}" height="{1.45 * s:.1f}" rx="8"/>')
  out.append(_t(bx + 1.3 * s, gy + 18, "following vehicle at 2.5 m (SG-03/SG-04 cases)", "t2", "middle"))
  out.append(f'<line class="laned" x1="{x0 + span * s - 0.3 * s:.1f}" y1="{gy - 1.0 * s:.1f}" x2="{bx:.1f}" y2="{gy - 1.1 * s:.1f}"/>')
  # what the figure is for
  ty = 500
  out.append(_t(60, ty, "What this figure will carry once the device position is measured (WP-C-01 OI, WP-S-05 HSI):", "tb"))
  for i, line in enumerate(["camera height and pitch on CFG-001, with the mount tolerance the HSI allows;",
                            "hood occlusion distance d_hood and the nearest lane-line point visible, used by the SOTIF triggering conditions (WP-C-06);",
                            "the driver-monitoring camera's view of the driver (not drawn here) and the following-vehicle gaps WP-S-04 §3.3 budgets."]):
    out.append(_t(80, ty + 24 + i * 22, "• " + line, "t2"))
  return footer(out, "Generated by assurance/sim/assets/tools/vehicle_figures.py. Device position, pitch and field of view are placeholders "
                     "until measured on the reference car (WP-S-04 M-01 family). Synthetic data, no evidence credit.")


# ---------------------------------------------------------------------------------------------- main
FIGS = {
  "fig-sim-mock-01-fault-topdown.svg": fig_fault_topdown,
  "fig-sim-mock-02-metadrive-frame.svg": fig_metadrive_frame,
  "fig-sim-mock-03-camera-geometry.svg": fig_camera_geometry,
}


def main(argv: list[str]) -> int:
  check = "--check" in argv
  sil = load_silhouette()
  FIGDIR.mkdir(parents=True, exist_ok=True)
  stale = []
  for name, fn in FIGS.items():
    svg = fn(sil)
    p = FIGDIR / name
    if check:
      if not p.is_file() or p.read_text(encoding="utf-8") != svg:
        stale.append(name)
    else:
      p.write_text(svg, encoding="utf-8", newline="\n")
      print("wrote", p.relative_to(SIM.parents[1]))
  if check and stale:
    print("stale:", ", ".join(stale))
    return 1
  if check:
    print("vehicle figures OK")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
