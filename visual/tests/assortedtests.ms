// All sorting networks sort unsigned 32-bit words
typedef Bit#(32) Word;

/* Combinational n-element Bitonic Sorting Network
 *
 * The following functions use four built-in functions on vectors:
 * 1.- take() takes elements starting from the front of the vector.
 *     For example, if v is a Vector#(8, Word),
 *        Vector#(2, Word) f = take(v);
 *     will make f have the first two elements of v (v[0] and v[1]).
 * 2.- takeTail() takes element from the back (i.e., tail) of the vector.
 *     For example, if v is a Vector#(8, Word),
 *        Vector#(2, Word) b = takeTail(v);
 *     will make b have the last two elements of v (v[6] and v[7]).
 * 3.- reverse() reverses the elements of a vector.
 *     For example, if v is a Vector#(4, Word),
 *        Vector#(4, Word) r = reverse(v);
 *     will make r have r[0] = v[3], r[1] = v[2], r[2] = v[1], and r[3] = v[0].
 * 4.- append() concatenates two vectors, creating a single vector
 *     with the sum of their lengths.  
 */ 
function Vector#(n, Word) bitonicSort#(Integer n)(Vector#(n, Word) in);
    if (n <= 1) begin
        return in;
    end else begin
    	Vector#(n/2, Word) lower = take(in); // lower = first n/2 elements of in
    	Vector#(n-n/2, Word) upper = takeTail(in); // upper = last n-n/2 elements of in

    	// Sort lower and upper
    	let lower_sorted = bitonicSort#(n/2)(lower);
        let upper_sorted = bitonicSort#(n-n/2)(upper);

        // Reverse the sorted upper half
        let upper_sorted_reversed = reverse(upper_sorted);

        let vector_to_merge = append(lower_sorted, upper_sorted_reversed);
        return bitonicMerge#(n)(vector_to_merge);
    end
endfunction

function Vector#(n, Word) bitonicMerge#(Integer n)(Vector#(n, Word) x);
    if (n <= 1) begin
        return x;
    end else begin
        let s = x;
        for (Integer i = 0; i < n/2; i = i + 1) begin
            Integer j = i + n/2;
            if (x[i] > x[j]) begin
                s[i] = x[j];
                s[j] = x[i];
            end
        end

        Vector#(n/2, Word) lower = take(s); // lower = first n/2 elements of s
    	Vector#(n-n/2, Word) upper = takeTail(s); // upper = last n-n/2 elements of s

    	// Merge lower and upper, then return their concatenation
        let lower_merged = bitonicMerge#(n/2)(lower);
        let upper_merged = bitonicMerge#(n-n/2)(upper);
        return append(lower_merged, upper_merged);
    end
endfunction

// Description: Pipelined 8-element Word sorting network
// TODO: Implement this module in Exercise 4
// NOTE: Depending on which implementation strategy you choose (see
// hints in handout), implementing this module and its submodules
// requires about 40-70 lines of code. Much of this code directly
// corresponds to code in the combinational sorting network.
module BitonicSorter8;
    // Instantiate your submodules here
    RegU#(Maybe#(Vector#(8, Word))) p1;
    RegU#(Maybe#(Vector#(8, Word))) p2;
    RegU#(Maybe#(Vector#(8, Word))) p3;
    RegU#(Maybe#(Vector#(8, Word))) p4;
    RegU#(Maybe#(Vector#(8, Word))) p5;
    RegU#(Maybe#(Vector#(8, Word))) p6;

    // When there is a new vector of elements to sort, they
    // will be passed in as a valid vector.
    input Maybe#(Vector#(8, Word)) in default = Invalid;

    // If 6 cycles ago (the number of pipeline stages) the module had
    // a valid input, getOutput should return a valid vector with
    // those input elements in sorted (ascending) order. If 6 cycles
    // ago the input was Invalid, getOutput should return Invalid.
    method Maybe#(Vector#(8, Word)) getOutput;
        // TODO: Implement this method in Exercise 4
return p6;
//        return Invalid;
    endmethod

    rule tick;
        // TODO: Implement this rule in Exercise 4

if (isValid(in)) begin
  Vector#(8, Word) inVal = fromMaybe(?, in);
  Vector#(8, Word) p1Val;
  for (Integer i = 0; i<8; i=i+2) begin
    p1Val[i] = (inVal[i]<inVal[i+1]) ? inVal[i] : inVal[i+1];
    p1Val[i+1] = (inVal[i]<inVal[i+1]) ? inVal[i+1] : inVal[i];
  end
  p1 <= Valid(p1Val);
end else p1 <= Invalid;

if (isValid(p1)) begin
  Vector#(8, Word) p1Val = fromMaybe(?, p1);
  Vector#(8, Word) p2Val;
  for (Integer i=0; i<8; i=i+4) begin
    for (Integer j=0; j<2; j=j+1) begin
      p2Val[i+j] = (p1Val[i+j]<p1Val[i+3-j]) ? p1Val[i+j] : p1Val[i+3-j];
      p2Val[i+3-j] = (p1Val[i+j]<p1Val[i+3-j]) ? p1Val[i+3-j] : p1Val[i+j];
    end
  end
  p2 <= Valid(p2Val);
end else p2 <= Invalid;

if (isValid(p2)) begin
  Vector#(8, Word) p2Val = fromMaybe(?, p2);
  Vector#(8, Word) p3Val;
  for (Integer i = 0; i<8; i=i+2) begin
    p3Val[i] = (p2Val[i]<p2Val[i+1]) ? p2Val[i] : p2Val[i+1];
    p3Val[i+1] = (p2Val[i]<p2Val[i+1]) ? p2Val[i+1] : p2Val[i];
  end
  p3 <= Valid(p3Val);
end else p3 <= Invalid;

if (isValid(p3)) begin
  Vector#(8, Word) p3Val = fromMaybe(?, p3);
  Vector#(8, Word) p4Val;
  for (Integer i = 0; i<4; i=i+1) begin
    p4Val[i] = (p3Val[i]<p3Val[7-i]) ? p3Val[i] : p3Val[7-i];
    p4Val[7-i] = (p3Val[i]<p3Val[7-i]) ? p3Val[7-i] : p3Val[i];
  end
  p4 <= Valid(p4Val);
end else p4 <= Invalid;

if (isValid(p4)) begin
  Vector#(8, Word) p4Val = fromMaybe(?, p4);
  Vector#(8, Word) p5Val;
  for (Integer i=0; i<8; i=i+4) begin
    for (Integer j=0; j<2; j=j+1) begin
      p5Val[i+j] = (p4Val[i+j]<p4Val[i+j+2]) ? p4Val[i+j] : p4Val[i+j+2];
      p5Val[i+j+2] = (p4Val[i+j]<p4Val[i+j+2]) ? p4Val[i+j+2] : p4Val[i+j];
    end
  end
  p5 <= Valid(p5Val);
end else p5 <= Invalid;

if (isValid(p5)) begin
  Vector#(8, Word) p5Val = fromMaybe(?, p5);
  Vector#(8, Word) p6Val;
  for (Integer i = 0; i<8; i=i+2) begin
    p6Val[i] = (p5Val[i]<p5Val[i+1]) ? p5Val[i] : p5Val[i+1];
    p6Val[i+1] = (p5Val[i]<p5Val[i+1]) ? p5Val[i+1] : p5Val[i];
  end
  p6 <= Valid(p6Val);
end else p6 <= Invalid;



    endrule
endmodule





