#!/usr/bin/env python3
"""Export work products with their document control stamped from the change ledger (WP-P-04 §5, §6, OI-7; DQ-441).

The Markdown file of a work product carries no authoritative version: the ledger does. An exported copy gets
  - a document-control block on page 1: ID, title, version, status, effective date, author, reviewer, approver,
    content commit, ledger row and copy;
  - a running footer on every page: ID, version, status, commit, copy, page n of N (PDF; Markdown gets one line);
  - a revision history at the end: every ledger row that set a version, then the history written in the header
    before the ledger existed.
The control table at the top of the source file is replaced by the generated block.

Formats: md (Markdown), html (self-contained, images inlined), pdf (html printed by render_export.cjs).

A rendering error must not drop content from a controlled copy, so every export is checked: every word of the
source body has to appear in the rendered text as often as in the source (check_complete). A failed check writes
nothing.

With --since, the export also writes a change record (change-record.<format>): for each selected document the
version then and now, and every recorded change in between with its PR, class and approver. --since takes
`last-copy` (the latest issued copy to --recipient in distribution.yaml), a copy ID, a date or a commit or tag.
Every export writes manifest.json: the commit, copy, versions and the SHA-256 of every file.

Usage:
  export_wp.py WP-S-02 [WP-W-02 ...] --format md|html|pdf --out DIR [--copy CC-YYYY-NNN] [--ledger FILE]
            [--commit REF] [--since SPEC [--recipient TEXT]]
  export_wp.py WP-S-02 [...] --versions     prints "WP-S-02 0.68.0,..." for the distribution record
Without --ledger the ledger is read from the `ledger` branch (origin/ledger). Before its first run there is none:
the version is then the one in the header, and the copy says so.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html as htmllib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ledger  # noqa: E402

REPO = HERE.parents[2]
UNCONTROLLED = "Uncontrolled copy: check the current version before use"
CONTROL_FIELDS = ("Work product", "Standard reference", "Status", "ASIL / scope", "Author", "Reviewer(s)", "Approver")


# ---------------------------------------------------------------------------------------------------- source

def split_source(text: str) -> tuple[str, dict[str, str], str]:
  """(title, control fields, body) of a work product's Markdown: the first table with a Version row is the header."""
  lines = text.splitlines()
  title = next((l[2:].strip() for l in lines if l.startswith("# ")), "")
  fields: dict[str, str] = {}
  start = end = None
  for i, line in enumerate(lines):
    if re.match(r"^\|\s*Version\s*\|", line):
      start = i
      while start > 0 and lines[start - 1].startswith("|"):
        start -= 1
      end = i
      while end + 1 < len(lines) and lines[end + 1].startswith("|"):
        end += 1
      break
  if start is None:
    return title, fields, text
  for line in lines[start:end + 1]:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) >= 2 and not re.match(r"^-+$", cells[0]) and cells[0] not in ("Field",):
      fields[cells[0]] = "|".join(cells[1:]).strip()
  body = lines[:start] + lines[end + 1:]
  body = [l for l in body if not (l.startswith("# ") and l[2:].strip() == title)]
  return title, fields, "\n".join(body).strip() + "\n"


def header_history(version_field: str) -> list[tuple[str, str]]:
  """'0.4 (text (nested); date). 0.3 (text). 0.1' -> [('0.4', 'text (nested); date'), ('0.3', 'text'), ('0.1', '')]"""
  out, i, s = [], 0, version_field.strip()
  num = re.compile(r"v?(\d+\.\d+(?:\.\d+)?)")
  while i < len(s):
    m = num.match(s, i)
    if not m:
      break
    ver, i, note = m.group(1), m.end(), ""
    while i < len(s) and s[i] == " ":
      i += 1
    if i < len(s) and s[i] == "(":
      depth, j = 0, i
      while j < len(s):
        depth += {"(": 1, ")": -1}.get(s[j], 0)
        if depth == 0:
          break
        j += 1
      note, i = s[i + 1:j], j + 1
    out.append((ver, note.strip()))
    while i < len(s) and s[i] in ". ":
      i += 1
  return out


