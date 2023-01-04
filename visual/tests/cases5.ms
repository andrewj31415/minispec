
function Bit#(2) f(Bool a, Bool b);
    Bit#(2) x = 0;
    case (False)
        a: x = 1;
        b: x = 2;
        False: x = 3;
    endcase
    return x;
endfunction

function Bit#(2) g(Bool a, Bool b);
    Bit#(2) x = 0;
    case (a)
        b: x = 1;
        False: x = 2;
    endcase
    return x;
endfunction