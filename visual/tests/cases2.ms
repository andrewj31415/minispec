
/* This function (f) shows that cases are evaluated by:
 *  1. Calculate the case choice expression
 *  2. Move down the list of cases. If we get a match, do that one branch and stop.
 *  3. Default matches anything. 
 */

function Bit#(8) f(Bool a, Bool b, Bool c, Bool d);
    Bit#(4) x = 0;
    Bit#(4) y = 0;
    case (True)
        a: x = 1;
        b: x = 2;
        c: x = 4;
        d: x = 8;
        default: y = 1;
    endcase
    return {x, y};
endfunction