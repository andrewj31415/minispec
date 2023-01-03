
function Bit#(6) f(Bit#(2) a, Bit#(1) c);
  Bit#(4) b = 4'b0110;
  return { b[2:0], b[3], b[a], a[c] };
endfunction