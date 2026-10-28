#!/usr/bin/env python3
"""Build a dated, versioned snapshot of the safety case: one self-contained HTML document plus a manifest.

The snapshot is what the README button downloads (as PDF, printed from this HTML by
render_snapshot.cjs in the safety-case-snapshot workflow). Every value in it is read from the
records, the work products and git; nothing is typed here except headings and fixed notices.

Usage:
  python3 assurance/case-records/tools/build_snapshot.py [--out DIR] [--previous MANIFEST] [--tag bl-NNN] [--copy CC-YYYY-NNN]

  --out       output directory (default build/snapshot)
  --previous  manifest.json of the previous snapshot, for "changes since the previous snapshot"
  --tag       build a baseline release for this tag instead of a living snapshot
  --copy      stamp the snapshot as this controlled copy; the copy must already be in
              assurance/case-records/distribution.yaml (distribution.py), so no copy exists without its record

Outputs: <out>/LionDriver-safety-case.html and <out>/manifest.json. The output depends only on the
commit and the previous manifest (the date is the commit date), so a rebuild gives the same bytes.

The records are validated first; invalid records produce no snapshot.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from html import escape
from pathlib import Path

from caselib import ASSURANCE_DIR, CASE_DIR, REPO_ROOT, load_case, release_status, summarize, validate

sys.path.insert(0, str(ASSURANCE_DIR / "trace" / "tools"))
import vmodel
import distribution
import snapshot_pages as pages

GENERATOR_VERSION = "1.0"
REPO_SLUG = "jherrodthomas/LionDriver"
RELEASES_URL = f"https://github.com/{REPO_SLUG}/releases"
HTML_NAME = "LionDriver-safety-case.html"
PDF_NAME = "LionDriver-safety-case.pdf"
SUBMODULES = ("panda", "opendbc_repo")
WP_M_02 = ASSURANCE_DIR / "01-management" / "WP-M-02-safety-plan.md"
WP_M_01 = ASSURANCE_DIR / "01-management" / "WP-M-01-assurance-strategy.md"
WP_M_06 = next((ASSURANCE_DIR / "01-management").glob("WP-M-06-*.md"))
WP_C_01 = ASSURANCE_DIR / "02-concept" / "WP-C-01-item-definition.md"
WP_K_01 = ASSURANCE_DIR / "10-safety-case" / "WP-K-01-safety-case.md"
WP_P_04 = ASSURANCE_DIR / "07-supporting" / "WP-P-04-documentation-management.md"
REFERENCE_CFG = "CFG-001"
REFERENCE_BUILD = "reference build (LIONDRIVER_REFERENCE=1)"
CONFIRMATION_DIR = ASSURANCE_DIR / "10-safety-case" / "confirmation"
GSN_DIR = ASSURANCE_DIR / "10-safety-case" / "gsn"
FIGURES = [
  ("How the safety case works", CASE_DIR / "figures" / "fig-case-1-how-it-works.svg"),
  ("Element hierarchy of LD-SDA (WP-C-01 Figure 3-1)", ASSURANCE_DIR / "02-concept" / "figures" / "fig-3-1-element-hierarchy.svg"),
]
AI_MARKERS = ("claude", "noreply@anthropic.com")
ABBREVIATIONS = [
  ("AoU", "assumption of use"), ("ASIL", "automotive safety integrity level"), ("BL", "engineering baseline"),
  ("CR", "confirmation review"), ("DF", "defeater: known counter-evidence against a claim"), ("FSA", "functional safety assessment"),
  ("GSN", "goal structuring notation"), ("I0…I3", "independence level of a reviewer (ISO 26262-2 Table 1)"),
  ("RACI", "responsible, accountable, consulted, informed"), ("RR", "review record"), ("SC", "safety case snapshot"),
  ("SG", "safety goal"), ("Sn", "evidence item (solution)"), ("TBD", "to be determined"),
]


# ---------------------------------------------------------------- sources

def git(*args: str) -> str:
  env = {**os.environ, "TZ": "UTC"}
  return subprocess.run(["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True, env=env).stdout.strip()


def plain(md: str) -> str:
  """Markdown cell to plain text: links to their text, no backticks or emphasis."""
  md = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)
  return md.replace("`", "").replace("**", "").replace("\\|", "|").strip()


def md_table(path: Path, heading: str) -> list[dict]:
  """The first table after the heading line that starts with `heading`, as a list of row dicts."""
  lines = path.read_text(encoding="utf-8").splitlines()
  start = next(i for i, ln in enumerate(lines) if ln.startswith(heading))
  rows, header = [], None
  for ln in lines[start + 1:]:
    if ln.startswith("#"):
      break
    if not ln.startswith("|"):
      if header:
        break
      continue
    cells = [c.strip() for c in re.split(r"(?<!\\)\|", ln.strip())[1:-1]]
    if header is None:
      header = cells
    elif not set("".join(cells)) <= set("-: "):
      rows.append(dict(zip(header, cells, strict=False)))
  return rows


def wp_version(path: Path) -> str:
  """The version in a work product's control header ("| Version | 0.4 (...)" gives "0.4")."""
  m = re.search(r"^\|\s*Version\s*\|\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)", path.read_text(encoding="utf-8"), re.M)
  if not m:
    raise SystemExit(f"no version in the control header of {path.name}")
  return m.group(1)


def retention(kind: str) -> str:
  """The WP-P-04 §10 retention period for this kind of snapshot."""
  key = "Work products, review" if kind == "baseline release" else "Records of unreleased baselines"
  row = next((r for r in md_table(WP_P_04, "## 10.") if plain(r["Record"]).startswith(key)), None)
  if row is None:
    raise SystemExit(f"WP-P-04 §10 has no retention row starting {key!r}")
  return plain(row["Retention"])


def identity(tag: str | None, previous: dict | None, copy: dict | None = None) -> dict:
  commit = git("rev-parse", "HEAD")
  date = git("-c", "log.showSignature=false", "log", "-1", "--format=%cd", "--date=format-local:%Y-%m-%d")
  issued = git("-c", "log.showSignature=false", "log", "-1", "--format=%cd", "--date=format-local:%Y-%m-%d %H:%M") + " UTC"
  pins = {}
  for name in SUBMODULES:
    entry = git("ls-tree", "HEAD", name).split()
    pins[name] = entry[2][:7] if len(entry) >= 3 else "unknown"
  if tag:
    if not re.fullmatch(r"bl-[0-9]{3}", tag):
      raise SystemExit(f"--tag must look like bl-NNN, got {tag!r}")
    sid, kind = f"{tag.upper()}-{commit[:7]}", "baseline release"
  else:
    sid, kind = f"SC-{date.replace('-', '.')}-{commit[:7]}", "living snapshot"
  return {"id": sid, "kind": kind, "tag": tag, "date": date, "issued": issued, "commit": commit, "commit_short": commit[:7],
          "pins": pins, "version": wp_version(WP_K_01), "retention": retention(kind), "copy": copy,
          "previous": previous["snapshot"]["id"] if previous else None,
          "previous_commit": previous["snapshot"]["commit"] if previous else None}


