

/* Memory contains 4 4-bit values. */

module Mem;
    RegU#(Vector#(4, Bit#(4))) memory;
    input Bit#(4) data;
    input Bit#(2) indx;
    method Bit#(4) getData(Bit#(2) indx) = memory[indx];
    rule tick;
        Vector#(4, Bit#(4)) current = memory;
        current[indx] = data;
        memory <= current;
    endrule
endmodule

/* 1-cycle latency selection of two memory locations */

module TopLevel;
    Mem mem;
    RegU#(Bit#(4)) stage1;
    RegU#(Bit#(4)) stage2;
    input Bit#(2) selector1;
    input Bit#(2) selector2;
    input Bit#(4) dataTop;
    input Bit#(2) indxTop;
    method Bit#(4) out1 = stage1;
    method Bit#(4) out2 = stage2;
    rule tick;
        stage1 <= mem.getData(selector1);
        stage2 <= mem.getData(selector2);
        mem.data = dataTop;
        mem.indx = indxTop;
    endrule
endmodule