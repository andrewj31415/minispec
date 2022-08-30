
function Bit#(2) f(Bit#(4) a);
    Bit#(2) x,y;
    {x, y} = a;
    return x+y;
endfunction