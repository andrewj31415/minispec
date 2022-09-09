

function Bit#(2) f1(Bit#(2) a, Bool b, Bool c, Bool d, Bit#(2) e);
    Bit#(2) x = case (a)
        0: 0;
        1: 2;
        2,3: 3;
        default: 1;
    endcase;
    return x;
endfunction

/* TODO synth on f2 seems to generate no hardware? But f2 is a nontrivial function ... */

function Bit#(2) f2(Bit#(2) a, Bool b, Bool c, Bool d, Bit#(2) e);
    Bit#(2) y = case (False)
        b: 0;
        True: 3;
        c: 1;
        False: 2;
        default: 0;
    endcase;
    return y;
endfunction

/* simpler version of f22 that should cause an error */

function Bit#(2) f22(Bit#(2) b);
    return case (b)
        0: 1;
        1: 0;
    endcase;
endfunction

function Bit#(2) f3(Bit#(2) a, Bool b, Bool c, Bool d, Bit#(2) e);
    Bit#(2) z = case (d)
        b: 0;
        c: 1;
        default: 2;
    endcase;
    return z;
endfunction

function Bit#(2) f4(Bit#(2) a, Bool b, Bool c, Bool d, Bit#(2) e);
    Bit#(2) w = case (1'b1)
        1'b1: ~e;
        1'b0: e+1;
    endcase;
    return w;
endfunction