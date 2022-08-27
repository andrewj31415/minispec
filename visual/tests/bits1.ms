
function Bit#(2) f(Bit#(2) a);
    return { ~a[0], ~a[1] };
endfunction

function Bit#(2) g(Bit#(2) a);
    return { ~a[1], ~a[0] };
endfunction