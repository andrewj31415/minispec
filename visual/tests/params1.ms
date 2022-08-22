
/* Various override testing */

function Bit#(n) f#(Integer n, Integer m)(Bit#(n) a, Bit#(n) b);
  return a + b;
endfunction

/* Should not override f */
function Bit#(n) f#(Integer n)(Bit#(n) a, Bit#(n) b);
  return a;
endfunction

/* Should override f */
function Bit#(n) f#(Integer n, 1)(Bit#(n) a, Bit#(n) b);
  return b;
endfunction

/* Should override f */
function Bit#(1) f#(1, 1)(Bit#(1) a, Bit#(1) b);
  return f(b, a); /* Should use the last f */
endfunction

/* Should not override f */
function Bit#(1) f(Bit#(1) a, Bit#(1) b);
  return a;
endfunction