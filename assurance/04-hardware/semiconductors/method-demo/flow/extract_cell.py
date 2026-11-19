#!/usr/bin/env python3
"""Turn the sky130_fd_sc_hd__dfxtp_1 layout (GDS) into a small JSON the figure generators can read with the standard
library: polygons of the drawn layers, pin labels, and the transistor gates (poly AND diffusion). Needs gdstk."""
import json
import sys

import gdstk

LAYERS = {"nwell": (64, 20), "diff": (65, 20), "poly": (66, 20), "licon": (66, 44), "li1": (67, 20), "mcon": (67, 44), "met1": (68, 20)}
lib = gdstk.read_gds(sys.argv[1])
cell = lib.top_level()[0]
polys = cell.get_polygons()
r = lambda pts: [[round(float(x), 3), round(float(y), 3)] for x, y in pts]
out = {"cell": cell.name, "source": "google/skywater-pdk-libs-sky130_fd_sc_hd @ ac7fb61, Apache-2.0",
       "bbox": r(cell.bounding_box()), "layers": {}, "pins": [], "gates": []}
for name, ld in LAYERS.items():
  out["layers"][name] = [r(p.points) for p in polys if (p.layer, p.datatype) == ld]
gates = gdstk.boolean([p for p in polys if (p.layer, p.datatype) == LAYERS["poly"]],
                      [p for p in polys if (p.layer, p.datatype) == LAYERS["diff"]], "and")
out["gates"] = sorted((r(g.points) for g in gates), key=lambda g: (min(p[0] for p in g), min(p[1] for p in g)))
nwell_y = min(p[1] for poly in out["layers"]["nwell"] for p in poly)
out["nwell_bottom"] = nwell_y
out["pins"] = sorted({(lab.text, round(lab.origin[0], 3), round(lab.origin[1], 3)) for lab in cell.labels
                      if lab.layer == 67 and lab.text in ("D", "CLK", "Q")})
json.dump(out, open(sys.argv[2], "w"), indent=0)
print(cell.name, len(out["gates"]), "transistors")
