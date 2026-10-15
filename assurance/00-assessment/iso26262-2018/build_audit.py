#!/usr/bin/env python3
"""Reproducible evidence-led audit aid; not an authoritative ISO requirement list."""

from pathlib import Path
import os
import csv
import hashlib
import html
import json
import re
import subprocess
import textwrap
from collections import Counter, defaultdict
import xlsxwriter
import yaml

os.environ.setdefault('MPLCONFIGDIR', '/tmp/liondriver-assessor-matplotlib')
os.environ.setdefault('XDG_CACHE_HOME', '/tmp/liondriver-assessor-cache')
import matplotlib

matplotlib.use('Agg')
matplotlib.rcParams['svg.fonttype'] = 'none'
matplotlib.rcParams['svg.hashsalt'] = 'ARA-26262-2018-001-v0.1'
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(os.environ.get('AUDIT_SOURCE_ROOT', '/workspace/LionDriver')).resolve()
GIT_REPO = Path(os.environ.get('AUDIT_GIT_REPO', str(ROOT))).resolve()
OUT = Path(os.environ.get('AUDIT_OUTPUT_DIR', str(Path(__file__).resolve().parent))).resolve()
OUT.mkdir(parents=True, exist_ok=True)
HEAD = subprocess.check_output(
  ['git', 'rev-parse', '--verify', os.environ.get('AUDIT_REVISION', '20569e916c9359243739b71e4dc79876aec48cc0') + '^{commit}'], cwd=GIT_REPO, text=True
).strip()
BASE_URL = f'https://github.com/jherrodthomas/LionDriver/blob/{HEAD}/'
NAVY = '#14263D'
GOLD = '#C79C49'
RED = '#AC3941'
AMBER = '#A46C15'
BLUE = '#376C95'
GRAY = '#718096'
PARTS = {
  1: 'Vocabulary',
  2: 'Management of functional safety',
  3: 'Concept phase',
  4: 'Product development at system level',
  5: 'Product development at hardware level',
  6: 'Product development at software level',
  7: 'Production, operation, service and decommissioning',
  8: 'Supporting processes',
  9: 'ASIL-oriented and safety-oriented analyses',
  10: 'Guidelines on ISO 26262',
  11: 'Guidelines on application to semiconductors',
  12: 'Adaptation for motorcycles',
}
PRIMARY = {
  'WP-M-00',
  'WP-M-01',
  'WP-M-02',
  'WP-M-06',
  'WP-M-14',
  'WP-C-01',
  'WP-C-03',
  'WP-C-04',
  'WP-S-04',
  'WP-H-03',
  'WP-H-04',
  'WP-H-05',
  'WP-H-07',
  'WP-P-07',
  'WP-P-08',
  'WP-P-09',
  'WP-A-01',
  'WP-A-02',
  'WP-W-06',
  'WP-K-01',
  'WP-K-04',
}


def plain(s):
  s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', str(s))
  return re.sub(r'[*`~]', '', s).strip()


docs = []
byid = {}
all_md = sorted((ROOT / 'assurance').rglob('*.md'))
for p in sorted(list((ROOT / 'assurance').rglob('WP-*.md')) + [ROOT / 'assurance/process/README.md', ROOT / 'assurance/trace/README.md']):
  lines = p.read_text().splitlines()
  meta = {}
  for l in lines[1:]:
    if l.startswith('## '):
      break
    cells = [x.strip() for x in l.strip('|').split('|')]
    if l.startswith('|') and len(cells) == 2 and cells[0] not in meta:
      meta[cells[0]] = plain(cells[1])
  ident = re.search(r'WP-[A-Z]+-\d+', p.name)[0] if re.search(r'WP-[A-Z]+-\d+', p.name) else ('WP-P-11' if p.parent.name == 'process' else 'WP-T-01')
  d = {
    'id': ident,
    'path': str(p.relative_to(ROOT)),
    'title': plain(lines[0].lstrip('# ')),
    'metadata': meta,
    'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
    'lines': lines,
    'open_items': [],
  }
  section = ''
  for n, l in enumerate(lines, 1):
    if l.startswith('#'):
      section = plain(l.lstrip('# '))
    if re.match(r'^\|\s*OI-\d+\b', l):
      cells = [plain(x) for x in l.strip('|').split('|')]
      state = 'Open / closure not established'
      if re.search(r'(?i)partly closed|partly addressed|partially closed', l):
        state = 'Partial'
      elif re.match(r'(?i)^closed\b', cells[1]):
        state = 'Author reports closed; not independently accepted'
      d['open_items'].append(
        {
          'id': ident + ':' + cells[0],
          'item': cells[1],
          'owner': cells[2] if len(cells) > 3 else 'Not stated in row',
          'gate': cells[-1],
          'state': state,
          'line': n,
          'section': section,
        }
      )
  docs.append(d)
  byid[ident] = d


def cite(ident, needle):
  d = byid[ident]
  matches = [(i, l) for i, l in enumerate(d['lines'], 1) if needle.lower() in l.lower()]
  if not matches:
    raise ValueError(f'Missing evidence: {ident}: {needle}')
  n, l = matches[0]
  return {'document': ident, 'path': d['path'], 'line': n, 'excerpt': plain(l), 'url': BASE_URL + d['path'] + f'#L{n}'}


