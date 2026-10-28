"""Status, traceability and document-control pages of the safety case snapshot (build_snapshot.py).

Each page is computed from the records, the trace data, the process model and git; nothing is typed
here except headings and fixed notes. One colour rule with vmodel.py: green only for approved,
baselined or passed; a complete specified link is blue, partial amber, missing red, untraced grey.

  front matter  controlled_documents (N7), distribution_record (N9)
  part 1        coverage (N2, 1.2), lifecycle (N4, 1.3), vv_matrix (N5, 1.4), freshness (N8, 1.5)
  annex D       rtm (N1)
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from html import escape
from pathlib import Path

from caselib import ASSURANCE_DIR, REPO_ROOT

sys.path.insert(0, str(ASSURANCE_DIR / "process" / "tools"))
sys.path.insert(0, str(ASSURANCE_DIR / "trace" / "tools"))

import distribution
import process_model as pm
import trace_map as tm
import vmodel

# vmodel.STATE colours, by meaning
TONE = {"ok": ("#ECFDF5", "#2E9E6A"), "done": ("#EFF6FF", "#2563EB"), "prog": ("#FFFBEB", "#D97706"),
        "gap": ("#FEF2F2", "#D2553F"), "none": ("#F8FAFC", "#94A3B8")}
COVER_TONE = {"full": "done", "partial": "prog", "none": "gap", "untraced": "none"}
WP_TONE = {"A": "ok", "B": "ok", "R": "done", "D": "prog", "S": "none", "N/A": "none"}
RTM_KINDS = ("SG", "FSR", "TSR", "SWSR", "HWSR")
KIND_ORDER = {k: i for i, k in enumerate(("H", "HE", "SG", "AOU", "FSR", "TSR", "SWSR", "HWSR"))}


def e(x) -> str:
  return escape(str(x))


def git(*args: str) -> str:
  env = {**os.environ, "TZ": "UTC"}
  return subprocess.run(["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True, env=env).stdout.strip()


def cell(text: str, tone: str, title: str = "") -> str:
  bg, fg = TONE[tone]
  t = f' title="{e(title)}"' if title else ""
  return f'<span class="hm" style="background:{bg};border-color:{fg};color:{fg}"{t}>{text}</span>'


def legend(tones: list[tuple[str, str]]) -> str:
  return '<p class="small">' + " · ".join(f'<span style="color:{TONE[t][1]}">■</span> {e(w)}' for t, w in tones) + "</p>"


def table(head: list[str], rows: list[list[str]], cls: str = "tbl") -> str:
  th = "".join(f"<th>{e(h)}</th>" for h in head)
  body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
  return f'<table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'


def sort_key(iid: str) -> tuple:
  kind = iid.split("-")[0]
  return (KIND_ORDER.get(kind, 99), [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", iid)])


def named_by(m: tm.Model) -> dict[str, list[str]]:
  """Item -> test cases (all specifications) that name it."""
  out: dict[str, list[str]] = {}
  for cases in m.specs.values():
    for case, refs in cases.items():
      for r in refs:
        out.setdefault(r, []).append(case)
  return {k: sorted(v) for k, v in out.items()}


def children_of(m: tm.Model) -> dict[str, list[str]]:
  out: dict[str, list[str]] = {}
  for iid, it in m.items.items():
    for p in it.get("parents") or []:
      out.setdefault(p, []).append(iid)
  return {k: sorted(v, key=sort_key) for k, v in out.items()}


# ---------------------------------------------------------------- front matter

def wp_header(path: Path) -> dict[str, str]:
  """Version and status from a work product's control header."""
  text = path.read_text(encoding="utf-8") if path.exists() else ""
  out = {}
  for field in ("Version", "Status"):
    m = re.search(rf"^\|\s*{field}\s*\|\s*([^|]+?)\s*\|", text, re.M)
    out[field] = m.group(1) if m else ""
  out["Version"] = (re.match(r"[0-9]+\.[0-9]+(?:\.[0-9]+)?", out["Version"]) or [""])[0]
  out["Status"] = re.sub(r"[*`]", "", out["Status"]).split("(")[0].strip()
  return out


def register_rows() -> list[dict]:
  register, _ = pm.load_register(pm.REGISTER_MD.read_text(encoding="utf-8"))
  rows = []
  for wp, row in register.items():
    h = wp_header(row.path)
    name = pm.STATUS_NAMES.get(row.status, row.status)
    rows.append({"wp": wp, "name": re.sub(r"[*`]", "", row.name), "gate": row.gate, "status": row.status,
                 "status_name": name, "version": h["Version"], "header_status": h["Status"], "exists": row.path.exists(),
                 "path": row.path.relative_to(REPO_ROOT).as_posix() if row.path.is_relative_to(REPO_ROOT) else str(row.path),
                 "agrees": row.path.exists() and h["Status"].lower().startswith(name.lower())})
  return rows


