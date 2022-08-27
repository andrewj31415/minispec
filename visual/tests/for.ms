
function Bit#(n) parity#(Integer n)(Bit#(n) a);
    Bit#(1) output = 0;
    for (Integer i = 0; i < n; i = i + 1)
        output = output ^ a[i];
    return output;
endfunction