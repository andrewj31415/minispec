
function Maybe#(Bit#(k)) computeHalf#(Integer k)( Bit#(k) in );
    let x;
    if (in[0] == 1) x = Invalid;
    else begin
        Bit#(k) shifted = 0;
        for (Integer i = 0; i < k-1; i = i + 1) begin
            shifted[i] = in[i+1];
        end
        x = Valid(shifted);
    end
    return x;
endfunction