def copy_line(ident: dict) -> str:
  c = ident["copy"]
  if c:
    return f"Controlled copy {c['id']} for {c['recipient']} ({c['purpose']}), issued by @{c['issued_by']} {c['issued_at']}"
  return "Uncontrolled copy: public download, not recorded"


def running_header(ident: dict, rs: dict, s: dict, cfg: dict) -> dict:
  """Header and footer of every printed page (render_snapshot.cjs): identity, status, configuration and copy."""
  bl = s["baseline"]
  copy = f"CONTROLLED COPY {ident['copy']['id']}" if ident["copy"] else "UNCONTROLLED"
  pins = " · ".join(f"{k.replace('_repo', '')} {v}" for k, v in ident["pins"].items())
  short_cfg = re.sub(r"\s*\(reference configuration\)", "", cfg["title"]).replace("Toyota Safety Sense", "TSS")
  short_cfg = re.sub(r",\s*[^,(]*\((\w+)\),", r" \1", short_cfg)
  return {
    "left": f"WP-K-01 Safety case · v{ident['version']} · {ident['id']}",
    "right": f"{rs['label']} · PUBLIC · {copy}",
    "footer": f"{cfg['id']} {short_cfg} · {REFERENCE_BUILD} · liondriver-dev @ {ident['commit_short']} · {pins} · "
              f"baseline {bl['id']} ({bl['lifecycle_status'].replace('-', ' ')})",
    "footer2": f"Issued {ident['issued']} · Retain: {ident['retention']} (WP-P-04 §10)",
    "footer3": copy_line(ident),
    "verify": RELEASES_URL,
  }


def changes(previous_commit: str | None) -> list[dict]:
  rng = [f"{previous_commit}..HEAD"] if previous_commit else ["-n", "6"]
  out = git("log", *rng, "--format=%h%x1f%cd%x1f%s", "--date=format-local:%Y-%m-%d", "--", "assurance")
  return [dict(zip(("commit", "date", "subject"), ln.split("\x1f"), strict=False)) for ln in out.splitlines() if ln]


def history() -> list[dict]:
  out = git("log", "--format=%h%x1f%cd%x1f%s", "--date=format-local:%Y-%m-%d", "--", "assurance")
  return [dict(zip(("commit", "date", "subject"), ln.split("\x1f"), strict=False)) for ln in out.splitlines() if ln]


def contributors() -> dict:
  out = git("log", "--format=%an%x1f%(trailers:key=Co-Authored-By,valueonly,separator=%x1e)", "--", "assurance")
  first = git("log", "--reverse", "--format=%cd", "--date=format-local:%Y-%m-%d", "--", "assurance").splitlines()
  people: dict[str, int] = {}
  ai_authored = ai_involved = total = 0
  for ln in out.splitlines():
    author, _, trailers = ln.partition("\x1f")
    total += 1
    is_ai_author = any(m in author.lower() for m in AI_MARKERS)
    if is_ai_author:
      ai_authored += 1
    else:
      people[author] = people.get(author, 0) + 1
    if is_ai_author or any(m in trailers.lower() for m in AI_MARKERS):
      ai_involved += 1
  return {"since": first[0] if first else None, "total": total, "people": sorted(people.items(), key=lambda kv: -kv[1]),
          "ai_authored": ai_authored, "ai_involved": ai_involved}


def review_records() -> list[dict]:
  out = []
  for path in sorted(ASSURANCE_DIR.glob("**/reviews/RR-*.md"), key=lambda p: p.stem):
    text = path.read_text(encoding="utf-8")
    title = text.splitlines()[0].lstrip("# ").split("—", 1)[-1].strip()
    indep = re.search(r"\|\s*Reviewer\(s\)[^|]*\|[^\n]*?\b(I[0-3])\b", text)
    date = re.search(r"^\|\s*Date\(s\)\s*\|\s*([0-9-]{10})", text, re.M)
    out.append({"id": path.stem, "object": title, "independence": indep.group(1) if indep else "not stated",
                "date": date.group(1) if date else "", "record": path.relative_to(REPO_ROOT).as_posix()})
  return out


def confirmation_measures() -> list[dict]:
  done = {p.stem.split("-WP-")[0] for p in CONFIRMATION_DIR.glob("*.md") if p.name != "README.md"}
  rows = []
  for row in md_table(WP_M_06, "## 9."):
    for mid in re.findall(r"\b(CR-[0-9]{2}|FSA-[A-Z0-9]+|AUD-[0-9]+|SR-[0-9]{2}|CS-I1)\b", row["Confirmation measures due"]):
      rows.append({"id": mid, "gate": row["Gate"], "performed": mid in done})
  return rows


def gate_skeletons() -> list[str]:
  return [p.stem.split("-")[0] for p in sorted((ASSURANCE_DIR / "10-safety-case" / "gates" / "skeletons").glob("G*-skeleton.md"))]


# ---------------------------------------------------------------- html helpers

def e(x) -> str:
  return escape(str(x))


def chip(text: str, tone: str) -> str:
  return f'<span class="chip {tone}">{e(text)}</span>'


def table(head: list[str], rows: list[list[str]], cls: str = "tbl") -> str:
  th = "".join(f"<th>{e(h)}</th>" for h in head)
  body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
  return f'<table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'


def img(path: Path, alt: str) -> str:
  data = base64.b64encode(path.read_bytes()).decode()
  return f'<img class="fig" alt="{e(alt)}" src="data:image/svg+xml;base64,{data}">'


def figure(path: Path, number: int, caption: str) -> str:
  return f'<figure>{img(path, caption)}<figcaption>Figure {number}. {e(caption)}.</figcaption></figure>'


def svg_img(svg: str, alt: str, cls: str = "fig") -> str:
  """A generated SVG inlined like img(): base64 data URI, so the snapshot stays one self-contained file."""
  data = base64.b64encode(svg.encode()).decode()
  return f'<img class="{cls}" alt="{e(alt)}" src="data:image/svg+xml;base64,{data}">'


def v_figure(dr: vmodel.Drawing, number: int, caption: str) -> str:
  return f'<figure>{svg_img(vmodel.svg(dr), dr.desc)}<figcaption>Figure {number}. {e(caption)}.</figcaption></figure>'


def v_signature(vd: vmodel.Data) -> str:
  """The cover caption, worded from the data: what has run and passed, and whether any work product is approved."""
  cases, run, passed = sum(vd.cases.values()), sum(vd.executed.values()), sum(vd.passed.values())
  approved = sum(1 for s_, _ in vd.register.values() if s_ in ("A", "B"))
  if not run:
    state = "nothing verified yet" if not approved else f"{approved} work products approved, nothing verified yet"
  else:
    state = f"{passed} of {cases} cases passed"
  return f"status signature · {state}"


def bar(parts: list[tuple[int, str]], total: int) -> str:
  segs = "".join(f'<i style="width:{100 * n / total:.2f}%;background:{c}"></i>' for n, c in parts if n and total)
  return f'<div class="track">{segs}</div>'


REVIEW_TONE = {"accepted": "ok", "in-review": "am", "changes-requested": "am", "rejected": "red", "not-reviewed": "g"}
EVID_TONE = {"available": "ok", "partial": "am", "missing": "red"}

