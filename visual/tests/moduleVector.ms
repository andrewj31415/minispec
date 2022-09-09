

Integer n = 2;

/* recursively reverses a bitstring of length 4**k while inverting each bit. */
module Reverse#(Integer k);
    Vector#(2, Vector#(2, Reverse#(k-1))) inner;
    input Bit#(4**k) in;
    method Bit#(4**k) out = {inner[1][1].out, inner[1][0].out, inner[0][1].out, inner[0][0].out};
    rule tick;
        for (Integer i = 0; i <= 1; i = i+1)
            for (Integer j = 0; j <= 1; j = j+1)
                inner[i][j].in = in[(2*i+j)*4**(k-1) + 4**(k-1) - 1 : (2*i+j)*(4**(k-1))];
    endrule
endmodule

module Reverse#(1);
    Vector#(2, Vector#(2, RegU#(Bit#(1)))) inner;
    input Bit#(4) in;
    method Bit#(4) out = {inner[1][1], inner[1][0], inner[0][1], inner[0][0]};
    rule tick;
        for (Integer i = 0; i <= 1; i = i+1)
            for (Integer j = 0; j <= 1; j = j+1)
                inner[i][j] <= ~in[2*i+j];
    endrule
endmodule