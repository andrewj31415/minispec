
typedef struct {
    Type car;
    SecondType cdr;    
} Cons#(type Type, type SecondType);

typedef Cons#(Type, List#(k-1, Type)) List#(Integer k, type Type);

typedef Type List#(1, type Type);

/* Gets a list of length k and type Type from the corresponding vector */
function List#(k, Type) getList#(Integer k, type Type)(Vector#(k, Type) v);
    Vector#(k-1, Type) rest;
    for (Integer i = 1; i < k; i = i + 1) begin
        rest[i-1] = v[i];
    end
    return Cons#(Type, List#(k-1, Type)){ car: v[0], cdr: getList#(k-1, Type)(rest) };
endfunction

function List#(1, Type) getList#(1, type Type)(Vector#(1, Type) v);
    return v[0];
endfunction

/* Adds a list of length k n-bit values */
function Bit#(n) sumBitList#(Integer k, Integer n)(List#(k, Bit#(n)) v);
    return v.car + sumBitList#(k-1, n)(v.cdr);
endfunction

function Bit#(n) sumBitList#(1, Integer n)(List#(1, Bit#(n)) v);
    return v;
endfunction

function Bit#(n) sumVector#(Integer k, Integer n)(Vector#(k, Bit#(n)) v);
    List#(k, Bit#(n)) l = getList#(k, Bit#(n))(v);
    return sumBitList#(k, n)(l);
endfunction