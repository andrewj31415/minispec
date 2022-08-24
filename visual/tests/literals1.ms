

Integer factor = 5;

function Bool f(Bit#(4) a);
  return ((a * 5) ^ g#(3 * factor)(a)) == 7;
endfunction

function Bit#(4) g#(Integer n)(Bit#(4) a);
  return otherFactor + n + a*6;
endfunction

Integer otherFactor = -2;