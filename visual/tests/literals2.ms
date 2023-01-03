

// to see what bsc does with each function,
//  synth literals2.ms t1
// will produce a single not gate when !a is returned and no output when False is returned.

function Bool t1(Bool a);
    Bit#(4) v = 4'd10;  // 10
    if (v == 10)
        return !a;
    else
        return False;
endfunction

function Bool t2(Bool a);
    Bit#(4) v = 4'b10 * 4'hF;  // 14
    if (v == 4'b1110)
        return !a;
    else
        return False;
endfunction

function Bool t3(Bool a);
    Bit#(4) v = 4'b1 - 6 + 4'd1;  // -4
    if (v == -4'b100 && v == 4'b1100)
        return !a;
    else
        return False;
endfunction


function Bool t4(Bool a);
    Integer v = -1;
    Bit#(4) w = 4'b0 - 1;
    Bit#(4) x = 4'b0 + v;
    Bit#(4) y = v + 4'b0;
    if (v < 0 && w > 0 && x > 0 && y > 0)
        return !a;
    else
        return False;
endfunction

function Bool t5(Bool a);
    Bit#(8) v = ~8'b10010011;  // 0
    Bool w = False && False; // False
    if (!((v != 8'b01101100) || w))
        return !a;
    else
        return False;
endfunction