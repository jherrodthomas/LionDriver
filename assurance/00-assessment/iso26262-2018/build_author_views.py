#!/usr/bin/env python3
"""Render bounded AI-author tasks and evidence annotations from the frozen audit."""

from pathlib import Path
import hashlib
import html
import json
import os
import re
import subprocess
import textwrap


RECIPES = {
  'A01': ('Source verification', 'Prepare the licensed-source intake and requirement inventory; verify clause/table/annex counts after source access.', []),
  'A02': ('Decision required', 'Draft options reconciling staffing and the existing gate plan; retain the gate blocker until the safety manager decides.', []),
  'A03': (
    'Authority boundary',
    'Keep AI-generated findings separate from human verification and confirmation; name actual reviewers only after appointment.',
    [],
  ),
  'A04': (
    'Evidence needed',
    'Prepare a configuration-specific AoU verification matrix and failed-assumption ASIL variants; retain provisional ratings.',
    ['A06'],
  ),
  'A05': ('Decision required', 'Prepare strategy alternatives and their controllability evidence needs; distinguish re-rating from decomposition.', ['A04']),
  'A06': (
    'Evidence needed',
    'Create an explicit configuration record with unknown fields marked TBD; populate only identities supported by actual records.',
    [],
  ),
  'A07': (
    'Evidence needed',
    'List BOM, rates, mission profile and diagnostic-coverage inputs needed per safety goal; retain uncomputed result fields.',
    ['A06'],
  ),
  'A08': (
    'Evidence needed',
    'Reconcile the generic-estimate and part-specific result sections with clear provenance, assumptions and separate status labels.',
    ['A07'],
  ),
  'A09': (
    'Documented discrepancy',
    'Draft an end-to-end timing discrepancy table and remedy options; include onset, detection, reaction and warning clocks.',
    [],
  ),
  'A10': (
    'Documented discrepancy',
    'Prepare the curve-bound controllability/ODD decision with dynamics validation needs; do not silently tighten the ODD or lower ASIL.',
    ['A04'],
  ),
  'A11': ('Documented discrepancy', 'Document all terms and tolerances in the forwarding-loss budget and the measurement needed to establish margin.', []),
  'A12': ('Evidence needed', 'Prepare an interference-channel evidence matrix at the actual pins; retain not-shown/partial verdicts until supported.', ['A06']),
  'A13': (
    'Decision required',
    'Prepare the E-01…E-15 entry checklist with links to actual approvals and unresolved prerequisites; do not activate Part 6.',
    ['A02', 'A05', 'A12'],
  ),
  'A14': ('Evidence needed', 'Reconcile HIL deferral with test/gate status and prepare the missing campaign specifications; retain unexecuted results.', []),
  'A15': ('Evidence needed', 'Prepare use-case-specific TI/TD/TCL and TQR completion tasks with independent error-detection criteria and version pins.', []),
  'A16': (
    'Evidence needed',
    'Prepare component-specific reuse/qualification records and trace to their real uses; initialization is not qualification.',
    ['A06'],
  ),
  'A17': (
    'Source verification',
    'Prepare the confirmation-measure/source-page comparison matrix; verify the licensed requirements before changing it.',
    ['A01'],
  ),
  'A18': ('Editorial clarification', 'Make the historical starting-point baseline unmistakable and add current-status cross-references; preserve history.', []),
  'A19': ('Editorial clarification', 'Correct stale folder/coordination references after checking the source baseline; keep the assessment unperformed.', []),
  'A20': (
    'Evidence needed',
    'Prepare claim-to-evidence-to-defeater closure tasks and missing review links; keep release unsupported.',
    ['A04', 'A07', 'A09', 'A12', 'A14'],
  ),
  'A21': (
    'Decision required',
    'Prepare an obligation/responsibility allocation proposal for retrofit and supplier activities; tailoring needs approval.',
    ['A01'],
  ),
  'A22': ('Source verification', 'Document why optional assurance routes are not used; require approved applicability before an N/A verdict.', ['A01']),
}

