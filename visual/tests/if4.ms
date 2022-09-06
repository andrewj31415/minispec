
function Maybe#(Bit#(32)) computeHalf( Bit#(32) in );
    let x;
    if (in[0] == 1) x = Invalid;
    else begin
        Bit#(32) shifted = 0;
        for (Integer i = 0; i < 31; i = i + 1) begin
            shifted[i] = in[i+1];
        end
        x = Valid(shifted);
    end
    return x;
endfunction