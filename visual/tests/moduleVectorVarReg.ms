
module Regs;
    Vector#(2, Vector#(3, Reg#(Bit#(4)))) regs(0);
    input Bit#(4) data;
    input Bit#(1) sel1;
    input Bit#(2) sel2;
    method Bit#(4) out = regs[sel1][sel2];
    rule tick;
        regs[sel1][0] <= data;
    endrule
endmodule