FOCUS = {
  'A04': ['If AOU-01/02 are not verified'],
  'A07': ['Cannot be computed'],
  'A08': ['not evidence of compliance'],
  'A09': ['1.26 s', '1 s warning budget'],
  'A10': ['0.7 s', 'shorter than driver reaction'],
  'A11': ['zero margin'],
  'A13': ['no entry criterion is met'],
}


def build(package, output, git_repository):
  output.mkdir(parents=True, exist_ok=True)
  data = json.loads((output / 'audit_data.json').read_text())
  baseline = data['summary']['baseline']
  source_cache = {}
  tasks = []
  annotations = []
  cards = []
  handoff = [
    '# AI-author update queue — ARA-26262-2018-001 v0.2',
    '',
    'Draft / I0 authoring aid. The subject is `' + baseline + '`. Complete ISO compliance is not assessed.',
    '',
    'Read [the authoring protocol](AUTHORING_PROTOCOL.md) before using this queue. Tasks authorize no change by themselves.',
    '',
    '| Task | Category | Proposed role | Document | Preparatory dependencies |',
    '|---|---|---|---|---|',
  ]
  for finding in data['findings']:
    evidence = finding['evidence']
    path = evidence['path']
    if path not in source_cache:
      source_cache[path] = subprocess.check_output(['git', 'show', baseline + ':' + path], cwd=git_repository)
    source_bytes = source_cache[path]
    digest = hashlib.sha256(source_bytes).hexdigest()
    expected = next(d['sha256'] for d in data['work_products'] if d['path'] == path)
    if digest != expected:
      raise ValueError('Annotation source hash mismatch: ' + path)
    lines = source_bytes.decode().splitlines()
    line = evidence['line']
    category, preparation, dependencies = RECIPES[finding['id']]
    annotation = {
      'id': 'AN-' + finding['id'],
      'finding_id': finding['id'],
      'category': category,
      'subject_revision': baseline,
      'source_path': path,
      'source_sha256': digest,
      'line_start': line,
      'line_end': line,
      'quote_exact': lines[line - 1],
      'meaning': finding['analysis'],
      'source_link': evidence['url'],
      'normative_verdict': 'Not assessed; licensed requirement verification pending',
    }
    annotation['focus_spans'] = []
    for phrase in FOCUS.get(finding['id'], []):
      match = re.search(re.escape(phrase), annotation['quote_exact'], flags=re.IGNORECASE)
      if match:
        annotation['focus_spans'].append({'start': match.start(), 'end': match.end(), 'text': match.group(0)})
    annotations.append(annotation)
    task = {
      'id': 'TASK-' + finding['id'],
      'finding_id': finding['id'],
      'category': category,
      'proposed_owner_role': finding['owner'],
      'assigned_agent': None,
      'state': 'Unassigned; preparation permitted only when the user assigns the task',
      'subject_revision': baseline,
      'source_sha256': digest,
      'primary_document': path,
      'source_line': line,
      'annotation_id': annotation['id'],
      'preparatory_dependencies': ['TASK-' + d for d in dependencies],
      'allowed_preparation': preparation,
      'required_author_action': finding['action'],
      'closure_evidence': finding['closure'],
      'target_gate': finding['gate'],
      'required_outputs': [
        'Evidence-linked proposed change and exact source/version crosswalk',
        'Actual executed checks, unrun checks, limitations and anomaly dispositions',
        'Impact analysis plus changed-document revision history',
        'Human-review request; no self-acceptance or confirmation credit',
      ],
      'forbidden_shortcuts': [
        'Invent measurements, identities, source clauses, reviews, signatures or results',
        'Lower ASIL or change ODD, FTTI, detection clocks, targets or allocations to make a finding disappear',
        'Close evidence/claims/defeaters or pass gates without the required human review and real evidence',
        'Treat keyword coverage or a similarity score as a compliance verdict',
        'Modify unrelated work products or solve a staffing/resource decision on behalf of the safety manager',
      ],
      'human_review': 'Required before closure; I0 drafting is not independent verification',
    }
    tasks.append(task)
    handoff.append(
      f"| {task['id']} | {category} | {finding['owner']} | {evidence['document']}:{line} | "
      + (', '.join(task['preparatory_dependencies']) or 'None; task-specific external prerequisites still apply')
      + ' |'
    )
    semantic = {
      'Documented discrepancy': 'discrepancy',
      'Editorial clarification': 'editorial',
      'Source verification': 'source',
      'Authority boundary': 'source',
    }.get(category, 'evidence')
    context = []
    for number in range(max(1, line - 4), min(len(lines), line + 4) + 1):
      text = html.escape(lines[number - 1])
      if number == line:
        pieces = []
        cursor = 0
        for span in sorted(annotation['focus_spans'], key=lambda s: s['start']):
          pieces.extend(
            [
              html.escape(lines[number - 1][cursor : span['start']]),
              '<span class="focus">' + html.escape(span['text']) + '</span>',
            ]
          )
          cursor = span['end']
        if pieces:
          pieces.append(html.escape(lines[number - 1][cursor:]))
          text = ''.join(pieces)
        text = '<mark>' + text + '</mark>'
      context.append(f'<div class="line"><span class="ln">{number}</span><code>{text}</code></div>')
    full_document = '\n'.join(f'{number:4d}  {text}' for number, text in enumerate(lines, 1))
    cards.append(
      '<article data-category="'
      + semantic
      + '"><h2><span class="circle">'
      + finding['id']
      + '</span> '
      + html.escape(finding['title'])
      + '</h2><p class="category">'
      + html.escape(category)
      + ' · '
      + html.escape(finding['owner'])
      + ' · '
      + html.escape(finding['gate'])
      + '</p><p><a href="'
      + html.escape(evidence['url'], quote=True)
      + '">'
      + html.escape(evidence['document'])
      + ':'
      + str(line)
      + '</a> · subject '
      + baseline[:12]
      + ' · SHA256 '
      + digest[:16]
      + '…</p><div class="passage '
      + semantic
      + '">'
      + ''.join(context)
      + '</div><p><strong>Why it matters:</strong> '
      + html.escape(finding['analysis'])
      + '</p><p><strong>AI-author preparation:</strong> '
      + html.escape(preparation)
      + '</p><p><strong>Closure evidence:</strong> '
      + html.escape(finding['closure'])
      + '</p><p><strong>Task:</strong> '
      + task['id']
      + ' · dependencies: '
      + html.escape(', '.join(task['preparatory_dependencies']) or 'None in this queue')
      + '</p><details><summary>Original document at the assessed commit (read-only)</summary><pre>'
      + html.escape(full_document).replace(' \n', '&#32;\n')
      + '</pre></details></article>'
    )
  common = {'record': 'ARA-26262-2018-001', 'revision': '0.2', 'subject_revision': baseline, 'normative_completeness': False}
  (output / 'author_tasks.json').write_text(json.dumps(dict(common, tasks=tasks), indent=2) + '\n')
  (output / 'annotations.json').write_text(json.dumps(dict(common, annotations=annotations), indent=2) + '\n')
  for task in tasks:
    handoff.extend(
      [
        '',
        '## ' + task['id'],
        '',
        '**Allowed preparation:** ' + task['allowed_preparation'],
        '',
        '**Author action:** ' + task['required_author_action'],
        '',
        '**Closure evidence:** ' + task['closure_evidence'],
        '',
        '**Human control:** ' + task['human_review'],
      ]
    )
  (output / 'AUTHOR_HANDOFF.md').write_text('\n'.join(handoff) + '\n')
  css = """
body{margin:0;background:#f7f9fc;color:#14263d;font:16px system-ui}main{max-width:1250px;margin:auto;padding:30px}
.notice{background:#fff0cf;border-left:6px solid #a46c15;padding:18px;line-height:1.6}
article{background:white;padding:24px;margin:24px 0;border:1px solid #d4dfeb;border-radius:10px}
h2{font-size:22px}.circle{display:inline-flex;border:3px solid #376c95;border-radius:50%;padding:10px;margin-right:10px}
.category{font-weight:bold}.passage{border:3px solid #a46c15;border-radius:12px;padding:16px;background:#fff9e8}
.passage.discrepancy{border-color:#ac3941;background:#fff0f0}.passage.editorial{border-color:#376c95;background:#edf5ff}
.passage.source{border-color:#7953a7;background:#f5f0ff}.line{display:flex;gap:14px;align-items:flex-start}
.ln{min-width:35px;text-align:right;color:#718096}code{white-space:pre-wrap;overflow-wrap:anywhere;font:13px ui-monospace,monospace}
mark{background:#ffe49b;color:#14263d;box-shadow:0 2px 0 #a46c15}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}
.focus{border:2px solid #ac3941;border-radius:50%;padding:1px 6px;font-weight:bold}
input,select{padding:12px;font:inherit;margin:8px 8px 8px 0;border:1px solid #aab8c8}a{color:#376c95}
@media print{input,select,details{display:none}article{break-inside:avoid}.circle{border-color:black}}
"""
  page = (
    '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    + '<title>LionDriver annotated assurance review</title><style>'
    + css
    + '</style><main>'
    + '<h1>Annotated assurance documents • author update guide</h1><p>ARA-26262-2018-001 v0.2 · UNCONTROLLED generated view · I0</p>'
    + '<div class="notice">Annotations are attached to exact source lines at the assessed commit; original documents are untouched. '
    + 'Red borders identify documented discrepancies, amber identifies evidence/decision needs, purple identifies source/authority checks, '
    + 'and blue identifies editorial clarification. A circled finding number connects the passage to an author task. '
    + 'These colors do not assert ISO noncompliance. Normative verdicts await licensed-source verification and human review.</div>'
    + '<p><a href="AUTHOR_HANDOFF.md">Author task queue</a> · <a href="AUTHORING_PROTOCOL.md">Authoring protocol</a> · '
    + '<a href="author_tasks.json">Machine-readable tasks</a> · <a href="README.md">Document-control record</a></p>'
    + '<input id="search" aria-label="Search annotations" placeholder="Find task, document, topic or role…">'
    + '<select id="category" aria-label="Annotation category"><option value="">All categories</option>'
    + '<option value="discrepancy">Documented discrepancies</option><option value="evidence">Evidence and decisions</option>'
    + '<option value="source">Source and authority checks</option><option value="editorial">Editorial clarification</option></select>'
    + '<p id="count"></p>'
    + ''.join(cards)
    + '<script>const s=document.querySelector("#search"),c=document.querySelector("#category"),a=[...document.querySelectorAll("article")];'
    + 'function filter(){let n=0;for(const e of a){const ok=e.textContent.toLowerCase().includes(s.value.toLowerCase())&&'
    + '(!c.value||e.dataset.category===c.value);e.hidden=!ok;if(ok)n++}document.querySelector("#count").textContent=n+" annotations shown"}'
    + 's.addEventListener("input",filter);c.addEventListener("change",filter);filter();</script></main></html>'
  )
  (output / 'Annotated_review.html').write_text(page)
  render_example(output, next(a for a in annotations if a['finding_id'] == 'A09'))
  print('Rendered 22 bounded author tasks and 22 exact-source visual annotations.')