def plain(md_text: str) -> str:
  """The text a reader sees, for the completeness check."""
  t = re.sub(r"<!--.*?-->", " ", md_text, flags=re.S)
  t = re.sub(r"!\[([^\]]*)\]\([^)]*\)", " ", t)
  t = re.sub(r"\]\([^)]*\)", "]", t)
  t = re.sub(r"</?[A-Za-z][^<>\n]*>", " ", t)  # real tags only: a bare "<" or "≤" in the text stays text
  t = re.sub(r"^(\s*)(```|~~~)[^\n]*$", r"\1", t, flags=re.M)  # fence lines and their info string (```mermaid)
  return htmllib.unescape(t)


def tokens(text: str) -> Counter:
  return Counter(w.lower() for w in re.findall(r"[A-Za-z0-9]{3,}", text))


def check_complete(source_body: str, rendered_text: str) -> list[str]:
  missing = tokens(plain(source_body)) - tokens(rendered_text)
  return [f"{w} (x{n})" for w, n in sorted(missing.items())]


# ---------------------------------------------------------------------------------------------------- ledger

def doc_versions(rows: list[dict] | None, doc: str, header_version_field: str) -> dict:
  """Current version of a document, the row that set it, and its history of versions from the ledger."""
  if rows is None:
    m = re.match(r"v?(\d+)\.(\d+)(?:\.(\d+))?", header_version_field.strip())
    v = f"{int(m.group(1))}.{int(m.group(2))}.{int(m.group(3) or 0)}" if m else "0.1.0"
    return {"version": v, "row": None, "history": [], "source": "header (the ledger has no rows yet)"}
  history = [r for r in rows if (r.get("documents") or {}).get(doc)]
  if not history:
    return {"version": None, "row": None, "history": [], "source": "not in the ledger"}
  return {"version": history[-1]["documents"][doc], "row": history[-1], "history": history, "source": "ledger"}


# ---------------------------------------------------------------------------------------------------- one document

def git(*args: str) -> str:
  return subprocess.run(["git", *args], cwd=REPO, check=True, capture_output=True, text=True).stdout


def find_doc(doc: str, commit: str) -> str:
  docs = ledger.documents_at(commit, REPO)
  if doc not in docs:
    raise SystemExit(f"{doc}: no work product with that ID at {commit[:8]}")
  return docs[doc]


def control(doc: str, commit: str, rows: list[dict] | None, copy: str | None) -> dict:
  path = find_doc(doc, commit)
  text = git("show", f"{commit}:{path}")
  title, fields, body = split_source(text)
  title = re.sub(rf"^{re.escape(doc)}\s*", "", title)
  pending = 0
  if rows is not None:
    # only the rows this commit's history contains: an older commit gets the version it had, and changes the
    # ledger has not recorded yet (a branch, or a merge whose ledger run is pending) are counted, not hidden
    history = set(ledger.first_parent_commits(commit, REPO))
    rows = [r for r in rows if r["commit"] in history]
    if rows:
      pending = int(git("rev-list", "--count", "--first-parent", f"{rows[-1]['commit']}..{commit}", "--", path).strip())
  v = doc_versions(rows, doc, fields.get("Version", ""))
  if v["version"] is None:
    raise SystemExit(f"{doc}: not in the ledger; it is added at the next merge that touches it")
  if copy and (pending or v["source"] != "ledger"):
    raise SystemExit(f"{doc}: a controlled copy needs a version the ledger has recorded "
                     f"({'changes not yet recorded' if pending else v['source']})")
  status = re.sub(r"[*`]", "", fields.get("Status", "")).split("(")[0].strip() or "—"
  row = v["row"]
  if row is None or row["kind"] == "seed":  # the date the content last changed, not the date the ledger started
    effective = git("log", "-1", "--format=%cs", row["commit"] if row else commit, "--", path).strip()
  else:
    effective = row["date"][:10]
  version = v["version"] + (f"+{pending}" if pending else "")
  return {"doc": doc, "title": title, "path": path, "fields": fields, "body": body, "version": version,
          "status": status, "commit": commit, "copy": copy, "version_source": v["source"], "pending": pending,
          "effective": effective,
          "ledger_row": f"{row['seq']} · {row['hash'][:12]}" if row else "—",
          "history": v["history"], "pre_ledger": header_history(fields.get("Version", ""))}


def footer_line(c: dict) -> str:
  copy = f"Controlled copy {c['copy']}" if c["copy"] else UNCONTROLLED
  return f"{c['doc']} · v{c['version']} · {c['status']} · {c['commit'][:8]} | {copy}"


