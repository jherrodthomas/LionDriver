// Two PicoRV32 cores on the same inputs; a comparator flags any difference on any output, every cycle.
module lockstep_top (
  input clk, resetn, mem_ready,
  input [31:0] mem_rdata, irq,
  output mem_valid, mem_instr, output [31:0] mem_addr, mem_wdata, output [3:0] mem_wstrb,
  output trap, output lockstep_error
);
  localparam N = 1 + 1 + 32 + 32 + 4 + 1 + 1 + 1 + 32 + 32 + 4 + 1 + 32 + 32 + 32 + 32 + 1 + 36;
  wire [N-1:0] oa, ob;
  picorv32 #(.ENABLE_MUL(1), .ENABLE_DIV(1), .ENABLE_IRQ(1), .ENABLE_IRQ_QREGS(1), .ENABLE_COUNTERS(1)) a (
    .clk(clk), .resetn(resetn), .mem_ready(mem_ready), .mem_rdata(mem_rdata), .irq(irq),
    .pcpi_wr(1'b0), .pcpi_rd(32'b0), .pcpi_wait(1'b0), .pcpi_ready(1'b0),
    .mem_valid(oa[0]), .mem_instr(oa[1]), .mem_addr(oa[33:2]), .mem_wdata(oa[65:34]), .mem_wstrb(oa[69:66]),
    .trap(oa[70]), .mem_la_read(oa[71]), .mem_la_write(oa[72]), .mem_la_addr(oa[104:73]), .mem_la_wdata(oa[136:105]),
    .mem_la_wstrb(oa[140:137]), .pcpi_valid(oa[141]), .pcpi_insn(oa[173:142]), .pcpi_rs1(oa[205:174]),
    .pcpi_rs2(oa[237:206]), .eoi(oa[269:238]), .trace_valid(oa[270]), .trace_data(oa[306:271]));
  picorv32 #(.ENABLE_MUL(1), .ENABLE_DIV(1), .ENABLE_IRQ(1), .ENABLE_IRQ_QREGS(1), .ENABLE_COUNTERS(1)) b (
    .clk(clk), .resetn(resetn), .mem_ready(mem_ready), .mem_rdata(mem_rdata), .irq(irq),
    .pcpi_wr(1'b0), .pcpi_rd(32'b0), .pcpi_wait(1'b0), .pcpi_ready(1'b0),
    .mem_valid(ob[0]), .mem_instr(ob[1]), .mem_addr(ob[33:2]), .mem_wdata(ob[65:34]), .mem_wstrb(ob[69:66]),
    .trap(ob[70]), .mem_la_read(ob[71]), .mem_la_write(ob[72]), .mem_la_addr(ob[104:73]), .mem_la_wdata(ob[136:105]),
    .mem_la_wstrb(ob[140:137]), .pcpi_valid(ob[141]), .pcpi_insn(ob[173:142]), .pcpi_rs1(ob[205:174]),
    .pcpi_rs2(ob[237:206]), .eoi(ob[269:238]), .trace_valid(ob[270]), .trace_data(ob[306:271]));
  assign {trap, mem_wstrb, mem_wdata, mem_addr, mem_instr, mem_valid} = oa[70:0];
  reg err;
  always @(posedge clk) err <= resetn && (oa != ob);   // registered compare
  assign lockstep_error = err;
endmodule
