#!/usr/bin/env python3
"""Clause-check register: standard obligations, in the project's own words, checked against the work products
(assurance/trace/clauses/README.md). Pilot: ISO 26262-3:2018, clauses 5 to 7.

Each obligation of clauses/<register>.yaml names the work product that answers it and the checks that evidence it:
  trace:<ID>      a check of check_trace.py; run here in-process, its errors and known findings (recorded with an
                  owner, such as the K5 baseline) are counted per check ID, and its
                  state (implemented, partly, not implemented) is read from the trace README §6 table
  section:<text>  the work product has a heading containing <text> with content under it
  items:<kind>:<field>[,<field>]  every trace item of that kind has those fields filled
  manual:<what>   human judgement, reported as open

An obligation is `open` when an automated check finds a gap in the work products, `gap` when a check it needs is not
implemented (or it names none), `manual` when its automated checks (if any) pass and a human judgement remains,
`partial` when it rests on a partly implemented trace check, and `pass` otherwise.

The script fails (exit 1) on a broken register: a malformed row, an unknown trace check, a work product, section,
item kind or field that does not exist, or a stale coverage page. An `open` obligation does not fail it: the coverage
page records the status, so a change shows in review, and check_trace.py fails CI on its own errors.

  python3 assurance/trace/tools/check_clauses.py           # check and write clauses/<register>-coverage.md
  python3 assurance/trace/tools/check_clauses.py --check   # check; fail if a coverage page is stale

Needs PyYAML (assurance/trace/requirements.txt, pinned).
"""

from __future__ import annotations

import io
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

import yaml

TOOLS = Path(__file__).resolve().parent
TRACE_DIR = TOOLS.parent
ASSURANCE_DIR = TRACE_DIR.parent
CLAUSES_DIR = TRACE_DIR / "clauses"
TRACE_README = TRACE_DIR / "README.md"
sys.path.insert(0, str(TOOLS))
import check_trace  # noqa: E402

ID_RE = re.compile(r"^O[0-9]+-[0-9]+\.[0-9]{2}$")
WP_RE = re.compile(r"^WP-[A-Z]-[0-9]{2}$")
KEYS = ("id", "clause", "topic", "obligation", "work_product", "checks", "subclause", "source_verified_by",
        "source_verified_date")
RANK = ("open", "gap", "manual", "partial", "pass")      # worst first
MARK = {"pass": "✅ pass", "partial": "🟡 partial", "manual": "👤 manual", "gap": "⬜ gap", "open": "❌ open"}


# ---------------------------------------------------------------- sources

def trace_states(readme: Path = TRACE_README) -> dict[str, str]:
  """Check ID -> 'yes', 'partly' or 'no', from the Implemented column of the README §6 table."""
  states, in_table = {}, False
  for line in readme.read_text().splitlines():
    if line.startswith("| Check | Description"):
      in_table = True
      continue
    if in_table:
      if not line.startswith("|"):
        break
      cells = [c.strip() for c in line.strip("|").split("|")]
      if len(cells) < 4 or set(cells[0]) <= {"-", " "}:
        continue
      cid = cells[0].split()[0].strip("*")
      impl = cells[-1].lower()
      states[cid] = "yes" if impl.startswith("yes") else "partly" if impl.startswith("partly") else "no"
  return states


def trace_errors() -> tuple[dict[str, list[str]], list[dict]]:
  """Run check_trace.py's checks (as its main does) and return, by check ID, its errors and its known findings
  (recorded with an owner, such as the K5 baseline), and the trace items."""
  rep = check_trace.Report()
  items: list[dict] = []
  for f in sorted(check_trace.ITEMS_DIR.glob("*.yaml")):
    items += check_trace.load_yaml(f)
  with redirect_stdout(io.StringIO()):
    by_id = check_trace.check_items(items, rep)
    check_trace.check_links(by_id, rep)
    if check_trace.LINKS.exists():
      check_trace.check_verification_links(by_id, check_trace.load_yaml(check_trace.LINKS), rep)
    check_trace.check_against_hara(by_id, rep)
    check_trace.check_against_itemdef(by_id, rep)
    check_trace.check_requirements_in_sync(rep)
  errors: dict[str, list[str]] = {}
  for e in rep.errors + rep.known:
    m = re.match(r"\[([A-Z][0-9]+)\]", e)
    errors.setdefault(m.group(1) if m else "?", []).append(e)
  return errors, items