def block_rows(c: dict) -> list[tuple[str, str]]:
  f = c["fields"]
  rows = [("Document", f"{c['doc']} {c['title']}"),
          ("Version", f"{c['version']} ({'X = 0: not yet approved at a gate' if c['version'].startswith('0.') else 'approved at a gate'})"
                      + ("" if c["version_source"] == "ledger" else f"; from the {c['version_source']}")
                      + (f"; +{c['pending']}: changes the ledger has not recorded yet, draft only" if c["pending"] else "")),
          ("Status", c["status"]), ("Effective", c["effective"])]
  for k in ("Standard reference", "ASIL / scope", "Author", "Reviewer(s)", "Approver"):
    if f.get(k):
      rows.append((k, f[k]))
  rows += [("Content commit", c["commit"][:12]), ("Ledger row", c["ledger_row"]),
           ("Copy", f"Controlled copy {c['copy']}" if c["copy"] else UNCONTROLLED)]
  return rows


def history_rows(c: dict) -> list[list[str]]:
  out = []
  for r in reversed(c["history"]):
    gh = r.get("github") or {}
    approved = ", ".join(gh.get("approved_by", [])) or ("gate " + ", ".join(a["gate"] for a in r["approvals"])
                                                         if r.get("approvals") else "—")
    kind = "seed: version taken from the header" if r["kind"] == "seed" else r["title"]
    out.append([r["documents"][c["doc"]], r["date"][:10], f"#{r['pr']}" if r.get("pr") else "—", kind, approved])
  return out


def esc_cell(s: str) -> str:
  return s.replace("|", "\\|").replace("\n", " ")


def to_markdown(c: dict) -> str:
  out = [f"# {c['doc']} {c['title']}", "", "| Document control | |", "|---|---|"]
  out += [f"| {k} | {esc_cell(v)} |" for k, v in block_rows(c)]
  out += ["", "*Document control generated from the change ledger at export (WP-P-04 §5). Nothing in it is typed.*",
          "", c["body"].rstrip(), "", "## Revision history", ""]
  hist = history_rows(c)
  if hist:
    out += ["| Version | Date | PR | Change | Approved by |", "|---|---|---|---|---|"]
    out += ["| " + " | ".join(esc_cell(x) for x in r) + " |" for r in hist]
  if c["pre_ledger"]:
    out += ["", "Before the ledger (from the document's header):", "", "| Version | Note |", "|---|---|"]
    out += [f"| {v} | {esc_cell(n) or '—'} |" for v, n in c["pre_ledger"]]
  out += ["", "---", "", footer_line(c), ""]
  return "\n".join(out)


def inline_images(html_text: str, base: Path) -> str:
  def repl(m):
    src = m.group(2)
    if re.match(r"^(https?:|data:)", src):
      return m.group(0)
    p = (base / src.split("#")[0]).resolve()
    if not p.is_file() or not p.is_relative_to(REPO):
      return m.group(0)
    mime = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".gif": "image/gif"}.get(p.suffix.lower())
    if not mime:
      return m.group(0)
    return f'{m.group(1)}data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"'
  return re.sub(r'(<img[^>]*?src=")([^"]+)"', repl, html_text)


CSS = """
@page{size:A4;margin:16mm 16mm 22mm}
body{font:10.5pt/1.45 Inter,Helvetica,Arial,sans-serif;color:#0F172A;max-width:900px;margin:0 auto;padding:24px}
@media print{body{padding:0;max-width:none}}
h1{font-size:19pt;margin:0 0 10px}h2{font-size:13.5pt;margin:22px 0 6px}h3{font-size:11.5pt;margin:16px 0 4px}
table{border-collapse:collapse;width:100%;margin:8px 0;font-size:9pt}th,td{border:1px solid #E2E8F0;padding:4px 6px;
text-align:left;vertical-align:top}th{background:#F8FAFC}img{max-width:100%}code{font-size:9pt;background:#F1F5F9;
padding:0 3px;border-radius:3px}a{color:#1D4ED8;text-decoration:none}
table.dc td:first-child{background:#F8FAFC;color:#475569;width:150px;font-weight:600}
.note{color:#475569;font-size:9pt}table.cr td:nth-child(2){white-space:nowrap}.foot{border-top:1px solid #CBD5E1;margin-top:24px;padding-top:6px;color:#475569;
font-size:8.5pt}@media print{.foot{display:none}}
"""


