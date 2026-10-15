#!/usr/bin/env bash
set -euo pipefail
audit_package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
audit_repository_root="$(git -C "$audit_package_dir" rev-parse --show-toplevel)"
audit_subject_revision=20569e916c9359243739b71e4dc79876aec48cc0
audit_render_root="$(mktemp -d /tmp/liondriver-audit-render.XXXXXX)"
mkdir -p "$audit_render_root/subject" "$audit_render_root/output"
git -C "$audit_repository_root" archive "$audit_subject_revision" assurance | tar -xf - -C "$audit_render_root/subject"
audit_python=3.12.13
if [[ -x "$audit_repository_root/.venv/bin/python" ]]; then
  audit_python="$audit_repository_root/.venv/bin/python"
fi
UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/liondriver-audit-uv-cache}" \
UV_PYTHON_INSTALL_DIR="${UV_PYTHON_INSTALL_DIR:-/tmp/liondriver-audit-python}" \
  uv venv "$audit_render_root/venv" --python "$audit_python"
UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/liondriver-audit-uv-cache}" uv pip install --python "$audit_render_root/venv/bin/python" -r "$audit_package_dir/requirements.lock.txt"
cp "$audit_package_dir/checks.json" "$audit_package_dir/engine_review.json" "$audit_package_dir/licensed_clause_inventory.csv" "$audit_render_root/output/"
AUDIT_SOURCE_ROOT="$audit_render_root/subject" \
AUDIT_GIT_REPO="$audit_repository_root" \
AUDIT_REVISION="$audit_subject_revision" \
AUDIT_OUTPUT_DIR="$audit_render_root/output" \
AUDIT_RENDER_PNG=0 \
  "$audit_render_root/venv/bin/python" "$audit_package_dir/build_audit.py"
printf 'Candidate generated views: %s\nSubject remains: %s\n' "$audit_render_root/output" "$audit_subject_revision"