# Reviewer analysis: facts come from the cited work products, not assumed standard wording.
SPECS = [
  (
    'A01',
    'P0',
    'Audit coverage',
    '2:6;8:9',
    'WP-M-14',
    'Check every clause reference',
    'Authoritative clause universe is not yet accessible',
    (
      'Repository cross-references cannot establish that every requirement, table and annex is covered. Use'
      + 'r confirms licensed 2018 source exists; the supplied Windows search link is not accessible from this'
      + ' cloud machine.'
    ),
    ('Obtain all 12 parts; build a verified requirement-level inventory with page provenance, normative/informative classification and ASIL applicability.'),
    'Assessor + standards custodian',
    'Before normative verdicts',
    'Source verified, all inventory entries counted, and independent coverage reconciliation completed.',
  ),
  (
    'A02',
    'P0',
    'Governance',
    '2:5;2:6',
    'WP-M-02',
    'no assessor for now',
    'The current staffing decision blocks the planned governance gate',
    (
      'The safety plan explicitly says the no-assessor decision prevents G0 under its existing CR-01/CR-03 '
      + 'plan. AI review cannot silently satisfy that requirement.'
    ),
    ('Reconcile staffing decision and confirmation plan; appoint qualified reviewers and assessor or formally re-plan without claiming gate completion.'),
    'Safety manager / project maintainer',
    'G0',
    'Named roles, competence/conflict declarations, approved plan and signed confirmation records.',
  ),
  (
    'A03',
    'P0',
    'Governance',
    '2:6;8:9',
    'WP-M-02',
    'AI drafting is not a verification',
    'AI-generated review has no independent verification credit under the project rules',
    (
      'This workbook is an assessment aid. The project explicitly assigns AI audits I0; this deliverable ca'
      + 'nnot be counted as an I1/I3 confirmation or signed FSA.'
    ),
    'Arrange human review appropriate to the approved ASIL and maintain a separate evidence acceptance trail.',
    'Safety manager',
    'G0–G5',
    'Qualified reviewer signs baseline-specific findings and disposition; independence is evidenced.',
  ),
  (
    'A04',
    'P0',
    'Concept',
    '3:5;3:6;3:7',
    'WP-C-03',
    'If AOU-01/02 are not verified',
    'Safety integrity ratings depend on unverified OEM/driver assumptions',
    (
      'The HARA explicitly increases the steering case from C to D if credited EPS assumptions are not veri'
      + 'fied. Current lower targets cannot be treated as established.'
    ),
    'Verify assumptions per exact ECU/configuration; challenge S/E/C rationale and document both credited and failed-assumption variants.',
    'HARA owner / vehicle test lead',
    'G1',
    'Approved HARA, witnessed characterization records, configuration binding and independent confirmation.',
  ),
  (
    'A05',
    'P0',
    'Concept',
    '3:7;9:5',
    'WP-C-04',
    'decision belongs to the maintainer',
    'Reduced-authority strategy is a recommendation rather than an approved safety basis',
    ('Option (c) requires measured controllability and speed-dependent limits before re-rating; ASIL reduction and decomposition are different arguments.'),
    ('Record the strategy decision, validate limits and re-rate only after justified controllability; preserve original integrity demands until then.'),
    'Safety manager / HARA owner',
    'G1–G2',
    'Signed strategy plus validated limit data, revised allocations and confirmed HARA.',
  ),
  (
    'A06',
    'P0',
    'Configuration',
    '3:5;8:7',
    'WP-C-01',
    'Record the reference vehicle VIN',
    'Assessment configuration is not fully identified',
    (
      'VIN, ECU firmware, device revision and harness identity are still open items. A generation-level veh'
      + 'icle label is insufficient to bind physical evidence.'
    ),
    'Freeze an assessed configuration including hardware serial/revision, ECU firmware, software/submodules, models and calibration.',
    'Configuration manager / maintainer',
    'G1',
    'Complete configuration record and matching manifests for every cited result.',
  ),
  (
    'A07',
    'P0',
    'Hardware',
    '5:8;5:9',
    'WP-H-04',
    'Cannot be computed',
    'Part-specific hardware metrics are not demonstrated',
    (
      'WP-H-04 lacks BOM-based calculation; WP-H-03 has generic estimates, not part-specific compliance evi'
      + 'dence. Generic results cannot close the metric obligation.'
    ),
    ('Acquire BOM/mission profile/failure-rate evidence, validate fault classes and diagnostic coverage, compute per-goal metrics and sensitivity.'),
    'Hardware safety lead',
    'G3',
    'Reviewed FMEDA and reproducible part-specific SPFM/LFM/PMHF with traceable inputs and valid targets.',
  ),
  (
    'A08',
    'P1',
    'Hardware',
    '5:7;5:8;5:9',
    'WP-H-03',
    'They are not evidence of compliance',
    'Generic FMEDA values must remain separated from demonstrated metrics',
    (
      'Generic SG-01 SPFM 96.9% and SG-07 86.8% miss the document targets; improved planned-measure values '
      + 'assume implementation and coverage. These are planning warnings, not verified pass/fail results.'
    ),
    'Label estimates, planned architecture and measured results separately; reconcile WP-H-03 with WP-H-04/05 and confirm target authority.',
    'Hardware safety lead',
    'G2–G3',
    'One configuration-consistent calculation set; planned mechanisms excluded until coverage is substantiated.',
  ),
  (
    'A09',
    'P0',
    'Timing',
    '4:6;6:7',
    'WP-S-04',
    'EPS-fault siren latency',
    'Documented warning latency exceeds the stated warning budget',
    (
      'The document records up to 1.26 s against SG-02 1 s; starting the clock after 1 s persistence can co'
      + 'nceal end-to-end delay. This is a documented requirement discrepancy, not a new hardware measurement'
      + '.'
    ),
    ('Resolve the requirement/detection-time definition and measure fault onset through actuation removal and audible warning under worst-case load.'),
    'Safety manager / system lead',
    'G2',
    'Approved consistent timing budget and witnessed end-to-end traces including tolerance and jitter.',
  ),
  (
    'A10',
    'P0',
    'Timing',
    '3:6;4:6',
    'WP-S-04',
    'physical time to departure',
    'Curve-bound time to departure is shorter than assumed driver reaction',
    (
      'The repository estimates roughly 0.7 s at the ODD bound and itself requests a controllability re-rat'
      + 'ing or tighter ODD. Driver supervision is not an automatic mitigation.'
    ),
    'Validate dynamics at the boundary; revise ODD, authority or hazard controllability and flow changes through FSC/TSRs.',
    'HARA owner / dynamics lead',
    'G2',
    'Measured validated model, updated ODD and accepted HARA/FTTI rationale.',
  ),
  (
    'A11',
    'P0',
    'Timing',
    '4:6;4:7',
    'WP-S-04',
    'forwarding loss has zero margin',
    'Stock PCS forwarding-loss budget has zero timing margin',
    (
      'The stated sum of detection and reaction equals FTTI before measured PCS timing. A watchdog nominal '
      + 'setting is insufficient to prove the end-to-end budget.'
    ),
    'Measure forwarding-loss response and PCS effects; include oscillator tolerance, scheduling, bus delay and safe-state behavior.',
    'System / hardware test lead',
    'G2–G4',
    'Worst-case FDTI+FRTI substantiated with positive justified margin or an explicitly accepted alternative safety argument.',
  ),
  (
    'A12',
    'P0',
    'Architecture',
    '6:7;9:6;9:7',
    'WP-A-02',
    'L-MCU spatial',
    'Freedom from interference is not established',
    (
      'The current verdicts include not shown and partially shown; the envelope-only ASIL allocation depend'
      + 's on resolving spatial, timing, communication and boot interference.'
    ),
    'Reconcile analysis to current pins, bound QM-triggered paths, document separation properties and verify adverse inputs and boot integrity.',
    'Software architect / safety analyst',
    'G2',
    'Reviewed FFI/DFA with traceable evidence for every interference channel and justified ASIL allocation.',
  ),
  (
    'A13',
    'P0',
    'Software lifecycle',
    '6:5;6:6;6:7;6:8;6:9;6:10;6:11',
    'WP-M-14',
    'no entry criterion is met',
    'The controlled Part 6 lifecycle has not been activated',
    (
      'The specification explicitly says entry prerequisites are draft/unapproved and Part 6 stays deferred'
      + '. Existing code and host tests do not establish lifecycle completion.'
    ),
    'Close E-01…E-15 prerequisites and record the authorized lifecycle baseline and activation decision.',
    'Safety manager / software lead',
    'G2',
    'Approved entry checklist, input baselines, confirmation records and activation decision.',
  ),
  (
    'A14',
    'P0',
    'Verification',
    '4:7;4:8;5:10;6:10;6:11',
    'WP-M-02',
    'defer the HIL bench',
    'HIL deferral prevents the stated verification closure',
    (
      'The safety plan records deferred HIL and says early-implementation credit cannot be earned until its'
      + ' conditions are met. Plans and host unit tests cannot replace target timing/fault-injection evidence'
      + '.'
    ),
    'Resource a controlled target bench and execute baseline-bound campaigns; if deferred, keep associated gate claims explicitly open.',
    'Test lead / maintainer',
    'G2–G4',
    'Target test logs, environment/calibration records, anomaly disposition and independent review.',
  ),
  (
    'A15',
    'P1',
    'Tools',
    '8:11;6:9',
    'WP-P-07',
    'write TQR-28',
    'Tool self-tests and classification do not complete qualification',
    (
      'In-house safety-relevant tools have open TQR records and review work; compiler/runner pinning is als'
      + 'o open. Agreement between tools sharing assumptions does not authenticate the standard.'
    ),
    ('Complete TI/TD/TCL decisions and applicable qualification records; test error detection against independently sourced criteria and pin the toolchain.'),
    'Tool qualification owner',
    'G3',
    'Reviewed use-case-specific tool qualification, known limitations, detection evidence and immutable versions.',
  ),
  (
    'A16',
    'P1',
    'Reuse',
    '8:12;8:13',
    'WP-P-08',
    'not confirmed',
    'Reuse/qualification conclusions remain unconfirmed',
    (
      'The work product requests review of RA-01…RA-09 and records for remaining safety-relevant components'
      + '; initialized submodules establish access, not qualification.'
    ),
    'Review component use cases, interfaces, failure modes and configuration; close reuse assessments and safety component evidence needs.',
    'Software lead / supplier manager',
    'G3',
    'Reviewed SCQ/RA records and traceable component qualification evidence for the actual use.',
  ),
  (
    'A17',
    'P1',
    'Standards accuracy',
    '2:6;8:9',
    'WP-M-06',
    'Check whether a separate row exists',
    'Confirmation-measure coverage and independence still require source verification',
    (
      'The plan itself questions whether several rows are required in the licensed edition. Planned I3 rigo'
      + 'r does not validate the underlying table transcription.'
    ),
    'Verify every measure, applicable ASIL and independence requirement directly against Part 2; reconcile the CR list and schedule.',
    'Assessor / safety manager',
    'G0–G1',
    'Source/page-referenced approved confirmation matrix with signed results at required gates.',
  ),
  (
    'A18',
    'P2',
    'Baseline control',
    '2:6;8:7;8:8;8:10',
    'WP-M-01',
    'The only change so far',
    'Historical baseline statements can be mistaken for current status',
    (
      'WP-M-01 already identifies this as a historical starting point, but its old facts could be read as c'
      + 'urrent status. Current assurance records and safety.yaml differ. This is a clarity observation, not '
      + 'proof of an incorrect historical assessment.'
    ),
    ('Mark historical observations and reconcile assessment baselines, software pins, current status and impact records without rewriting history.'),
    'Configuration manager / document authors',
    'G0–G2',
    'Baseline crosswalk plus reviewed current-status statements and supersession links.',
  ),
  (
    'A19',
    'P1',
    'Documentation',
    '2:6;8:10',
    'WP-K-04',
    'folder to be created',
    'Assessment template contains stale status/coordination references',
    (
      'WP-K-04 says the confirmation folder is to be created via OI-6, although the folder exists and WP-M-'
      + '02 OI-5 reports closure; no FSA is actually executed.'
    ),
    'Update template coordination links through normal document control, leaving execution/approval fields explicitly unperformed.',
    'Safety case owner',
    'Before assessment kickoff',
    'Correct reference and folder state with reviewed revision; no fabricated assessor signature or result.',
  ),
  (
    'A20',
    'P0',
    'Safety case',
    '2:6;4:8',
    'WP-K-01',
    'does not support any release',
    'The current safety case does not support release',
    (
      'The work product explicitly disclaims a release claim; machine-readable records show 0 accepted clai'
      + 'ms, 0 accepted evidence and 41 open defeaters. Structural validity is not evidence sufficiency.'
    ),
    ('Close safety-critical defeaters with configuration-bound evidence; obtain applicable verification, confirmation and assessment before release.'),
    'Safety case owner / safety manager',
    'G5',
    'Accepted claim/evidence chains, dispositioned defeaters, FSA and signed release record.',
  ),
  (
    'A21',
    'P1',
    'Operation and tailoring',
    '7:5;7:6;8:5',
    'WP-M-01',
    'T-07',
    'Retrofit tailoring must cover residual production/supplier responsibilities',
    (
      'The strategy tails production to installation and distributed development to upstream reuse. These a'
      + 're proposed project arguments; supplier responsibilities and applicable obligations need source-base'
      + 'd review.'
    ),
    'Map each applicable Part 7/8 requirement to installer, upstream supplier or LionDriver; justify retained/allocated/tailored obligations.',
    'Supplier manager / operations lead',
    'G0–G5',
    'Approved obligation allocation, installation/process evidence and residual-risk disposition.',
  ),
  (
    'A22',
    'P2',
    'Applicability',
    '8:14;9:5',
    'WP-P-09',
    'no PIU claim is made',
    'Proven-in-use non-use is a declared strategy, not a blanket compliance failure',
    (
      'The project deliberately makes no proven-in-use claim. Likewise, ASIL decomposition is not automatic'
      + 'ally mandatory. Requirement applicability needs an approved rationale.'
    ),
    (
      'Keep the alternative routes visible and justify non-use; do not count an unused route as complied wi'
      + 'th or mark it failed solely because no artifact exists.'
    ),
    'Safety manager / assessor',
    'G1–G3',
    'Source-verified applicability/tailoring decisions and no contradictory reuse/decomposition claims.',
  ),
]
findings = []
for ident, priority, area, clause, doc, needle, title, judgement, action, owner, gate, closure in SPECS:
  findings.append(
    {
      'id': ident,
      'priority': priority,
      'area': area,
      'clauses': clause.split(';'),
      'title': title,
      'basis': 'Documentary finding; ISO normative verdict pending source verification',
      'analysis': judgement,
      'action': action,
      'owner': owner,
      'gate': gate,
      'closure': closure,
      'state': 'Open',
      'evidence': cite(doc, needle),
    }
  )

