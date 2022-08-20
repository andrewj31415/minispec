

function Bit#(n) f#(Integer n, Integer m)(Bit#(n) a, Bit#(n) b);
  return a + b;
endfunction

/* Overrides f's f#(1, m) */
function Bit#(2) f#(1, Integer m)(Bit#(2) a, Bit#(2) b);
  return a;
endfunction

/* Is its own function, distinct from f#(n, m). */
function Bit#(1) f(Bit#(1) a, Bit#(1) b);
  return a;
endfunction

function Bit#(m) g#(Integer n, Integer m)(Bit#(m) a);
  return a;
endfunction

function Bit#(3) h#(Integer n)(Bit#(3) a);
  return g#(n, 3)(a);
endfunction

function Bit#(3) e(Bit#(3) a);
  return h#(5)(a);
endfunction