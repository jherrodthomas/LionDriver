#!/usr/bin/env python3
"""Make picorv32_ecc.v from the fetched picorv32.v: use the SECDED register file (PICORV32_REGS hook) and bring its
corrected/error flags out as two new ports. The original licence and notice stay in the file unchanged."""
import sys

src, dst = sys.argv[1], sys.argv[2]
s = open(src).read()
head = ("// Modified for a fault-injection demonstration: register file replaced by a SECDED version (picorv32_regs_ecc.v)\n"
        "// and its corrected/error flags brought out as ports. Original licence and notice below are unchanged.\n"
        "`define PICORV32_REGS picorv32_regs_ecc\n")
edits = [("\toutput reg [35:0] trace_data\n);", "\toutput reg [35:0] trace_data,\n\n\t// ECC flags of the register file\n"
          "\toutput ecc_corrected,\n\toutput ecc_error\n);"),
         ("\t\t.rdata2(cpuregs_rdata2)\n\t);", "\t\t.rdata2(cpuregs_rdata2),\n\t\t.corr(ecc_corrected),\n\t\t.err(ecc_error)\n\t);")]
for old, new in edits:
  if s.count(old) < 1:
    sys.exit(f"patch point not found: {old!r}")
  s = s.replace(old, new, 1)
open(dst, "w").write(head + s)