register = ROOT / 'assurance/01-management/WP-M-00-work-product-register.md'
associations = []


def refs(s):
  result = []
  # This parser consumes only the register ISO 26262 column; it never infers a missing clause.
  starts = list(re.finditer(r'(?<!\d)(\d{1,2})\s+(?=§|Annex)', s))
  for i, m in enumerate(starts):
    part = int(m.group(1))
    segment = s[m.end() : starts[i + 1].start() if i + 1 < len(starts) else len(s)]
    for cm in re.finditer(r'(?:^|,)\s*§?\s*(\d+(?:\.\d+)*)(?:\s*[–—-]\s*(\d+))?', segment):
      first, last = cm.group(1), cm.group(2)
      if last and first.isdigit():
        result.extend(f'{part}:{n}' for n in range(int(first), int(last) + 1))
      else:
        result.append(f'{part}:{first}')
    for am in re.finditer(r'Annex\s+([A-Z])', segment):
      result.append(f'{part}:Annex {am.group(1)}')
  return sorted(set(result))


assert refs('5 §7, §8') == ['5:7', '5:8']
assert set(refs('6 §5–11, Annex C; 8 §6–12')) == {*(f'6:{n}' for n in range(5, 12)), *(f'8:{n}' for n in range(6, 13)), '6:Annex C'}
register_rows = []
for n, line in enumerate(register.read_text().splitlines(), 1):
  if not re.match(r'^\|\s*\[WP-', line):
    continue
  cells = [x.strip() for x in line.strip('|').split('|')]
  if len(cells) != 9:
    raise ValueError(f'Unexpected register row {n}')
  ident = re.search(r'WP-[A-Z]+-\d+', cells[0])[0]
  raw = cells[2]
  register_rows.append({'id': ident, 'iso_reference': raw, 'gate': plain(cells[7]), 'status': cells[8], 'line': n})
  for ref in refs(raw):
    associations.append(
      {
        'clause': ref,
        'document': ident,
        'source': str(register.relative_to(ROOT)),
        'line': n,
        'raw': raw,
        'basis': 'Project register mapping; not independently source-verified',
      }
    )
  byid[ident]['register'] = register_rows[-1]

# Preserve exact explicit in-text ISO references, including subclauses. No bare section numbers.
explicit = re.compile(r'(?:ISO\s+)?26262[-–](\d{1,2})(?::2018)?\s*§\s*(\d+(?:\.\d+)*)')
for p in all_md:
  for n, line in enumerate(p.read_text().splitlines(), 1):
    for m in explicit.finditer(line):
      ref = f'{int(m.group(1))}:{m.group(2)}'
      associations.append(
        {
          'clause': ref,
          'document': re.search(r'WP-[A-Z]+-\d+', p.name)[0] if re.search(r'WP-[A-Z]+-\d+', p.name) else p.stem,
          'source': str(p.relative_to(ROOT)),
          'line': n,
          'raw': plain(line),
          'basis': 'Explicit document citation; not independently source-verified',
        }
      )
unique = {}
for a in associations:
  unique[(a['clause'], a['document'], a['source'], a['line'])] = a
associations = list(unique.values())
clause_docs = defaultdict(set)
for a in associations:
  clause_docs[a['clause']].add(a['document'])
clause_findings = defaultdict(list)
for f in findings:
  for c in f['clauses']:
    clause_findings[c].append(f['id'])


def clause_key(s):
  p, c = s.split(':', 1)
  return (int(p), [int(n) for n in c.split('.')] if c[0].isdigit() else [999, ord(c[-1])])


clause_ids = sorted(set(clause_docs) | set(clause_findings), key=clause_key)

standard_fields = [
  'edition',
  'part',
  'clause_id',
  'requirement_id',
  'title_or_paraphrase',
  'kind',
  'asil_applicability',
  'source_file',
  'source_page',
  'source_verified_by',
  'source_verified_date',
  'applicability_decision',
  'applicability_rationale',
]
template = OUT / 'licensed_clause_inventory.csv'
if not template.exists():
  with template.open('w', newline='') as f:
    csv.writer(f).writerow(standard_fields)
licensed = list(csv.DictReader(template.open()))
if licensed:
  raise ValueError('Licensed inventory supplied: review and integrate the authoritative rows before regeneration; do not silently ignore them.')

case = json.loads((ROOT / 'assurance/case/status.json').read_text())
evidence = yaml.safe_load((ROOT / 'assurance/case/evidence/evidence.yaml').read_text())
defeaters = yaml.safe_load((ROOT / 'assurance/case/defeaters/defeaters.yaml').read_text())
decisions = yaml.safe_load((ROOT / 'assurance/01-management/decisions/register.yaml').read_text())
requirements = []
for p in sorted((ROOT / 'assurance/trace/items').glob('*.yaml')):
  for r in yaml.safe_load(p.read_text()):
    if r.get('kind') in ('fsr', 'tsr', 'hwsr', 'swsr'):
      requirements.append(dict(r, path=str(p.relative_to(ROOT))))
checks = json.loads((OUT / 'checks.json').read_text())
engine = json.loads((OUT / 'engine_review.json').read_text())
ENGINE_HEAD = engine['reference_head']
ENGINE_URL = f'https://github.com/jherrodthomas/compliance-checker-algo/blob/{ENGINE_HEAD}/agnostic_engine.py'
engine_rows = []
engine_lines = {'E01': 726, 'E02': 1028, 'E03': 989, 'E04': 1206}
for probe in engine['probes']:
  observed = probe['observed']
  outcome = str(observed['score']) + '% heuristic score' if isinstance(observed, dict) else observed
  engine_rows.append(
    [
      probe['id'],
      'Diagnostic false-positive / authority risk',
      probe['case'],
      outcome,
      probe['implication'],
      ENGINE_URL + f"#L{engine_lines[probe['id']]}",
      'Observed diagnostic; not a standard verdict',
    ]
  )
engine_rows.extend(
  [
    [
      'E05',
      'Static review',
      'Unmapped artifact is assigned N/A; mapped artifact with no critical/major findings can be labeled Compliant',
      'Status assignment at engine lines 1655–1665',
      'Missing mapping must be a coverage gap or unknown; document mapping and absence of findings cannot authenticate normative compliance.',
      ENGINE_URL + '#L1655',
      'Source inspection',
    ],
    [
      'E06',
      'Static review',
      'An engine advertised as agnostic contains a hardcoded ISO independence map and confirmation checklist',
      'Engine lines 1813–1840',
      ('Verify every table/independence rule against the licensed edition and actual measure/ASIL; prevent these guesses from becoming confirmation records.'),
      ENGINE_URL + '#L1813',
      'Source inspection',
    ],
  ]
)
summary = {
  'baseline': HEAD,
  'work_products': len(docs),
  'markdown_inventory': len(all_md),
  'register_rows': len(register_rows),
  'referenced_clause_buckets': len(clause_ids),
  'citation_links': len(associations),
  'findings': len(findings),
  'open_item_rows': sum(len(d['open_items']) for d in docs),
  'case': case,
  'checks': checks,
  'complete_standard_inventory': False,
  'scope': 'ISO 26262:2018 parts 1–12; requirement-level completeness pending access to user-provided licensed source',
}
(OUT / 'audit_data.json').write_text(
  json.dumps(
    {
      'summary': summary,
      'work_products': [{k: v for k, v in d.items() if k != 'lines'} for d in docs],
      'findings': findings,
      'clause_associations': associations,
      'requirements': requirements,
    },
    indent=2,
  )
)

