

module Outer;
    MysteryBluespec inner;
    input Bit#(4) i;
    method Bit#(4) o1 = inner.someMethod1;
    method Bit#(4) o2() = inner.someMethod2();
    method Bit#(4) o3(Bit#(4) a) = inner.someMethod3(a);
    method Bit#(4) o4 = inner.someMethod4(6);
    rule tick;
        inner.someInput1 = i;
        inner.someInput2 = 5;
    endrule
endmodule

module OuterMost;
    Outer outer;
    method Bit#(4) o1 = outer.o1();
    method Bit#(4) o2 = outer.o2();
    method Bit#(4) o3 = outer.o3(9);
    method Bit#(4) o4 = outer.o4;
    rule tick;
        outer.i = 1;
    endrule
endmodule
