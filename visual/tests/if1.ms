

function Bit#(4) f#(Integer n)(Bit#(4) a);
  Bit#(4) x;
  if (n == 0)
    x = 1 ^ a;
  else
    if (a == 4)
      x = a;
    else
      x = 2;
  return x;
endfunction