def work_product(wp: str) -> Path | None:
  hits = sorted(p for p in ASSURANCE_DIR.rglob(f"{wp}-*.md") if "00-assessment" not in p.parts)
  return hits[0] if hits else None


def sections(md: Path) -> list[tuple[int, str, int]]:
  """(level, heading text, characters of content up to the next heading of the same or a higher level)."""
  lines = md.read_text().splitlines()
  heads = [(i, len(m.group(1)), m.group(2).strip()) for i, line in enumerate(lines)
           if (m := re.match(r"^(#{1,6})\s+(.*)$", line))]
  out = []
  for k, (i, level, text) in enumerate(heads):
    end = next((j for j, lv, _ in heads[k + 1:] if lv <= level), len(lines))
    body = "\n".join(line for line in lines[i + 1:end] if not line.startswith("#"))
    out.append((level, text, len(body.strip())))
  return out


# ---------------------------------------------------------------- evaluation

def evaluate(reg: dict, states: dict[str, str], terrors: dict[str, list[str]], items: list[dict]) -> tuple[list, list]:
  """([(obligation, status, [(check, result, note)])], [register errors])."""
  problems: list[str] = []
  rows = []
  seen: set[str] = set()
  kinds: dict[str, list[dict]] = {}
  for it in items:
    kinds.setdefault(it["kind"], []).append(it)
  for ob in reg.get("obligations") or []:
    oid = ob.get("id", "?")
    missing = [k for k in KEYS if k not in ob]
    if missing:
      problems.append(f"{oid}: missing keys {missing}")
      continue
    if not ID_RE.match(oid) or oid in seen:
      problems.append(f"{oid}: ID malformed or duplicated")
    seen.add(oid)
    if not oid.startswith(f"O{reg['standard'].split('-')[1].split(':')[0]}-{ob['clause']}."):
      problems.append(f"{oid}: ID does not match the standard part and clause {ob['clause']}")
    if not str(ob["obligation"]).strip() or not ob["checks"]:
      problems.append(f"{oid}: empty obligation or no checks")
    wp = ob["work_product"]
    md = work_product(wp) if WP_RE.match(str(wp)) else None
    if md is None:
      problems.append(f"{oid}: work product {wp} not found under assurance/")
    heads = sections(md) if md else []
    results = []
    for chk in ob["checks"]:
      kind, _, arg = str(chk).partition(":")
      if kind == "trace":
        state = states.get(arg)
        if state is None:
          problems.append(f"{oid}: {chk} is not a check of the trace README §6 table")
          continue
        errs = terrors.get(arg, [])
        if state == "no":
          results.append((chk, "gap", "not implemented in check_trace.py"))
        elif errs:
          results.append((chk, "open", f"{len(errs)} finding(s), e.g. {errs[0]}"))
        else:
          results.append((chk, "pass" if state == "yes" else "partial", "passes" if state == "yes"
                          else "passes; check only partly implemented"))
      elif kind == "section":
        hit = next(((lv, t, n) for lv, t, n in heads if arg.lower() in t.lower()), None)
        if md and hit is None:
          problems.append(f"{oid}: {wp} has no heading containing '{arg}'")
          continue
        if hit:
          results.append((chk, "pass" if hit[2] else "open", f"'{hit[1]}'" + ("" if hit[2] else " is empty")))
      elif kind == "items":
        ikind, _, fields = arg.partition(":")
        group = kinds.get(ikind)
        flist = [f for f in fields.split(",") if f]
        if not group or not flist or any(f not in check_trace.REQUIRED.get(ikind, []) for f in flist):
          problems.append(f"{oid}: {chk}: unknown item kind or field")
          continue
        empty = [it["id"] for it in group if any(it.get(f) in (None, "", []) for f in flist)]
        results.append((chk, "open" if empty else "pass",
                        f"{len(empty)} of {len(group)} without " + ", ".join(flist) + (f": {', '.join(empty[:5])}"
                                                                                       if empty else "")))
      elif kind == "manual":
        results.append((chk, "manual", arg))
      else:
        problems.append(f"{oid}: unknown check kind in {chk}")
    auto = [r for _, r, _ in results if r != "manual"]
    has_manual = any(r == "manual" for _, r, _ in results)
    if any(r == "open" for r in auto):
      status = "open"
    elif any(r == "gap" for r in auto) or not (auto or has_manual):
      status = "gap"
    elif has_manual:
      status = "manual"
    else:
      status = min(auto, key=RANK.index)
    rows.append((ob, status, results))
  return rows, problems


