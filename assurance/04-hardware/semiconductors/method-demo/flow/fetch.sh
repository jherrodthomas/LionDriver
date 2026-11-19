#!/usr/bin/env bash
# Fetch the three third-party inputs at pinned commits and check them by SHA-256. Nothing third-party is committed.
#   PicoRV32 (ISC licence), YosysHQ/picorv32
#   sky130_fd_sc_hd typical-corner liberty (Apache-2.0), via OpenROAD-flow-scripts
#   sky130_fd_sc_hd__dfxtp_1 cell layout (Apache-2.0), google/skywater-pdk-libs-sky130_fd_sc_hd
set -euo pipefail
OUT="${1:-build}"
mkdir -p "$OUT"
get() {  # url file sha256
  curl -sSfL -o "$OUT/$2" "$1"
  echo "$3  $OUT/$2" | sha256sum -c --quiet -
}
get https://raw.githubusercontent.com/YosysHQ/picorv32/ef203c2b0a3fb793280f5114941416c425c5b461/picorv32.v \
    picorv32.v 0836050971b3c6cdd28ac3b1e5719a67fb645161912bef1e472e63995ceb0622
get https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD-flow-scripts/5cbd5178dc15264dbb2c6233922953347b6de92c/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib \
    tt.lib ec0e1067a35c8bf20b11e58d1e8ac53326067e4dac84a125cc1b917a3518d0d9
get https://raw.githubusercontent.com/google/skywater-pdk-libs-sky130_fd_sc_hd/ac7fb61f06e6470b94e8afdf7c25268f62fbd7b1/cells/dfxtp/sky130_fd_sc_hd__dfxtp_1.gds \
    dfxtp_1.gds 2b0eaaeedd5b7b2c359942098aee0cef69387108e02e10bc09940680e4cc7ec3
echo "fetched into $OUT"
