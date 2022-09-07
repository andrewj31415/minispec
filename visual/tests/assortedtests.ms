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



import ALU;
typedef Bit#(32) Word;

// ALU function enumeration is provided by imported ALU.ms

// Branch function enumeration
typedef enum {Eq, Neq, Lt, Ltu, Ge, Geu, Dbr} BrFunc;

// AUIPC added for this lab - Add Upper Immediate to PC
typedef enum {OP, OPIMM, BRANCH, LUI, JAL, JALR, LOAD, STORE, AUIPC, Unsupported} IType;

// Return type for Decode function
typedef struct {
    IType iType;
    AluFunc aluFunc;
    BrFunc brFunc;
    Maybe#(RIndx) dst;
    RIndx src1;
    RIndx src2;
    Word imm;
} DecodedInst;

// Register File
typedef Bit#(5) RIndx;

typedef struct {
    RIndx index;
    Word data;
} RegWriteArgs;

// Opcode
Bit#(7) opOpImm  = 7'b0010011;
Bit#(7) opOp     = 7'b0110011;
Bit#(7) opLui    = 7'b0110111;
Bit#(7) opJal    = 7'b1101111;
Bit#(7) opJalr   = 7'b1100111;
Bit#(7) opBranch = 7'b1100011;
Bit#(7) opLoad   = 7'b0000011;
Bit#(7) opStore  = 7'b0100011;
Bit#(7) opAuipc  = 7'b0010111;

// funct3 - ALU
Bit#(3) fnADD   = 3'b000;
Bit#(3) fnSLL   = 3'b001;
Bit#(3) fnSLT   = 3'b010;
Bit#(3) fnSLTU  = 3'b011;
Bit#(3) fnXOR   = 3'b100;
Bit#(3) fnSR    = 3'b101;
Bit#(3) fnOR    = 3'b110;
Bit#(3) fnAND   = 3'b111;
// funct3 - Branch
Bit#(3) fnBEQ   = 3'b000;
Bit#(3) fnBNE   = 3'b001;
Bit#(3) fnBLT   = 3'b100;
Bit#(3) fnBGE   = 3'b101;
Bit#(3) fnBLTU  = 3'b110;
Bit#(3) fnBGEU  = 3'b111;
// funct3 - Load
Bit#(3) fnLW    = 3'b010;
Bit#(3) fnLB    = 3'b000;
Bit#(3) fnLH    = 3'b001;
Bit#(3) fnLBU   = 3'b100;
Bit#(3) fnLHU   = 3'b101;
// funct3 - Store
Bit#(3) fnSW    = 3'b010;
Bit#(3) fnSB    = 3'b000;
Bit#(3) fnSH    = 3'b001;
// funct3 - JALR
Bit#(3) fnJALR  = 3'b000;

// Return type for Execute function
typedef struct {
    IType iType;
    Maybe#(RIndx) dst;
    Word data;
    Word addr;
    Word nextPc;
} ExecInst;

// Memory writes
typedef struct {
    Word addr;
    Word data;
} MemWriteReq;


import ProcTypes;

////////////////////////////////////////////////////////////////////////////////////////////
/// The following are relevant types and constants for the decoder, copied from ProcTypes.ms
////////////////////////////////////////////////////////////////////////////////////////////
// typedef enum {OP, OPIMM, BRANCH, LUI, JAL, JALR, LOAD, STORE, AUIPC, Unsupported} IType;

// typedef struct {
//     IType iType;
//     AluFunc aluFunc;
//     BrFunc brFunc;
//     RDst dst;
//     RIndx src1;
//     RIndx src2;
//     Word imm;
// } DecodedInst;

// // Opcode
// Bit#(7) opOpImm  = 7'b0010011;
// Bit#(7) opOp     = 7'b0110011;
// Bit#(7) opLui    = 7'b0110111;
// Bit#(7) opJal    = 7'b1101111;
// Bit#(7) opJalr   = 7'b1100111;
// Bit#(7) opBranch = 7'b1100011;
// Bit#(7) opLoad   = 7'b0000011;
// Bit#(7) opStore  = 7'b0100011;
// Bit#(7) opAuipc  = 7'b0010111;

