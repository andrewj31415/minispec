
typedef Bit#(32) Word;

Integer n = 4;

typedef struct {
    Word data;
    Bit#(2**n) index;
} Packet;

function Packet combine#(Word data1, Bit#(2**n) index1, Word data2, Bit#(2**n) index2)(Packet a, Packet b);
    Packet default1 = Packet{data:data1, index:index1};
    Packet default2 = Packet{data:data2, index:index2};
    Packet c;
    if (default1 == default2)
        c = default1;
    else begin
        c = Packet{data: a.data,
                   index: b.index};
        c.data = c.data | b.data;
    end
    return c;
endfunction