

function Bit#(n) constant#(Integer n)();
    return log2(n);
endfunction

module Buffer;
    Reg#(Bit#(4)) r(0);
    input Bit#(4) in;
    method Bit#(4) out = r;
    rule tick;
        let f = "Got value 0x%x";
        $display(f, in);
        if (in == 0) $finish;
        r <= in;
    endrule
endmodule