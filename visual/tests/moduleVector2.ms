

module Test;
    Vector#(2, Vector#(2, Reg#(Bit#(4)))) r(0);
    input Bit#(1) sel1;
    input Bit#(1) sel2;
    input Bit#(1) sel3;
    method Bit#(1) out1 = r[sel1][sel2][sel3];
    method Bit#(1) out2 = r[sel1][0][sel3];
    method Bit#(1) out3 = r[1][sel2][sel3];
    input Bit#(1) sh1;
    input Bit#(16) in;
    rule tick;
        r[sh1][0] <= in[3:0];
        r[sh1][1] <= in[7:4];
        r[~sh1][sh1] <= in[11:8];
        r[~sh1][~sh1] <= in[15:12];
    endrule
endmodule