// // funct3 - ALU
// Bit#(3) fnADD   = 3'b000;
// Bit#(3) fnSLL   = 3'b001;
// Bit#(3) fnSLT   = 3'b010;
// Bit#(3) fnSLTU  = 3'b011;
// Bit#(3) fnXOR   = 3'b100;
// Bit#(3) fnSR    = 3'b101;
// Bit#(3) fnOR    = 3'b110;
// Bit#(3) fnAND   = 3'b111;
// // funct3 - Branch
// Bit#(3) fnBEQ   = 3'b000;
// Bit#(3) fnBNE   = 3'b001;
// Bit#(3) fnBLT   = 3'b100;
// Bit#(3) fnBGE   = 3'b101;
// Bit#(3) fnBLTU  = 3'b110;
// Bit#(3) fnBGEU  = 3'b111;
// // funct3 - Load
// Bit#(3) fnLW    = 3'b010;
// Bit#(3) fnLB    = 3'b000;
// Bit#(3) fnLH    = 3'b001;
// Bit#(3) fnLBU   = 3'b100;
// Bit#(3) fnLHU   = 3'b101;
// // funct3 - Store
// Bit#(3) fnSW    = 3'b010;
// Bit#(3) fnSB    = 3'b000;
// Bit#(3) fnSH    = 3'b001;
// // funct3 - JALR
// Bit#(3) fnJALR  = 3'b000;