def controlled_documents() -> str:
  rows = register_rows()
  out, disagree = [], 0
  for r in rows:
    if not r["exists"]:
      check = '<span class="chip red">no file</span>'
      disagree += 1
    elif r["agrees"]:
      check = '<span class="chip g">agrees</span>'
    else:
      check = f'<span class="chip am">header: {e(r["header_status"] or "none")}</span>'
      disagree += 1
    out.append([f"<span class='mono nw'>{e(r['wp'])}</span>", e(r["name"]), e(r["gate"]),
                cell(e(r["status"]), WP_TONE.get(r["status"], "none"), r["status_name"]), e(r["version"] or "—"), check])
  counts: dict[str, int] = {}
  for r in rows:
    counts[r["status_name"]] = counts.get(r["status_name"], 0) + 1
  summary = " · ".join(f"{n} {e(k.lower())}" for k, n in sorted(counts.items(), key=lambda kv: -kv[1]))
  return f"""<section id="documents"><h1>Controlled documents</h1>
<p class="lead">The work products under document control (WP-M-00 §3, {len(rows)} rows: {summary}), with the version and status in each
document's own control header (WP-P-04 §5). The last column compares the two; WP-P-04 OI-1 asks for this check.</p>
{table(["ID", "Work product", "Gate", "Register", "Version", "Header"], out, "tbl compact")}
<p class="small">{disagree} of {len(rows)} rows disagree with their document header or have no file.</p></section>"""


def distribution_record() -> str:
  copies = distribution.load()
  rows = [[f"<span class='mono nw'>{e(c['id'])}</span>", f"<span class='nw'>{e(c['issued_at'])}</span>", e(c["recipient"]), e(c["purpose"]),
           f"@{e(c['issued_by'])}", f"<span class='mono'>{e(str(c['based_on'])[:7])}</span>",
           '<span class="chip g">issued</span>' if c["status"] == "issued" else f'<span class="chip red">withdrawn {e(c.get("withdrawn_at", ""))}</span>']
          for c in copies]
  body = table(["Copy", "Issued (UTC)", "Recipient", "Purpose", "Issued by", "Source", "State"], rows) if rows else \
    '<div class="box">No controlled copy has been issued at this commit. Every copy of this document is uncontrolled.</div>'
  return f"""<section id="distribution"><h1>Distribution record</h1>
<p class="lead">Controlled copies issued by the safety-case-controlled-copy workflow, from assurance/case-records/distribution.yaml
(ISO 9001 §7.5.3.2; IATF 16949 §7.5.3.2.1; WP-P-04 §9.1). Public downloads are anonymous and are not listed.</p>
{body}</section>"""


# ---------------------------------------------------------------- part 1

def coverage(m: tm.Model) -> str:
  der = []
  for parent, child, label, alloc in tm.DERIVATIONS:
    done, total, missing = tm.derivation(m, parent, child, alloc)
    st = tm.status_of(done, total)
    der.append([e(label), cell(f"{done}/{total}", COVER_TONE[st], tm.STATUS_WORD[st]),
                f"<span class='mono'>{e(', '.join(missing[:8]))}{' …' if len(missing) > 8 else ''}</span>" if missing else "—"])
  ver = []
  for left, right, kinds in tm.PAIRS:
    lv, rv = tm.level(left), tm.level(right)
    for kind in kinds:
      done, total, missing = tm.verified_by(m, right, kind)
      st = tm.status_of(done, total)
      ver.append([f"{e(lv.process)} → {e(rv.process)}", e(kind), e(", ".join(rv.tests)),
                  cell(f"{done}/{total}", COVER_TONE[st], tm.STATUS_WORD[st]),
                  f"<span class='mono'>{e(', '.join(missing[:6]))}{' …' if len(missing) > 6 else ''}</span>" if missing else "—"])
  # kind x test specification: how many items of the kind the specification's cases name
  prefixes = [p for lv_ in tm.RIGHT for p in lv_.tests]
  prefixes = list(dict.fromkeys(prefixes))
  kinds = [k for k in ("SG", "SH", "FSR", "TSR", "SWSR", "HWSR", "AIR", "DSR") if m.ids.get(k)]
  head = ["Kind"] + prefixes
  grid = []
  for k in kinds:
    row = [f"<b>{e(k)}</b> <span class='small'>{len(m.ids[k])}</span>"]
    for p in prefixes:
      named = {r for refs in m.specs.get(p, {}).values() for r in refs if r.split('-')[0] == k}
      n = len(named)
      row.append(cell(str(n), "done" if n else "none") if n else "<span class='small'>·</span>")
    grid.append(row)
  dang = tm.dangling(m)
  return f"""<section id="coverage" class="land wide"><h1>1.2 Trace coverage</h1>
<p class="lead">Computed by assurance/trace/tools/trace_map.py, the same rules as the ASPICE trace map. A link is specified when the trace
data or a test case names it; nothing here says a test passed.</p>
<div class="cols2"><div><div class="sect">Derivation on the left of the V</div>{table(["Link", "Parents with a child", "Without"], der)}</div>
<div><div class="sect">Requirements named by test cases (ASPICE pairs)</div>{table(["Pair", "Kind", "Specifications", "Named", "Not named"], ver)}</div></div>
<div class="sect">Traceability matrix: items of each kind named by each test specification</div>
{table(head, grid, "tbl hmx")}
{legend([("done", "complete, specified only"), ("prog", "partial"), ("gap", "missing"), ("none", "not in the trace data")])}
<p class="small">{len(dang)} test cases name an ID that is defined nowhere{(': ' + e(', '.join(list(dang)[:8]))) if dang else ''}.</p></section>"""


