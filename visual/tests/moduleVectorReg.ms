
module Regs;
    Vector#(3, Vector#(2, Vector#(2, Reg#(Bit#(4))))) regs(0);
    input Bit#(4) data;
    input Bit#(2) sel1;
    input Bit#(2) sel2;
    method Bit#(4) getData = regs[sel1][1][sel2];
    rule tick;
        regs[sel1][sel2][0] <= data;
    endrule
endmodule