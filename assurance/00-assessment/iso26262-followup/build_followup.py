#!/usr/bin/env python3
"""Build advisory documentary views from immutable Git objects; --check detects drift."""

import argparse
import csv
import datetime
import hashlib
import html
import io
import json
from pathlib import Path
import re
import subprocess
import tempfile

import xlsxwriter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = '20569e916c9359243739b71e4dc79876aec48cc0'
DOCS = {
  'S-08': '03-system/WP-S-08-system-integration-test.md',
  'S-09': '03-system/WP-S-09-system-verification.md',
  'H-06': '04-hardware/WP-H-06-hardware-integration-verification.md',
  'W-06': '05-software/WP-W-06-software-unit-verification.md',
  'W-07': '05-software/WP-W-07-software-integration-verification.md',
  'W-08': '05-software/WP-W-08-embedded-software-testing.md',
  'W-10': '05-software/WP-W-10-ml-engineering.md',
  'V-01': '06-validation/WP-V-01-safety-validation.md',
  'V-05': '06-validation/WP-V-05-fault-injection.md',
}


def git(*args):
  return subprocess.check_output(['git', '-C', str(ROOT), *args])


def digest(data):
  return hashlib.sha256(data).hexdigest()


def dump(path, value):
  path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def build(out):
  config = json.loads((HERE / 'findings.json').read_text())
  revision = config['subject_revision']
  sources = {}

  def source(path):
    raw = git('show', f'{revision}:{path}')
    sources[path] = digest(raw)
    return raw.decode()

  def citation(path, needle):
    lines = source(path).splitlines()
    matches = [(i, s) for i, s in enumerate(lines, 1) if needle in s]
    if len(matches) != 1:
      raise ValueError(f'Expected one source anchor: {path}: {needle}')
    line, quote = matches[0]
    return {
      'source_path': path,
      'line': line,
      'quote_exact': quote,
      'sha256': sources[path],
      'url': f'https://github.com/jherrodthomas/LionDriver/blob/{revision}/{path}#L{line}',
    }

  findings = []
  for item in config['findings']:
    row = dict(item)
    row['citation'] = citation(row['source_path'], row['anchor'])
    findings.append(row)
  corroboration = [
    ('B02', 'assurance/04-hardware/reviews/RR-2026-010.md', '| FMEDA SG-001 / SG-009 rev 0.3 |'),
    ('B03', 'assurance/06-validation/WP-V-05-fault-injection.md', '| SG-02, SG-06 |'),
    ('B03', 'assurance/06-validation/WP-V-05-fault-injection.md', '| VS-FI-09 | Process kill'),
    ('B04', 'assurance/06-validation/WP-V-05-fault-injection.md', '| OI-6 |'),
    ('B05', 'assurance/04-hardware/reviews/RR-2026-010.md', '# RR-2026-010 Review record'),
  ]
  for fid, path, needle in corroboration:
    next(f for f in findings if f['id'] == fid).setdefault('corroboration', []).append(citation(path, needle))
  crosswalk = []
  old = json.loads(git('show', f'{revision}:assurance/00-assessment/iso26262-2018/annotations.json'))
  for a in old['annotations']:
    text = source(a['source_path'])
    matches = [i for i, line in enumerate(text.splitlines(), 1) if line == a['quote_exact']]
    same = sources[a['source_path']] == a['source_sha256']
    crosswalk.append(
      {
        'finding': a['finding_id'],
        'source_path': a['source_path'],
        'old_revision': BASE,
        'current_revision': revision,
        'old_sha256': a['source_sha256'],
        'current_sha256': sources[a['source_path']],
        'source_changed': not same,
        'exact_quote_lines': ','.join(map(str, matches)),
        'disposition': 'Source unchanged; finding remains open' if same else 'Source changed; re-evaluate finding; no closure credit',
      }
    )
  changed_paths = git('diff', '--name-only', BASE, revision, '--', 'assurance').decode().splitlines()
  drift = []
  for path in changed_paths:
    if re.search(r'/WP-[A-Z]-\d+[^/]*\.md$', path):
      source(path)
      drift.append(
        {
          'source_path': path,
          'old_revision': BASE,
          'current_revision': revision,
          'current_sha256': sources[path],
          'disposition': 'Re-assessment required; baseline is not interchangeable',
        }
      )
  cases, summary = [], []
  for wp, suffix in DOCS.items():
    path = 'assurance/' + suffix
    heading = ''
    docrows = []
    for n, line in enumerate(source(path).splitlines(), 1):
      if line.startswith('## '):
        heading = line
      match = re.match(r'^\| (VS-[A-Z]+-[A-Z]?\d+(?:\s*…\s*(?:VS-[A-Z]+-)?[A-Z]?\d+)?) \|', line)
      if match:
        label = match[1]
        start = re.match(r'(VS-[A-Z]+-[A-Z]?)(\d+)', label)
        end = int(re.search(r'(\d+)$', label)[1])
        expanded = [start[1] + str(i).zfill(len(start[2])) for i in range(int(start[2]), end + 1)]
        report = bool(re.search(r'\b(report|results)\b', heading, re.I))
        row = {
          'work_product': 'WP-' + wp,
          'case_id': label,
          'expanded_ids': ','.join(expanded),
          'kind': 'Report row' if report else 'Specification/reference row',
          'recorded_status': 'Not yet executed'
          if report and 'Not yet executed' in line
          else 'Requires manual interpretation'
          if report
          else 'Specification only',
          'source_path': path,
          'line': n,
          'section': heading,
          'quote_exact': line,
          'normative_verdict': 'Not assessed',
        }
        cases.append(row)
        docrows.append(row)
    specs = {i for r in docrows if r['kind'] != 'Report row' for i in r['expanded_ids'].split(',')}
    reports = {i for r in docrows if r['kind'] == 'Report row' for i in r['expanded_ids'].split(',')}
    notrun = {i for r in docrows if r['recorded_status'] == 'Not yet executed' for i in r['expanded_ids'].split(',')}
    summary.append(
      {
        'work_product': 'WP-' + wp,
        'specified_ids': len(specs),
        'report_ids': len(reports),
        'explicitly_not_executed': len(notrun),
        'ids_without_report_row': ','.join(sorted(specs - reports)),
        'limitation': 'Counts are documentary, not executed/accepted test coverage',
      }
    )
  data = {
    'record': config['record'],
    'revision': config['revision'],
    'subject_revision': revision,
    'normative_verdict': 'Not assessed',
    'findings': findings,
    'baseline_crosswalk': crosswalk,
    'test_summary': summary,
    'test_rows': cases,
    'changed_work_products': drift,
    'source_sha256': sources,
  }
  dump(out / 'assessment.json', data)
  for name, rows in [('test_rows', cases), ('test_summary', summary), ('baseline_crosswalk', crosswalk), ('changed_work_products', drift)]:
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    (out / f'{name}.csv').write_text(stream.getvalue())
  wb = xlsxwriter.Workbook(out / 'Assessment_followup.xlsx', {'strings_to_formulas': False, 'strings_to_urls': False})
  wb.set_properties({'title': 'ARA-26262-2018-002 v0.1 Draft', 'author': 'Codex (OpenAI), I0', 'created': datetime.datetime(2026, 10, 15)})
  readme = [
    {'field': k, 'value': v}
    for k, v in {
      'Record': config['record'],
      'Revision': '0.1 Draft; human review pending',
      'Subject': revision,
      'Normative verdict': 'Not assessed; licensed source unavailable',
      'Distribution': 'Uncontrolled generated view; JSON/CSV source records control',
      'Test counts': 'Documentary specification/report rows only; no execution or acceptance inferred',
      'Assessor': 'Codex (OpenAI), I0; not an appointed independent FSA assessor',
    }.items()
  ]
  flat = [{k: v for k, v in f.items() if k not in ('citation', 'corroboration')} | {'source_line': f['citation']['line']} for f in findings]
  for name, rows in [
    ('Read me', readme),
    ('Findings and author tasks', flat),
    ('Baseline crosswalk', crosswalk),
    ('Test readiness', summary),
    ('Exact test rows', cases),
    ('Changed work products', drift),
  ]:
    sheet = wb.add_worksheet(name)
    keys = list(rows[0])
    sheet.write_row(0, 0, keys, wb.add_format({'bold': True, 'bg_color': '#e0e8f0'}))
    for i, row in enumerate(rows, 1):
      sheet.write_row(i, 0, [str(row[k]) if row[k] is not None else 'Unassigned' for k in keys])
    sheet.freeze_panes(1, 0)
    sheet.autofilter(0, 0, len(rows), len(keys) - 1)
    sheet.set_column(0, len(keys) - 1, 26)
  wb.close()
  e = html.escape
  cards = []
  for f in findings:
    quotes = ''.join(
      f'<p><a href="{e(c["url"])}">{e(c["source_path"])}:{c["line"]}</a></p><pre><mark>{e(c["quote_exact"])}</mark></pre>'
      for c in [f['citation']] + f.get('corroboration', [])
    )
    cards.append(
      f'<article><h2><span class="circle">{f["id"]}</span> {e(f["title"])}</h2><p>{e(f["priority"])} · Open · Normative: Not assessed</p>{quotes}<p>{e(f["analysis"])}</p><h3>Author action</h3><p>{e(f["author_action"])}</p><h3>Human closure evidence</h3><p>{e(f["closure_evidence"])}</p></article>'  # noqa: E501 - embedded HTML/SVG template
    )
  page = (
    '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Assessment follow-up</title><style>body{font:17px system-ui;max-width:1100px;margin:2em auto;padding:1em;color:#182534}article{border:2px solid #956100;border-radius:16px;padding:1em;margin:1em 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}mark{background:#fff0b0;color:#182534}.circle{display:inline-block;border:3px solid #a52c20;border-radius:50%;padding:.3em}button{padding:.7em}@media print{button{display:none}article{break-inside:avoid}}</style><h1>ARA-26262-2018-002 v0.1 — Draft</h1><p>Codex (OpenAI), I0. Human verification pending. Uncontrolled generated view. Highlighting identifies source passages, not ISO nonconformity.</p><p>Subject: '  # noqa: E501 - embedded HTML/SVG template
    + revision
    + '</p><button onclick="window.print()">Print annotated review</button>'
    + ''.join(cards)
    + '</html>'
  )
  (out / 'Annotated_followup.html').write_text(page)
  svg = [
    '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="640" viewBox="0 0 1000 640"><rect width="1000" height="640" fill="white"/><g font-family="sans-serif" fill="#182534"><text x="30" y="35" font-size="24">Documented verification readiness — Draft I0</text><text x="30" y="65" font-size="15">Specified case IDs / IDs explicitly unexecuted in report rows / IDs without report rows</text>'  # noqa: E501 - embedded HTML/SVG template
  ]
  for i, row in enumerate(summary):
    y = 105 + i * 48
    n = row['specified_ids']
    u = row['explicitly_not_executed']
    missing = n - row['report_ids']
    svg.append(
      f'<text x="30" y="{y + 18}" font-size="17">{row["work_product"]}</text><rect x="160" y="{y}" width="{n * 15}" height="25" fill="#d7e4ef"/><rect x="160" y="{y}" width="{u * 15}" height="25" fill="#f4c36b"/><text x="660" y="{y + 18}" font-size="16">{n} specified; {u} unexecuted; {missing} no row</text>'  # noqa: E501 - embedded HTML/SVG template
    )
  svg.append(
    '<text x="30" y="565" font-size="16">Amber = explicit unexecuted report IDs. Blue = specified IDs without report rows.</text><text x="30" y="595" font-size="16">No execution, acceptance, ISO coverage or compliance percentage is inferred.</text><text x="30" y="620" font-size="13">ARA-26262-2018-002 v0.1 | Uncontrolled generated view | Subject 1033d98e83ca</text></g></svg>'  # noqa: E501 - embedded HTML/SVG template
  )
  (out / 'verification_readiness.svg').write_text(''.join(svg))
  manifest = {
    'record': config['record'],
    'revision': '0.1',
    'subject_revision': revision,
    'source_sha256': sources,
    'artifacts': {p.name: digest(p.read_bytes()) for p in sorted(out.iterdir()) if p.name != 'manifest.json'},
  }
  dump(out / 'manifest.json', manifest)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--check', action='store_true')
  args = parser.parse_args()
  with tempfile.TemporaryDirectory() as temp:
    out = Path(temp)
    build(out)
    # Manifest seals generated files. Source config and script are controlled by Git.
    if args.check:
      bad = [p.name for p in out.iterdir() if not (HERE / p.name).exists() or p.read_bytes() != (HERE / p.name).read_bytes()]
      if bad:
        raise SystemExit('Generated artifact mismatch: ' + ', '.join(bad))
      print('PASS: immutable source anchors, baseline crosswalk and all generated artifacts reproduced')
    else:
      for p in out.iterdir():
        (HERE / p.name).write_bytes(p.read_bytes())
      print('Built follow-up views from immutable subject Git objects')


if __name__ == '__main__':
  main()
