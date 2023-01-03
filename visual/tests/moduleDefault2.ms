

module Inner;
    input Bool enable default = False;
    rule tick;
    endrule
endmodule

module Outer;
    Inner inner;
    rule tick;
    endrule
endmodule