CSS = """
@page{size:A4;margin:20mm 16mm 24mm}
@page land{size:A4 landscape;margin:16mm 16mm 22mm}
:root{--ink:#0F172A;--mut:#475569;--line:#E2E8F0;--b2:#CBD5E1;--or:#C2410C;--orf:#FFF7ED;--amf:#FFFBEB;--red:#D2553F}
*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;font-family:Inter,"Segoe UI",Helvetica,Arial,sans-serif;color:var(--ink);font-size:9.6pt;line-height:1.45}
main{max-width:180mm;margin:0 auto}
.mono,code{font-family:"JetBrains Mono",Menlo,Consolas,monospace;font-size:.92em}
.wm{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%) rotate(-32deg);font-size:120pt;font-weight:800;
  color:rgba(194,65,12,.05);letter-spacing:.08em;white-space:nowrap;pointer-events:none;z-index:-1}
section{page-break-before:always;break-before:page}
section.land{page:land;max-width:none}
section.land figure{break-before:page}
section.land h1+figure,section.land .lead+figure{break-before:auto}
.nw{white-space:nowrap}
h1{font-size:19pt;margin:0 0 2mm;letter-spacing:-.01em}
h2{font-size:12pt;margin:6mm 0 2mm}
.lead{color:var(--mut);font-size:9pt;margin:0 0 3mm}
.sect{font-size:7.6pt;font-weight:700;letter-spacing:.1em;color:#64748B;margin:6mm 0 2mm;text-transform:uppercase;break-after:avoid;page-break-after:avoid}
.chip{display:inline-block;font-size:7.4pt;font-weight:700;border-radius:8px;padding:0 6px;white-space:nowrap;line-height:1.6}
.chip.am{background:var(--amf);color:#92400E;border:1px solid #FCD34D}.chip.red{background:#FEF2F2;color:#991B1B;border:1px solid #FCA5A5}
.chip.g{background:#F1F5F9;color:#334155;border:1px solid var(--b2)}.chip.ok{background:#ECFDF5;color:#065F46;border:1px solid #6EE7B7}
.tbl{width:100%;border-collapse:collapse;font-size:8.4pt;margin:1mm 0 2mm}
.tbl th{text-align:left;font-size:7pt;letter-spacing:.06em;color:#64748B;font-weight:700;border-bottom:1.2px solid var(--b2);
  padding:1.4mm 1.2mm;text-transform:uppercase}
.tbl td{padding:1.3mm 1.2mm;border-bottom:1px solid #F1F5F9;vertical-align:top}
.tbl tr{break-inside:avoid}
.box{border:1px solid var(--line);border-radius:6px;padding:3mm 3.5mm;font-size:8.6pt;color:#334155;margin:2mm 0}
.box.or{border-color:#FDBA74;background:var(--orf);color:#7C2D12}
.tbd{color:#991B1B;font-weight:700}
.cover{height:250mm;position:relative;display:flex;flex-direction:column}
.brand{display:flex;align-items:center;gap:3mm}
.logo{width:9mm;height:9mm;border-radius:2mm;background:linear-gradient(135deg,#C2410C,#B45309);color:#fff;font-weight:800;font-size:13pt;display:flex;align-items:center;justify-content:center}
.kicker{font-size:8.5pt;font-weight:700;letter-spacing:.16em;color:var(--or);margin-top:30mm}
.ttl{font-size:34pt;font-weight:800;line-height:1.05;margin:2mm 0;letter-spacing:-.015em}
.rule{height:3px;width:20mm;background:var(--or);border-radius:2px;margin:7mm 0}
.idg{display:grid;grid-template-columns:42mm 1fr;row-gap:2.6mm;font-size:10pt}
.idg div:nth-child(odd){color:var(--mut)}
.banner{margin-top:8mm;border:1.5px solid var(--or);background:var(--orf);border-radius:2mm;padding:3mm 4mm;display:flex;gap:4mm;align-items:center}
.banner.ok{border-color:#2E9E6A;background:#ECFDF5}
.pill{background:var(--or);color:#fff;font-weight:800;font-size:9pt;letter-spacing:.08em;padding:1mm 3.5mm;border-radius:4mm}
.banner.ok .pill{background:#2E9E6A}
.std{display:flex;gap:2mm;flex-wrap:wrap;margin-top:7mm}
.std span{font-size:7.6pt;border:1px solid var(--b2);border-radius:4mm;padding:.6mm 3mm;color:#334155}
.cfoot{margin-top:auto;border-top:1px solid var(--line);padding-top:3mm;font-size:7.6pt;color:var(--mut)}
.gates{display:grid;grid-template-columns:repeat(7,1fr);gap:2mm}
.gate{border:1px solid var(--b2);background:#F8FAFC;border-radius:1.5mm;padding:1.5mm;text-align:center;font-size:7.2pt;color:var(--mut)}
.gate b{display:block;font-size:11pt;color:var(--ink)}
.gate.pass{border-color:#6EE7B7;background:#ECFDF5;color:#065F46}
.gate.block{border-color:#FCA5A5;background:#FEF2F2;color:#991B1B}
.toc a{display:flex;justify-content:space-between;color:var(--ink);text-decoration:none;border-bottom:1px dotted var(--b2);padding:1.1mm 0;font-size:9pt}
.toc a.fm{color:var(--mut)}
.raci{border-collapse:collapse;width:100%;font-size:8pt}
.raci th{font-size:7pt;color:#64748B;padding:1.2mm .8mm;border-bottom:1.2px solid var(--b2)}
.raci td{padding:1mm .8mm;border-bottom:1px solid #F1F5F9;text-align:center}
.raci td:first-child,.raci th:first-child{text-align:left}
.raci i{display:inline-block;min-width:8mm;border-radius:1mm;font-style:normal;font-weight:700;font-size:7.2pt;padding:0 1mm}
.rA{background:#0F172A;color:#fff}.rR{background:#C2410C;color:#fff}.rC{background:#E0F2F1;color:#0F766E}.rI{background:#F1F5F9;color:#64748B}
.rAR{background:linear-gradient(90deg,#0F172A 50%,#C2410C 50%);color:#fff}
.hm{display:inline-block;min-width:7mm;text-align:center;border:1px solid;border-radius:1mm;font-size:7.2pt;font-weight:700;padding:0 1mm;margin:.3mm;font-variant-numeric:tabular-nums}
.cols2{display:grid;grid-template-columns:1fr 1.5fr;gap:6mm}
.tbl.hmx td,.tbl.hmx th{text-align:center}.tbl.hmx td:first-child,.tbl.hmx th:first-child{text-align:left;white-space:nowrap}
.tbl.compact{font-size:7.6pt}.tbl.compact td{padding:.8mm 1mm}
.tbl.rtm{font-size:6.6pt;table-layout:fixed}.tbl.rtm td{padding:.5mm .8mm}.tbl.rtm .mono{font-size:6.2pt}.tbl.rtm th:nth-child(1){width:19mm}.tbl.rtm th:nth-child(2){width:11mm}.tbl.rtm th:nth-child(3){width:16mm}.tbl.rtm th:nth-child(4){width:40mm}.tbl.rtm th:nth-child(5){width:62mm}.tbl.rtm th:nth-child(6){width:26mm}
.swim{width:100%;border-collapse:collapse;font-size:7pt;table-layout:fixed}
.swim th{font-size:7pt;color:#334155;border-bottom:1.2px solid var(--b2);padding:1mm;text-align:left;vertical-align:bottom}
.swim th.lane{width:30mm;vertical-align:top;border-bottom:1px solid var(--line);background:#F8FAFC}
.swim td{border-bottom:1px solid var(--line);border-left:1px dashed var(--line);padding:.8mm;vertical-align:top}
.swim .hm{font-size:6.4pt;min-width:0;padding:0 .7mm}
.swim tr{break-inside:avoid}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm;margin-top:3mm}
.kpi{border:1px solid var(--line);border-radius:2mm;padding:3mm}
.kpi .v{font-size:19pt;font-weight:800;line-height:1}.kpi .v small{font-size:10pt;color:var(--mut)}
.kpi .l{font-size:7.6pt;color:var(--mut);margin-top:1mm}
.ar{display:grid;grid-template-columns:44mm 1fr 52mm;align-items:center;gap:3mm;font-size:8.6pt;margin:1.2mm 0}
.track{height:3mm;border-radius:1.5mm;background:#F1F5F9;display:flex;overflow:hidden}.track i{display:block;height:100%}
.ar .n{color:var(--mut);font-size:8pt;text-align:right}
.delta span{display:inline-block;font-size:8pt;border:1px solid var(--b2);border-radius:4mm;padding:.4mm 2.5mm;margin:0 1.5mm 1.5mm 0;background:#F8FAFC}
figure{margin:0 0 5mm;break-inside:avoid}
.fig{display:block;max-width:100%;max-height:150mm;margin:2mm auto 1.5mm;border:1px solid var(--line);border-radius:1.5mm}
figcaption{font-size:8pt;color:var(--mut)}
section.wide{width:265mm;margin-left:-42.5mm}
section.wide .fig{max-height:128mm}
.chead{display:grid;grid-template-columns:1fr 72mm;gap:6mm;align-items:end}
.vsig{display:block;width:72mm;border:1px solid var(--line);border-radius:1.5mm}
.vsig+div{font-size:7.6pt;color:var(--mut);text-align:center;margin-top:1mm}
.hgate{display:grid;grid-template-columns:1fr 58mm;gap:6mm;align-items:start}
.vloc{display:block;width:58mm;border:1px solid var(--line);border-radius:1.5mm}
.vloc+div{font-size:7.4pt;color:var(--mut);margin-top:1mm}
.small{font-size:8pt;color:var(--mut)}
"""


