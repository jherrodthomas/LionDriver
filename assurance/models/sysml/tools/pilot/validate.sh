#!/usr/bin/env bash
# Validate the LionDriver SysML v2 model with the OMG pilot implementation (WP-P-07 TL-26).
# Parses the model files in dependency order and fails on any syntax or semantic error.
# Usage: validate.sh [cache-dir]   (needs JDK 21+ (javac), python3 with zstandard)
set -euo pipefail
JAVA_MAJOR="$(javac -version 2>&1 | grep -oE '[0-9]+' | head -1)"
if [ "${JAVA_MAJOR:-0}" -lt 21 ]; then
  echo "validate.sh: the pilot implementation needs JDK 21 or newer; javac reports ${JAVA_MAJOR:-none}" >&2
  exit 1
fi
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL="$HERE/../../model"
CACHE="${1:-${XDG_CACHE_HOME:-$HOME/.cache}/liondriver-sysml-pilot}"
KERNEL="$(python3 "$HERE/fetch_pilot.py" "$CACHE")"
JAR="$(ls "$KERNEL"/jupyter-sysml-kernel-*-all.jar)"
BUILD="$CACHE/classes"
mkdir -p "$BUILD"
javac -d "$BUILD" -cp "$JAR" "$HERE/SysMLValidate.java"
java -cp "$JAR:$BUILD" SysMLValidate "$KERNEL/sysml.library" \
  "$MODEL/LionDriverLibrary.sysml" "$MODEL/Mechanisms.sysml" "$MODEL/Functions.sysml" "$MODEL/Architecture.sysml" "$MODEL/Security.sysml" "$MODEL/Integration.sysml" "$MODEL/Behaviour.sysml" "$MODEL/Requirements.sysml" \
  "$MODEL/Satisfaction.sysml" "$MODEL/Verification.sysml" "$MODEL/Needs.sysml" "$MODEL/StateRecords.sysml" "$MODEL/Sequences.sysml" "$MODEL/Lifecycle.sysml" "$MODEL/Timing.sysml" "$MODEL/Signals.sysml" "$MODEL/Views.sysml" \
  2>&1 | grep -vE '^(Reading |log4j:)'
