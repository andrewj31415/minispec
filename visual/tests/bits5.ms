
function Bit#(8) f(Bit#(2) a, Bit#(2) c);
  Bit#(4) b = 4'b0110;
  Bit#(4) x = b[3:a];
  Bit#(4) y = b[a:c];
  return { x, y };
endfunction