def to_html(c: dict) -> str:
  import markdown
  md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])
  body_html = inline_images(md.convert(c["body"]), (REPO / c["path"]).parent)
  e = htmllib.escape
  dc = "".join(f"<tr><td>{e(k)}</td><td>{e(v)}</td></tr>" for k, v in block_rows(c))
  hist = history_rows(c)
  hist_html = ""
  if hist:
    hist_html += ("<table><tr><th>Version</th><th>Date</th><th>PR</th><th>Change</th><th>Approved by</th></tr>"
                  + "".join("<tr>" + "".join(f"<td>{e(x)}</td>" for x in r) + "</tr>" for r in hist) + "</table>")
  if c["pre_ledger"]:
    hist_html += ("<p class='note'>Before the ledger (from the document's header):</p><table><tr><th>Version</th>"
                  "<th>Note</th></tr>" + "".join(f"<tr><td>{e(v)}</td><td>{e(n) or '—'}</td></tr>"
                                                  for v, n in c["pre_ledger"]) + "</table>")
  return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(c['doc'])} v{e(c['version'])} {e(c['title'])}</title><style>{CSS}</style></head><body>
<h1>{e(c['doc'])} {e(c['title'])}</h1>
<table class="dc">{dc}</table>
<p class="note">Document control generated from the change ledger at export (WP-P-04 §5). Nothing in it is typed.</p>
<main>{body_html}</main>
<h2>Revision history</h2>{hist_html}
<div class="foot">{e(footer_line(c))}</div>
</body></html>
"""


def rendered_text(fmt: str, out: str) -> str:
  if fmt == "md":
    return plain(out)
  return htmllib.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<style.*?</style>", " ", out, flags=re.S)))


def versions_at(commit: str, rows: list[dict] | None) -> tuple[dict[str, str], str]:
  """Version of every work product at a commit, as an export would stamp it, and where it came from."""
  commit = git("rev-parse", commit).strip()
  docs = ledger.documents_at(commit, REPO)
  if rows is None:
    return {d: ledger.header_version(commit, p, REPO) for d, p in docs.items()}, "the headers: the change ledger has no rows yet"
  history = set(ledger.first_parent_commits(commit, REPO))
  rows = [r for r in rows if r["commit"] in history]
  current = ledger.current_versions(rows)
  out = {}
  for d, p in docs.items():
    if d not in current:
      out[d] = ledger.header_version(commit, p, REPO) + " (header)"
      continue
    n = int(git("rev-list", "--count", "--first-parent", f"{rows[-1]['commit']}..{commit}", "--", p).strip())
    out[d] = current[d] + (f"+{n}" if n else "")
  return out, "the change ledger; +N counts changes it has not recorded yet"


def distribution_module():
  sys.path.insert(0, str(HERE.parents[1] / "case-records" / "tools"))
  import distribution
  return distribution


# ---------------------------------------------------------------------------------------------------- change record

def resolve_since(spec: str | None, recipient: str | None, copy: str | None, commit: str) -> dict | None:
  """Where the change record starts: the recipient's last copy, a copy ID, a date, or a commit or tag."""
  if not spec:
    return None
  if spec == "last-copy":
    if not recipient:
      raise SystemExit("--since last-copy needs --recipient")
    prev = distribution_module().last_copy_to(recipient, exclude=copy)
    if prev is None:
      return {"spec": spec, "commit": None, "label": f"first copy to {recipient}: every recorded change is listed"}
    return {"spec": spec, "commit": prev["based_on"], "copy": prev["id"],
            "label": f"since copy {prev['id']} to {prev['recipient']} ({prev['issued_at'][:10]}, commit {prev['based_on'][:8]})"}
  if re.fullmatch(r"CC-\d{4}-\d{3}", spec):
    prev = next((c for c in distribution_module().load() if c.get("id") == spec), None)
    if prev is None:
      raise SystemExit(f"{spec} is not in the distribution record")
    return {"spec": spec, "commit": prev["based_on"], "copy": spec,
            "label": f"since copy {spec} ({prev['issued_at'][:10]}, commit {prev['based_on'][:8]})"}
  if re.fullmatch(r"\d{4}-\d{2}-\d{2}", spec):
    sha = git("rev-list", "-1", "--first-parent", f"--before={spec}T23:59:59Z", commit).strip()
    if not sha:
      return {"spec": spec, "commit": None, "label": f"since {spec}: no commit before that date, every recorded change is listed"}
    return {"spec": spec, "commit": sha, "label": f"since {spec} (commit {sha[:8]})"}
  sha = git("rev-parse", f"{spec}^{{commit}}").strip()
  return {"spec": spec, "commit": sha, "label": f"since {spec} (commit {sha[:8]})"}