# ---------------------------------------------------------------- sections

def cover(ident: dict, s: dict, rs: dict, vd: vmodel.Data) -> str:
  bl = s["baseline"]
  sig = vmodel.draw("status", "card", model=vd)
  kind_chip = chip("not a baseline", "g") if ident["kind"] == "living snapshot" else chip("baseline release", "ok" if rs["approved"] else "am")
  banner_text = ("<b>Approved.</b> Gate record and approvals are listed on the approval page." if rs["approved"] else
                 f"<b>Not approved. {e(rs['detail'][0].upper() + rs['detail'][1:])}.</b> Valid only as a record of the repository at the commit above.")
  return f"""<section class="cover" style="break-before:auto;page-break-before:auto">
<div class="brand"><div class="logo">L</div><div><b>LionDriver</b> <span class="small">· Assurance</span></div></div>
<div class="chead"><div><div class="kicker">SAFETY CASE · WP-K-01</div>
<div class="ttl">LD-SDA<br>Safety Case</div></div>
<div>{svg_img(vmodel.svg(sig), "Status signature: " + sig.desc, "vsig")}
<div>{e(v_signature(vd))}</div></div></div>
<div class="small" style="font-size:10pt">LionDriver Supervised Driving Assistance, a supervised SAE Level 2 retrofit<br>
Reference configuration: Toyota Corolla, 12th generation (E210), TSS 2.0</div>
<div class="rule"></div>
<div class="idg">
<div>Snapshot</div><div class="mono"><b>{e(ident['id'])}</b></div>
<div>Kind</div><div>{e(ident['kind'].capitalize())} {kind_chip}</div>
<div>Version</div><div>{e(ident['version'])}</div>
<div>Date</div><div>{e(ident['date'])} (commit date, UTC)</div>
<div>Source</div><div class="mono">liondriver-dev @ {e(ident['commit_short'])}</div>
<div>Engineering baseline</div><div>{e(bl['id'])} {chip(bl['lifecycle_status'].replace('-', ' '), 'ok' if bl['lifecycle_status'] == 'frozen' else 'am')}</div>
<div>Owner</div><div>Safety manager (WP-M-02 §3.1)</div>
</div>
<div class="banner{' ok' if rs['approved'] else ''}"><span class="pill">{e(rs['label'])}</span><div>{banner_text}</div></div>
<div class="std"><span>ISO 26262:2018</span><span>ISO 21448:2022</span><span>ISO/SAE 21434:2021</span><span>ISO/PAS 8800</span>
<span>Automotive SPICE 4.0</span></div>
<div class="cfoot">Public · MIT licence · {e(f"controlled copy {ident['copy']['id']} for {ident['copy']['recipient']}" if ident['copy'] else "uncontrolled when downloaded")}. Current version and verification: {e(RELEASES_URL)}<br>
Generated by assurance/case-records/tools/build_snapshot.py {GENERATOR_VERSION} from the records; not edited by hand.</div>
</section>"""