workbook = xlsxwriter.Workbook(OUT / 'LionDriver_ISO26262_Audit.xlsx', {'strings_to_formulas': False, 'strings_to_urls': False})
workbook.set_properties(
  {
    'title': 'LionDriver ISO 26262:2018 — Evidence-led Audit',
    'subject': 'Provisional documentary audit; authoritative clause completeness pending',
    'author': 'Codex (OpenAI AI assistant), I0 documentary assessor',
    'comments': f'Baseline {HEAD}. No claim of certification or independent confirmation.',
  }
)
formats = {
  'title': workbook.add_format({'bold': True, 'font_size': 20, 'font_color': NAVY}),
  'note': workbook.add_format({'text_wrap': True, 'font_color': NAVY, 'valign': 'top'}),
  'cell': workbook.add_format({'text_wrap': True, 'valign': 'top', 'font_size': 10}),
  'header': workbook.add_format({'bold': True, 'bg_color': NAVY, 'font_color': '#FFFFFF', 'text_wrap': True, 'valign': 'top'}),
  'red': workbook.add_format({'bg_color': '#F7DFE1', 'font_color': RED}),
  'amber': workbook.add_format({'bg_color': '#FFF0CF', 'font_color': AMBER}),
  'blue': workbook.add_format({'bg_color': '#E3EDF7', 'font_color': BLUE}),
  'url': workbook.add_format({'font_color': BLUE, 'underline': 1, 'text_wrap': True, 'valign': 'top'}),
}


def sheet(name, headers, rows, widths=None, editable=None):
  ws = workbook.add_worksheet(name)
  ws.hide_gridlines(2)
  ws.freeze_panes(4, 1)
  ws.merge_range(0, 0, 0, len(headers) - 1, name.upper(), formats['title'])
  ws.merge_range(
    1,
    0,
    1,
    len(headers) - 1,
    'ARA-26262-2018-001 | v0.1 | Draft / uncontrolled generated view | ISO 26262:2018 | baseline '
    + HEAD[:12]
    + ' | documentary audit; normative verdicts and complete clause inventory pending licensed source',
    formats['note'],
  )
  ws.set_row(1, 32)
  ws.set_row(3, 36)
  for j, h in enumerate(headers):
    ws.write(3, j, h, formats['header'])
    ws.set_column(j, j, (widths or {}).get(j, 25), formats['cell'])
  for i, row in enumerate(rows, 4):
    for j, val in enumerate(row):
      if val is None:
        val = ''
      if isinstance(val, list):
        val = '; '.join(map(str, val))
      if isinstance(val, str) and val.startswith('https://'):
        ws.write_url(i, j, val, formats['url'])
      else:
        ws.write(i, j, val, formats['cell'])
    ws.set_row(i, min(150, max(58, max((len(str(v or '')) / max(12, (widths or {}).get(j, 25)) * 13 for j, v in enumerate(row)), default=58))))
  if rows:
    ws.add_table(3, 0, len(rows) + 3, len(headers) - 1, {'columns': [{'header': h} for h in headers], 'style': 'Table Style Medium 2', 'autofilter': True})
  ws.set_landscape()
  ws.fit_to_pages(1, 0)
  ws.repeat_rows(0, 3)
  ws.set_paper(9)
  ws.set_footer('&LARA-26262-2018-001 v0.1 | UNCONTROLLED&C&P / &N&R' + HEAD[:12])
  if editable:
    for j, choices in editable.items():
      ws.data_validation(
        4,
        j,
        max(1000, len(rows) + 3),
        j,
        {
          'validate': 'list',
          'source': choices,
          'error_title': 'Choose a review status',
          'error_message': 'Use the controlled list; add rationale in the adjacent field.',
        },
      )
  return ws


method_rows = [
  (
    'Document control',
    (
      'ARA-26262-2018-001 v0.1; Draft. Codex (OpenAI AI assistant), I0 documentary assessor and artifact au'
      + 'thor. Not a qualified independent I3 assessor. Published downloads are uncontrolled generated views;'
      + ' controlled source/revision history is in this package README and JSON/CSV records.'
    ),
  ),
  ('Purpose', 'Help work-product authors locate evidence, deficiencies and closure requirements; provide an assessor working ledger.'),
  ('Scope', 'ISO 26262:2018, all 12 parts as requested. Scope does not mean every clause is applicable.'),
  (
    'Coverage limitation',
    (
      'No licensed source is currently accessible. The user confirms one exists; location is pending. Claus'
      + 'e audit rows are extracted project references and finding associations, not a complete official clau'
      + 'se list.'
    ),
  ),
  (
    'Normative verdict',
    ('Not assessed. A draft, passing test, citation or empty evidence field cannot prove compliance or automatically prove a standard nonconformity.'),
  ),
  (
    'Documentary assessment',
    'Findings state observed gaps and internal inconsistencies. P0 is an assessor triage priority, not an ISO or ASIL severity classification.',
  ),
  (
    'Review depth',
    (
      'All '
      + f'{len(docs)}'
      + ' registered WP headers, register mappings and OI rows inventoried (including WP-P-11/process README '
      + 'and WP-T-01/trace README); explicit ISO references across assurance Markdown extracted. Targeted sub'
      + 'stantive review of '
      + f'{len(PRIMARY)}'
      + ' high-leverage WPs and supporting review/record files. No claim of exhaustive sentence-level review.'
    ),
  ),
  (
    'Evidence authority',
    (
      'Repository status and author-side findings are labeled as such. Machine-readable case status was reg'
      + 'enerated/checked against the same baseline. Fresh local checks are separate from accepted project ev'
      + 'idence.'
    ),
  ),
  (
    'Independent confirmation',
    (
      'AI-assisted documentary review, not a human I1/I3 review, certified audit, witnessed vehicle assessm'
      + 'ent or signed FSA. No assurance records or acceptance statuses were changed.'
    ),
  ),
  (
    'Part applicability',
    (
      'Parts 1, 10 and 11 are treated as reference/guidance context pending source verification. Part 12 is'
      + ' provisionally outside the Corolla configuration; formal applicability review is still required.'
    ),
  ),
  (
    'Compliance workflow',
    (
      'Import authoritative requirements; verify every clause/table/annex; decide applicability/ASIL; ident'
      + 'ify actual evidence; assess correctness and sufficiency; raise source-bound findings; independent re'
      + 'view; accept only with traceable authority.'
    ),
  ),
  (
    'Missing source handling',
    (
      'licensed_clause_inventory.csv is deliberately empty. Unreferenced standard clauses cannot be counted'
      + ' or marked compliant, N/A or failed from this snapshot.'
    ),
  ),
  (
    'Source location supplied',
    (
      'User supplied a Windows search-ms link pointing to a Windows-local OneDrive standards folder. That l'
      + 'ocal Windows path is inaccessible to this cloud machine. Attach files or provide an accessible cloud'
      + ' location to complete normative review.'
    ),
  ),
  (
    'Compliance-checker repository',
    (
      'Read-only inspection at '
      + f'{ENGINE_HEAD}'
      + '. Synthetic smoke execution and four diagnostic probes completed. Six engine issues are in Engine re'
      + 'view; no engine grade is used as a compliance finding.'
    ),
  ),
  (
    'Evidence status legend',
    (
      'Documented partial = drafts or incomplete analysis. Not demonstrated = no adequate result located. N'
      + 'on-compliant requires a verified applicable requirement and supported deviation. N/A requires a just'
      + 'ified approved applicability decision.'
    ),
  ),
  (
    'Author use',
    (
      'Filter Clause audit by part; follow Clause links to source lines; filter Findings by responsible rol'
      + 'e; use closure criteria; reconcile OI rows without accepting historical closed labels automatically.'
    ),
  ),
  (
    'Regeneration',
    ('Run build_audit.py in the assessor-only .venv. Source files and baseline are hashed. Generated outputs stay outside the LionDriver checkout.'),
  ),
]
sheet('Read me', ['Topic', 'Rule / interpretation'], method_rows, {0: 30, 1: 120})
wp_rows = []
for d in docs:
  m = d['metadata']
  fs = [f['id'] for f in findings if f['evidence']['document'] == d['id']]
  ois = d['open_items']
  wp_rows.append(
    [
      d['id'],
      d['title'],
      m.get('Status', 'Not stated'),
      m.get('Standard reference', ''),
      d.get('register', {}).get('gate', ''),
      m.get('Author', ''),
      m.get('Reviewer(s)', ''),
      m.get('Approver', ''),
      m.get('Baseline', ''),
      sum(x['state'].startswith('Open') for x in ois),
      fs,
      'Targeted substantive review' if d['id'] in PRIMARY else 'Inventory + header/reference/OI extraction',
      'Not assessed against licensed requirements',
      d['path'],
      d['sha256'],
    ]
  )