def change_record(controls: list[dict], rows: list[dict] | None, since: dict, commit: str) -> dict:
  """Per document: version then and now, and every ledger row in between that touched it."""
  base = set(ledger.first_parent_commits(since["commit"], REPO)) if since["commit"] else set()
  history = set(ledger.first_parent_commits(commit, REPO))
  was = versions_at(since["commit"], rows)[0] if since["commit"] else {}
  docs = []
  for c in controls:
    changes = []
    for r in rows or []:
      if r["commit"] in history and r["commit"] not in base and c["doc"] in (r.get("documents") or {}) \
         and r["kind"] != "seed":
        gh = r.get("github")
        changes.append({"version": r["documents"][c["doc"]] or "before the ledger", "date": r["date"][:10],
                        "pr": r.get("pr"), "title": r["title"],
                        "class": ", ".join(l for l in gh["labels"] if l in ledger.CLASSES) if gh else "not recorded",
                        "approved_by": ", ".join(gh["approved_by"]) if gh and gh["approved_by"] else
                                       ("—" if gh else "not recorded")})
    safety = sum(1 for ch in changes if any(k in ch["class"] for k in ledger.SAFETY_CLASSES))
    unknown = sum(1 for ch in changes if ch["class"] == "not recorded")
    docs.append({"doc": c["doc"], "title": c["title"], "was": was.get(c["doc"], "—" if since["commit"] else "—"),
                 "now": c["version"], "changes": changes, "safety": safety, "unknown_class": unknown})
  return {"since": since, "commit": commit, "documents": docs}


def change_record_rows(cr: dict) -> tuple[list[list[str]], list[tuple[str, list[list[str]]]]]:
  def safety(d):
    if d["changes"] and d["unknown_class"] == len(d["changes"]):
      return "not recorded"
    return str(d["safety"]) + (f" (+{d['unknown_class']} not recorded)" if d["unknown_class"] else "")
  summary = [[d["doc"] + " " + d["title"], d["was"], d["now"], str(len(d["changes"])), safety(d)]
             for d in cr["documents"]]
  details = [(d["doc"], [[ch["version"], ch["date"], f"#{ch['pr']}" if ch["pr"] else "—", ch["title"], ch["class"],
                          ch["approved_by"]] for ch in d["changes"]]) for d in cr["documents"]]
  return summary, details


def change_record_md(cr: dict, copy: str | None) -> str:
  summary, details = change_record_rows(cr)
  out = ["# Change record", "", f"{len(summary)} work product(s), {cr['since']['label']}, up to commit {cr['commit'][:12]}. "
         f"{'Controlled copy ' + copy if copy else UNCONTROLLED}.", "",
         "| Work product | Was | Now | Changes | Safety-class changes |", "|---|---|---|---|---|"]
  out += ["| " + " | ".join(esc_cell(x) for x in r) + " |" for r in summary]
  for doc, rows in details:
    out += ["", f"## {doc}", ""]
    if rows:
      out += ["| Version | Date | PR | Change | Class | Approved by |", "|---|---|---|---|---|---|"]
      out += ["| " + " | ".join(esc_cell(x) for x in r) + " |" for r in rows]
    else:
      out += ["No change recorded in this period."]
  out += ["", "*Generated from the change ledger at export (WP-P-04 §6). \"Not recorded\": the change predates the "
          "ledger's GitHub data.*", "", "---", "", f"Change record · {cr['commit'][:8]} | "
          + (f"Controlled copy {copy}" if copy else UNCONTROLLED), ""]
  return "\n".join(out)


