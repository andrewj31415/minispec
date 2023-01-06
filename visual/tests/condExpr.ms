
function Bit#(4) f(Bool a);
    Bit#(4) n = 100 == 99 ? 1 : 2; // 2
    Bit#(4) m = n == 2 ? 3 : 4; // 3
    return a ? n : m;
endfunction