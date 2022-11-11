
# needed to import parsesynth.py
import os, sys  # see https://stackoverflow.com/questions/16780014/import-file-from-parent-directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware import *
import synth

import pathlib
def pull(name):
    '''reads the text of the given file and returns it'''
    textFile = pathlib.Path(__file__).with_name(name + ".ms")
    text = textFile.read_text()
    return text

# Setup to run the tests in order
tests = []  # Array[(testName: str, testFunc: ()=>{}, skipped: Bool) | categoryName: str]
def it(name: 'str'):
    def logger(func):
        tests.append((name, func, False))
    return logger

def skip(name: 'str'):
    def skipLogger(func):
        tests.append((name, func, True))
    return skipLogger

it.skip = skip


def describe(categoryName: 'str'):
    tests.append(categoryName)

def compare(output: 'Function|Module', expected: 'Function|Module'):
    ''' Prints a comparison of two pieces of hardware. Helpful for debugging. '''
    print()
    print('output')
    for child in output.children:
        print(child.__repr__())
    print(len(output.children), len(output.getNodeListRecursive()))
    print()
    print('expected')
    for child in expected.children:
        print(child.__repr__())
    print(len(expected.children), len(expected.getNodeListRecursive()))
    print()

describe("Function Calls")

@it('''A simple function wrapping an xor''')
def _():
    text = pull('function')
    output = synth.parseAndSynth(text, 'f')
    fa, fb, fo = Node('fa'), Node('fb'), Node('fo')
    xfa, xfb, xfo = Node('xfa'), Node('xfb'), Node('xfo')
    expected = Function("f", [Function("^", [], [xfa, xfb], xfo), Wire(fa, xfa),
                                    Wire(fb, xfb), Wire(xfo, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''One function calling another for a three-way xor''')
def _():
    text = pull('functions')
    output = synth.parseAndSynth(text, 'g')
    ga, gb, gc, go = Node('ga'), Node('gb'), Node('gc'), Node('go')
    fa, fb, fo = Node('fa'), Node('fb'), Node('fo')
    xfa, xfb, xfo = Node('xfa'), Node('xfb'), Node('xfo')
    xga, xgb, xgo = Node('xga'), Node('xgb'), Node('xgo')
    expected = Function("g", [Function("f", [Function("^", [], [xfa, xfb], xfo),
                                            Wire(fa, xfa), Wire(fb, xfb), Wire(xfo, fo)], [fa, fb], fo),
                            Function("^", [], [xga, xgb], xgo),
                            Wire(ga, xga), Wire(gb, xgb), Wire(xgo, fa), Wire(gc, fb), Wire(fo, go)], [ga, gb, gc], go)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    '''
    Parameterization features to test:
    Multiple parameters
    Parameter overriding, partial overriding, no overriding (overriding 0, some, all parameters)
    Functions with same name but different numbers of parameters (0, 1, >1) should not interfere with each other
    Integer parameter arithmetic, including defining functions with parameters not evaluatable until runtime
    After implementing types/modules:
        custom types/modules, with the same categories as above
    '''

describe("Parameterized Functions")
''' 
text = pull('parameterize')
output = parseAndSynth(text, 'e')
#print(output.__repr__())
'''

@it('''Function should not be overwritten by nearby functions with different parameters''')
def _():
    text = pull('params1')
    fa, fb, fo = Node(), Node(), Node()
    inner1, inner2, innerOut = Node(), Node(), Node()
    output = synth.parseAndSynth(text, 'f#(2,2)') #the original f
    expected = Function('f#(2,2)', [Function('+', [], [inner1, inner2], innerOut), Wire(fa, inner1), Wire(fb, inner2), Wire(innerOut, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Function should correctly take parameter''')
def _():
    text = pull('params1')
    fa, fb, fo = Node(), Node(), Node()
    output = synth.parseAndSynth(text, 'f#(1)') #the second f
    expected = Function('f#(1)', [Wire(fa, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Function should correctly partially specialize''')
def _():
    text = pull('params1')
    fa, fb, fo = Node(), Node(), Node()
    output = synth.parseAndSynth(text, 'f#(2,1)') #the third f
    expected = Function('f#(2,1)', [Wire(fb, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Function should correctly fully specialize''')
def _():
    text = pull('params1')
    fa, fb, fo = Node(), Node(), Node()
    inner1, inner2, innerOut = Node(), Node(), Node()
    output = synth.parseAndSynth(text, 'f#(1,1)') #the fourth f
    expected = Function('f#(1,1)', [Function('f', [Wire(inner1, innerOut)], [inner1, inner2], innerOut), Wire(fa, inner2), Wire(fb, inner1), Wire(innerOut, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Function should be correctly processed''')
def _():
    text = pull('params1')
    fa, fb, fo = Node(), Node(), Node()
    output = synth.parseAndSynth(text, 'f') #the fifth f
    expected  = Function('f', [Wire(fa, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly computes fixed param''')
def _():
    text = pull('params2')
    fa, fb, fo = Node(), Node(), Node()
    output = synth.parseAndSynth(text, 'f#(10,0)') #the second f
    expected  = Function('f#(10,0)', [Wire(fa, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly computes fixed param from constants''')
def _():
    text = pull('params2')
    fa, fb, fo = Node(), Node(), Node()
    output = synth.parseAndSynth(text, 'f#(1,7)') #the third f
    expected  = Function('f#(1,7)', [Wire(fb, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"


describe('Literal Arithmetic')

@it('''Correctly folds constants''')
def _():
    text = pull('literals1')

    fa, fo, ga, go = Node('fa'), Node('fo'), Node('ga'), Node('go')
    xor1, xor2, xoro = Node('xor1'), Node('xor2'), Node('xoro')
    mulf1, mulf2, mulfo = Node('mulf1'), Node('mulf2'), Node('mulfo')
    mulg1, mulg2, mulgo = Node('mulg1'), Node('mul2'), Node('mulo')
    add1, add2, addo = Node('add1'), Node('add2'), Node('addo')
    eq1, eq2, eqo = Node('eq1'), Node('eq2'), Node('eqo')
    five, six, seven, thirteen = Function('5', [], []), Function('6', [], []), Function('7', [], []), Function('13', [], [])
    mulg = Function('*', [], [mulg1, mulg2], mulgo)
    add = Function('+', [], [add1, add2], addo)
    g = Function('g#(15)', [add, mulg, six, thirteen, Wire(ga, mulg1), Wire(six.output, mulg2), Wire(mulgo, add2), Wire(thirteen.output, add1), Wire(addo, go)], [ga], go)
    xor = Function('^', [], [xor1, xor2], xoro)
    eq = Function('==', [], [eq1, eq2], eqo)
    mulf = Function('*', [], [mulf1, mulf2], mulfo)
    f = Function('f', [xor, eq, g, mulf, five, seven, Wire(fa, mulf1), Wire(five.output, mulf2), Wire(mulfo, xor1), Wire(fa, ga), Wire(go, xor2), Wire(xoro, eq1), Wire(seven.output, eq2), Wire(eqo, fo)], [fa], fo)
    
    output = synth.parseAndSynth(text, 'g#(15)')
    expected = g
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    output = synth.parseAndSynth(text, 'f')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

describe("If and Ternary Statements")

@it('''Correctly synthesizes mux''')
def _():
    text = pull('if1')

    fa, fo = Node(), Node()
    eq = Function("==", [], [Node(), Node()])
    eq1, eq2 = eq.inputs
    four = Function("4", [], [])
    two = Function("2", [], [])
    mux1, mux2, muxc = Node(), Node(), Node()
    mux = Mux([mux1, mux2], muxc)
    f2 = Function("f#(2)", [eq, four, two, mux, Wire(fa, eq1), Wire(four.output, eq2), Wire(eq.output, muxc), Wire(fa, mux1), Wire(two.output, mux2), Wire(mux.output, fo)], [fa], fo)

    output = synth.parseAndSynth(text, 'f#(2)')
    expected = f2
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly skips other branch''')
def _():
    text = pull('if1')

    fa, fo = Node(), Node()
    one = Function("1", [], [])
    xor = Function("^", [], [Node(), Node()])
    xor1, xor2 = xor.inputs
    f0 = Function("f#(0)", [xor, one, Wire(one.output, xor1), Wire(fa, xor2), Wire(xor.output, fo)], [fa], fo)

    output = synth.parseAndSynth(text, 'f#(0)')
    expected = f0
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles begin/end statement''')
def _():
    text = pull('if2')

    fa, fo = Node(), Node()
    one = Function("1", [], [])
    three = Function("3", [], [])
    mux1, mux2, muxc = Node(), Node(), Node()
    mux = Mux([mux1, mux2], muxc)
    f = Function("f", [mux, one, three, Wire(fa, muxc), Wire(one.output, mux1), Wire(three.output, mux2), Wire(mux.output, fo)], [fa], fo)

    output = synth.parseAndSynth(text, 'f')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles ternary ? operator''')
def _():
    text = pull('if3')

    fsel, fa, fb, fo = Node(), Node(), Node(), Node()
    eq1, eq2, eqo = Node(), Node(), Node()
    m1, m2, mc = Node(), Node(), Node()
    zero = Function('0', [], [])
    eq = Function('==', [], [eq1, eq2], eqo)
    m = Mux([m1, m2], mc)
    f = Function('multiplexer1', [m, zero, eq, Wire(fa, m1), Wire(fb, m2), Wire(fsel, eq1), Wire(zero.output, eq2), Wire(eqo, mc), Wire(m.output, fo)], [fsel, fa, fb], fo)

    output = synth.parseAndSynth(text, 'multiplexer1')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles variable declared locally in begin/end block''')
def _():
    text = pull('if4')

    k = 8

    fin, fo = Node(), Node()

    mux = Mux([Node(), Node()])
    eq = Function('==', [], [Node(), Node()])
    cOne, sZero = Function('1'), Function('0')
    lowBit = Function('[0]', [], [Node()])
    inv = Function('Invalid')
    val = Function('Valid', [], [Node()])
    sftComps = []
    for i in range(1,k):
        sftComps.append(Function(f'[{i}]', [], [Node()])) # from input
    for i in range(k-1):
        sftComps.append(Function(f'[{i}]', [], [Node(), Node()])) # collect output
    sftWires = [Wire(sZero.output, sftComps[k-1].inputs[0]), Wire(sftComps[2*k-3].output, val.inputs[0])]
    for i in range(0,k-1):
        sftWires.append(Wire(fin, sftComps[i].inputs[0]))
        sftWires.append(Wire(sftComps[i].output, sftComps[i+k-1].inputs[1]))
    for i in range(0,k-2):
        sftWires.append(Wire(sftComps[i+k-1].output, sftComps[i+k].inputs[0]))

    computeHalf = Function('computeHalf#(' + str(k) + ')', [mux, eq, cOne, sZero, lowBit, inv, val] + sftComps + sftWires + [Wire(val.output, mux.inputs[1]), Wire(inv.output, mux.inputs[0]), Wire(mux.output, fo), Wire(lowBit.output, eq.inputs[0]), Wire(cOne.output, eq.inputs[1]), Wire(eq.output, mux.control), Wire(fin, lowBit.inputs[0])], [fin], fo)

    output = synth.parseAndSynth(text, 'computeHalf#(' + str(k) + ')')
    expected = computeHalf
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

describe('''Case Statements''')

@it('''Correctly handles constant-folded case statement''')
def _():
    text = pull('cases1')

    fa0, fo0 = Node(), Node()
    f0 = Function('addFib#(0,4)', [Wire(fa0, fo0)], [fa0], fo0)

    fa1, fo1 = Node(), Node()
    add = Function('+', [], [Node(), Node()])
    one = Function('1')
    f1 = Function('addFib#(1,4)', [add, one, Wire(fa1, add.inputs[0]), Wire(one.output, add.inputs[1]), Wire(add.output, fo1)], [fa1], fo1)

    fa2, fo2 = Node(), Node()
    add2 = Function('+', [], [Node(), Node()])
    zero = Function('0')
    f2 = Function('addFib#(2,4)', [f0, f1, add2, zero, Wire(fa2, f1.inputs[0]), Wire(f1.output, add2.inputs[0]), Wire(zero.output, f0.inputs[0]), Wire(f0.output, add2.inputs[1]), Wire(add2.output, fo2)], [fa2], fo2)

    fa13, fo13 = Node(), Node()
    add13 = Function('+', [], [Node(), Node()])
    one13 = Function('1')
    f13 = Function('addFib#(1,4)', [add13, one13, Wire(fa13, add13.inputs[0]), Wire(one13.output, add13.inputs[1]), Wire(add13.output, fo13)], [fa13], fo13)

    fa3, fo3 = Node(), Node()
    add3 = Function('+', [], [Node(), Node()])
    zero3 = Function('0')
    f3 = Function('addFib#(3,4)', [f2, f13, add3, zero3, Wire(fa3, f2.inputs[0]), Wire(f2.output, add3.inputs[0]), Wire(zero3.output, f13.inputs[0]), Wire(f13.output, add3.inputs[1]), Wire(add3.output, fo3)], [fa3], fo3)

    output = synth.parseAndSynth(text, 'addFib#(0, 4)')
    expected = f0
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    output = synth.parseAndSynth(text, 'addFib#(1, 4)')
    expected = f1
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    output = synth.parseAndSynth(text, 'addFib#(2, 4)')
    expected = f2
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    output = synth.parseAndSynth(text, 'addFib#(3, 4)')
    expected = f3
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it.skip('''Correctly handles partially constant-folded case statement''')
def _():
    text = pull('cases2')

    fa, fb, fc, fd, fo = Node(), Node(), Node(), Node(), Node()
    zero, one, two, four, zeroy, oney = Function('0'), Function('1'), Function('2'), Function('4'), Function('0'), Function('1')
    concat = Function('{}', [], [Node(), Node()])
    ma, mb, mc, md = Mux([Node(), Node()]), Mux([Node(), Node()]), Mux([Node(), Node()]), Mux([Node(), Node()])
    may, mby, mcy, mdy = Mux([Node(), Node()]), Mux([Node(), Node()]), Mux([Node(), Node()]), Mux([Node(), Node()])

    #TODO finish writing spec

    f = Function('f', [zero, one, two, four, zeroy, oney, ma, mb, mc, md, may, mby, mcy, mdy, concat, Wire(concat.output, fo)], [fa, fb, fc, fd], fo)

    output = synth.parseAndSynth(text, 'f')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles dynamic case statement''')
def _():
    text = pull('cases3')

    fa, fb, fop, fo = Node(), Node(), Node(), Node()
    add, sub, mul = Function('+', [], [Node(), Node()] ), Function('-', [], [Node(), Node()] ), Function('*', [], [Node(), Node()] )
    mux = Mux([Node(), Node(), Node()])
    f = Function('f#(4)', [add, sub, mul, mux, Wire(mux.output, fo), Wire(fa, add.inputs[0]), Wire(fb, add.inputs[1]), Wire(fa, sub.inputs[0]), Wire(fb, sub.inputs[1]), Wire(fa, mul.inputs[0]), Wire(fb, mul.inputs[1]), Wire(add.output, mux.inputs[0]), Wire(sub.output, mux.inputs[1]), Wire(mul.output, mux.inputs[2]), Wire(fop, mux.control)], [fa, fb, fop], fo)

    output = synth.parseAndSynth(text, 'f#(4)')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Handles case statements with default present or not''')
def _():
    text = pull('cases4')

    fa, fflip, fo = Node(), Node(), Node()
    mux = Mux([Node(), Node()])
    n = Function('~', [], [Node()])
    f = Function('f', [mux, n, Wire(fflip, mux.control), Wire(mux.output, fo), Wire(fa, n.inputs[0]), Wire(n.output, mux.inputs[0]), Wire(fa, mux.inputs[1])], [fa, fflip], fo)
    g = Function('g', [mux, n, Wire(fflip, mux.control), Wire(mux.output, fo), Wire(fa, n.inputs[0]), Wire(n.output, mux.inputs[0]), Wire(fa, mux.inputs[1])], [fa, fflip], fo)
    h = Function('h', [mux, n, Wire(fflip, mux.control), Wire(mux.output, fo), Wire(fa, n.inputs[0]), Wire(n.output, mux.inputs[0]), Wire(fa, mux.inputs[1])], [fa, fflip], fo)

    output = synth.parseAndSynth(text, 'f')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    output = synth.parseAndSynth(text, 'g')
    expected = g
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"
    
    output = synth.parseAndSynth(text, 'h')
    expected = h
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"


describe('''Case Expressions''')

@it('''Correctly handles some case expressions''')
def _():
    text = pull('caseExpr1')

    fa, fb, fc, fd, fe, fo = Node(), Node(), Node(), Node(), Node(), Node()

    zeroA, oneA, twoA, threeA = Function('0'), Function('1'), Function('2'), Function('3')
    muxA = Mux([Node(), Node(), Node(), Node()])
    xWires = [Wire(zeroA.output, muxA.inputs[0]), Wire(twoA.output, muxA.inputs[1]), Wire(threeA.output, muxA.inputs[2]), Wire(oneA.output, muxA.inputs[3]), Wire(fa, muxA.control), Wire(muxA.output, fo)]

    zeroY, oneY, twoY = Function('0'), Function('1'), Function('2')
    nb, nc = Function('~', [], [Node()]), Function('~', [], [Node()])
    myb, myc = Mux([Node(), Node()]), Mux([Node(), Node()])
    yWires = [Wire(fb, nb.inputs[0]), Wire(fc, nc.inputs[0]), Wire(nb.output, myb.control), Wire(nc.output, myc.control), Wire(myb.output, fo), Wire(zeroY.output, myb.inputs[0]), Wire(myc.output, myb.inputs[1]), Wire(oneY.output, myc.inputs[0]), Wire(twoY.output, myc.inputs[1])]

    zeroZ, oneZ, twoZ = Function('0'), Function('1'), Function('2')
    eqb, eqc = Function('==', [], [Node(), Node()]), Function('==', [], [Node(), Node()])
    mzb, mzc = Mux([Node(), Node()]), Mux([Node(), Node()])
    zWires = [Wire(fd, eqb.inputs[0]), Wire(fb, eqb.inputs[1]), Wire(eqb.output, mzb.control), Wire(fd, eqc.inputs[0]), Wire(fc, eqc.inputs[1]), Wire(eqc.output, mzc.control), Wire(mzb.output, fo), Wire(zeroZ.output, mzb.inputs[0]), Wire(mzc.output, mzb.inputs[1]), Wire(oneZ.output, mzc.inputs[0]), Wire(twoZ.output, mzc.inputs[1])]

    ne = Function('~', [], [Node()])
    wWires = [Wire(fe, ne.inputs[0]), Wire(ne.output, fo)]

    f1 = Function('f1', [zeroA, oneA, twoA, threeA, muxA] + xWires, [fa, fb, fc, fd, fe], fo)
    f2 = Function('f2', [zeroY, oneY, twoY, nb, nc, myb, myc] + yWires, [fa, fb, fc, fd, fe], fo)
    f3 = Function('f3', [zeroZ, oneZ, twoZ, eqb, eqc, mzb, mzc] + zWires, [fa, fb, fc, fd, fe], fo)
    f4 = Function('f4', [ne] + wWires, [fa, fb, fc, fd, fe], fo)

    output = synth.parseAndSynth(text, 'f1')
    expected = f1
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    output = synth.parseAndSynth(text, 'f2')
    expected = f2
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    output = synth.parseAndSynth(text, 'f3')
    expected = f3
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    output = synth.parseAndSynth(text, 'f4')
    expected = f4
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"


describe('''Modules''')

@it('''Correctly handles a simple counter''')
def _():
    text = pull('counters')

    count = Register('Reg#(Bit#(4))')
    mux = Mux([Node(), Node()])
    add = Function('+', [], [Node(), Node()])
    enable = Node()
    getCount = Node()
    one = Function('1', [], [])
    counter = Module('FourBitCounter', [count, mux, add, one, Wire(enable, mux.control), Wire(count.value, getCount), Wire(add.output, mux.inputs[0]), Wire(count.value, mux.inputs[1]), Wire(mux.output, count.input), Wire(count.value, add.inputs[0]), Wire(one.output, add.inputs[1])], {'enable': enable}, {'getCount': getCount})
    
    output = synth.parseAndSynth(text, 'FourBitCounter')
    expected = counter
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles a more complicated counter''')
def _():
    text = pull('counters')

    ucount = Register('Reg#(Bit#(4))')
    umux = Mux([Node(), Node()])
    uadd = Function('+', [], [Node(), Node()])
    uenable = Node()
    ugetCount = Node()
    uone = Function('1', [], [])
    ucounter = Module('FourBitCounter', [ucount, umux, uadd, uone, Wire(uenable, umux.control), Wire(ucount.value, ugetCount), Wire(uadd.output, umux.inputs[0]), Wire(ucount.value, umux.inputs[1]), Wire(umux.output, ucount.input), Wire(ucount.value, uadd.inputs[0]), Wire(uone.output, uadd.inputs[1])], {'enable': uenable}, {'getCount': ugetCount})
    
    lcount = Register('Reg#(Bit#(4))')
    lmux = Mux([Node(), Node()])
    ladd = Function('+', [], [Node(), Node()])
    lenable = Node()
    lgetCount = Node()
    lone = Function('1', [], [])
    lcounter = Module('FourBitCounter', [lcount, lmux, ladd, lone, Wire(lenable, lmux.control), Wire(lcount.value, lgetCount), Wire(ladd.output, lmux.inputs[0]), Wire(lcount.value, lmux.inputs[1]), Wire(lmux.output, lcount.input), Wire(lcount.value, ladd.inputs[0]), Wire(lone.output, ladd.inputs[1])], {'enable': lenable}, {'getCount': lgetCount})
    
    concat = Function('{}', [], [Node(), Node()])
    fifteen = Function('15')
    eq = Function('==', [], [Node(), Node()])
    a = Function('&&', [], [Node(), Node()])
    enable = Node()
    getCount = Node()
    counter = Module('EightBitCounter', [ucounter, lcounter, concat, fifteen, eq, a, Wire(lgetCount, eq.inputs[0]), Wire(fifteen.output, eq.inputs[1]), Wire(eq.output, a.inputs[1]), Wire(enable, a.inputs[0]), Wire(enable, lenable), Wire(a.output, uenable), Wire(lgetCount, concat.inputs[1]), Wire(ugetCount, concat.inputs[0]), Wire(concat.output, getCount)], {'enable': enable}, {'getCount': getCount})

    output = synth.parseAndSynth(text, 'EightBitCounter')
    expected = counter
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles recursive parametric counter''')
def _():
    text = pull('counters')

    upper1, lower1 = [ synth.parseAndSynth(text, 'Counter#(0)') for i in range(2)]

    enable1, getCount1 = Node(), Node()
    and1, eq1, concat1, one1 = Function('&&', [], [Node(), Node()]), Function('==', [], [Node(), Node()]), Function('{}', [], [Node(), Node()]), Function('1')
    counter1 = Module('Counter#(1)', [and1, eq1, concat1, one1, upper1, lower1, Wire(enable1, lower1.inputs['enable']), Wire(lower1.methods['getCount'], eq1.inputs[0]), Wire(one1.output, eq1.inputs[1]), Wire(eq1.output, and1.inputs[1]), Wire(enable1, and1.inputs[0]), Wire(and1.output, upper1.inputs['enable']), Wire(upper1.methods['getCount'], concat1.inputs[0]), Wire(lower1.methods['getCount'], concat1.inputs[1]), Wire(concat1.output, getCount1)], {'enable': enable1}, {'getCount': getCount1})

    output = synth.parseAndSynth(text, 'Counter#(1)')
    expected = counter1
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles larger recursive parametric counter''')
def _():
    text = pull('counters')

    upper1, lower1, upper2, lower2 = [ synth.parseAndSynth(text, 'Counter#(0)') for i in range(4)]

    enable1, getCount1 = Node(), Node()
    and1, eq1, concat1, one1 = Function('&&', [], [Node(), Node()]), Function('==', [], [Node(), Node()]), Function('{}', [], [Node(), Node()]), Function('1')
    lower3 = Module('Counter#(1)', [and1, eq1, concat1, one1, upper1, lower1, Wire(enable1, lower1.inputs['enable']), Wire(lower1.methods['getCount'], eq1.inputs[0]), Wire(one1.output, eq1.inputs[1]), Wire(eq1.output, and1.inputs[1]), Wire(enable1, and1.inputs[0]), Wire(and1.output, upper1.inputs['enable']), Wire(upper1.methods['getCount'], concat1.inputs[0]), Wire(lower1.methods['getCount'], concat1.inputs[1]), Wire(concat1.output, getCount1)], {'enable': enable1}, {'getCount': getCount1})

    enable2, getCount2 = Node(), Node()
    and2, eq2, concat2, one2 = Function('&&', [], [Node(), Node()]), Function('==', [], [Node(), Node()]), Function('{}', [], [Node(), Node()]), Function('1')
    upper3 = Module('Counter#(1)', [and2, eq2, concat2, one2, upper2, lower2, Wire(enable2, lower2.inputs['enable']), Wire(lower2.methods['getCount'], eq2.inputs[0]), Wire(one2.output, eq2.inputs[1]), Wire(eq2.output, and2.inputs[1]), Wire(enable2, and2.inputs[0]), Wire(and2.output, upper2.inputs['enable']), Wire(upper2.methods['getCount'], concat2.inputs[0]), Wire(lower2.methods['getCount'], concat2.inputs[1]), Wire(concat2.output, getCount2)], {'enable': enable2}, {'getCount': getCount2})

    enable3, getCount3 = Node(), Node()
    and3, eq3, concat3, three = Function('&&', [], [Node(), Node()]), Function('==', [], [Node(), Node()]), Function('{}', [], [Node(), Node()]), Function('3')
    counter2 = Module('Counter#(2)', [and3, eq3, concat3, three, upper3, lower3, Wire(enable3, lower3.inputs['enable']), Wire(lower3.methods['getCount'], eq3.inputs[0]), Wire(three.output, eq3.inputs[1]), Wire(eq3.output, and3.inputs[1]), Wire(enable3, and3.inputs[0]), Wire(and3.output, upper3.inputs['enable']), Wire(upper3.methods['getCount'], concat3.inputs[0]), Wire(lower3.methods['getCount'], concat3.inputs[1]), Wire(concat3.output, getCount3)], {'enable': enable3}, {'getCount': getCount3})

    output = synth.parseAndSynth(text, 'Counter#(2)')
    expected = counter2
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"


@it('''Handles input with default value''')
def _():
    text = pull('moduleDefault')
    
    storage = Register('Reg#(Bit#(4))')
    mux = Mux([Node(), Node()])
    add = Function('+', [], [Node(), Node()])
    enable = Node()
    getStorage = Node()
    one = Function('1', [], [])
    Inner = Module('Inner', [storage, mux, add, one, Wire(enable, mux.control), Wire(storage.value, getStorage), Wire(add.output, mux.inputs[0]), Wire(storage.value, mux.inputs[1]), Wire(mux.output, storage.input), Wire(storage.value, add.inputs[0]), Wire(one.output, add.inputs[1])], {'enable': enable}, {'getStorage': getStorage})
    
    muxO = Mux([Node(), Node()])
    true = Function('True')
    false = Function('False')
    enableO = Node()
    getStorageO = Node()
    Outer = Module('Outer', [Inner, true, false, muxO, Wire(true.output, muxO.inputs[0]), Wire(false.output, muxO.inputs[1]), Wire(enableO, muxO.control), Wire(muxO.output, Inner.inputs['enable']), Wire(Inner.methods['getStorage'], getStorageO)], {'enable': enableO}, {'getStorage': getStorageO})

    output = synth.parseAndSynth(text, 'Outer')
    expected = Outer
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

describe('''Bit Manipulation''')

@it('''Correctly modifies and collects bits''')
def _():
    text = pull('bits1')

    fa, fo = Node(), Node()
    n1, n2, zero, one, concat = Function('~', [], [Node()]), Function('~', [], [Node()]), Function('[0]', [], [Node()]), Function('[1]', [], [Node()]), Function('{}', [], [Node(), Node()])
    f = Function('f', [n1, n2, zero, one, concat, Wire(fa, zero.inputs[0]), Wire(fa, one.inputs[0]), Wire(zero.output, n1.inputs[0]), Wire(one.output, n2.inputs[0]), Wire(n1.output, concat.inputs[0]), Wire(n2.output, concat.inputs[1]), Wire(concat.output, fo)], [fa], fo)

    output = synth.parseAndSynth(text, 'f')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"
    
    ga, go = Node(), Node()
    n1, n2, zero, one, concat = Function('~', [], [Node()]), Function('~', [], [Node()]), Function('[0]', [], [Node()]), Function('[1]', [], [Node()]), Function('{}', [], [Node(), Node()])
    g = Function('g', [n1, n2, zero, one, concat, Wire(ga, zero.inputs[0]), Wire(ga, one.inputs[0]), Wire(zero.output, n1.inputs[0]), Wire(one.output, n2.inputs[0]), Wire(n1.output, concat.inputs[1]), Wire(n2.output, concat.inputs[0]), Wire(concat.output, go)], [ga], go)

    output = synth.parseAndSynth(text, 'g')
    expected = g
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly modifies specific bits''')
def _():
    text = pull('bits2')

    twoone, two1, zero1 = Function('[2][1]', [], [Node(), Node()]), Function('[2]', [], [Node()]), Function('[0]', [], [Node()])
    n = Function('~', [], [Node()])
    zero2, one2 = Function('[0]', [], [Node()]), Function('[1]', [], [Node()])
    one3, zero3 = Function('[1]', [], [Node(), Node()]), Function('[0]', [], [Node(), Node()])
    fa, fo = Node(), Node()
    f = Function('f', [twoone, two1, zero1, n, zero2, one2, one3, zero3, Wire(fa, two1.inputs[0]), Wire(two1.output, zero1.inputs[0]), Wire(zero1.output, n.inputs[0]), Wire(n.output, twoone.inputs[1]), Wire(fa, twoone.inputs[0]), Wire(twoone.output, zero2.inputs[0]), Wire(twoone.output, one2.inputs[0]), Wire(twoone.output, one3.inputs[0]), Wire(zero2.output, one3.inputs[1]), Wire(one3.output, zero3.inputs[0]), Wire(one2.output, zero3.inputs[1]), Wire(zero3.output, fo)], [fa], fo)

    output = synth.parseAndSynth(text, 'f')
    expected = f
    assert expected.match(output), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles variable indices and slice assignment''')
def _():
    text = pull('bits3')

    fa, fi, fj, fk, fo = Node(), Node(), Node(), Node(), Node()
    s1 = Function('[1][_:_][_]', [], [Node(), Node(), Node(), Node(), Node()])
    s21 = Function('[_]', [], [Node(), Node()])
    s22 = Function('[_:2]', [], [Node(), Node()])
    s23 = Function('[0]', [], [Node()])
    n = Function('~', [], [Node()])
    s3 = Function('[2][3:1]', [], [Node(), Node()])
    six = Function('6')
    f = Function('f', [s1, s21, s22, s23, n, s3, six, Wire(fa, s21.inputs[0]), Wire(s21.output, s22.inputs[0]), Wire(s22.output, s23.inputs[0]), Wire(fk, s21.inputs[1]), Wire(fj, s22.inputs[1]), Wire(s23.output, n.inputs[0]), Wire(n.output, s1.inputs[4]), Wire(fa, s1.inputs[0]), Wire(fi, s1.inputs[1]), Wire(fj, s1.inputs[2]), Wire(fk, s1.inputs[3]), Wire(s1.output, s3.inputs[0]), Wire(six.output, s3.inputs[1]), Wire(s3.output, fo)], [fa, fi, fj, fk], fo)
    
    output = synth.parseAndSynth(text, 'f')
    expected = f
    assert expected.match(output), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

describe('''For Loops''')

@it('''Correctly handles for loop''')
def _():
    text = pull('for')

    zero, one, two, three = Function('[0]', [], [Node()]), Function('[1]', [], [Node()]), Function('[2]', [], [Node()]), Function('[3]', [], [Node()])
    output = Function('0')
    xor0, xor1, xor2, xor3 = Function('^', [], [Node(), Node()]), Function('^', [], [Node(), Node()]), Function('^', [], [Node(), Node()]), Function('^', [], [Node(), Node()])
    fa, fo = Node(), Node()
    f = Function('parity#(4)', [zero, one, two, three, output, xor0, xor1, xor2, xor3, Wire(fa, zero.inputs[0]), Wire(fa, one.inputs[0]), Wire(fa, two.inputs[0]), Wire(fa, three.inputs[0]), Wire(output.output, xor0.inputs[0]), Wire(xor0.output, xor1.inputs[0]), Wire(xor1.output, xor2.inputs[0]), Wire(xor2.output, xor3.inputs[0]), Wire(xor3.output, fo), Wire(zero.output, xor0.inputs[1]), Wire(one.output, xor1.inputs[1]), Wire(two.output, xor2.inputs[1]), Wire(three.output, xor3.inputs[1])], [fa], fo)

    output = synth.parseAndSynth(text, 'parity#(4)')
    expected = f
    assert expected.match(output), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

describe('''Types''')

@it('''Handles typedef synonyms''')
def _():
    text = pull('synonym')

    n1, n2, n3 = Function('~', [], [Node()]), Function('~', [], [Node()]), Function('~', [], [Node()])
    fa, fo = Node(), Node()

    output = synth.parseAndSynth(text, 'f')
    expected = Function('f', [n1, n2, n3, Wire(fa, n1.inputs[0]), Wire(n1.output, n2.inputs[0]), Wire(n2.output, n3.inputs[0]), Wire(n3.output, fo)], [fa], fo)
    assert expected.match(output), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

#TODO test synonyms in a module register

@it('''Handles enum types''')
def _():
    text = pull('enum')

    fa, fo = Node(), Node()
    a2, a1, a4, a3 = Function('A2'), Function('A1'), Function('A4'), Function('A3')
    m1, m2, m3 = Mux([Node(), Node()]), Mux([Node(), Node()]), Mux([Node(), Node()])
    eq1, eq2, eq3 = Function('==', [], [Node(), Node()]), Function('==', [], [Node(), Node()]), Function('==', [], [Node(), Node()])
    ea1, ea2, ea3 = Function('A1'), Function('A2'), Function('A3')
    permute = Function('permute', [a2, a1, a4, a3, m1, m2, m3, eq1, eq2, eq3, ea1, ea2, ea3, Wire(eq1.output, m1.control), Wire(eq2.output, m2.control), Wire(eq3.output, m3.control), Wire(ea1.output, eq1.inputs[1]), Wire(ea2.output, eq2.inputs[1]), Wire(ea3.output, eq3.inputs[1]), Wire(fa, eq1.inputs[0]), Wire(fa, eq2.inputs[0]), Wire(fa, eq3.inputs[0]), Wire(m1.output, fo), Wire(m2.output, m1.inputs[1]), Wire(m3.output, m2.inputs[1]), Wire(a4.output, m3.inputs[0]), Wire(a3.output, m3.inputs[1]), Wire(a1.output, m2.inputs[0]), Wire(a2.output, m1.inputs[0])], [fa], fo)

    output = synth.parseAndSynth(text, 'permute')
    expected = permute
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

#TODO test enum literals

@it('''Handles struct type literals''')
def _():
    text = pull('struct')

    a, b, o = Node(), Node(), Node()
    de = Function('Packet{data:1,index:1}')

    output = synth.parseAndSynth(text, 'combine#(1, 1, 1, 1)')
    expected = Function('combine#(1,1,1,1)', [de, Wire(de.output, o)], [a, b], o)
    assert expected.match(output), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Handles struct types''')
def _():
    text = pull('struct')

    a, b, o = Node(), Node(), Node()
    inp1, ind = Function('.data', [], [Node()]), Function('.index', [], [Node()])
    inp2, inp3 = Function('.data', [], [Node()]), Function('.data', [], [Node()])
    inpset = Function('.data', [], [Node(), Node()])
    r = Function('|', [], [Node(), Node()])
    pack = Function('Packet{}', [], [Node(), Node()])

    output = synth.parseAndSynth(text, 'combine#(1, 1, 1, 2)')
    expected = Function('combine#(1,1,1,2)', [inp1, ind, inp2, inp3, inpset, r, pack, Wire(a, inp1.inputs[0]), Wire(b, ind.inputs[0]), Wire(inp1.output, pack.inputs[0]), Wire(ind.output, pack.inputs[1]), Wire(pack.output, inpset.inputs[0]), Wire(pack.output, inp2.inputs[0]), Wire(b, inp3.inputs[0]), Wire(inp2.output, r.inputs[0]), Wire(inp3.output, r.inputs[1]), Wire(r.output, inpset.inputs[1]), Wire(inpset.output, o)], [a, b], o)
    assert expected.match(output), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Handles parameterized typedef synonyms''')
def _():
    text = pull('paramTypedefs1')

    fv, fo = Node(), Node()
    gEv, gEo = Node(), Node()
    s = Function('[1]', [], [Node()])
    gE = Function('getEntry#(Bool,2,1)', [s, Wire(gEv, s.inputs[0]), Wire(s.output, gEo)], [gEv], gEo)
    f = Function('f', [gE, Wire(fv, gE.inputs[0]), Wire(gE.output, fo)], [fv], fo)

    output = synth.parseAndSynth(text, 'f')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Handles parameterized typedef structs''')
def _():
    text = pull('paramTypedefs2')

    sv, so = Node(), Node()
    gl3 = synth.parseAndSynth(text, 'getList#(3, Bit#(3))')  #TODO elaborate these expected items
    sb3 = synth.parseAndSynth(text, 'sumBitList#(3,3)')
    sumVec = Function('sumVector#(3,3)', [gl3, sb3, Wire(sv, gl3.inputs[0]), Wire(gl3.output, sb3.inputs[0]), Wire(sb3.output, so)], [sv], so)

    output = synth.parseAndSynth(text, 'sumVector#(3,3)')
    expected = sumVec
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"


describe('''Maybe Types''')

@it('''Handles maybe input to module''')
def _():
    text = pull('maybe')

    reg = Register('Reg#(Bit#(8))')
    setCount, getCount = Node(), Node()
    fm = Function('fromMaybe', [], [Node(), Node()]);
    u, one = Function('?'), Function('1')
    mux = Mux([Node(), Node()])
    add = Function('+', [], [Node(), Node()])
    isv = Function('isValid', [], [Node()])
    m = Module('SettableCounter', [reg, fm, u, one, mux, add, isv, Wire(setCount, isv.inputs[0]), Wire(isv.output, mux.control), Wire(setCount, fm.inputs[1]), Wire(u.output, fm.inputs[0]), Wire(fm.output, mux.inputs[0]), Wire(reg.value, add.inputs[0]), Wire(one.output, add.inputs[1]), Wire(add.output, mux.inputs[1]), Wire(mux.output, reg.input), Wire(reg.value, getCount)], {'setCount': setCount}, {'getCount': getCount})

    output = synth.parseAndSynth(text, 'SettableCounter')
    expected = m
    assert expected.match(output), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"
  

describe('''Advanced Modules''')

@it('''Correctly handles vectors of submodules''')
def _():
    text = pull('moduleVector')

    output = synth.parseAndSynth(text, 'Reverse#(2)')
    print(output.__repr__())

    compare(output, None)

    expected = None
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Handles module methods with arguments''')
def _():
    pass
    # TODO

@it('''Handles shared modules''')
def _():
    text = pull('moduleShared')

    s1, s2 = Register('Reg#(Bit#(4))'), Register('Reg#(Bit#(4))')
    out = Node()
    input = Node()
    fifo = Module('FIFO', [s1, s2, Wire(input, s1.input), Wire(s1.value, s2.input), Wire(s2.value, out)], {'in': input}, {'out': out})

    output = synth.parseAndSynth(text, 'FIFO')
    expected = fifo
    assert expected.match(output), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    count = Register('Reg#(Bit#(4))')
    mux = Mux([Node(), Node()])
    add = Function('+', [], [Node(), Node()])
    enable = Node()
    one = Function('1', [], [])
    counter = Module('FourBitCounter', [count, mux, add, one, Wire(enable, mux.control), Wire(add.output, mux.inputs[0]), Wire(count.value, mux.inputs[1]), Wire(mux.output, count.input), Wire(count.value, add.inputs[0]), Wire(one.output, add.inputs[1])], {'enable': enable}, {})

    sumCount = Register('Reg#(Bit#(4))')
    getCount = Node()
    sumAdd = Function('+', [], [Node(), Node()])
    sum = Module('Sum', [sumCount, sumAdd, Wire(sumCount.value, getCount), Wire(sumAdd.output, sumCount.input), Wire(sumCount.value, sumAdd.inputs[0]), Wire(out, sumAdd.inputs[1])], {}, {'getCount': getCount})

    topEnable = Node()
    topGetCount = Node()
    top = Module('TopLevel', [fifo, counter, sum, Wire(count.value, input), Wire(topEnable, enable), Wire(getCount, topGetCount)], {'enable': topEnable}, {'getCount': topGetCount})

    output = synth.parseAndSynth(text, 'TopLevel')
    expected = top
    assert expected.match(output), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"
  

#run all the tests
import time
import sys
import traceback
categoryName = ""
numTestsFailed = 0
numTestsPassed = 0
numTestsSkipped = 0
failedTests = []  # Array[(category: 'str', name: 'str', error: 'str')]
testingTimeStart = time.time()
for i in range(len(tests)):
    if tests[i].__class__ == str: #we have the name of a category of tests
        categoryName = tests[i]
        print()
        print("  " + categoryName)
    else:  # we have a testName/test/skipped trio
        testName, it, skipped = tests[i]
        if skipped:
            print("    -", testName)
            numTestsSkipped += 1
            continue
        try:
            _t = time.time()
            it()
            msElapsed = (time.time() - _t)*1000
            if msElapsed > 30:
                print("    √", testName, "(" + str(int(msElapsed)) + "ms)")
            else:
                print("    √", testName)
            numTestsPassed += 1
        except:
            msElapsed = (time.time() - _t)*1000
            numTestsFailed += 1
            if msElapsed > 30:
                print("    " + str(numTestsFailed) + ")", testName, "(" + str(int(msElapsed)) + "ms)")
            else:
                print("    " + str(numTestsFailed) + ")", testName)

            # hold on to the error for report at the end of testing
            errorReport = ""
            errorReport += "Traceback (most recent call last):"

            # see third answer of https://stackoverflow.com/questions/4690600/python-exception-message-capturing
            ex_type, ex_value, ex_traceback = sys.exc_info()
            # Extract unformatter stack traces as tuples
            trace_back = traceback.extract_tb(ex_traceback)
            # Format stacktrace
            stackTraceLines = list()
            for trace in trace_back:
                stackTraceLines.append("File \"%s\", line %d, in %s" % (trace[0], trace[1], trace[2]))
                stackTraceLines.append("  " + trace[3])
            for line in stackTraceLines:
                errorReport += "\n  " + line
            errorName, errorMessage = ex_type.__name__, ex_value
            errorReport += "\n" + errorName + ": " + str(errorMessage)
            
            failedTests.append((categoryName, testName, errorReport))

msElapsedTotal = (time.time() - testingTimeStart)*1000
print()
print("  " + str(numTestsPassed), "passing", "(" + str(int(msElapsedTotal)) + "ms)")
if numTestsFailed > 0:
    print("  " + str(numTestsFailed), "failing")
if numTestsSkipped > 0:
    print("  " + str(numTestsSkipped), "pending")
print()

#report details of failing tests (if any)
for i in range(len(failedTests)):
    failedTest = failedTests[i]
    categoryName, testName, errorMessage = failedTest
    print("  " + str(i+1) + ")", categoryName)
    print("      " + testName + ":")
    print()
    print(errorMessage)
    print()

