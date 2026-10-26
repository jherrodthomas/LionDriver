#!/usr/bin/env bash
# LionDriver (WP-W-03 ATC-19, RR-2026-009 F-33): select the release variant explicitly. Sourced by build_release.sh.
#
#   RELEASE_VARIANT=reference (default)  panda firmware and pandad built with LIONDRIVER_REFERENCE=1: safety-mode lock,
#                                         reduced TX whitelist, TX-rate and command-freshness supervision; the panda
#                                         reports HEALTH_FLAG_REFERENCE_BUILD and pandad refuses a non-reference panda;
#                                         no joystick or maneuver processes registered or shipped (DQ-131)
#   RELEASE_VARIANT=upstream              built without them, for upstream compatibility only; not a LionDriver release
#
# The root SConstruct already defaults to the reference build when LIONDRIVER_REFERENCE is unset; setting it here
# explicitly means a stray empty LIONDRIVER_REFERENCE in the environment cannot silently produce an upstream build.

RELEASE_VARIANT="${RELEASE_VARIANT:-reference}"
case "$RELEASE_VARIANT" in
  reference)
    export LIONDRIVER_REFERENCE=1
    ;;
  upstream)
    export LIONDRIVER_REFERENCE=
    echo "WARNING: upstream release variant: the LionDriver reference safety mechanisms are NOT built in" >&2
    ;;
  *)
    echo "RELEASE_VARIANT must be 'reference' or 'upstream', not '$RELEASE_VARIANT'" >&2
    return 1 2>/dev/null || exit 1
    ;;
esac
export RELEASE_VARIANT