def approval(s: dict, rs: dict, reviews: list[dict]) -> str:
  roles = {plain(r["Role"]): plain(r["Assigned to"]) for r in md_table(WP_M_02, "### 3.1")}
  accepted = [r for r in s["gates"]["records"] if r["outcome"].startswith("pass")]
  case_reviews = load_case().of_kind("review")
  vr = [r for r in case_reviews if r.get("independence") in ("I1", "I2", "I3") and r.get("outcome") == "accepted"]
  rows = [
    ["<b>Prepared</b>", f"{e(roles.get('Project maintainer', 'TBD'))}, project maintainer, with AI assistance (Claude Code)", "—", "git",
     chip("prepared", "g")],
    ["<b>Verification review</b><br><span class='small'>WP-P-05</span>",
     "; ".join(e(r["reviewer"]) for r in vr) or f"<span class='tbd'>{e(roles.get('Verification reviewer(s)', 'TBD'))}</span>",
     "I1 or higher", "; ".join(e(r["id"]) for r in vr) or "—", chip("recorded", "ok") if vr else chip("not performed", "red")],
    ["<b>Confirmation review</b><br><span class='small'>CR-12, safety case</span>",
     f"<span class='tbd'>{e(roles.get('External functional safety assessor', 'TBD'))}</span>", "I3", "—",
     chip("performed", "ok") if any(CONFIRMATION_DIR.glob("CR-12-*.md")) else chip("not performed", "red")],
    ["<b>Approval</b><br><span class='small'>gate decision</span>", f"Safety manager: {e(roles.get('Safety manager', 'TBD'))}", "—",
     "; ".join(e(g["record"].split("/")[-1]) for g in accepted) or "—", chip("approved", "ok") if rs["approved"] else chip("not approved", "red")],
  ]
  recorded = {g["gate"]: g for g in s["gates"]["records"]}
  cells = []
  for gid in gate_skeletons():
    g = recorded.get(gid)
    cls, txt = ("pass", g["outcome"]) if g and g["outcome"].startswith("pass") else (("block", g["outcome"]) if g else ("", "no record"))
    cells.append(f'<div class="gate {cls}"><b>{gid}</b>{e(txt)}</div>')
  i0 = [r for r in reviews if r["independence"] == "I0"]
  return f"""<section id="approval"><h1>Approval</h1>
<p class="lead">Approvals exist only as review and gate records in the repository. This page lists them. It is not signed, and
<b>a signature added to a downloaded copy is not valid</b>.</p>
<div class="sect">Preparation, review and approval</div>
{table(["Function", "Who", "Independence", "Record", "Status"], rows)}
<div class="sect">Gates (WP-M-00 §2)</div><div class="gates">{''.join(cells)}</div>
<div class="sect">What does not count as review</div>
<div class="box">{len(i0)} review records ({e(i0[0]['id'] if i0 else '')}…{e(i0[-1]['id'] if i0 else '')}) are pre-review audits at independence <b>I0</b>.
They find and fix problems, but under WP-M-02 §3.3 they are not verification and accept nothing. CI results are not review records either.</div>
<div class="box or"><b>Approved state.</b> Only a baseline release with a passed gate record and a frozen, tagged baseline shows “approved”.
A living snapshot never does.</div>
</section>"""


def document_control(ident: dict, s: dict, prev: dict | None, contrib: dict) -> str:
  c = ident["copy"]
  cfg = next((x for x in load_case().of_kind("configuration") if x["id"] == REFERENCE_CFG), {"id": REFERENCE_CFG, "title": ""})
  rows = [["Document", "WP-K-01 Safety case (ISO 26262-2 §6.4.8, ISO 21448 §13, ISO/SAE 21434 §6.4.8)"],
          ["Version", f"{e(ident['version'])} (WP-K-01 control header; WP-P-04 §5)"],
          ["Status", f"{e(release_status(s)['label'])}: {e(release_status(s)['detail'])}"],
          ["This snapshot", f"<span class='mono'>{e(ident['id'])}</span>"],
          ["Issued", f"{e(ident['issued'])} (commit time)"],
          ["Configuration", f"<span class='mono'>{e(cfg['id'])}</span> {e(cfg['title'])}; {e(REFERENCE_BUILD)}"],
          ["Classification", "Public (MIT licence)"],
          ["Copy", (f"<b>Controlled copy <span class='mono'>{e(c['id'])}</span></b> for {e(c['recipient'])}; purpose: {e(c['purpose'])}; "
                    f"issued by @{e(c['issued_by'])} at {e(c['issued_at'])}") if c else
                   "Uncontrolled: public download, not recorded. Controlled copies are issued and recorded as described in Annex C"],
          ["Distribution record", f"<span class='mono'>assurance/case-records/distribution.yaml</span>: {len(distribution.load())} controlled "
                                  f"cop{'y' if len(distribution.load()) == 1 else 'ies'} recorded at this commit"],
          ["Retention", f"{e(ident['retention'])} (WP-P-04 §10)"],
          ["Previous snapshot", f"<span class='mono'>{e(ident['previous'])}</span>" if ident["previous"] else "none (first snapshot)"],
          ["Last approved baseline", "none" if not release_status(s)["approved"] else e(s["baseline"]["id"])],
          ["Pins", " · ".join(f"{e(k)} <span class='mono'>{e(v)}</span>" for k, v in ident["pins"].items())],
          ["Records digest", f"<span class='mono'>{e(s['records_digest'])}</span>"]]
  ch = changes(ident["previous_commit"])
  title = "Changes since the previous snapshot" if prev else "Latest changes to the assurance set (no previous snapshot)"
  change_rows = [[f"<span class='mono'>{e(c['commit'])}</span>", f"<span class='nw'>{e(c['date'])}</span>", e(c["subject"])] for c in ch]
  change_rows = change_rows or [["—", "", "no change to assurance/"]]
  delta = status_delta(s, prev)
  return f"""<section id="control"><h1>Document control</h1>
<p class="lead">Generated from git and, when given, the manifest of the previous snapshot.</p>
{table(["Field", "Value"], rows)}
<div class="sect">{e(title)}</div>{table(["Commit", "Date", "Change"], change_rows)}
<div class="sect">Status change since the previous snapshot</div><div class="delta">{delta}</div>
<div class="sect">Notice</div>
<div class="box">{(f"<b>Controlled copy {e(c['id'])}.</b> Issued to the recipient above and recorded in the distribution record. "
  "It is not updated when the safety case changes; the current version is the repository and the newest release.") if c else
  "<b>Uncontrolled copy.</b> The controlled version is the repository at the commit above."}
Check that this copy is current, and that it is genuine, as described in Annex C.<br>
<b>AI-assisted authoring.</b> {contrib['ai_involved']} of {contrib['total']} commits to the assurance set since {e(contrib['since'])}
are AI-authored or AI co-authored. The AI assistant is a contributor, never a reviewer (WP-M-02 §3.3).<br>
<b>Distribution.</b> Public, through GitHub releases (anonymous, not recorded). Controlled copies are recorded by
recipient in the distribution record (ISO 9001 §7.5.3.2; IATF 16949 §7.5.3.2.1).</div>
</section>"""


DELTA_KEYS = [("claims accepted", ("claims", "accepted")), ("evidence accepted", ("evidence", "accepted")),
              ("evidence missing", ("evidence", "missing")), ("defeaters open", ("defeaters_open",)), ("actions open", ("actions_open",))]


def _get(d: dict, path: tuple) -> object:
  for k in path:
    d = d[k]
  return d


def status_delta(s: dict, prev: dict | None) -> str:
  if not prev:
    return "<span>first snapshot: no comparison</span>"
  ps = prev["status"]
  out = [f"<span>{e(lbl)} {e(_get(ps, p))} → {e(_get(s, p))}</span>" for lbl, p in DELTA_KEYS]
  out.append(f"<span>baseline {e(ps['baseline']['id'])} → {e(s['baseline']['id'])}</span>")
  same = all(_get(ps, p) == _get(s, p) for _, p in DELTA_KEYS) and ps["baseline"] == s["baseline"]
  return ("<span><b>no status change</b></span>" if same else "") + "".join(out)


