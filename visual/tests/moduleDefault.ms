

module Inner;
    Reg#(Bit#(4)) storage(0);
    method Bit#(4) getStorage = storage;
    input Bool enable default = False;
    rule step;
        if (enable) storage <= storage + 1;
    endrule
endmodule

module Outer;
    Inner inner;
    method Bit#(4) getStorage;
      return inner.getStorage;
    endmethod
    input Bool enable;
    rule step;
        if (enable) inner.enable = True;
    endrule
endmodule