

module FourBitCounter;
    Reg#(Bit#(4)) count(0);
    method Bit#(4) getCount = count;
    input Bool enable;
    rule increment;
        if (enable)
            count <= count + 1;
    endrule
endmodule


module EightBitCounter;
    FourBitCounter lower;
    FourBitCounter upper;
    method Bit#(8) getCount;
        return {upper.getCount, lower.getCount};
    endmethod
    input Bool enable;
    rule increment;
        lower.enable = enable;
        upper.enable = enable && (lower.getCount == 15);
    endrule
endmodule

module Counter#(Integer n);
    Counter#(n-1) lower;
    Counter#(n-1) upper;
    method Bit#(2**n) getCount;
        return {upper.getCount, lower.getCount};
    endmethod
    input Bool enable;
    rule increment;
        lower.enable = enable;
        upper.enable = enable && (lower.getCount == (2**n)-1);
    endrule
endmodule

module Counter#(0);
    Reg#(Bit#(1)) count(0);
    method Bit#(1) getCount = count;
    input Bool enable;
    rule increment;
        if (enable)
            count <= count + 1;
    endrule
endmodule
