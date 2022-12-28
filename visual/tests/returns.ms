
function Bit#(1) password(Bit#(4) x);
    if (x == 5) return 1;
    else return 0;
endfunction