def contents() -> str:
  items = [("approval", "Approval", True), ("control", "Document control", True),
           ("documents", "Controlled documents", True), ("distribution", "Distribution record", True), ("roles", "Roles and responsibilities", True),
           ("raci", "RACI", True), ("contributors", "Contributors, reviews and confirmation measures", True),
           ("status", "1 Status at a glance", False), ("traceability", "1.1 Traceability on the V", False),
           ("coverage", "1.2 Trace coverage", False), ("lifecycle", "1.3 Lifecycle swimlanes", False),
           ("vv", "1.4 Verification and validation", False), ("freshness", "1.5 Evidence freshness", False),
           ("scope", "2 Scope", False), ("hierarchy", "2.1 Element hierarchy", False),
           ("argument", "3 Argument (GSN)", False),
           ("claims", "4 Claims", False), ("evidence", "5 Evidence register", False), ("defeaters", "6 Open defeaters", False),
           ("gates", "7 Gates, actions and decisions", False), ("config", "8 Configuration and pins", False),
           ("annex-a", "A Revision history", False), ("annex-b", "B Abbreviations", False), ("annex-c", "C How to verify this snapshot", False),
           ("annex-d", "D Requirements traceability matrix", False)]
  links = "".join(f'<a class="{"fm" if fm else ""}" href="#{i}"><span>{e(t)}</span><span>›</span></a>' for i, t, fm in items)
  return f'<section id="contents"><h1>Contents</h1><p class="lead">Every entry links to its page.</p><div class="toc">{links}</div></section>'


def roles() -> str:
  rows, held, tbd, acting = [], 0, 0, 0
  for r in md_table(WP_M_02, "### 3.1"):
    who = plain(r["Assigned to"])
    if who.startswith("TBD"):
      tone, tbd = chip("TBD", "red"), tbd + 1
      who_html = f"<span class='tbd'>{e(who)}</span>"
    else:
      held += 1
      is_acting = "acting" in who
      acting += is_acting
      tone, who_html = chip("acting", "am") if is_acting else chip("assigned", "g"), e(who)
    rows.append([e(plain(r["Role"])), who_html, e(plain(r.get("Needed by", ""))), tone])
  total = held + tbd
  return f"""<section id="roles"><h1>Roles and responsibilities</h1>
<p class="lead">Table 1, generated from WP-M-02 §3.1. Competence evidence is in WP-M-04.</p>
{table(["Role", "Assigned to", "Needed by", ""], rows)}
<div class="box or"><b>{held} of {total} roles are assigned ({acting} acting); {tbd} are TBD.</b> One person holding several roles is allowed for planning and
authoring, but not where independence is required: verification review at I1 or higher, confirmation measures, audit and assessment (WP-M-02 §3.1).</div>
</section>"""


def raci() -> str:
  rows = md_table(WP_M_02, "### 3.2")
  roles_ = [k for k in rows[0] if k != "Activity"]
  cls = {"A": "rA", "R": "rR", "C": "rC", "I": "rI", "A/R": "rAR"}
  body = []
  for r in rows:
    cells = [e(plain(r["Activity"]))]
    for k in roles_:
      v = plain(r[k])
      base = v.split(" ")[0]
      note = " CR" if "CR" in v else ""
      cells.append(f'<i class="{cls.get(base, "rI")}">{e(base + note)}</i>')
    body.append(cells)
  legend = (f'{chip("A", "g")} accountable · {chip("R", "g")} responsible · {chip("C", "g")} consulted · {chip("I", "g")} informed · '
            + "CR: the assessor performs the confirmation review")
  th = "".join(f"<th>{e(h)}</th>" for h in ["Activity"] + roles_)
  tb = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in body)
  intro = plain(md_table_intro(WP_M_02, "### 3.2"))
  return f"""<section id="raci" class="land"><h1>RACI per activity</h1>
<p class="lead">Table 2, generated from WP-M-02 §3.2. {e(intro)}</p>
<table class="raci"><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table>
<p class="small">{legend}</p></section>"""


def md_table_intro(path: Path, heading: str) -> str:
  lines = path.read_text(encoding="utf-8").splitlines()
  start = next(i for i, ln in enumerate(lines) if ln.startswith(heading))
  return next((ln for ln in lines[start + 1:] if ln.strip() and not ln.startswith("|")), "")


def contributors_page(contrib: dict, reviews: list[dict], measures: list[dict], s: dict) -> str:
  people = [[f"<b>{e(n)}</b>", "Author; merges every change to the default branch", f"{c} authored"] for n, c in contrib["people"]]
  people.append(["<b>AI assistant</b> (Claude Code)", "Tool-assisted authoring. Not a reviewer; cannot approve",
                 f"{contrib['ai_authored']} authored · on {contrib['ai_involved']} of {contrib['total']}"])
  human_only = contrib["total"] - contrib["ai_involved"]
  rv = [[f"<span class='mono nw'>{e(r['id'])}</span>", e(r["object"]), e(r["independence"]), f"<span class='nw'>{e(r['date'])}</span>",
         chip("no · pre-review", "am") if r["independence"] == "I0" else chip("see record", "g")] for r in reviews]
  accepted = sum(1 for r in load_case().of_kind("review") if r.get("outcome") == "accepted")
  rv.append(["", "Accepted review records in assurance/case-records/reviews/", "", "", chip(str(accepted), "red" if not accepted else "ok")])
  gates_: dict[str, list[str]] = {}
  for m in measures:
    gates_.setdefault(m["gate"], []).append(chip(m["id"], "ok" if m["performed"] else "red"))
  cm = [[f"<b>{e(g)}</b>", " ".join(ids)] for g, ids in gates_.items()]
  performed = sum(m["performed"] for m in measures)
  return f"""<section id="contributors"><h1>Contributors and reviews</h1>
<div class="sect">Contributors to the assurance set (git, since {e(contrib['since'])})</div>
{table(["Contributor", "Role in this document", "Commits"], people)}
{bar([(human_only, "#334155"), (contrib['ai_involved'], "#A5B4FC")], contrib['total'])}
<p class="small">■ human only {human_only} · ■ AI-authored or co-authored {contrib['ai_involved']}</p>
<div class="sect">Review records</div>{table(["ID", "Object", "Indep.", "Date", "Counts as review"], rv)}
<div class="sect">Confirmation measures (WP-M-06 §9) · {performed} of {len(measures)} performed</div>
{table(["Due at gate", "Measures (green: record in 10-safety-case/confirmation/, red: not performed)"], cm)}
</section>"""


def area_row(a: dict) -> str:
  parts = [(a["accepted"], "#2E9E6A"), (a["partial"], "#F59E0B"), (a["missing"], "#D2553F")]
  label = f'{a["partial"]} partial · {a["missing"]} missing · {a["accepted"]} accepted'
  return f'<div class="ar"><span>{e(a["title"])}</span>{bar(parts, a["evidence"])}<span class="n">{label}</span></div>'