function DecodedInst decode(Bit#(32) inst);
    let opcode = inst[6:0];
    let funct3 = inst[14:12];
    let funct7 = inst[31:25];
    let dst    = inst[11:7];
    let src1   = inst[19:15];
    let src2   = inst[24:20];

    Maybe#(RIndx) validDst = Valid(dst);
    Maybe#(RIndx) dDst = Invalid; // default value
    RIndx dSrc = 5'b0;

    // DEFAULT VALUES - Use the following for your default values:

    // dst: dDst
    // src1: dSrc
    // src2: dSrc
    // imm: immD
    // BrFunc: Dbr
    // AluFunc: ?

  //default:
  //  dInst = DecodedInst {iType: TBD, dst: dDst, src1: dSrc, src2: dSrc, imm: immD, brFunc: Dbr, aluFunc: ?};

    // Since many groups of instructions use the same immediate constructed
    // from the same pattern of bits of the instruction (corresponding to the
    // "type", i.e. I-type, S-type, B-type, U-type, or J-type, described in the
    // RISC-V reference), we construct all the immediates first so we can use
    // them in multiple places. We can do this in two steps for each pattern:
    // (1) Concatenate all the immediate bits from the instruction.
    // (2) Sign-extend and/or pad with 0s on the right to produce a 32-bit word.

    // We have provided a default value and done immB for you.
    Word immD32 = signExtend(1'b0); // default value

    Bit#(12) immB = { inst[31], inst[7], inst[30:25], inst[11:8] };
    Word immB32 = signExtend({ immB, 1'b0 });

    // TODO: Consult the RISC-V reference and fill in the correct value for the
    // other immediates (these are provided in the order the microtests test
    // them):
    Bit#(20) immU = inst[31:12]; // TODO Replace 0 with the correct value
    Word immU32 = {immU, 12'b000000000000};   // TODO Replace 0 with the correct value

    Bit#(12) immI = inst[31:20]; // TODO Replace 0 with the correct value
    Word immI32 = signExtend(immI);   // TODO Replace 0 with the correct value

    Bit#(20) immJ = { inst[31], inst[19:12], inst[20], inst[30:21] }; // TODO Replace 0 with the correct value
    Word immJ32 = signExtend({immJ, 1'b0});   // TODO Replace 0 with the correct value

    Bit#(12) immS = { inst[31:25], inst[11:7] }; // TODO Replace 0 with the correct value
    Word immS32 = signExtend(immS);   // TODO Replace 0 with the correct value

    DecodedInst dInst = unpack(0);
    dInst.iType = Unsupported; // unsupported by default

    case (opcode)
        // We have decoded AUIPC and some OP instructions for you.
        // TODO: Decode the remaining instruction types.
        opAuipc: begin
            // There are two ways you might want to construct the DecodedInst.
            // One is to create a complete DecodedInst all at once, which you
            // can do with this syntax: the name of the struct "DecodedInst"
            // followed by curly braces. Inside the braces, each field is
            // specified by fieldName: fieldValue, separated by commas.

            // NOTE: this will only work after you've correctly filled in immU/immU32
            // above!
            dInst = DecodedInst {iType: AUIPC, dst: validDst, src1: dSrc, src2: dSrc, imm: immU32, brFunc: Dbr, aluFunc: ?};
        end
        opLui: begin
            // LUI is a simple instruction and is tested by microtest 1. You
            // can construct a DecodedInst as in the code above. (Make sure
            // you've also filled in immU/immU32.)
            // After you've implemented decoding and executing LUI
            // instructions, your processor should pass microtest 1.
            dInst = DecodedInst {iType: LUI, dst: validDst, src1: dSrc, src2: dSrc, imm: immU32, brFunc: Dbr, aluFunc: ?};
        end

        opOpImm: begin
            // The other way to construct a DecodedInst is to assign to fields
            // of the struct individually, with dInst.fieldName = fieldValue.

            // In this block of code, we handle all OPIMM instructions, namely
            // ANDI, ORI, XORI, ADDI, SLTI, SLTUI, SLLI, SRLI, and SRAI. Since
            // all these instructions have the same iType, src1, and dst, we
            // can assign them here:
            dInst.iType = OPIMM;
            dInst.src1  = src1;
            dInst.imm   = immI32;
            dInst.dst   = validDst;

            // However, note that even if opcode == opOpImm, it's still
            // possible that the instruction we're decoding is invalid, for
            // example if funct3 (i.e. inst[14:12]) corresponds to SLLI, but
            // funct7 (i.e. inst[31:25]) is not all 0s. (If you consult the
            // RISC-V reference you'll see that valid SLLI instructions must
            // start with seven 0 bits.) In those cases we have to say that the
            // instruction is invalid by setting dInst.iType back to
            // Unsupported.

            // We also put the statement "dInst.iType = Unsupported;" in some
            // other places as placeholders, so that you can compile your
            // processor directly without having finished all the parts; they
            // are meant to be replaced.

            case (funct3)
                fnAND : dInst.aluFunc = And; // Decode ANDI instructions
                fnOR  : dInst.aluFunc = Or; // TODO: Replace this statement to decode the aluFunc for ORI instructions
                fnXOR : dInst.aluFunc = Xor; // TODO: Replace this statement to decode the aluFunc for XORI instructions
                fnADD : dInst.aluFunc = Add; // TODO: Replace this statement to decode the aluFunc for ADDI instructions
                fnSLT : dInst.aluFunc = Slt; // TODO: Replace this statement to decode the aluFunc for SLTI instructions
                fnSLTU: dInst.aluFunc = Sltu; // TODO: Replace this statement to decode the aluFunc for SLTUI instructions
                fnSLL : case (funct7)
                    // Here is where we check if funct7 is all 0. If it is then
                    // it's a valid SLLI instruction so we can set aluFunc to
                    // Sll as expected:
                    7'b0000000: dInst.aluFunc = Sll;
                    // Otherwise we must say the instruction is invalid:
                    default:    dInst.iType = Unsupported;
                endcase
                fnSR  :
                    case (funct7)
                      7'b0000000: dInst.aluFunc = Srl;
                      7'b0100000: dInst.aluFunc = Sra;
                      default: dInst.iType = Unsupported;
                    endcase
                default: dInst.iType = Unsupported;
            endcase

            // After you've implemented decoding and executing OPIMM
            // instructions, your processor should pass microtest 2.
        end
        opOp: begin
            // TODO: Decode instructions of type OP here (i.e. ADD, SUB, AND,
            // OR, XOR, SLT, SLTU, SLL, SRL, and SRA)

            // As in OPIMM, make sure you check funct7 to see if instructions
            // are valid.

            // After you've implemented decoding and executing OP
            // instructions, your processor should pass microtest 3.

            dInst.iType = OP;
            dInst.src1  = src1;
            dInst.src2  = src2;
            dInst.dst   = validDst;

             case (funct3)
                fnAND : case (funct7) 7'b0000000: dInst.aluFunc = And; default: dInst.iType = Unsupported; endcase
                fnOR : case (funct7) 7'b0000000: dInst.aluFunc = Or; default: dInst.iType = Unsupported; endcase
                fnXOR : case (funct7) 7'b0000000: dInst.aluFunc = Xor; default: dInst.iType = Unsupported; endcase
                fnADD : case (funct7) 7'b0000000: dInst.aluFunc = Add; 7'b0100000: dInst.aluFunc = Sub; default: dInst.iType = Unsupported; endcase
                fnSLT : case (funct7) 7'b0000000: dInst.aluFunc = Slt; default: dInst.iType = Unsupported; endcase
                fnSLTU : case (funct7) 7'b0000000: dInst.aluFunc = Sltu; default: dInst.iType = Unsupported; endcase
                fnSLL : case (funct7)
                    7'b0000000: dInst.aluFunc = Sll;
                    default:    dInst.iType = Unsupported;
                endcase
                fnSR  :
                    case (funct7)
                      7'b0000000: dInst.aluFunc = Srl;
                      7'b0100000: dInst.aluFunc = Sra;
                      default: dInst.iType = Unsupported;
                    endcase
                default: dInst.iType = Unsupported;
            endcase


        end
        opBranch: begin
            // TODO: Decode instructions of type BRANCH here (i.e. BEQ, BNE,
            // BLT, BGE, BLTU, and BGEU)

            // After you've implemented decoding and executing branch
            // instructions, your processor should pass microtest 4.

            dInst.iType = BRANCH;
            dInst.src1  = src1;
            dInst.src2  = src2;
            dInst.imm   = immB32;

            case (funct3)
                fnBEQ: dInst.brFunc = Eq;
                fnBNE: dInst.brFunc = Neq;
                fnBLT: dInst.brFunc = Lt;
                fnBGE: dInst.brFunc = Ge;
                fnBLTU: dInst.brFunc = Ltu;
                fnBGEU: dInst.brFunc = Geu;
                default: dInst.iType = Unsupported;
            endcase
        end
        opJal: begin
            // TODO: Decode instructions of type JAL here

            // After you've implemented decoding and executing JAL
            // instructions, your processor should pass microtest 5.

            dInst.iType = JAL;
            dInst.dst = validDst;
            dInst.imm = immJ32;

        end
        opLoad: begin
            // TODO: Decode instructions of type LOAD here (i.e. LW)

            // After you've implemented decoding and executing LW
            // instructions, your processor should pass microtest 7.
            // (We skipped 6 because it tests AUIPC but also requires JAL.)

            dInst.dst = validDst;
            dInst.src1 = src1;
            dInst.imm = immI32;

            case (funct3)
                fnLW: dInst.iType = LOAD;
                default: dInst.iType = Unsupported;
            endcase

        end
        opStore: begin
            // TODO: Decode instructions of type STORE here (i.e. SW)

            // After you've implemented decoding and executing SW
            // instructions, your processor should pass microtest 8.

            dInst.src1 = src1;
            dInst.src2 = src2;
            dInst.imm = immS32;
            
            case(funct3)
                fnSW: dInst.iType = STORE;
                default: dInst.iType = Unsupported;
            endcase

        end
        opJalr: begin
            // TODO: Decode instructions of type JALR here

            // After you've implemented decoding and executing JALR
            // instructions, your processor should pass microtest 9.

            dInst.dst = validDst;
            dInst.src1 = src1;
            dInst.imm = immI32;
            
            case(funct3)
                fnJALR: dInst.iType = JALR;
                default: dInst.iType = Unsupported;
            endcase


        end
    endcase

    return dInst;
endfunction


import ProcTypes;

// ALU
// Imports your ALU from Lab 4
import ALU;

// Branch ALU
// BrFunc defined in ProcTypes.ms
function Bool aluBr(Word a, Word b, BrFunc brFunc);
    Bool res = case (brFunc)
        Eq:     (a == b);
        Neq:    (a != b);
        Lt:     signedLT(a, b); // Built-in signed comparison
        Ltu:    (a < b);
        Ge:     signedGE(a, b); // Built-in signed comparison
        Geu:    (a >= b);
        default: False;
    endcase;
    return res;
endfunction

// Execute function
// ExecInst defined in ProcTypes.ms
function ExecInst execute( DecodedInst dInst, Word rVal1, Word rVal2, Word pc );
    let imm = dInst.imm;
    let brFunc = dInst.brFunc;
    let aluFunc = dInst.aluFunc;
    let aluVal2 = dInst.iType == OPIMM ? imm : rVal2;

    // TODO: Compute the correct value for data. For OP, OPIMM, LUI, JAL, JALR,
    // and AUIPC, data should be the value that will be stored in the
    // destination register; we have done AUIPC for you. (Reminder that for LUI
    // and AUIPC, your decoder should already have shifted the immediate, so
    // you don't need to do that here.) For STORE, data should be the value
    // that will be written to memory.
    Word data = case (dInst.iType)
        AUIPC:     pc + imm;
        LUI:       imm;
        OP, OPIMM: alu(rVal1, aluVal2, aluFunc); // TODO Replace 0 with the correct expression
        JAL, JALR: pc+4; // TODO Replace 0 with the correct expression
        STORE:     rVal2; // TODO Replace 0 with the correct expression
        default:   0;
    endcase;

    // TODO: Compute the correct value for nextPc, that is, the address of the
    // next instruction to execute. We have done JALR for you.
    Word nextPc = case (dInst.iType)
        BRANCH: aluBr(rVal1, rVal2, brFunc) ? (pc + imm) : (pc + 4); // TODO Replace 0 with the correct expression
        JAL:   (pc+imm); // TODO Replace 0 with the correct expression
        JALR: (rVal1 + imm) & ~1; // "& ~1" clears the bottom bit.
        default: pc + 4;
    endcase;

    // TODO: Compute the correct value for addr. This should be the memory
    // address that LW loads from or that SW stores to.
    Word addr = rVal1 + dInst.imm; // TODO Replace 0 with the correct expression

    return ExecInst{iType: dInst.iType, dst: dInst.dst, data: data, addr: addr, nextPc: nextPc};
endfunction
