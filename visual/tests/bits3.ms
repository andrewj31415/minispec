
function Vector#(4, Bit(4)) f( Vector#(4, Bit#(4)) a, Bit#(2) i, Bit#(2) j, Bit#(2) k );
  a[1][i:j][k] = ~a[k][j:2][0];
  a[2][3:1] = 6;
  return a;
endfunction