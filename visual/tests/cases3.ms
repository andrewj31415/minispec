

/* Dynamically evaluated case statement */

typedef enum {
    Add,
    Sub,
    Mul
} OpName;

function Bit#(n) f#(Integer n)(Bit#(n) a, Bit#(n) b, OpName op);
    Bit#(n) x = 0;
    case (op)
        Add: x = a+b;
        Add: x = a/b;  // should never be reached
        Sub: x = a-b;
        Mul: x = a*b;
    endcase
    return x;
endfunction