
/* This file was used to explore some of the quirks (overlapping statements, etc) of the minispec case statement. */

function Bit#(8) f(Bit#(4) a, Bit#(4) b);
    Bit#(4) x = 0;
    Bit#(4) y = 0;
    case (a)
        b: begin x = 15; y = 1; end
        b: x = 1;
        default: y = 0;
    endcase
    return {x, y};
endfunction