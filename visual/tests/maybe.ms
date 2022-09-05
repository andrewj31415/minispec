
module SettableCounter;
    Reg#(Bit#(8)) counter(0);
    input Maybe#(Bit#(8)) setCount default = Invalid;
    method Bit#(8) getCount = counter;
    rule tick;
        if (isValid(setCount)) counter <= fromMaybe(?, setCount);
        else counter <= counter + 1;
    endrule
endmodule