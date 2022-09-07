


typedef Vector#(k, Type) OtherVector#(type Type, Integer k);

function Type getEntry#(type Type, Integer n, Integer index)(OtherVector#(Type, n) v);
    return v[index];
endfunction

function Bool f(SpecificVector v);
  return getEntry#(Bool, 2, 1)(v);
endfunction

typedef OtherVector#(Bool, 2) SpecificVector;