sheet(
  'Work products',
  [
    'WP ID',
    'Title',
    'Author-declared status',
    'Author standard references',
    'Gate',
    'Author',
    'Planned reviewer',
    'Planned approver',
    'Document baseline',
    'Unclosed OI rows',
    'Audit findings',
    'Review depth',
    'Normative verdict',
    'Source path',
    'SHA256',
  ],
  wp_rows,
  {1: 47, 2: 42, 3: 50, 12: 30, 13: 60, 14: 65},
)
clause_rows = []
for c in clause_ids:
  p, cl = c.split(':', 1)
  ids = sorted(clause_docs.get(c, set()))
  fids = clause_findings.get(c, [])
  clause_rows.append(
    [
      f'26262-{p}:2018 ' + ('' if cl.startswith('Annex') else '§') + cl,
      int(p),
      PARTS.get(int(p), 'Unknown'),
      cl,
      'Not verified — source pending',
      'Applicability pending',
      'Not assessed',
      len(ids),
      ids,
      fids,
      'Partial documentation / closure gaps' if ids else 'Finding association only; coverage not established',
      'No verified normative requirement inventory',
      '',
      '',
      '',
    ]
  )
clws = sheet(
  'Clause audit',
  [
    'Reference bucket',
    'Part',
    'Part subject',
    'Clause / annex bucket',
    'Authoritative requirement',
    'Applicability',
    'Reviewer verdict',
    'Mapped source count',
    'Mapped sources',
    'Findings',
    'Documentary state',
    'Coverage limitation',
    'Reviewer name',
    'Decision rationale / source page',
    'Review date',
  ],
  clause_rows,
  {0: 28, 2: 42, 4: 42, 8: 58, 11: 48, 13: 60},
  editable={
    5: ['Applicability pending', 'Applicable', 'N/A — approved rationale', 'Informative / reference'],
    6: ['Not assessed', 'Compliant — verified evidence', 'Non-compliant — verified requirement', 'Partially satisfied', 'N/A — approved rationale'],
  },
)
sheet(
  'Clause links',
  ['Clause bucket', 'Document / artifact', 'Citation basis', 'Original citation / source line', 'Path', 'Line', 'Commit-pinned link'],
  [[a['clause'], a['document'], a['basis'], a['raw'], a['source'], a['line'], BASE_URL + a['source'] + f"#L{a['line']}"] for a in associations],
  {3: 100, 4: 65, 6: 85},
)
fws = sheet(
  'Findings',
  [
    'Finding',
    'Priority',
    'Area',
    'Clause associations (unverified)',
    'Title',
    'Assessment basis',
    'Observed issue / reasoning',
    'Required author action',
    'Responsible role (proposed)',
    'Needed gate',
    'Closure evidence / acceptance criterion',
    'State',
    'Source WP',
    'Source line',
    'Excerpt',
    'Source link',
    'Assigned person',
    'Due date',
    'Closure artifact / verification',
    'Closure reviewer',
  ],
  [
    [
      f['id'],
      f['priority'],
      f['area'],
      f['clauses'],
      f['title'],
      f['basis'],
      f['analysis'],
      f['action'],
      f['owner'],
      f['gate'],
      f['closure'],
      f['state'],
      f['evidence']['document'],
      f['evidence']['line'],
      f['evidence']['excerpt'],
      f['evidence']['url'],
      '',
      '',
      '',
      '',
    ]
    for f in findings
  ],
  {4: 54, 6: 80, 7: 75, 10: 80, 14: 85, 15: 85, 18: 70},
  editable={11: ['Open', 'Action in progress', 'Evidence submitted', 'Verified closed', 'Rejected / revised']},
)
fws.conditional_format(4, 1, len(findings) + 3, 1, {'type': 'text', 'criteria': 'containing', 'value': 'P0', 'format': formats['red']})
fws.conditional_format(4, 1, len(findings) + 3, 1, {'type': 'text', 'criteria': 'containing', 'value': 'P1', 'format': formats['amber']})
oi_rows = []
for d in docs:
  for o in d['open_items']:
    oi_rows.append(
      [o['id'], d['id'], o['state'], o['item'], o['owner'], o['gate'], o['section'], d['path'], o['line'], BASE_URL + d['path'] + f"#L{o['line']}", '', '']
    )
sheet(
  'Author open items',
  [
    'Scoped OI ID',
    'WP',
    'Author closure classification',
    'Item (exact project wording)',
    'Owner as recorded',
    'Gate as recorded',
    'Section',
    'Source path',
    'Line',
    'Source link',
    'Assessor disposition',
    'Closure evidence',
  ],
  oi_rows,
  {3: 115, 7: 65, 9: 85, 10: 45, 11: 60},
)
sheet(
  'Evidence ledger',
  [
    'Evidence ID',
    'Title',
    'Author evidence status',
    'Author review state',
    'Claim links',
    'Location',
    'Baseline ID',
    'Source revision',
    'Reviewer',
    'Review reference',
    'Description',
    'Assessor conclusion',
  ],
  [
    [
      e['id'],
      e.get('title'),
      e.get('evidence_status'),
      e.get('review_state'),
      e.get('related_claims', []),
      e.get('location'),
      e.get('baseline'),
      e.get('source_revision'),
      e.get('reviewer'),
      e.get('review_ref'),
      e.get('description'),
      'Not accepted by this audit',
    ]
    for e in evidence
  ],
  {1: 60, 5: 80, 10: 85},
)
sheet(
  'Defeaters',
  [
    'Defeater',
    'Author status',
    'Title',
    'Closure route as recorded',
    'Related claims',
    'Gap links',
    'Baseline ID',
    'Source revision',
    'Assessor closure status',
  ],
  [
    [
      e['id'],
      e.get('lifecycle_status'),
      e.get('title'),
      e.get('description'),
      e.get('related_claims', []),
      e.get('gaps', []),
      e.get('baseline'),
      e.get('source_revision'),
      'No closure accepted by this audit',
    ]
    for e in defeaters
  ],
  {2: 90, 3: 90},
)
sheet(
  'Requirements',
  [
    'Requirement ID',
    'Kind',
    'ASIL as proposed',
    'Status as recorded',
    'Parents',
    'Allocated to',
    'Acceptance criteria',
    'Verification methods',
    'Implementation note (author)',
    'Source WP',
    'Source path',
    'Evidence judgment',
  ],
  [
    [
      r['id'],
      r.get('kind'),
      r.get('asil'),
      r.get('status'),
      r.get('parents', []),
      r.get('allocated_to'),
      r.get('acceptance'),
      r.get('verification'),
      r.get('baseline_impl'),
      r.get('source'),
      r['path'],
      'Trace entry is not execution or acceptance evidence',
    ]
    for r in requirements
  ],
  {5: 55, 6: 80, 8: 95, 10: 65},
)
sheet(
  'Decisions',
  ['Decision', 'Status as recorded', 'Gate', 'Question', 'Blocks / consequences', 'Recorded choice', 'Applied reference', 'Assessor note'],
  [
    [
      d['id'],
      d.get('status'),
      d.get('gate'),
      d.get('question'),
      d.get('blocks'),
      (d.get('answer') or {}).get('choice'),
      (d.get('applied') or {}).get('ref'),
      'Answered is not applied; verify impact/closure independently',
    ]
    for d in decisions
  ],
  {3: 85, 4: 80},
)
sheet(
  'Checks',
  ['Check', 'Exact command', 'Working directory', 'Start UTC', 'Exit code', 'Outcome', 'Raw log', 'Interpretation'],
  [
    [
      r['id'],
      r['command'],
      r['cwd'],
      r['started_utc'],
      r['exit_code'],
      r['summary'],
      r['log'],
      'Local execution only; does not establish normative adequacy or accepted safety evidence',
    ]
    for r in checks
  ],
  {1: 95, 5: 65, 7: 90},
)
sheet(
  'Engine review',
  ['Issue', 'Type', 'Diagnostic / source observation', 'Observed engine result', 'Risk and required control', 'Source link', 'Evidence basis'],
  engine_rows,
  {2: 80, 3: 48, 4: 100, 5: 85},
)
part_rows = []
for p, title in PARTS.items():
  n = sum(c.startswith(f'{p}:') for c in clause_ids)
  state = (
    'Provisional reference/guidance context'
    if p in (1, 10, 11)
    else ('Provisional outside Corolla scope; verify applicability' if p == 12 else 'Likely project relevance; verify per requirement')
  )
  part_rows.append(
    [p, title, 'User-requested audit scope', state, 'No full source inventory loaded', n, 'Unknown', 'Not established', 'Source custodian + assessor']
  )