def status_page(s: dict, rs: dict, prev: dict | None, vd: vmodel.Data) -> str:
  cl, ev = s["claims"], s["evidence"]
  kpis = [(f"{cl['accepted']}<small> / {cl['registered']}</small>", f"claims accepted · {cl['undeveloped']} undeveloped"),
          (f"{ev['accepted']}<small> / {ev['registered']}</small>", f"evidence accepted · {ev['awaiting_review']} awaiting review · {ev['missing']} missing"),
          (f"<span style='color:var(--red)'>{s['defeaters_open']}</span>", "defeaters open"),
          (f"{s['actions_open']}", f"actions open · {s['reviews']} review records")]
  k = "".join(f'<div class="kpi"><div class="v">{v}</div><div class="l">{e(lbl)}</div></div>' for v, lbl in kpis)
  areas = "".join(area_row(a) for a in s["lifecycle_areas"])
  actions = sorted((a for a in load_case().of_kind("action") if a["lifecycle_status"] == "open"), key=lambda a: (a.get("needed_by") or "G9", a["id"]))
  act_rows = [[f"<b>{e(a.get('needed_by') or '—')}</b>", f"<span class='mono'>{e(a['id'])}</span>", e(a["title"])] for a in actions]
  return f"""<section id="status"><h1>1 Status at a glance</h1>
<p class="lead">Assurance state <b>{e(s['assurance_state'])}</b> · baseline {e(s['baseline']['id'])} ({e(s['baseline']['lifecycle_status'].replace('-', ' '))})
· {e(rs['label'])}: {e(rs['detail'])} · records digest <span class="mono">{e(s['records_digest'])}</span></p>
<div class="kpis">{k}</div>
<div class="sect">The system V, status lens</div>
{v_figure(vmodel.draw("status", "full", model=vd), 1, V_CAPTIONS["status"])}
<div class="sect">Since the previous snapshot</div><div class="delta">{status_delta(s, prev)}</div>
<div class="sect">Evidence by lifecycle area</div>{areas}
<p class="small"><span style="color:#2E9E6A">■</span> accepted · <span style="color:#F59E0B">■</span> partial / awaiting review ·
<span style="color:#D2553F">■</span> missing</p>
<div class="sect">Open actions, by the gate that needs them</div>{table(["Gate", "Action", "Title"], act_rows)}
</section>"""


V_CAPTIONS = {
  "status": "The system V (ASPICE 4.0), status lens: each level coloured by the WP-M-00 register status of its work products, " +
            "verification levels with their cases specified and run, the gate records below; generated by assurance/trace/tools/vmodel.py",
  "trace": "The system V, trace lens: items per level (* only in work products), cases per test specification and items named " +
           "across the V; the same drawing as Figure 1 of the ASPICE trace map",
  "goal": "The system V per safety goal: left, the goal's items at each level; right, how many of them the paired test cases " +
          "name (named / items)",
}


def traceability(vd: vmodel.Data) -> str:
  lead = ("Where the trace data stands on the V. The trace lens counts the items each specification level holds and how many of " +
          "the paired level's items the test cases name; the goal lens repeats the V once per safety goal. A case naming an item " +
          "is a specified link, not a passed test.")
  return f"""<section id="traceability" class="land wide"><h1>1.1 Traceability on the V</h1><p class="lead">{e(lead)}</p>
{v_figure(vmodel.draw("trace", "full", model=vd), 2, V_CAPTIONS["trace"])}
{v_figure(vmodel.goal_grid(vd), 3, V_CAPTIONS["goal"])}
</section>"""


def scope() -> str:
  rows = [[e(plain(r["Attribute"])), e(plain(r["Value"]))] for r in md_table(WP_C_01, "## 1.")]
  title, path = FIGURES[1]
  return f"""<section id="scope"><h1>2 Scope</h1><p class="lead">Item identification, from WP-C-01 §1.</p>
{table(["Attribute", "Value"], rows)}</section>
<section id="hierarchy" class="land"><h1>2.1 Element hierarchy</h1>{figure(path, 4, title)}</section>"""


def argument() -> str:
  title, path = FIGURES[0]
  sheets = sorted(GSN_DIR.glob("gsn-*.svg"), key=lambda p: (p.name.startswith("gsn-cs"), int(re.search(r"-(\d+)-", p.name).group(1))))
  parts = [figure(path, 5, title)]
  for n, p in enumerate(sheets, start=6):
    t = re.search(r"<title>(.*?)</title>", p.read_text(encoding="utf-8"))
    cap = t.group(1) if t else p.stem
    parts.append(figure(p, n, cap))
  lead = '<p class="lead">The GSN sheets generated by gsn_diagrams.py from the records.</p>'
  return f'<section id="argument" class="land"><h1>3 Argument (GSN)</h1>{lead}{"".join(parts)}</section>'