def page(reg: dict, src: Path, rows: list) -> str:
  n = len(rows)
  counts = {s: sum(1 for _, st, _ in rows if st == s) for s in RANK}
  verified = sum(1 for ob, _, _ in rows if ob["source_verified_by"])
  head = (f"# {reg['standard']} clause checks: coverage\n\n"
          f"Generated by [`../tools/check_clauses.py`](../tools/check_clauses.py) from "
          f"[`{src.name}`]({src.name}); do not edit. What the statuses mean and how a row is verified: "
          f"[README](README.md).\n\n"
          f"**{n} obligations.** " + ", ".join(f"{MARK[s]}: {counts[s]}" for s in reversed(RANK)) +
          f". **Checked against the licensed standard: {verified} of {n}.**"
          + (" Until a row is verified it is a proposal (I0) and its clause reference is unconfirmed." if verified < n
             else "") + "\n\n")
  table = ["| Obligation | Clause | Topic | Work product | Status | Evidence | Verified |",
           "|---|---|---|---|---|---|---|"]
  for ob, status, results in rows:
    ev = "<br>".join(f"{MARK[r].split()[0]} `{c}`" + (f": {note}" if r not in ("pass", "manual") else "")
                     for c, r, note in results).replace("|", "\\|")
    clause = f"§{ob['clause']}" + (f" ({ob['subclause']})" if ob["subclause"] else "")
    who = f"{ob['source_verified_by']}, {ob['source_verified_date']}" if ob["source_verified_by"] else "no"
    table.append(f"| **{ob['id']}** {ob['obligation']} | {clause} | {ob['topic']} | {ob['work_product']} | "
                 f"{MARK[status]} | {ev} | {who} |")
  return head + "\n".join(table) + "\n"


def main(argv: list[str]) -> int:
  check = "--check" in argv
  states = trace_states()
  terrors, items = trace_errors()
  bad = 0
  for src in sorted(CLAUSES_DIR.glob("*.yaml")):
    reg = yaml.safe_load(src.read_text())
    rows, problems = evaluate(reg, states, terrors, items)
    for p in problems:
      print(f"ERROR {src.name}: {p}")
    bad += len(problems)
    out = src.with_name(src.stem + "-coverage.md")
    text = page(reg, src, rows)
    if check and (not out.exists() or out.read_text() != text):
      print(f"ERROR {out.name} is stale: run check_clauses.py without --check")
      bad += 1
    elif not check:
      out.write_text(text)
    summary = ", ".join(f"{s} {sum(1 for _, st, _ in rows if st == s)}" for s in reversed(RANK))
    print(f"{src.name}: {len(rows)} obligations ({summary}); "
          f"{sum(1 for ob, _, _ in rows if ob['source_verified_by'])} verified against the standard")
  if bad:
    print(f"FAILED: {bad} error(s)")
    return 1
  print("OK: register consistent" + (", coverage pages current" if check else ", coverage pages written"))
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
