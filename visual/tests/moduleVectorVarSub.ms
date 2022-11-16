
/* write to/read from one register at a time. */

module Regs;
    Vector#(2, Reg#(Bit#(4))) regs(0);
    input Bit#(4) data default = 0;
    input Bit#(1) sel default = 0;
    method Bit#(4) getData = regs[sel];
    rule tick;
        regs[sel] <= data;
    endrule
endmodule

module MoreRegs;
    Vector#(2, Regs) regs;
    input Bit#(4) data;
    input Bit#(1) sel1;
    input Bit#(1) sel2;
    method Bit#(4) getData = regs[sel1].getData;
    rule tick;
        regs[sel1].sel = sel2;
        regs[sel1].data = data;
    endrule
endmodule