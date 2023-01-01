

function Bit#(2) f#(2, 2)(Bit#(2) a, Bit#(2) b);
  return a * b;
endfunction

function Bit#(1) f#(1, Integer m)(Bit#(1) a, Bit#(1) b);
  return a + b;
endfunction

function Bit#(n) f#(Integer n, 1)(Bit#(n) a, Bit#(n) b);
  return a - b;
endfunction

function Bit#(n) f#(Integer n, Integer m)(Bit#(n) a, Bit#(n) b);
  return 1;
endfunction
