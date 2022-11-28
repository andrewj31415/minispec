
/* Multiple methods with arguments of submodules */

module Inner;
    Reg#(Bit#(2)) storage(0);
    input Bit#(2) next;
    method Bit#(2) getUp(Bit#(2) a) = storage + a;
    rule tick;
        storage <= next;
    endrule
endmodule

module Outer;
    Inner s1;
    Inner s2;
    input Bit#(2) next1;
    input Bit#(2) next2;
    method Bit#(2) out1 = s1.getUp(1);
    method Bit#(2) out2 = s2.getUp(1);
    rule tick;
        s1.next = next1;
        s2.next = next2;
    endrule
endmodule