def change_record_html(cr: dict, copy: str | None) -> str:
  summary, details = change_record_rows(cr)
  e = htmllib.escape
  def tbl(head, rows):
    return ("<table class='cr'><tr>" + "".join(f"<th>{e(h)}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{e(x)}</td>" for x in r) + "</tr>" for r in rows) + "</table>")
  parts = [f"<h1>Change record</h1><p class='note'>{len(summary)} work product(s), {e(cr['since']['label'])}, up to "
           f"commit {e(cr['commit'][:12])}. {e('Controlled copy ' + copy if copy else UNCONTROLLED)}.</p>",
           tbl(["Work product", "Was", "Now", "Changes", "Safety-class changes"], summary)]
  for doc, rows in details:
    parts.append(f"<h2>{e(doc)}</h2>" + (tbl(["Version", "Date", "PR", "Change", "Class", "Approved by"], rows)
                                          if rows else "<p class='note'>No change recorded in this period.</p>"))
  parts.append("<p class='note'>Generated from the change ledger at export (WP-P-04 §6). \u201cNot recorded\u201d: "
               "the change predates the ledger's GitHub data.</p>")
  return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,"
          f"initial-scale=1'><title>Change record</title><style>{CSS}</style></head><body>{''.join(parts)}"
          f"<div class='foot'>{e('Change record · ' + cr['commit'][:8])}</div></body></html>\n")


# ---------------------------------------------------------------------------------------------------- export

def export(docs: list[str], fmt: str, out_dir: Path, copy: str | None = None, rows: list[dict] | None = None,
           commit: str = "HEAD", since: str | None = None, recipient: str | None = None) -> list[Path]:
  commit = git("rev-parse", commit).strip()
  if copy:  # no controlled copy without its distribution record (WP-P-04 §9.1)
    distribution_module().find(copy)
  since_info = resolve_since(since, recipient, copy, commit)
  out_dir.mkdir(parents=True, exist_ok=True)
  written, controls, footers = [], [], {}
  for doc in docs:
    c = control(doc, commit, rows, copy)
    text = to_markdown(c) if fmt == "md" else to_html(c)
    missing = check_complete(c["body"], rendered_text(fmt, text))
    if missing:
      raise SystemExit(f"{doc}: the rendered copy lost text, nothing written: {', '.join(missing[:12])}")
    path = out_dir / f"{doc}-v{c['version']}.{'md' if fmt == 'md' else 'html'}"
    path.write_text(text, encoding="utf-8")
    footers[path] = footer_line(c)
    written.append(path)
    controls.append(c)
  if since_info is not None:
    cr = change_record(controls, rows, since_info, commit)
    path = out_dir / f"change-record.{'md' if fmt == 'md' else 'html'}"
    path.write_text(change_record_md(cr, copy) if fmt == "md" else change_record_html(cr, copy), encoding="utf-8")
    footers[path] = f"Change record · {commit[:8]} | " + (f"Controlled copy {copy}" if copy else UNCONTROLLED)
    written.insert(0, path)
  if fmt == "pdf":
    for path in written:
      path.with_suffix(".footer.txt").write_text(footers[path], encoding="utf-8")
    subprocess.run(["node", str(HERE / "render_export.cjs"), *map(str, written)], check=True)
    written = [p.with_suffix(".pdf") for p in written]
  manifest = {"commit": commit, "copy": copy, "format": fmt,
              "since": since_info and {k: since_info.get(k) for k in ("spec", "commit", "copy", "label")},
              "documents": {c["doc"]: {"version": c["version"], "file": p.name,
                                       "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                            for c, p in zip(controls, written[-len(controls):])}}
  if since_info is not None:
    manifest["change_record"] = {"file": written[0].name, "sha256": hashlib.sha256(written[0].read_bytes()).hexdigest()}
  (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
  return written


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("docs", nargs="+")
  ap.add_argument("--format", choices=["md", "html", "pdf"], default="md")
  ap.add_argument("--out", type=Path, required=True)
  ap.add_argument("--copy")
  ap.add_argument("--ledger", type=Path)
  ap.add_argument("--commit", default="HEAD")
  ap.add_argument("--since", help="last-copy (with --recipient), CC-YYYY-NNN, YYYY-MM-DD, or a commit or tag")
  ap.add_argument("--recipient")
  ap.add_argument("--versions", action="store_true", help="print 'WP-x-nn X.Y.Z' for the documents and exit")
  a = ap.parse_args(argv)
  rows = ledger.load(a.ledger) if a.ledger else ledger.load_ref("origin/ledger", REPO)
  if a.versions:
    print(",".join(f"{d} {control(d, git('rev-parse', a.commit).strip(), rows, None)['version']}" for d in a.docs))
    return 0
  for p in export(a.docs, a.format, a.out, a.copy, rows, a.commit, a.since, a.recipient):
    print(f"wrote {p}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
