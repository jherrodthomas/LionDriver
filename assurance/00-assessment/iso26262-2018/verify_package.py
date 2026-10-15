#!/usr/bin/env python3
"""Verify evidence binding and published-view integrity, not normative compliance."""

from pathlib import Path
import csv
import hashlib
import json
import subprocess
import zipfile


def verify():
  package = Path(__file__).resolve().parent
  root = Path(subprocess.check_output(['git', '-C', str(package), 'rev-parse', '--show-toplevel'], text=True).strip())
  data = json.loads((package / 'audit_data.json').read_text())
  manifest = json.loads((package / 'manifest.json').read_text())
  subject = data['summary']['baseline']
  assert subject == manifest['subject_head'], 'Subject revision mismatch'
  assert subprocess.check_output(['git', 'rev-parse', '--verify', subject + '^{commit}'], cwd=root, text=True).strip() == subject
  assert data['summary']['complete_standard_inventory'] is False, 'Normative completeness must not be inferred'
  assert len(data['work_products']) == data['summary']['work_products'] == 88
  source_records = {d['id']: d for d in manifest['source_work_products']}
  for document in data['work_products']:
    source = subprocess.check_output(['git', 'show', subject + ':' + document['path']], cwd=root)
    digest = hashlib.sha256(source).hexdigest()
    assert digest == document['sha256'] == source_records[document['id']]['sha256'], document['id']
  for name, expected in manifest['artifact_sha256'].items():
    target = (package / name).resolve()
    assert target.is_relative_to(package), 'Manifest path escapes package'
    assert hashlib.sha256(target.read_bytes()).hexdigest() == expected, 'Artifact mismatch: ' + name
  findings = list(csv.DictReader((package / 'findings.csv').open()))
  assert len(findings) == len(data['findings']) == 22
  for row, record in zip(findings, data['findings'], strict=True):
    for field in ['id', 'priority', 'area', 'title', 'analysis', 'action', 'owner', 'gate', 'closure', 'state']:
      assert row[field] == record[field], 'Finding source mismatch: ' + row['id'] + ':' + field
    assert row['document'] == record['evidence']['document']
    assert row['source_path'] == record['evidence']['path']
    assert int(row['source_line']) == record['evidence']['line']
    assert row['state'] == 'Open', 'No finding closure accepted in this revision'
  links = list(csv.DictReader((package / 'clause-map.csv').open()))
  assert len(links) == len(data['clause_associations']) == 368
  for row, record in zip(links, data['clause_associations'], strict=True):
    for field in row:
      assert row[field] == str(record[field]), 'Clause-map mismatch'
  assert all(c['exit_code'] == 0 for c in data['summary']['checks'])
  for check in data['summary']['checks']:
    assert (package / check['log']).is_file(), 'Missing raw execution log'
  with zipfile.ZipFile(package / 'LionDriver_ISO26262_Audit.xlsx') as book:
    assert book.testzip() is None, 'Workbook ZIP corruption'
  assert (package / 'Review_board.html').read_text().count('<svg ') == 5
  print('PASS: source objects, 88 WPs, 22 findings, 368 source associations, hashes, logs and generated views agree.')
  print('No normative completeness, acceptance, independent confirmation or QMS approval inferred.')


if __name__ == '__main__':
  verify()
