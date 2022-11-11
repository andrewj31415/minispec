
/* A module where a four bit counter produces values and passes them to a fifo queue,
which passes them to a sum module that adds them up. */

module FourBitCounter(FIFO queue);
    Reg#(Bit#(4)) count(0);
    input Bool enable;
    rule increment;
        if (enable)
            count <= count + 1;
        queue.in = count;
    endrule
endmodule

module FIFO;
    RegU#(Bit#(4)) stage1;
    RegU#(Bit#(4)) stage2;
    method Bit#(4) out = stage2;
    input Bit#(4) in;
    rule tick;
        stage1 <= in;
        stage2 <= stage1;
    endrule
endmodule

module Sum(FIFO queue);
    Reg#(Bit#(4)) count(0);
    method Bit#(4) getCount = count;
    rule add;
        count <= count + queue.out;
    endrule
endmodule

module TopLevel;
    FIFO queue;
    FourBitCounter producer(queue);
    Sum consumer(queue);
    input Bool enable;
    method Bit#(4) getCount = consumer.getCount;
    rule tick;
        producer.enable = enable;
    endrule
endmodule