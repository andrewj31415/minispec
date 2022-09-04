// Don't change signature of existing functions. You may write additional helper functions if you want.


function Bit#(32) barrelRightInteger#(Integer n)(Bit#(32) in, Bit#(1) sft_in);
    Bit #(32) ret = in;
    for (Integer i = 0; i < 32-n; i = i+1)   //compute the shift
        ret[i] = in[i+n];
    for (Integer i = 32-n; i < 32; i = i+1)  //fill in the upper bits
        ret[i] = sft_in;
    return ret;
endfunction

// Description: 32-bit right barrel shifter
// Arguments: in (value to be shifted); sftSz (shift size); sft_in (the bit shifted in)
// Return: {sft_in's, in[31:sftSz]}
function Bit#(32) barrelRShift(Bit#(32) in, Bit#(5) sftSz, Bit#(1) sft_in);
    Bit #(32) ret = 0;
    //////////////////
    // YOUR CODE HERE
    /////////////////
    ret = in;
    for (Integer i = 0; i<5; i = i+1)   //select the appropriate power-of-two-shifts to perform
        ret = case (sftSz[i])
            0: ret;
            1: barrelRightInteger#(2**i)(ret, sft_in);
        endcase;
    return ret;
endfunction

// Description: 32-bit arithmetic/logic right shifter
// Arguments: in (value to be shifted); sftSz (shift size); arith (1 = arithmetic, 0 = logic)
// Return: in >> sftSz
function Bit#(32) sr32(Bit#(32) in, Bit#(5) sftSz, Bit#(1) arith);
    Bit #(32) ret = 0;
    //////////////////
    // YOUR CODE HERE
    /////////////////
    Bit#(1) toShiftIn = case (arith)  //if we are doing an arithmetic shift, we duplicate the leading bit
        0: 0;
        1: in[31];
    endcase;
    ret = barrelRShift(in, sftSz, toShiftIn);
    return ret;
endfunction


// Description: 32-bit logic left shifter
// Arguments: in (values to be shifted); sftSz (shift size)
// Return: a << b
function Bit#(32) sll32(Bit#(32) in, Bit#(5) sftSz);
    Bit #(32) ret = 0;
    //////////////////
    // YOUR CODE HERE
    /////////////////
    ret = reverseBits(in);
    ret = sr32(ret, sftSz, 0);
    ret = reverseBits(ret);
    return ret;
endfunction


// Description: 32-bit FULL shifter
// Arguments: in (value to be shifted); sftSz (shift size);
// ShiftTypes:
// LogicalRightShift
// ArithmeticRightShift
// LeftShift
//
// Return: in >> sftSz when right shift; in << sftSz otherwise
typedef enum {LogicalRightShift, ArithmeticRightShift, LeftShift} ShiftType;

function Bit#(32) sft32(Bit#(32) in, Bit#(5) sftSz, ShiftType shiftType);
    Bit#(32) ret = 0;
    //////////////////
    // YOUR CODE HERE
    /////////////////
    ret = in;
    Bit#(1) arith = case(shiftType)  //decide if we need to do an arithmetic shift or not
        LogicalRightShift: 0;
        ArithmeticRightShift: 1;
        LeftShift: 0;
    endcase;
    case(shiftType)
        LeftShift: ret = reverseBits(ret);
    endcase
    ret = sr32(ret, sftSz, arith);  //we reverse the bits before and after if we are doing a left shift
    case(shiftType)
        LeftShift: ret = reverseBits(ret);
    endcase
    return ret;
endfunction



// Description: one-bit less-than comparator
// Arguments: a, b (1-bit values), eq, lt (eq and lt from previous comparator)
// Return: {eq_i, lt_i}
function Bit#(2) cmp(Bit#(1) a, Bit#(1) b, Bit#(1) eq, Bit#(1) lt);
    Bit#(2) ret = 0;
    //////////////////
    // YOUR CODE HERE
    /////////////////
    //set the outputs to 0 and switch them to 1 as needed
    Bit#(1) outeq = 0;
    Bit#(1) outlt = 0;
    case ({a, b, eq})  //only true if eq is true and a,b match
        3'b001: outeq = 1;
        3'b111: outeq = 1;
    endcase
    outlt = lt;
    case ({a, b, eq})  //true if lt holds or if eq holds and a<b
        3'b011: outlt = 1;
    endcase
    ret = {outeq, outlt};
    return ret;