sheet(
  'All parts scope',
  [
    'Part',
    'Subject',
    'Requested scope',
    'Provisional relevance',
    'Licensed source state',
    'Referenced buckets only',
    'Total authoritative requirements',
    'Every-clause coverage',
    'Action owner',
  ],
  part_rows,
  {1: 62, 3: 62, 4: 45},
)
sheet('Licensed inventory', standard_fields, [], {4: 65, 7: 65, 12: 65})
gate_names = ['Governance', 'Concept', 'System design', 'HW/SW development', 'Integration & verification', 'Validation & release', 'Operation']
gate_rows = []
for i, name in enumerate(gate_names):
  affected = [f['id'] for f in findings if f'G{i}' in f['gate']]
  gate_rows.append(
    [
      f'G{i}',
      name,
      'No accepted gate record in case/status.json',
      affected,
      'Plans/results/reviews must satisfy the approved gate criteria',
      'No gate accepted by this audit',
    ]
  )
sheet('Gates', ['Gate', 'Lifecycle area', 'Recorded acceptance', 'Priority audit findings', 'Closure rule', 'Audit decision'], gate_rows, {1: 40, 2: 55, 4: 75})

dash = workbook.add_worksheet('Dashboard')
dash.hide_gridlines(2)
dash.set_column(0, 0, 42)
dash.set_column(1, 9, 15)
dash.merge_range('A1:J1', 'LIONDRIVER • ISO 26262 AUDIT', formats['title'])
dash.merge_range(
  'A2:J3', 'Documentary readiness and author actions | Complete standards-clause coverage and normative compliance are NOT yet established.', formats['note']
)
metrics = [
  ('Work-product documents', len(docs)),
  ('Referenced clause buckets (not complete)', len(clause_ids)),
  ('Audit findings', len(findings)),
  ('Registered evidence', len(evidence)),
  ('Accepted evidence (project records)', case['evidence']['accepted']),
  ('Accepted claims (project records)', case['claims']['accepted']),
  ('Open defeaters (project records)', case['defeaters_open']),
  ('Fresh checks passing', sum(c['exit_code'] == 0 for c in checks)),
]
for i, (label, value) in enumerate(metrics, 4):
  dash.write(i, 0, label, formats['note'])
  dash.write_number(i, 1, value)
dash.write('A14', 'Standard compliance percentage', formats['note'])
dash.write('B14', 'Unknown', formats['amber'])
dash.write('A15', 'Authoritative requirement count', formats['note'])
dash.write('B15', 'Unknown', formats['amber'])
dash.write('A17', 'Priority', formats['header'])
dash.write('B17', 'Findings', formats['header'])
counts = Counter(f['priority'] for f in findings)
for i, p in enumerate(['P0', 'P1', 'P2'], 17):
  dash.write(i, 0, p)
  dash.write_formula(i, 1, f'=COUNTIF(Findings!B5:B{len(findings) + 4},A{i + 1})', None, counts[p])
chart = workbook.add_chart({'type': 'column'})
chart.add_series({'name': 'Documentary findings', 'categories': '=Dashboard!$A$18:$A$20', 'values': '=Dashboard!$B$18:$B$20', 'fill': {'color': GOLD}})
chart.set_title({'name': 'Triage priorities — not ASIL or compliance ratings'})
chart.set_legend({'none': True})
dash.insert_chart('D5', chart)
dash.write('A23', 'Part', formats['header'])
dash.write('B23', 'Reference buckets', formats['header'])
for i, p in enumerate(PARTS, 23):
  dash.write(i, 0, p)
  dash.write(i, 1, sum(c.startswith(f'{p}:') for c in clause_ids))
chart = workbook.add_chart({'type': 'bar'})
chart.add_series({'categories': '=Dashboard!$A$24:$A$35', 'values': '=Dashboard!$B$24:$B$35', 'fill': {'color': BLUE}})
chart.set_title({'name': 'Project-cited buckets by part — no completeness denominator'})
chart.set_legend({'none': True})
dash.insert_chart('D22', chart)
dash.activate()
workbook.close()


def setup_plot(title, subtitle, w=14, h=8):
  fig, ax = plt.subplots(figsize=(w, h))
  fig.patch.set_facecolor('#F7F9FC')
  ax.set_facecolor('#F7F9FC')
  ax.set_xlim(0, 100)
  ax.set_ylim(0, 100)
  ax.axis('off')
  ax.text(2, 97, title, fontsize=19, fontweight='bold', color=NAVY, va='top')
  ax.text(2, 90, subtitle, fontsize=10, color=GRAY, va='top')
  ax.text(2, 1, f'ARA-26262-2018-001 v0.1 | UNCONTROLLED | {HEAD[:12]} | Codex / AI-assisted I0 review', fontsize=8, color=GRAY)
  return fig, ax


def box(ax, x, y, w, h, title, body, color=BLUE):
  ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.5', facecolor='white', edgecolor=color, linewidth=1.8))
  ax.text(x + 1.2, y + h - 2, title, fontsize=11, fontweight='bold', color=color, va='top')
  ax.text(x + 1.2, y + h - 7, '\n'.join(textwrap.wrap(body, int(w * 1.55))), fontsize=9, color=NAVY, va='top')


def arrow(ax, a, b):
  ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=14, color=GRAY, lw=1.5))


def save(fig, name):
  svg_path = OUT / f'{name}.svg'
  fig.savefig(svg_path, bbox_inches='tight', metadata={'Date': None})
  svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text().splitlines()) + '\n')
  if os.environ.get('AUDIT_RENDER_PNG', '1') != '0':
    fig.savefig(OUT / f'{name}.png', dpi=160, bbox_inches='tight')
  plt.close(fig)


fig, ax = setup_plot('What the records establish', 'Document presence, reproducibility and acceptance are separate layers.')
layers = [
  (f'{len(docs)} work products', 'Draft documents or skeletons exist; no document approval inferred.', BLUE),
  ('35 partial + 15 missing evidence', 'Author-recorded safety-case evidence; available and accepted counts are zero.', AMBER),
  ('6 local checks pass', 'Consistency and tool tests reproduced here. Hardware, full coverage and normative correctness not established.', BLUE),
  ('0 accepted claims; 41 open defeaters', 'The project safety case does not support release. No signed FSA is supplied.', RED),
]
for i, (t, b, c) in enumerate(layers):
  box(ax, 8, 66 - i * 17, 84, 13, t, b, c)
save(fig, '01_evidence_ladder')
fig, ax = setup_plot('The safety argument depends on unresolved premises', 'Dependencies explain why isolated passing tests do not close the release argument.')
box(ax, 2, 62, 29, 19, 'A06 • Configuration', 'VIN, ECU firmware, device and harness identity remain open.', AMBER)
box(ax, 36, 62, 29, 19, 'A04–A05 • HARA / strategy', 'OEM assumptions and controllability affect ASIL and allocation.', RED)
box(ax, 70, 62, 28, 19, 'A07–A08 • Hardware', 'Generic FMEDA is planning evidence; part-specific metrics missing.', RED)
box(ax, 2, 30, 29, 22, 'A09–A12 • Timing / FFI', 'Warning overrun, curve-bound reaction, zero margin and interference.', RED)
box(ax, 36, 30, 29, 22, 'A13–A16 • Lifecycle / V&V', 'Part 6 deferred; HIL, qualifications and reuse review incomplete.', RED)
box(ax, 70, 30, 28, 22, 'A02–A03 • Confirmation', 'Named independent human review and assessment remain unperformed.', RED)
box(ax, 28, 7, 48, 14, 'A20 • Release claim not supported', '0 accepted evidence, 0 accepted claims, 41 open defeaters.', RED)
for a, b in [
  ((31, 72), (36, 72)),
  ((65, 72), (70, 72)),
  ((16, 62), (16, 52)),
  ((50, 62), (50, 52)),
  ((84, 62), (84, 52)),
  ((16, 30), (38, 21)),
  ((50, 30), (50, 21)),
  ((84, 30), (65, 21)),
]:
  arrow(ax, a, b)
save(fig, '02_argument_dependencies')
fig, ax = setup_plot('Coverage across all 12 parts', 'Numbers count extracted project references, not standard requirements or compliance.')
for i, (p, title) in enumerate(PARTS.items()):
  col = i % 2
  row = i // 2
  n = sum(c.startswith(f'{p}:') for c in clause_ids)
  box(ax, 2 + col * 49, 72 - row * 11, 46, 9, f'Part {p} • {n} reference buckets', title, GRAY if p in (1, 10, 11, 12) else BLUE)
