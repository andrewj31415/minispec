

module Buffer#(type SomeType);
    RegU#(Maybe#(SomeType)) r;
    input Maybe#(SomeType) in;
    method Maybe#(SomeType) out = r;
    rule tick;
        if (isValid(in))
            r <= in;
        else
            r <= Invalid;
    endrule
endmodule