
function Vector#(3, Bit#(2)) f(Vector#(3, Bit#(2)) a);
  a[2][1] = ~a[2][0];
  let temp = a[1];
  a[1] = a[0];
  a[0] = temp;
  return a;
endfunction