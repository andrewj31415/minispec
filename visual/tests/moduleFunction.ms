

module Outer;
    Reg#(Bit#(4)) r(0);
    function Bit#(4) my_value;
        return r;
    endfunction
    method Bit#(4) getR1;
      return my_value;
    endmethod
    method Bit#(4) getR2;
      return my_value();
    endmethod
    input Bit#(4) set;
    rule step;
        r <= set;
    endrule
endmodule