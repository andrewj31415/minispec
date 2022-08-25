
function Bit#(2) f(Bool a);
    Bit#(2) x, y;
    Bit#(2) z;
    if (a) begin
        x = 1;
        y = 0;
        z = x + y;
    end else begin
        x = 2;
        y = 1;
        z = x + y;
    end
    return z;
endfunction