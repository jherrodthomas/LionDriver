#!/usr/bin/env bash
# Reproduce every result in ../results from scratch: fetch, synthesise, split, run the three campaigns, score.
# Needs: python3, curl, `pip install yowasp-yosys gdstk`. About 20 minutes on 4 CPUs.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
B="${1:-$HERE/../build}"
bash "$HERE/fetch.sh" "$B"
cd "$B"
export PYTHONPATH="$HERE"
cp "$HERE"/synth.ys "$HERE"/synth_ecc.ys "$HERE"/synth_ls.ys "$HERE"/lockstep_top.v .

# synthesis: plain core, ECC core, lockstep pair
yowasp-yosys -q synth.ys && mv stat.txt stat_base.txt
python3 "$HERE/gen_regs_ecc.py"
python3 "$HERE/patch_picorv32_ecc.py" picorv32.v picorv32_ecc.v
yowasp-yosys -q synth_ecc.ys && mv stat.txt stat_ecc.txt
yowasp-yosys -q synth_ls.ys && mv stat.txt stat_lockstep.txt

# split and self-test campaign
python3 "$HERE/subparts.py" netlist.json tt.lib subparts.json
python3 "$HERE/campaign.py" golden
python3 "$HERE/campaign.py" run 4 faults.json
python3 "$HERE/analyze.py" netlist.json subparts.json subparts-cells.json faults.json coverage.json

# ECC: the same flips in both register files
for p in 0 1; do
  NETLIST=netlist.json python3 "$HERE/ecc_campaign.py" base $p 2 ecc_base_$p.json &
  NETLIST=netlist_ecc.json python3 "$HERE/ecc_campaign.py" ecc $p 2 ecc_ecc_$p.json &
done
wait
python3 "$HERE/ecc_score.py" stat_base.txt stat_ecc.txt

# lockstep: all faults in one core, then the common-cause glitches
python3 "$HERE/lockstep.py" golden
for p in 0 1 2 3; do python3 "$HERE/lockstep.py" run $p 4 ls_$p.json & done
wait
python3 "$HERE/lockstep_cc.py"
python3 "$HERE/lockstep_score.py" stat_base.txt stat_lockstep.txt

python3 "$HERE/extract_cell.py" dfxtp_1.gds sky130_dfxtp_1.json
cp subparts.json coverage.json ecc_summary.json lockstep_summary.json sky130_dfxtp_1.json "$HERE/../results/"
echo "results updated; run figures/fig_md_core.py and figures/fig_md_explainers.py"