ax.text(3, 6, 'Every-clause denominator: UNKNOWN. Source access and requirement-level reconciliation are mandatory.', fontsize=10, color=RED, fontweight='bold')
save(fig, '03_parts_coverage')
fig, ax = setup_plot(
  'How an author closes an audit finding', 'Compliance status changes only after requirement, applicability, evidence and review are linked.'
)
stages = [
  ('1 • Verify requirement', 'Licensed clause, table/annex, ASIL and page citation.'),
  ('2 • Decide applicability', 'Configuration-specific rationale; no automatic N/A.'),
  ('3 • Locate actual evidence', 'Analysis + baseline-bound execution, anomalies and results.'),
  ('4 • Evaluate sufficiency', 'Correctness, independence, assumptions, margins and completeness.'),
  ('5 • Close with review', 'Assigned qualified reviewer and documented disposition.'),
]
for i, (t, b) in enumerate(stages):
  box(ax, 7, 70 - i * 13, 86, 10, t, b, BLUE)
  if i < 4:
    arrow(ax, (50, 70 - i * 13), (50, 67 - i * 13))
ax.text(8, 6, 'A draft, a passing checker or an author-side AI review cannot jump directly to compliant.', fontsize=11, color=RED)
save(fig, '04_closure_workflow')
fig, ax = setup_plot('Where the compliance checker belongs', 'Observed false positives require a boundary between matching and assessor verdicts.')
box(
  ax, 5, 59, 41, 22, 'Verified ISO source inventory', 'Exact edition, part, requirement, ASIL, tables, annexes and source pages. Pending source access.', AMBER
)
box(ax, 54, 59, 41, 22, 'LionDriver subject evidence', 'Configuration, work products, results, reviews and anomalies; linked to immutable revisions.', BLUE)
box(
  ax,
  22,
  31,
  56,
  18,
  'Matcher • candidate links only',
  'Fuzzy matching can support navigation. E01–E04 diagnostics produced misleading 100% scores or compliance labels.',
  AMBER,
)
box(
  ax,
  14,
  7,
  72,
  16,
  'Assessor ledger • evidence-based decisions',
  'Verify applicability and evidence sufficiency independently. Neither text similarity nor an automatic grade supplies confirmation.',
  BLUE,
)
arrow(ax, (25, 59), (40, 49))
arrow(ax, (75, 59), (60, 49))
arrow(ax, (50, 31), (50, 23))
save(fig, '05_checker_boundary')

# Standalone interactive review board; all contents are escaped project-derived text.
cards = ''.join(f'<div class="card"><b>{v}</b><span>{html.escape(k)}</span></div>' for k, v in metrics[:7])
rows = ''.join(
  '<tr data-priority="'
  + f['priority']
  + '"><td>'
  + html.escape(f['id'])
  + '</td><td>'
  + f['priority']
  + '</td><td>'
  + html.escape(f['area'])
  + '</td><td>'
  + html.escape(f['title'])
  + '</td><td>'
  + html.escape(f['analysis'])
  + '</td><td>'
  + html.escape(f['owner'] + ' · ' + f['gate'] + ' — ' + f['action'])
  + '</td><td>'
  + html.escape(f['closure'])
  + '</td><td><a href="'
  + html.escape(f['evidence']['url'], quote=True)
  + '">'
  + f['evidence']['document']
  + ':'
  + str(f['evidence']['line'])
  + '</a></td></tr>'
  for f in findings
)
figures = ''.join(
  '<figure>' + re.search(r'<svg[\s\S]+</svg>', (OUT / f'{name}.svg').read_text()).group(0) + f'<figcaption>{label}</figcaption></figure>'
  for name, label in [
    ('01_evidence_ladder', 'Evidence maturity'),
    ('02_argument_dependencies', 'Safety argument dependencies'),
    ('03_parts_coverage', 'All-parts coverage boundaries'),
    ('04_closure_workflow', 'Author closure workflow'),
    ('05_checker_boundary', 'Compliance checker authority boundary'),
  ]
)
page = (
  '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-wid'
  + 'th,initial-scale=1"><title>LionDriver assurance audit</title><style>body{margin:0;background:#f7f9fc'
  + ';color:#14263d;font:16px system-ui}main{max-width:1450px;margin:auto;padding:32px}h1{font-size:34px}'
  + '.notice{background:#fff0cf;border-left:6px solid #a46c15;padding:18px;line-height:1.6}.cards{display'
  + ':flex;flex-wrap:wrap;gap:12px;margin:24px 0}.card{background:white;border:1px solid #d9e1eb;padding:'
  + '18px;flex:1;min-width:140px}.card b{display:block;font-size:30px}.card span{font-size:13px}figure{ma'
  + 'rgin:20px 0;background:white;border:1px solid #d9e1eb;padding:10px}img,svg{width:100%;height:auto}fi'
  + 'gcaption{padding:8px}input,select{padding:12px;border:1px solid #aab8c8;font:inherit;margin:8px}tabl'
  + 'e{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:12px;text-align:left;vertical-ali'
  + 'gn:top;border-bottom:1px solid #d9e1eb}th{background:#14263d;color:white;position:sticky;top:0}tr[da'
  + 'ta-priority=P0] td:nth-child(2){color:#ac3941;font-weight:bold}a{color:#376c95}.table{overflow:auto}'
  + 'td:nth-child(5),td:nth-child(6),td:nth-child(7){min-width:260px}@media print{input,select{display:no'
  + 'ne}.table{overflow:visible}th{position:static}figure{break-inside:avoid}}</style><main><h1>LionDrive'
  + 'r • ISO 26262:2018 audit workbench</h1><p>BASELINE</p><div class="notice"><strong>Provisional docume'
  + 'ntary audit.</strong> Complete clause coverage and normative compliance are not established until th'
  + 'e licensed source is accessible, its requirement inventory is reconciled and applicability is approv'
  + 'ed. Findings are source-linked author actions. This is AI-assisted analysis, not a signed independen'
  + 't confirmation or FSA.</div>CARDS<p><a href="LionDriver_ISO26262_Audit.xlsx">Open the audit workbook'
  + '</a> · <a href="Audit_report.md">Read the assessment report</a> · <a href="licensed_clause_inventory'
  + '.csv">Licensed source inventory template</a></p>FIGURES<h2>Author action ledger</h2><input id="searc'
  + 'h" placeholder="Search finding, owner action or evidence…" aria-label="Search findings"><select id="'
  + 'priority" aria-label="Priority"><option value="">All priorities</option><option>P0</option><option>P'
  + '1</option><option>P2</option></select><p id="count"></p><div class="table"><table><thead><tr><th>ID<'
  + '/th><th>Priority</th><th>Area</th><th>Finding</th><th>Reasoning</th><th>Author action</th><th>Closur'
  + 'e evidence</th><th>Source</th></tr></thead><tbody>ROWS</tbody></table></div><script>const search=doc'
  + "ument.querySelector('#search'),priority=document.querySelector('#priority'),rows=[...document.queryS"
  + "electorAll('tbody tr')];function filter(){let count=0;for(const row of rows){const shown=row.textCon"
  + 'tent.toLowerCase().includes(search.value.toLowerCase())&&(!priority.value||row.dataset.priority===pr'
  + "iority.value);row.hidden=!shown;if(shown)count++}document.querySelector('#count').textContent=count+"
  + "' findings shown'}search.addEventListener('input',filter);priority.addEventListener('change',filter)"
  + ';filter();</script></main></html>'
)
page = page.replace('BASELINE', html.escape(HEAD)).replace('CARDS', cards).replace('FIGURES', figures).replace('ROWS', rows)
(OUT / 'Review_board.html').write_text(page)

