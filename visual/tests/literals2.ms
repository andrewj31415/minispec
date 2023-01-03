

// to see what bsc does with each function,
//  synth literals2.ms t1
// will produce a single not gate when !a is returned and no output when False is returned.

function Bool t0(Bool a);
    Bit#(4) v = 4'd10;  // 10
    if (v == 10)
        return !a;
    else
        return False;
endfunction

function Bool t1(Bool a);
    Bit#(4) v = 4'b10 * 4'hF;  // 14
    if (v == 4'b1110)
        return !a;
    else
        return False;
endfunction

function Bool t2(Bool a);
    Bit#(4) v = 4'b1 - 6 + 4'd1;  // -4
    if (v == -4'b100 && v == 4'b1100)
        return !a;
    else
        return False;
endfunction