endfunction

// Description: unsigned 32-bit less-than comparator
// Arguments: a, b unsigned 32-bit values
// Return: 1 if a < b
function Bit#(1) ltu32(Bit#(32) a, Bit#(32) b);
    Bit#(1) ret = 0;
    //////////////////
    // YOUR CODE HERE
    /////////////////
    Bit #(2) eqlt = 2'b01;
    for (Integer i = 31; i >= 0; i = i-1)  //exactly as described in the lab instructions
        eqlt = reverseBits(cmp(a[i],b[i], eqlt[0], eqlt[1]));
    ret = eqlt[1];  //pick out if a<b
    return ret;
endfunction

// Description: Signed/Unsigned 32-bit less-than comparator
// Arguments: a b (32-bit values); isSigned (signed comparator when 1, unsigned otherwise)
// Return: 1 if a < b
function Bit#(1) lt32(Bit#(32) a, Bit#(32) b, Bit#(1) isSigned);
    Bit#(1) ret = 0;
    //////////////////
    // YOUR CODE HERE
    /////////////////
    ret = ltu32(a, b);
    case ({a[31], b[31], isSigned})
        3'b101: ret = 1;  //if b is positive and a is negative, return true
        3'b011: ret = 0;  //if the other way around, false
    endcase
    return ret;
endfunction

// Description: one-bit full adder
// Arguments: a, b, carry in
// Return: {carry out, sum}
function Bit#(2) fullAdder(Bit#(1) a, Bit#(1) b, Bit#(1) carryIn);
    Bit#(2) ret = 0;
    //////////////////
    // YOUR CODE HERE
    /////////////////
    ret[0] = a^b^carryIn;
    ret[1] = a&b | b&carryIn | carryIn&a;
    return ret;
endfunction

// Description: n-bit ripple-carry adder with a carry-in
// Arguments: a, b, carryIn
// Return: sum of a, b, and carryIn
function Bit#(n) rca#(Integer n)(Bit#(n) a, Bit#(n) b, Bit#(1) carryIn);
    Bit#(n) ret = 0;
    //////////////////
    // YOUR CODE HERE
    /////////////////
    for (Integer i = 0; i < n; i=i+1)  //apply chained adders exactly as usual
        begin
            Bit#(2) vals = fullAdder(a[i], b[i], carryIn);
            ret[i] = vals[0];
            carryIn = vals[1];
        end
    return ret;
endfunction

// Description: n-bit ripple-carry adder/subractor
// Arguments: a, b (n-bit operands); isSub (1 => subtract, 0 => add)
// Return: isSub == 0 ? a + b : a - b
function Bit#(n) addSub#(Integer n)(Bit#(n) a, Bit#(n) b, Bit#(1) isSub);
    Bit#(n) ret = 0;
    //////////////////
    // YOUR CODE HERE
    /////////////////
    Bit#(1) carry = 1;
    case (isSub)
        1: b = ~b; //flip bits of b
    endcase
    
    ret = rca#(n)(a, b, isSub); //putting in isSub for the initial carry makes sure we add 1 to b if we are subtracting
    return ret;
endfunction


// Alu Functions:
// Add: 32-bit Addition         (a + b)
// Sub: 32-bit Subtraction      (a - b)
// And: 32-bit Bitwise And      (a & b)
// Or: 32-bit Bitwise Or        (a | b)
// Xor: 32-bit Bitwise Xor      (a ^ b)
// Slt: Set less than           (a <u b ? 1 : 0)
// Sltu: Set less than unsigned (a <s b ? 1:0)
// Sll: Left logic shfit        (a << b)
// Srl: Right logic shift       (a >>u b)
// Sra: Right arithmetic shift  (a >>s b)
typedef enum {Add, Sub, And, Or, Xor, Slt, Sltu, Sll, Srl, Sra} AluFunc;