def lifecycle() -> str:
  model = pm.load_model()
  ctx = pm.load_context()
  phases = sorted(model.phases, key=lambda p: int(p[1:]) if p[1:].isdigit() else 99)
  lanes = list(model.lanes)
  grid: dict[tuple[str, str], list[str]] = {}
  worst = {"none": 0, "prog": 1, "done": 2, "ok": 3}
  for aid, act in sorted(model.activities.items()):
    sts = [ctx.register[wp].status for wp in act["produces"] if wp in ctx.register]
    tone = min((WP_TONE.get(s, "none") for s in sts), key=lambda t: worst.get(t, 0), default="none")
    wps = ", ".join(act["produces"])
    grid.setdefault((act["lane"], act["phase"]), []).append(cell(e(aid), tone, f"{act['name']} → {wps}"))
  head = "".join(f"<th>{e(p)}<br><span class='small'>{e(ctx.gates.get(p, ('', ''))[0])}</span></th>" for p in phases)
  rows = []
  for lid in lanes:
    lane = model.lanes[lid]
    tds = "".join(f"<td>{' '.join(grid.get((lid, p), []))}</td>" for p in phases)
    rows.append(f"<tr><th class='lane'>{e(lane['name'])}<br><span class='small'>{e(lane['role'])}</span></th>{tds}</tr>")
  n = len(model.activities)
  return f"""<section id="lifecycle" class="land wide"><h1>1.3 Lifecycle swimlanes</h1>
<p class="lead">The {n} activities of the process model (assurance/process/model/), one row per discipline lane and one column per gate phase.
Each activity is coloured by the least advanced WP-M-00 status of the work products it produces. Full maps with inputs and reviews:
assurance/process/maps/.</p>
<table class="swim"><thead><tr><th></th>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>
{legend([("ok", "approved or baselined"), ("done", "in review"), ("prog", "draft"), ("none", "skeleton or not registered")])}</section>"""


def vv_matrix(vd: vmodel.Data) -> str:
  m = vd.m
  right = [r for _, r, _ in tm.PAIRS]
  head = ["Safety goal"] + [tm.level(r).process for r in right]
  rows = []
  for sg in vmodel.goals(vd):
    title = m.items.get(sg, {}).get("text") or m.items.get(sg, {}).get("title") or ""
    row = [f"<span class='mono'>{e(sg)}</span> <span class='small'>{e(m.items.get(sg, {}).get('asil', ''))}</span>"]
    for r in right:
      left = next(lf for lf, rr, _ in tm.PAIRS if rr == r)
      total, named = vmodel.goal_counts(vd, sg, left)
      st = tm.status_of(named, total)
      row.append(cell(f"{named}/{total}", COVER_TONE[st], f"{title[:120]}") if total else "<span class='small'>·</span>")
    rows.append(row)
  runs = [[e(tm.level(r).process), e(tm.level(r).name), e(", ".join(tm.level(r).tests)), str(vd.cases.get(r, 0)),
           str(vd.executed.get(r, 0)), cell(str(vd.passed.get(r, 0)), "ok" if vd.passed.get(r) else "none")] for r in right]
  return f"""<section id="vv" class="land wide"><h1>1.4 Verification and validation</h1>
<p class="lead">For each safety goal and each verification or validation level: the goal's requirements of the level's kinds (its descendants in
the trace data) that the level's test cases name. The second table counts cases specified, executed and passed per level.</p>
{table(head, rows, "tbl hmx")}
{legend([("done", "every requirement named by a case (specified, not run)"), ("prog", "some named"), ("gap", "none named"), ("ok", "passed (none yet)")])}
<div class="sect">Cases per level</div>{table(["Process", "Level", "Specifications", "Specified", "Executed", "Passed"], runs)}</section>"""


