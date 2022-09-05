
function Bit#(4) f(Bit#(4) a, Bool flip);
    case (flip)
        True: a = ~a;
    endcase
    return a;
endfunction

function Bit#(4) g(Bit#(4) a, Bool flip);
    case (flip)
        True: a = ~a;
        False: a = a;
    endcase
    return a;
endfunction

function Bit#(4) h(Bit#(4) a, Bool flip);
    case (flip)
        True: a = ~a;
        default: a = a;
    endcase
    return a;
endfunction