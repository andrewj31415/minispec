

/* fully pre-evaluated case statement */

/* adds the nth fibonacci number to a, with a bit-width of m. */

function Bit#(m) addFib#(Integer n, Integer m)(Bit#(m) a);
    Bit#(m) x;
    case (n)
        0: x = a;
        1: x = a+1;
        default: x = addFib#(n-1, m)(a) + addFib#(n-2, m)(0);
    endcase
    return x;
endfunction