// Description: Arithmetic Logic Unit (ALU)
// Arguments: a, operand a; b, operand b; func, ALU operation
// Return: output of ALU
function Bit#(32) alu(Bit#(32) a, Bit#(32) b, AluFunc func);
    Bit #(32) ret = 0;
    //////////////////
    // YOUR CODE HERE
    /////////////////
    Bit#(1) addType = 0;  //type of add to perform, default (0) is addition
    Bit#(1) compType = 0;  //type of compare, default (0) is unsigned
    ShiftType shiftType = LeftShift;  //type of shift
    case (func)
        Sub: addType = 1;
        Slt: compType = 1;
        Srl: shiftType = LogicalRightShift;
        Sra: shiftType = ArithmeticRightShift;
    endcase
    Bit #(32) sum = addSub#(32)(a, b, addType);
    Bit #(32) comp = zeroExtend(lt32(a, b, compType));
    Bit #(32) shift = sft32(a, b[4:0], shiftType);
    case(func)
        Add: ret = sum;
        Sub: ret = sum;
        And: ret = a&b;
        Or: ret = a|b;
        Xor: ret = a^b;
        Slt: ret = comp;
        Sltu: ret = comp;
        Sll: ret = shift;
        Srl: ret = shift;
        Sra: ret = shift;
    endcase
    return ret;
endfunction


// Description: Alternative shifter implementation (Discussion Question)
function Bit#(32) sft32_alt(Bit#(32) in, Bit#(5) sftSz, ShiftType shiftType);
    return (shiftType == LeftShift) ? sft32(in, sftSz, LeftShift) : ((shiftType == ArithmeticRightShift)? sft32(in, sftSz, ArithmeticRightShift) : sft32(in, sftSz, LogicalRightShift));
endfunction



//chain adders together
function Bit#(n+1) chain#(Integer n)(Bit#(n) a, Bit#(n) b, Bit#(1) carryIn);
    Bit#(n) ret = 0;
    //////////////////
    // YOUR CODE HERE
    /////////////////
    for (Integer i = 0; i < n; i=i+1)  //apply chained adders exactly as usual
        begin
            Bit#(2) vals = fullAdder(a[i], b[i], carryIn);
            ret[i] = vals[0];
            carryIn = vals[1];
        end
    return {carryIn, ret};
endfunction

typedef enum {G, P, K} Func;  //generate, propogate, kill

//returns h=fg, that is, h(x)=f(g(x))
function Func comp(Func f, Func g);
  Func h = case(f)
    K: K;
    G: G;
    P: g;
  endcase;
  return h;
endfunction

//evaluate a function on an input
function Bit#(1) eval(Func f, Bit#(1) val);
  Bit#(1) out = case(f)
    K: 0;
    G: 1;
    P: val;
  endcase;
  return out;
endfunction

// Description: N-bit fast adder with a carry-in (Design Exercise)
// Arguments: a, b, carryIn
// Return: sum of a, b, and carryIn
function Bit#(n) fastAdd#(Integer n)(Bit#(n) a, Bit#(n) b, Bit#(1) carryIn);
    Bit#(n) ret = 0;
    //////////////////
    // YOUR CODE HERE
    /////////////////

Vector#(n, Func) fff;
for (Integer i=0; i<n; i=i+1)
  fff[i] = case ({a[i], b[i]})
    2'b00: K;
    2'b01: P;
    2'b10: P;
    2'b11: G;
  endcase;

for (Integer i = 0; 2**i<n; i=i+1)
  begin
  for (Integer j = n-1; j >= 0; j=j-1)
  begin
    if (2**i <= j)  fff[j] = comp(fff[j], fff[j-2**i]);
  end
  end


Bit#(n) c = zeroExtend(carryIn);

for(Integer i = 0; i+1<n; i=i+1)
  c[i+1] = eval(fff[i], carryIn);

   ret=a^b^c;

    return ret;
endfunction





function Bit#(1) f(Bit#(1) a);
    return ~a;
endfunction

function Bit#(1) g(Bit#(1) a);
    let x = f(f(f(a)));
    return x;
endfunction