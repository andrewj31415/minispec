
typedef Bit#(32) Word;

Integer n = 4;

typedef struct {
    Word input;
    Bit#(2**n) index;
} Packet;

function Packet combine#(Packet default1, Packet default2)(Packet a, Packet b);
    Packet c;
    if (default1 == default2)
        c = default1;
    else begin
        c = Packet{input: a.input | b.input,
                   index: b.index};
    end
    return c
endfunction;