

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