def freshness(case) -> str:
  rows, changed, missing = [], 0, 0
  head = git("rev-parse", "HEAD")
  for x in sorted(case.of_kind("evidence"), key=lambda x: int(re.sub(r"\D", "", x["id"]) or 0)):
    loc, rev = x.get("location") or "", str(x.get("source_revision") or "")
    path = REPO_ROOT / loc if loc else None
    if not loc or not path.exists():
      state, n, last = cell("no file", "gap"), "—", "—"
      missing += 1
    else:
      try:
        n = int(git("rev-list", "--count", f"{rev}..{head}", "--", loc)) if rev else None
      except subprocess.CalledProcessError:
        n = None
      last = git("log", "-1", "--format=%cd", "--date=format-local:%Y-%m-%d", "--", loc) or "—"
      if n is None:
        state = cell("revision unknown", "gap")
        missing += 1
        n = "—"
      elif n == 0:
        state = cell("unchanged", "done")
      else:
        state = cell(f"{n} commits since", "prog")
        changed += 1
    rows.append([f"<span class='mono'>{e(x['id'])}</span>", e(x["title"]), f"<span class='mono'>{e(rev or '—')}</span>",
                 f"<span class='nw'>{e(last)}</span>", state])
  total = len(rows)
  return f"""<section id="freshness"><h1>1.5 Evidence freshness</h1>
<p class="lead">Each evidence record names the file and the commit it was recorded against (source_revision). This page counts the commits
that changed that file since. A changed file means the record must be re-checked before it can support a claim.</p>
<div class="box">{total - changed - missing} of {total} unchanged since recorded · {changed} changed since · {missing} without a file or known revision</div>
{table(["Evidence", "Title", "Recorded at", "File last changed", "Since recorded"], rows)}</section>"""


# ---------------------------------------------------------------- annex

def rtm(m: tm.Model) -> str:
  named, kids = named_by(m), children_of(m)
  rows = []
  for iid in sorted((i for i in m.items if i.split("-")[0] in RTM_KINDS), key=sort_key):
    it = m.items[iid]
    cases = named.get(iid, [])
    status = it.get("status", "")
    short = lambda v: re.split(r"\s*\(|;", str(v or "—"))[0].strip() or "—"
    tag = ' <span class="chip red">withdrawn</span>' if status == "withdrawn" else ""
    rows.append([f"<span class='mono nw'>{e(iid)}</span>{tag}", e(short(it.get("asil"))), e(short(it.get("allocated_to"))),
                 f"<span class='mono'>{e(', '.join(it.get('parents') or []) or '—')}</span>",
                 f"<span class='mono'>{e(', '.join(kids.get(iid, [])[:8]) or '—')}{' …' if len(kids.get(iid, [])) > 8 else ''}</span>",
                 e(it.get("verification", "") or "—"),
                 f"<span class='mono'>{e(', '.join(cases[:6]))}{' …' if len(cases) > 6 else ''}</span>" if cases else cell("none", "gap")])
  counts = {k: sum(1 for i in m.items if i.split("-")[0] == k) for k in RTM_KINDS}
  unnamed = sum(1 for i in m.items if i.split("-")[0] in RTM_KINDS and not named.get(i))
  return f"""<section id="annex-d" class="land wide"><h1>D Requirements traceability matrix</h1>
<p class="lead">Every safety goal and safety requirement in the trace data ({', '.join(f'{n} {k}' for k, n in counts.items())}): its ASIL,
allocation, parents and children, the verification methods it states, and the test cases that name it. {unnamed} are named by no case.
Source: assurance/trace/items/. ASIL and allocation are shown without their notes. Every requirement is <i>proposed</i> until a recorded review accepts it; withdrawn ones are marked.</p>
{table(["ID", "ASIL", "Alloc.", "Parents", "Children", "Methods", "Named by cases"], rows, "tbl rtm")}</section>"""
