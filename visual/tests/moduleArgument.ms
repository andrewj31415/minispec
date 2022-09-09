
Integer n = 1;

module AddDepth#(Integer depth);
    AddDepth#(depth-1) submodule;
    input Bit#(n) setValue;
    method Bit#(n) getValue(Bit#(n) add);
        Bit#(n) x = submodule.getValue(depth) + add;
        return x;
    endmethod
    rule tick;
        submodule.setValue = setValue + submodule.getValue(depth);
    endrule
endmodule

module AddDepth#(0);
    Reg#(Bit#(n)) value(0);
    input Bit#(n) setValue;
    method Bit#(n) getValue(Bit#(n) add);
        Bit#(n) x = value + add;
        return x;
    endmethod
    rule tick;
        value <= setValue;
    endrule
endmodule