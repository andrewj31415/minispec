

function Bit#(8) f(Bit#(2) a, Bool b, Bool c, Bool d, Bit#(2) e);
    Bit#(2) x = case (a)
        0: 0;
        1: 2;
        2,3: 3;
        default: 1;
    endcase;
    Bit#(2) y = case (False)
        b: 0;
        True: 3;
        c: 1;
        False: 2;
        default: 0;
    endcase;
    Bit#(2) z = case (d)
        b: 0;
        c: 1;
        default: 2;
    endcase;
    Bit#(2) w = case (1'b1)
        1'b1: ~e;
        1'b0: e+1;
    endcase;
    return {x, y, z, w};
endfunction