report = (
  '# LionDriver ISO 26262:2018 documentary audit\n\n| Field | Value |\n|---|---|\n| Record | ARA-26262-2018'
  + '-001 (supporting assessment aid) |\n| Revision | 0.1 |\n| Status | Draft — awaiting human verification'
  + ' |\n| Author / documentary assessor | Codex (OpenAI AI assistant), I0 |\n| Qualified independent asses'
  + 'sor | Not appointed by this record |\n| Approver | Project maintainer / safety manager; approval pend'
  + 'ing |\n| Distribution | Uncontrolled generated public view |\n| Document control | Package README, fin'
  + 'dings.csv, clause-map.csv, audit_data.json and manifest.json |\n\nAssessment subject: `'
  + f'{HEAD}'
  + '` (`liondriver-dev` checkout). User-requested scope: all 12 parts, ISO 26262:2018. Artifacts are out'
  + 'side the subject checkout; no source, work-product or acceptance records were changed.\n\n## Overall j'
  + 'udgment\n\nThe documentary record does **not demonstrate ISO 26262 compliance or support a release cla'
  + 'im**. This is not a finding that every clause is violated. The available record contains substantive'
  + ' drafts and reproducible consistency tools, but the central configuration, assumptions, quantitative'
  + ' hardware evidence, end-to-end timing, interference argument and independent confirmation remain unr'
  + 'esolved.\n\n**Every-clause completeness is pending**: the user confirms a licensed source exists, but '
  + 'the supplied Windows search link is not accessible from this cloud machine and no standards source h'
  + 'as been accessed during this pass. The workbook contains '
  + f'{len(clause_ids)}'
  + ' project-referenced clause buckets and '
  + f'{len(associations)}'
  + ' source associations. These are not the total standard requirements. No compliance percentage is cal'
  + 'culated and no normative verdict is set to compliant, non-compliant or N/A.\n\n## What was examined\n\nA'
  + 'll '
  + f'{len(docs)}'
  + ' work-product files were inventoried for headers, declared references and open items. The register w'
  + 'as reconciled to '
  + f'{len(register_rows)}'
  + ' rows. Explicit ISO references were extracted across '
  + f'{len(all_md)}'
  + ' assurance Markdown files. '
  + f'{len(PRIMARY)}'
  + ' key work products received targeted substantive examination, alongside current case records, select'
  + 'ed pre-review records, the decision register and trace records. Remaining documents have inventory-l'
  + 'evel review; the workbook makes this distinction explicit. This was not an exhaustive sentence-level'
  + ' or requirement-level audit.\n\nThe case records report '
  + f"{case['claims']['registered']}"
  + ' claims, '
  + f"{case['claims']['accepted']}"
  + ' accepted claims, '
  + f"{case['evidence']['registered']}"
  + ' evidence items ('
  + f"{case['evidence']['partial']}"
  + ' partial, '
  + f"{case['evidence']['missing']}"
  + ' missing, '
  + f"{case['evidence']['accepted']}"
  + ' accepted), and '
  + f"{case['defeaters_open']}"
  + ' open defeaters. These values are project-declared, checker-validated status, not new acceptance dec'
  + 'isions.\n\n## Priority judgment\n\nThe chain of dependencies matters more than the number of documents. '
  + 'An unfrozen device/ECU configuration prevents evidence binding. Unverified OEM assumptions can incre'
  + 'ase the required ASIL. The resulting integrity demand drives hardware metrics, FFI, software scope a'
  + 'nd independence. A lower target chosen before the assumptions are validated can make later apparentl'
  + 'y passing results irrelevant. HIL deferral and no-assessor decisions are incompatible with closure u'
  + "nder the project's current gate plan; retain open status or formally re-plan.\n\nThe explicit timing i"
  + 'ssues need resolution before approval: the 1.26 s EPS-warning analysis exceeds the 1 s budget; the c'
  + 'urve-bound estimate is about 0.7 s before departure; PCS forwarding-loss timing has zero margin. The'
  + 'se are documentary analyses and discrepancies, not witnessed hardware measurements. Planned hardware'
  + '-measure results and generic failure rates must never be presented as demonstrated metrics. WP-H-03 '
  + 'explicitly says its generic estimates are not compliance evidence.\n\n## Findings and author actions\n\n'
)
for f in findings:
  e = f['evidence']
  report += (
    '### '
    + f"{f['id']}"
    + ' · '
    + f"{f['priority']}"
    + ' · '
    + f"{f['title']}"
    + '\n\n'
    + f"{f['analysis']}"
    + '\n\nSource: ['
    + f"{e['document']}"
    + ':'
    + f"{e['line']}"
    + ']('
    + f"{e['url']}"
    + ').\n\nAction ('
    + f"{f['owner']}"
    + '; '
    + f"{f['gate']}"
    + '): '
    + f"{f['action']}"
    + '\n\nClosure: '
    + f"{f['closure']}"
    + '\n\n'
  )
report += (
  '## Review of compliance-checker-algo\n\nThe user-supplied repository was inspected read-only at `'
  + f'{ENGINE_HEAD}'
  + '`. It contains fictional example standards only; it does not supply the licensed ISO 26262 source. I'
  + 'ts standard/artifact normalization and candidate matching may help navigation, but its automatic com'
  + 'pliance labels are not used in this audit.\n\nThe synthetic example completed. Four targeted diagnosti'
  + 'c probes demonstrated that (E01) one unqualified clause ID can cover two different standard parts; ('
  + 'E02) text explicitly saying MC/DC was not performed scores the method as matched; (E03) no parsed me'
  + 'thod tables scores 100%; and (E04) a generic aggregate grade of 90 becomes A — Compliant. Static rev'
  + 'iew additionally found that unmapped artifacts become N/A and that a hardcoded confirmation/independ'
  + 'ence model is presented inside the agnostic engine. Source lines, observed results and controls are '
  + 'in the Engine review sheet and `engine_review.json`.\n\nUse this engine only for candidate cross-refer'
  + 'ences until these behaviors are controlled and its intended safety use is independently validated. U'
  + 'se edition+part+clause+requirement-qualified IDs; preserve negation and unperformed status; distingu'
  + 'ish missing parsing from N/A; require source-based applicability and evidence/independence before an'
  + 'y normative verdict. The prototype has not been modified.\n\n'
)
report += (
  '## Local verification and its limits\n\nSix checks were rerun with exact commands and logs on the asse'
  + 'ssed checkout. They validate record consistency, generated views, trace relationships and checker te'
  + 'sts. They do not establish semantic correctness of the requirements, validity of all HARA judgments,'
  + ' authoritative ASIL-table accuracy, target timing, hardware fault coverage, supplier evidence, or in'
  + 'dependence. Skips and advisory state-machine findings remain visible in the raw logs.\n\n| Check | Exi'
  + 't code | Outcome |\n|---|---|---|\n'
)
for c in checks:
  report += f"| {c['id']} | {c['exit_code']} | {c['summary']} |\n"
report += (
  '\n## Finishing the normative audit\n\n1. Provide the location of the licensed ISO 26262:2018 source for'
  + ' all parts. Read normative requirements, tables, annexes and ASIL-dependent method requirements dire'
  + 'ctly; do not reconstruct them from project citations or memory.\n2. Populate the authoritative invent'
  + 'ory at requirement granularity, recording edition, part, clause/table/annex, requirement identifier,'
  + ' paraphrase, normative/informative kind, ASIL applicability and source page. Compare the inventory a'
  + "gainst the standard's own contents and every normative requirement. A clause can contain multiple se"
  + 'parately auditable obligations.\n3. Determine applicability for the actual Corolla configuration. Voc'
  + 'abulary/guidance and motorcycle adaptations require appropriate treatment; do not blanket-mark them '
  + 'as applicable or non-compliant.\n4. Map each applicable obligation to its work products, actual resul'
  + 'ts and acceptance/review records. Assess correctness and sufficiency, not merely existence. Evaluate'
  + ' tailoring and supplier allocations against exact authority.\n5. Issue evidence-linked normative find'
  + 'ings and have qualified independent reviewers disposition them. Close only when the acceptance crite'
  + 'ria and required independence are met.\n\nNo work-product status, evidence acceptance, gate record, FS'
  + 'A recommendation or release authorization has been changed by this deliverable.\n'
)
(OUT / 'Audit_report.md').write_text(report)
(OUT / 'GENERATED_VIEW_GUIDE.md').write_text(
  '# Audit package\n\nOpen `LionDriver_ISO26262_Audit.xlsx` for the filterable workbook, or `Review_board'
  + '.html` for the offline interactive diagrams and finding ledger. Read `Audit_report.md` for scope, su'
  + 'bstantive findings and limits. SVG and PNG files are standalone exportable diagrams.\n\nThe workbook i'
  + 'ntentionally contains no verified compliant/non-compliant verdicts and no guessed complete standard '
  + 'inventory. User-provided licensed source access is pending. `licensed_clause_inventory.csv` is the s'
  + 'ource inventory input template; a non-empty input makes the generator stop for explicit normative in'
  + 'tegration instead of silently ignoring it.\n\nUse the controlled package README and `regenerate.sh` to'
  + ' render the archived subject revision. Dependencies are recorded in `requirements.lock.txt`. The sou'
  + 'rce root, source Git repository, subject revision and output directory are supplied by the reproduct'
  + 'ion script. Fresh checks and raw logs are in `checks.json` and `logs/`. Source hashes and exact chec'
  + 'kout identity are in `audit_data.json` and `manifest.json`. This workbook is an AI-assisted review a'
  + 'id and has not been independently qualified as a safety assessment tool.\n'
)
manifest = {
  'subject_head': HEAD,
  'submodule_pins': [l for l in subprocess.check_output(['git', 'ls-tree', HEAD], cwd=GIT_REPO, text=True).splitlines() if l.startswith('160000 ')],
  'source_work_products': [{k: d[k] for k in ('id', 'path', 'sha256')} for d in docs],
  'document_control': {
    'record': 'ARA-26262-2018-001',
    'revision': '0.1',
    'status': 'Draft',
    'artifact_author': 'Codex (OpenAI AI assistant)',
    'independence_credit': 'I0 only; no qualified third-party assessor appointment',
    'approval': 'Pending',
  },
  'artifact_sha256': {},
}
for p in sorted(OUT.rglob('*')):
  if p.is_file() and p.name != 'manifest.json':
    manifest['artifact_sha256'][str(p.relative_to(OUT))] = hashlib.sha256(p.read_bytes()).hexdigest()
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps({k: v for k, v in summary.items() if k not in ('case', 'checks')}, indent=2))