def claims_page(case) -> str:
  rows = []
  for c in sorted(case.of_kind("claim"), key=lambda c: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", c["id"])]):
    rows.append([f"<span class='mono'>{e(c['id'])}</span>", e(c["title"]), e(c.get("parent") or "—"), chip(c["lifecycle_status"], "g"),
                 chip(c["review_state"], REVIEW_TONE.get(c["review_state"], "g")), e(", ".join(c.get("evidence_refs") or []) or "—")])
  tbl = table(["ID", "Claim", "Parent", "Lifecycle", "Review", "Evidence"], rows)
  return f'<section id="claims"><h1>4 Claims</h1><p class="lead">All registered claims, from assurance/case-records/claims/.</p>{tbl}</section>'


def evidence_page(case) -> str:
  rows = [[f"<span class='mono'>{e(x['id'])}</span>", e(x["title"]), e(x["lifecycle_area"].replace("-", " ")),
           chip(x["evidence_status"], EVID_TONE[x["evidence_status"]]), chip(x["review_state"], REVIEW_TONE.get(x["review_state"], "g")),
           f"<span class='mono'>{e(x.get('location') or '')}</span>"]
          for x in sorted(case.of_kind("evidence"), key=lambda x: int(re.sub(r"\D", "", x["id"]) or 0))]
  tbl = table(["ID", "Evidence", "Area", "Status", "Review", "Location"], rows)
  return f'<section id="evidence"><h1>5 Evidence register</h1><p class="lead">From assurance/case-records/evidence/.</p>{tbl}</section>'


def defeaters_page(case) -> str:
  rows = [[f"<span class='mono'>{e(d['id'])}</span>", e(d["title"]), e(d.get("description") or ""), e(", ".join(d.get("related_claims") or []))]
          for d in sorted(case.of_kind("defeater"), key=lambda d: int(re.sub(r"\D", "", d["id"]) or 0)) if d["lifecycle_status"] == "open"]
  lead = f'<p class="lead">Known counter-evidence against claims, from assurance/case-records/defeaters/ ({len(rows)} open).</p>'
  tbl = table(["ID", "Defeater", "Closure route", "Claims"], rows)
  return f'<section id="defeaters"><h1>6 Open defeaters</h1>{lead}{tbl}</section>'


def gates_page(s: dict, vd: vmodel.Data) -> str:
  recs = [[e(g["gate"]), e(g["date"]), e(g["outcome"]), f"<span class='mono'>{e(g['record'])}</span>"] for g in s["gates"]["records"]]
  dec = [[f"<span class='mono'>{e(plain(r['ID']))}</span>", e(plain(r["Decision"]))] for r in md_table(WP_M_01, "## 8.")]
  card = vmodel.draw("gate", "card", model=vd)
  loc = (f'<div>{svg_img(vmodel.svg(card), "Gate lens: " + card.desc, "vloc")}' +
         '<div>Gate lens: each level shows the gate that first needs it, coloured by that gate\'s record.</div></div>')
  return f"""<section id="gates"><div class="hgate"><div><h1>7 Gates, actions and decisions</h1>
<p class="lead">Gates G0–G6 of WP-M-00 §2. A gate passes only with a gate review record in 10-safety-case/gates/.</p></div>{loc}</div>
<div class="sect">Gate review records</div>{table(["Gate", "Date", "Outcome", "Record"], recs) if recs else '<p>No gate review has been held.</p>'}
<div class="sect">Strategic decisions (WP-M-01 §8)</div><p class="small">Owned by the project maintainer; each stays open in WP-M-07 until decided.</p>
{table(["ID", "Decision"], dec)}</section>"""


def config_page(case, ident: dict, s: dict) -> str:
  cfg = [[f"<span class='mono'>{e(c['id'])}</span>", e(c["title"]), e(c["classification"]), e(c["evaluation_state"])] for c in case.of_kind("configuration")]
  bls = [[f"<span class='mono'>{e(b['id'])}</span>", e(b["title"]), e(b["lifecycle_status"]), e(b.get("tag") or "—"),
          f"<span class='mono'>{e(b['source_revision'])}</span>"]
         for b in sorted(case.of_kind("baseline"), key=lambda b: b["id"])]
  pins = [[e(k), f"<span class='mono'>{e(v)}</span>"] for k, v in ident["pins"].items()]
  up = s["configurations"]["upstream_compatible"]
  return f"""<section id="config"><h1>8 Configuration and pins</h1>
<div class="sect">Configurations</div>{table(["ID", "Configuration", "Classification", "Evaluation"], cfg)}
<p class="small">Upstream lists {up['stated_count']} car models from {up['makes']} makes ({e(up['source'])});
only the configurations above are evaluated by LionDriver.</p>
<div class="sect">Engineering baselines</div>{table(["ID", "Baseline", "Status", "Tag", "Source"], bls)}
<div class="sect">Submodule pins at this snapshot</div>{table(["Submodule", "Commit"], pins)}</section>"""


def annexes(ident: dict) -> str:
  hist = [[f"<span class='mono'>{e(h['commit'])}</span>", f"<span class='nw'>{e(h['date'])}</span>", e(h["subject"])] for h in history()]
  abbr = [[f"<b>{e(a)}</b>", e(b)] for a, b in ABBREVIATIONS]
  verify = f"""<ol>
<li>Download the files of this snapshot from {e(RELEASES_URL)}. The newest living snapshot is the release <span class="mono">snapshot-latest</span>;
baseline releases are tagged <span class="mono">bl-NNN</span> and never replaced.</li>
<li>Check the hash: <span class="mono">sha256sum -c SHA256SUMS</span>.</li>
<li>Check where it was built: <span class="mono">gh attestation verify {PDF_NAME} -R {REPO_SLUG}</span>. It must name the
<span class="mono">safety-case-snapshot.yaml</span> workflow and the commit <span class="mono">{e(ident['commit_short'])}</span>.</li>
<li>Check that it is current: compare the snapshot ID with the newest release. An older ID is superseded.</li>
<li>Rebuild it yourself: check out <span class="mono">{e(ident['commit_short'])}</span> and run
<span class="mono">python3 assurance/case-records/tools/build_snapshot.py</span>; the HTML is identical byte for byte.</li>
<li>For a controlled copy: find its <span class="mono">CC-YYYY-NNN</span> in <span class="mono">assurance/case-records/distribution.yaml</span>.
The entry names the recipient, the purpose, who issued it and the workflow run. Copies are issued only by the
<span class="mono">safety-case-controlled-copy.yaml</span> workflow, which records the copy before it prints it.</li></ol>"""
  return f"""<section id="annex-a"><h1>A Revision history</h1><p class="lead">Every commit that changed assurance/, newest first.</p>
{table(["Commit", "Date", "Change"], hist)}</section>
<section id="annex-b"><h1>B Abbreviations</h1>{table(["Term", "Meaning"], abbr)}</section>
<section id="annex-c"><h1>C How to verify this snapshot</h1>{verify}</section>"""


# ---------------------------------------------------------------- build

def build(tag: str | None, previous: dict | None, copy_id: str | None = None) -> tuple[str, dict]:
  case = load_case()
  rep = validate(case)
  if rep.errors:
    for err in rep.errors:
      print(f"ERROR {err}")
    raise SystemExit("FAIL: records are invalid; no snapshot built")
  s = summarize(case)
  rs = release_status(s)
  errs = distribution.check(distribution.load())
  if errs:
    raise SystemExit("FAIL: distribution record: " + "; ".join(errs))
  ident = identity(tag, previous, distribution.find(copy_id) if copy_id else None)
  cfg = next(c for c in case.of_kind("configuration") if c["id"] == REFERENCE_CFG)
  contrib, reviews = contributors(), review_records()
  vd = vmodel.load()
  body = "".join([
    cover(ident, s, rs, vd), approval(s, rs, reviews), document_control(ident, s, previous, contrib), contents(),
    pages.controlled_documents(), pages.distribution_record(), roles(), raci(),
    contributors_page(contrib, reviews, confirmation_measures(), s), status_page(s, rs, previous, vd), traceability(vd),
    pages.coverage(vd.m), pages.lifecycle(), pages.vv_matrix(vd), pages.freshness(case), scope(),
    argument(), claims_page(case), evidence_page(case), defeaters_page(case), gates_page(s, vd), config_page(case, ident, s),
    annexes(ident), pages.rtm(vd.m)])
  wm = "" if rs["approved"] else '<div class="wm">DRAFT</div>'
  html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(ident['id'])} · LD-SDA safety case</title>
<meta name="snapshot-id" content="{e(ident['id'])}"><meta name="snapshot-status" content="{e(rs['label'])}: {e(rs['detail'])}">
<style>{CSS}</style></head><body>{wm}<main>{body}</main></body></html>
"""
  manifest = {
    "schema": 1,
    "snapshot": {k: ident[k] for k in ("id", "kind", "tag", "date", "issued", "version", "commit", "pins", "previous", "copy")},
    "release_status": rs,
    "status": s,
    "generator": {"tool": "assurance/case-records/tools/build_snapshot.py", "version": GENERATOR_VERSION},
    "files": {HTML_NAME: hashlib.sha256(html.encode()).hexdigest()},
    "header": running_header(ident, rs, s, cfg),
  }
  return html, manifest


def main(argv: list[str]) -> int:
  args = dict(zip(argv[::2], argv[1::2], strict=False))
  unknown = set(args) - {"--out", "--previous", "--tag", "--copy"}
  if unknown or len(argv) % 2:
    print(__doc__)
    return 2
  out = Path(args.get("--out", REPO_ROOT / "build" / "snapshot"))
  prev_path = args.get("--previous")
  previous = json.loads(Path(prev_path).read_text(encoding="utf-8")) if prev_path and Path(prev_path).exists() else None
  html, manifest = build(args.get("--tag"), previous, args.get("--copy"))
  out.mkdir(parents=True, exist_ok=True)
  (out / HTML_NAME).write_text(html, encoding="utf-8")
  (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
  print(f"OK: {manifest['snapshot']['id']} ({manifest['release_status']['label']}: {manifest['release_status']['detail']}) -> {out}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
