

typedef Bit#(32) Word;

typedef Bit#(32) TempWord;

typedef TempWord OtherWord;

OtherWord i = 27;
Word j = 27;

function Word f(OtherWord a);
  Bit#(32) x = 0;
  if (i == j) x = ~a;
  if (i == 27) x = ~x;
  if (i == j+1) x = ~x; /* should not happen */
  if (i+j == 54) x = ~x;
  return x;
endfunction