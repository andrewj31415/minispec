
function Bit#(1) and1(Bit#(1) a, Bit#(1) b);
    return a & b;
endfunction

function Bit#(1) or1(Bit#(1) a, Bit#(1) b);
    return a | b;
endfunction

function Bit#(1) xor1( Bit#(1) a, Bit#(1) b );
    return a ^ b;
endfunction

function Bit#(1) not1(Bit#(1) a);
    return ~ a;
endfunction

function Bit#(1) multiplexer1(Bit#(1) sel, Bit#(1) a, Bit#(1) b);
    return (sel==0)? a: b;
endfunction


// bit_scan_reverse
// TODO: how many of each kind of gates did you use?
// # and1 = 1
// # or1 = 2
// # xor1 = 0
// # not1 = 1
// # multiplexer1 = 0

function Bit#(2) bit_scan_reverse(Bit#(4) a);
    Bit#(2) ret = 0;
    // your code here
    ret[1] = or1(a[3],  a[2]); //if the first nonzero bit occurs past 2
    ret[0] = or1(a[3], and1(a[1], not1(a[2])));
    return ret;
endfunction


// is_power_of_2
// TODO: how many of each kind of gates did you use?
// # and1 = 4
// # or1 = 1
// # xor1 = 2
// # not1 = 4
// # multiplexer1 = 0

function Bit#(1) is_power_of_2(Bit#(4) a);
    Bit#(1) ret = 0; // not a not b xor c,d  or not c not d xor a,b
    ret = or1( and1(and1( not1(a[0]),not1(a[1])), xor1(a[2],a[3])), and1(and1( not1(a[2]),not1(a[3])), xor1(a[0],a[1])) );
    return ret;
endfunction


// log_of_power_of_2
// TODO: how many of each kind of gates did you use?
// # and1 = 7
// # or1 = 3
// # xor1 = 2
// # not1 = 5
// # multiplexer1 = 0

function Bit#(2) log_of_power_of_2(Bit#(4) a);
    Bit#(2) ret = 0;
    // your code here
    Bit#(2) sweep = bit_scan_reverse(a);
    Bit#(1) switch = is_power_of_2(a);
    ret[0] = and1(switch, sweep[0]);
    ret[1] = and1(switch, sweep[1]);
    return ret;
endfunction


function Bit#(1) equal(Bit#(8) a, Bit#(8) b);
    Bit#(1) ret = 0;
    // your code here
    Bit#(1) uu = not1(or1(xor1(a[0],b[0]), xor1(a[1], b[1])));
    Bit#(1) ul = not1(or1(xor1(a[2],b[2]), xor1(a[3], b[3])));
    Bit#(1) lu = not1(or1(xor1(a[4],b[4]), xor1(a[5], b[5])));
    Bit#(1) ll = not1(or1(xor1(a[6],b[6]), xor1(a[7], b[7])));
    ret = and1( and1(uu, ul), and1(lu, ll) );
    return ret;
endfunction


function Bit#(4) vector_equal(Bit#(32) a, Bit#(32) b);
    Bit#(4) ret = 0;
    // your code here
    ret[3] = equal(a[31:24],b[31:24]);
    ret[2] = equal(a[23:16],b[23:16]);
    ret[1] = equal(a[15:8],b[15:8]);
    ret[0] = equal(a[7:0],b[7:0]);
    return ret;
endfunction


function Bit#(7) seven_segment_decoder(Bit#(4) input_binary_number);
    Bit#(7) ret = case(input_binary_number)   //write each case separately--minispec does the rest.
      4'b0000 : 7'b1111110;
      4'b0001 : 7'b0110000; 
      4'b0010 : 7'b1101101;
      4'b0011 : 7'b1111001;
      4'b0100 : 7'b0110011;
      4'b0101 : 7'b1011011;
      4'b0110 : 7'b1011111;
      4'b0111 : 7'b1110000;
      4'b1000 : 7'b1111111;
      4'b1001 : 7'b1111011;
      default : 7'b1001111; // value for "E"
    endcase;
    return ret;
endfunction

function Bit#(1) adds(Bit#(1) a, Bit#(1) b, Bit#(1) cin);
  Bit#(1) s = xor1(a, xor1(b,cin));
  return s;
endfunction

function Bit#(1) addc(Bit#(1) a, Bit#(1) b, Bit#(1) cin);
  Bit#(1) cout = or1( or1( and1(a,b), and1(b,cin) ), and1(cin,a) );
  return cout;
endfunction

function Bit#(3) population_count(Bit#(4) in);
    Bit#(3) ret = 0;
    ret[2] = and1( and1(in[0],in[1]), and1(in[2],in[3]) );
    //put in[0]+in[1] into ret
    ret[1] = addc(in[0], in[1], 0);
    ret[0] = adds(in[0], in[1], 0);
    //put ret+in[2] into ret
    ret[1] = adds(ret[1], 0, addc(ret[0], in[2], 0));
    ret[0] = adds(ret[0], in[2], 0);
    //put ret+in[3] into ret
    ret[1] = adds(ret[1], 0, addc(ret[0], in[3], 0));
    ret[0] = adds(ret[0], in[3], 0);
    return ret;
endfunction

function Bit#(1) geq(Bit#(1) a, Bit#(1) b);
    return or1(a, not1(b));
endfunction
function Bit#(1) eq(Bit#(1) a, Bit#(1) b);
    return not1(xor1(a,b));
endfunction
function Bit#(1) gt(Bit#(1) a, Bit#(1) b);
    return and1(a, not1(b));
endfunction
function Bit#(1) is_geq(Bit#(4) a, Bit#(4) b);
    Bit#(1) ret = 0;
    // your code here
    ret = gt(a[3],b[3]);
    ret = or1(ret, and1( eq(a[3],b[3]), gt(a[2],b[2]) ));
    ret = or1(ret, and1(and1( eq(a[3],b[3]), eq(a[2],b[2])), gt(a[1],b[1]) ));
    ret = or1(ret, and1(and1(and1( eq(a[3],b[3]), eq(a[2],b[2])), eq(a[1],b[1])), geq(a[0],b[0]) ));
    return ret;
endfunction

// Demo code below here. Do not modify
function Bit#(1) parity4(Bit#(4) n);
    return xor1(xor1(xor1(n[0], n[1]), n[2]), n[3]);
endfunction

function Bit#(1) doubleInverter(Bit#(1) n);
  return ~(~n);
endfunction

/*function Bit#(1) doubleInverter(Bit#(1) n);
  return n;
endfunction*/

function Bit#(1) combine(Bit#(1) a, Bit#(1) b, Bit#(1) c);
  Bit#(1) cout = and1( or1(b, a), xor1(c, b) );
  return cout;
endfunction
