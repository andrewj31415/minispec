

/* More complicated parameters */

function Bit#(hello) f#(Integer hello, Integer lol)(Bit#(hello) a, Bit#(hello) b);
  return a + b;
endfunction

function Bit#(3*(2-1)+7) f#(3*(2-1)+7, Integer yo)(Bit#(3*(2-1)+7) a, Bit#(3*(2-1)+7) b);
  return a;
endfunction

Integer i = 3;

function Bit#(n) f#(Integer n, Integer i+j)(Bit#(n) a, Bit#(n) b);
  return b;
endfunction

Integer j = 4;