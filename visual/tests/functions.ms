
function Bit#(1) f(Bit#(1) a, Bit#(1) b);
    let x = a ^ b;
    return x;
endfunction

function Bit#(1) g(Bit#(1) a, Bit#(1) b, Bit#(1) c);
    let x = f(a ^ b, c);
    return x;
endfunction