def render_example(output, annotation):
  import matplotlib

  matplotlib.use('Agg')
  import matplotlib.pyplot as plt
  from matplotlib.patches import Ellipse
  from matplotlib.text import Text

  matplotlib.rcParams['svg.fonttype'] = 'none'
  matplotlib.rcParams['svg.hashsalt'] = 'ARA-26262-2018-001-v0.2-annotation'
  quote = annotation['quote_exact']
  chunks = textwrap.wrap(quote, width=118, replace_whitespace=False, drop_whitespace=False, expand_tabs=False, break_long_words=False, break_on_hyphens=False)
  assert ''.join(chunks) == quote
  offsets = []
  cursor = 0
  for chunk in chunks:
    offsets.append(cursor)
    cursor += len(chunk)
  fig, ax = plt.subplots(figsize=(14, max(7, 3.5 + len(chunks) * 0.25)), dpi=150)
  ax.axis('off')
  ax.set_xlim(0, 100)
  ax.set_ylim(0, 100)
  fig.patch.set_facecolor('#f7f9fc')
  ax.text(1, 97, 'A09 • Annotated source example', fontsize=20, weight='bold', color='#14263d', va='top')
  ax.text(1, 88, 'Documented timing discrepancy; normative ISO verdict remains unassessed.', fontsize=11, color='#ac3941')
  source_label = annotation['source_path'] + ':' + str(annotation['line_start'])
  ax.text(1, 81, source_label, fontsize=9, color='#376c95')
  texts = []
  spacing = 43 / max(1, len(chunks))
  for row, chunk in enumerate(chunks):
    texts.append(ax.text(1, 74 - row * spacing, chunk, fontsize=9, family='DejaVu Sans Mono', va='top', color='#14263d'))
  fig.canvas.draw()
  renderer = fig.canvas.get_renderer()
  for span in annotation['focus_spans']:
    row = max(i for i, start in enumerate(offsets) if start <= span['start'])
    column = span['start'] - offsets[row]
    if span['end'] > offsets[row] + len(chunks[row]):
      continue
    bbox = texts[row].get_window_extent(renderer)

    def width(value, properties):
      probe = Text(text=value, fontproperties=properties)
      probe.set_figure(fig)
      return probe.get_window_extent(renderer).width

    properties = texts[row].get_fontproperties()
    prefix_width = width(chunks[row][:column], properties)
    focus_width = width(span['text'], properties)
    center = ax.transData.inverted().transform((bbox.x0 + prefix_width + focus_width / 2, (bbox.y0 + bbox.y1) / 2))
    size = ax.transData.inverted().transform((bbox.x0 + focus_width + width('  ', properties), bbox.y0 + bbox.height * 1.7))
    origin = ax.transData.inverted().transform((bbox.x0, bbox.y0))
    ax.add_patch(Ellipse(center, size[0] - origin[0], size[1] - origin[1], fill=False, edgecolor='#ac3941', linewidth=2))
  ax.text(1, 22, 'Author preparation', fontsize=13, weight='bold', color='#376c95')
  ax.text(
    1,
    16,
    'Separate fault onset, persistence, detection, reaction and warning clocks.\n'
    + 'Propose remedy options; do not redefine the budget to hide the discrepancy.',
    fontsize=11,
    color='#14263d',
  )
  ax.text(1, 5, 'Closure needs an approved timing decision and real end-to-end measurement evidence.', fontsize=10, color='#ac3941')
  ax.text(1, 0, 'ARA-26262-2018-001 v0.2 | UNCONTROLLED | Exact source quote, wrapped for display | I0', fontsize=8, color='#718096')
  svg = output / '06_annotation_example.svg'
  fig.savefig(svg, bbox_inches='tight', metadata={'Date': None})
  svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
  fig.savefig('/tmp/liondriver-annotation-example.png', dpi=150, bbox_inches='tight')
  plt.close(fig)


if __name__ == '__main__':
  package = Path(__file__).resolve().parent
  build(package, Path(os.environ.get('AUDIT_OUTPUT_DIR', str(package))), Path(os.environ.get('AUDIT_GIT_REPO', '/workspace/LionDriver')))
