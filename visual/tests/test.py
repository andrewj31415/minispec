
'''
This file tests that the minispec interpreter in synth.py correctly interprets minispec
code to the hardware representation in hardware.py.

To run the tests, call `python3 test.py`.

To perform coverage testing, first install coverage with `pip install coverage`. Then
run `coverage run test.py` and `coverage html`, which generates an html webpage
which may be accessed from htmlcov/index.html.
'''

# needed to import synth.py and hardware.py since they are in a different folder
import os, sys  # see https://stackoverflow.com/questions/16780014/import-file-from-parent-directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware import *
import synth

import pathlib
def pull(name: 'str') -> 'str':
    ''' reads the text of the given file and returns it '''
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

def compare(output: 'Component', expected: 'Component'):
    ''' Prints a comparison of two pieces of hardware. Helpful for debugging. '''
    print()
    # print(output.__repr__())
    print('output')
    for child in output._children:
        print(child.__repr__())
    for wire in output.getAllWires():
        print(wire.__repr__())
    print(len(output._children), len(output.getAllWires()))
    print()
    # print(expected.__repr__())
    print('expected')
    for child in expected._children:
        print(child.__repr__())
    for wire in expected.getAllWires():
        print(wire.__repr__())
    print(len(expected._children), len(expected.getAllWires()))
    print()

describe("Function Calls")

@it('''A simple function wrapping an xor''')
def _():
    text = pull('function')
    output = synth.parseAndSynth(text, 'f')
    fa, fb, fo = Node('fa'), Node('fb'), Node('fo')
    xfa, xfb, xfo = Node('xfa'), Node('xfb'), Node('xfo')
    expected = Function("f", [fa, fb], fo, {Function("^", [xfa, xfb], xfo)})
    Wire(fa, xfa)
    Wire(fb, xfb)
    Wire(xfo, fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''One function calling another for a three-way xor''')
def _():
    text = pull('functions')
    output = synth.parseAndSynth(text, 'g')
    ga, gb, gc, go = Node('ga'), Node('gb'), Node('gc'), Node('go')
    fa, fb, fo = Node('fa'), Node('fb'), Node('fo')
    xfa, xfb, xfo = Node('xfa'), Node('xfb'), Node('xfo')
    xga, xgb, xgo = Node('xga'), Node('xgb'), Node('xgo')
    expected = Function("g", [ga, gb, gc], go, {Function("f", [fa, fb], fo, {Function("^", [xfa, xfb], xfo)}),
                                                Function("^", [xga, xgb], xgo)})
    Wire(fa, xfa), Wire(fb, xfb), Wire(xfo, fo)
    Wire(ga, xga),  Wire(gb, xgb), Wire(xgo, fa)
    Wire(gc, fb), Wire(fo, go)
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
    expected = Function('f#(2,2)', [fa, fb], fo, {Function('+', [inner1, inner2], innerOut)})
    Wire(fa, inner1), Wire(fb, inner2), Wire(innerOut, fo)
    output = synth.parseAndSynth(text, 'f#(2,2)') #the original f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Function should correctly take parameter''')
def _():
    text = pull('params1')
    fa, fb, fo = Node(), Node(), Node()
    expected = Function('f#(1)', [fa, fb], fo)
    Wire(fa, fo)
    output = synth.parseAndSynth(text, 'f#(1)') #the second f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Function should correctly partially specialize''')
def _():
    text = pull('params1')
    fa, fb, fo = Node(), Node(), Node()
    expected = Function('f#(2,1)', [fa, fb], fo)
    Wire(fb, fo)
    output = synth.parseAndSynth(text, 'f#(2,1)') #the third f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Function should correctly fully specialize''')
def _():
    text = pull('params1')
    fa, fb, fo = Node(), Node(), Node()
    inner1, inner2, innerOut = Node(), Node(), Node()
    expected = Function('f#(1,1)', [fa, fb], fo, {Function('f', [inner1, inner2], innerOut)})
    Wire(inner1, innerOut), Wire(fa, inner2), Wire(fb, inner1), Wire(innerOut, fo)
    output = synth.parseAndSynth(text, 'f#(1,1)') #the fourth f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Function should be correctly processed''')
def _():
    text = pull('params1')
    fa, fb, fo = Node(), Node(), Node()
    expected = Function('f', [fa, fb], fo)
    Wire(fa, fo)
    output = synth.parseAndSynth(text, 'f') #the fifth f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly computes fixed param''')
def _():
    text = pull('params2')
    fa, fb, fo = Node(), Node(), Node()
    expected = Function('f#(10,0)', [fa, fb], fo)
    Wire(fa, fo)
    output = synth.parseAndSynth(text, 'f#(10,0)') #the second f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly computes fixed param from constants''')
def _():
    text = pull('params2')
    fa, fb, fo = Node(), Node(), Node()
    expected = Function('f#(1,7)', [fa, fb], fo)
    Wire(fb, fo)
    output = synth.parseAndSynth(text, 'f#(1,7)') #the third f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly prefers more specialized parameters''')
def _():
    text = pull('params3')
    fa, fb, fo = Node(), Node(), Node()
    inner1, inner2, innerOut = Node(), Node(), Node()
    expected = Function('f#(2,2)', [fa, fb], fo, {Function('*', [inner1, inner2], innerOut)})
    Wire(fa, inner1), Wire(fb, inner2), Wire(innerOut, fo)
    output = synth.parseAndSynth(text, 'f#(2, 2)')
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly prefers earlier of equally specialized parameters''')
def _():
    text = pull('params3')
    fa, fb, fo = Node(), Node(), Node()
    inner1, inner2, innerOut = Node(), Node(), Node()
    expected = Function('f#(1,1)', [fa, fb], fo, {Function('+', [inner1, inner2], innerOut)})
    Wire(fa, inner1), Wire(fb, inner2), Wire(innerOut, fo)
    output = synth.parseAndSynth(text, 'f#(1, 1)')
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"


describe('Literal Arithmetic')

@it('''Correctly folds some simple constants''')
def _():
    text = pull('literals1')

    fa, fo, ga, go = Node('fa'), Node('fo'), Node('ga'), Node('go')
    xor1, xor2, xoro = Node('xor1'), Node('xor2'), Node('xoro')
    mulf1, mulf2, mulfo = Node('mulf1'), Node('mulf2'), Node('mulfo')
    mulg1, mulg2, mulgo = Node('mulg1'), Node('mul2'), Node('mulo')
    add1, add2, addo = Node('add1'), Node('add2'), Node('addo')
    eq1, eq2, eqo = Node('eq1'), Node('eq2'), Node('eqo')
    five, six, seven, thirteen = Constant(Integer(5)), Constant(Integer(6)), Constant(Integer(7)), Constant(Integer(13))
    mulg = Function('*', [mulg1, mulg2], mulgo)
    add = Function('+', [add1, add2], addo)
    g = Function('g#(15)', [ga], go, {add, mulg, six, thirteen})
    Wire(ga, mulg1), Wire(six.output, mulg2), Wire(mulgo, add2), Wire(thirteen.output, add1), Wire(addo, go)
    
    output = synth.parseAndSynth(text, 'g#(15)')
    expected = g
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    xor = Function('^', [xor1, xor2], xoro)
    eq = Function('==', [eq1, eq2], eqo)
    mulf = Function('*', [mulf1, mulf2], mulfo)
    f = Function('f', [fa], fo, {xor, eq, g, mulf, five, seven})
    Wire(fa, mulf1), Wire(five.output, mulf2), Wire(mulfo, xor1), Wire(fa, ga), Wire(go, xor2), Wire(xoro, eq1), Wire(seven.output, eq2), Wire(eqo, fo)

    output = synth.parseAndSynth(text, 'f')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"


def testn(n):
    def test():
        text = pull('literals2')

        t = Function(f't{n}', [Node()])
        inv = Function('!', [Node()])
        t.addChild(inv)
        Wire(t.inputs[0], inv.inputs[0]), Wire(inv.output, t.output)

        output = synth.parseAndSynth(text, f't{n}')
        expected = t
        assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"
    return test

for n in range(1,5):
    it(f'''Correctly folds all constants {n}''')(testn(n))
    

describe("If and Ternary Statements")

@it('''Correctly synthesizes mux''')
def _():
    text = pull('if1')

    fa, fo = Node(), Node()
    eq = Function("==", [Node(), Node()])
    eq1, eq2 = eq.inputs
    four = Constant(Integer(4))
    two = Constant(Integer(2))
    mux1, mux2, muxc = Node(), Node(), Node()
    mux = Mux([mux1, mux2], muxc)
    f2 = Function("f#(2)", [fa], fo, {eq, four, two, mux})
    Wire(fa, eq1), Wire(four.output, eq2), Wire(eq.output, muxc), Wire(fa, mux1), Wire(two.output, mux2), Wire(mux.output, fo)

    output = synth.parseAndSynth(text, 'f#(2)')
    expected = f2
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly skips other branch''')
def _():
    text = pull('if1')

    fa, fo = Node(), Node()
    one = Constant(Integer(1))
    xor = Function("^", [Node(), Node()])
    xor1, xor2 = xor.inputs
    f0 = Function("f#(0)", [fa], fo, {xor, one})
    Wire(one.output, xor1), Wire(fa, xor2), Wire(xor.output, fo)

    output = synth.parseAndSynth(text, 'f#(0)')
    expected = f0
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles begin/end statement''')
def _():
    text = pull('if2')

    fa, fo = Node(), Node()
    one = Constant(Integer(1))
    three = Constant(Integer(3))
    mux1, mux2, muxc = Node(), Node(), Node()
    mux = Mux([mux1, mux2], muxc)
    f = Function("f", [fa], fo, {mux, one, three})
    Wire(fa, muxc), Wire(one.output, mux1), Wire(three.output, mux2), Wire(mux.output, fo)

    output = synth.parseAndSynth(text, 'f')
    garbageCollection1(output)
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles ternary ? operator''')
def _():
    text = pull('if3')

    fsel, fa, fb, fo = Node(), Node(), Node(), Node()
    eq1, eq2, eqo = Node(), Node(), Node()
    m1, m2, mc = Node(), Node(), Node()
    zero = Constant(Integer(0))
    eq = Function('==', [eq1, eq2], eqo)
    m = Mux([m1, m2], mc)
    f = Function('multiplexer1', [fsel, fa, fb], fo, {m, zero, eq})
    Wire(fa, m1), Wire(fb, m2), Wire(fsel, eq1), Wire(zero.output, eq2), Wire(eqo, mc), Wire(m.output, fo)

    output = synth.parseAndSynth(text, 'multiplexer1')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles variable declared locally in begin/end block''')
def _():
    text = pull('if4')

    k = 8

    fin, fo = Node(), Node()

    mux = Mux([Node(), Node()])
    eq = Function('==', [Node(), Node()])
    cOne, sZero = Constant(Integer(1)), Constant(Integer(0))
    lowBit = Function('[0]', [Node()])
    inv = Constant(Maybe(Any)())
    val = Function('Valid', [Node()])
    sftComps = []
    for i in range(1,k):
        sftComps.append(Function(f'[{i}]', [Node()])) # from input
    for i in range(k-1):
        sftComps.append(Function(f'[{i}]', [Node(), Node()])) # collect output

    computeHalf = Function('computeHalf#(' + str(k) + ')', [fin], fo, set([mux, eq, cOne, sZero, lowBit, inv, val] + sftComps))

    Wire(sZero.output, sftComps[k-1].inputs[0]), Wire(sftComps[2*k-3].output, val.inputs[0])
    for i in range(0,k-1):
        Wire(fin, sftComps[i].inputs[0])
        Wire(sftComps[i].output, sftComps[i+k-1].inputs[1])
    for i in range(0,k-2):
        Wire(sftComps[i+k-1].output, sftComps[i+k].inputs[0])
    Wire(val.output, mux.inputs[1]), Wire(inv.output, mux.inputs[0]), Wire(mux.output, fo), Wire(lowBit.output, eq.inputs[0]), Wire(cOne.output, eq.inputs[1]), Wire(eq.output, mux.control), Wire(fin, lowBit.inputs[0])
    
    output = synth.parseAndSynth(text, 'computeHalf#(' + str(k) + ')')
    expected = computeHalf
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles multiple return statements''')
def _():
    text = pull('returns')

    five = Constant(Integer(5))
    eq = Function('==', [Node(), Node()])
    m = Mux([Node(), Node()])
    one, zero = Constant(Integer(1)), Constant(Integer(0))
    i, o = Node(), Node()
    p = Function('password', [i], o, {eq, five, m, one, zero})
    Wire(i, eq.inputs[0]), Wire(five.output, eq.inputs[1]), Wire(eq.output, m.control), Wire(m.output, o), Wire(one.output, m.inputs[0]), Wire(zero.output, m.inputs[1])

    output = synth.parseAndSynth(text, 'password')
    expected = p
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"


describe('''Case Statements''')

@it('''Correctly handles constant-folded case statement''')
def _():
    text = pull('cases1')

    fa0, fo0 = Node(), Node()
    f0 = Function('addFib#(0,4)', [fa0], fo0)
    Wire(fa0, fo0)

    output = synth.parseAndSynth(text, 'addFib#(0, 4)')
    expected = f0
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    fa1, fo1 = Node(), Node()
    add = Function('+', [Node(), Node()])
    one = Constant(Integer(1))
    f1 = Function('addFib#(1,4)', [fa1], fo1, {add, one})
    Wire(fa1, add.inputs[0]), Wire(one.output, add.inputs[1]), Wire(add.output, fo1)

    output = synth.parseAndSynth(text, 'addFib#(1, 4)')
    expected = f1
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    fa2, fo2 = Node(), Node()
    add2 = Function('+', [Node(), Node()])
    zero = Constant(Integer(0))
    f2 = Function('addFib#(2,4)', [fa2], fo2, {f0, f1, add2, zero})
    Wire(fa2, f1.inputs[0]), Wire(f1.output, add2.inputs[0]), Wire(zero.output, f0.inputs[0]), Wire(f0.output, add2.inputs[1]), Wire(add2.output, fo2)

    output = synth.parseAndSynth(text, 'addFib#(2, 4)')
    expected = f2
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    fa13, fo13 = Node(), Node()
    add13 = Function('+', [Node(), Node()])
    one13 = Constant(Integer(1))
    f13 = Function('addFib#(1,4)', [fa13], fo13, {add13, one13})
    Wire(fa13, add13.inputs[0]), Wire(one13.output, add13.inputs[1]), Wire(add13.output, fo13)

    fa3, fo3 = Node(), Node()
    add3 = Function('+', [Node(), Node()])
    zero3 = Constant(Integer(0))
    f3 = Function('addFib#(3,4)', [fa3], fo3, {f2, f13, add3, zero3})
    Wire(fa3, f2.inputs[0]), Wire(f2.output, add3.inputs[0]), Wire(zero3.output, f13.inputs[0]), Wire(f13.output, add3.inputs[1]), Wire(add3.output, fo3)

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
    add, sub, mul = Function('+', [Node(), Node()] ), Function('-', [Node(), Node()] ), Function('*', [Node(), Node()] )
    mux = Mux([Node(), Node(), Node()])
    f = Function('f#(4)', [fa, fb, fop], fo, {add, sub, mul, mux})
    Wire(mux.output, fo), Wire(fa, add.inputs[0]), Wire(fb, add.inputs[1]), Wire(fa, sub.inputs[0]), Wire(fb, sub.inputs[1])
    Wire(fa, mul.inputs[0]), Wire(fb, mul.inputs[1]), Wire(add.output, mux.inputs[0]), Wire(sub.output, mux.inputs[1]), Wire(mul.output, mux.inputs[2]), Wire(fop, mux.control)

    output = synth.parseAndSynth(text, 'f#(4)')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Handles case statements with default present or not''')
def _():
    text = pull('cases4')

    fa, fflip, fo = Node(), Node(), Node()
    mux = Mux([Node(), Node()])
    n = Function('~', [Node()])
    f = Function('f', [fa, fflip], fo, {mux, n})
    Wire(fflip, mux.control), Wire(mux.output, fo), Wire(fa, n.inputs[0]), Wire(n.output, mux.inputs[0]), Wire(fa, mux.inputs[1])

    output = synth.parseAndSynth(text, 'f')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    fa, fflip, fo = Node(), Node(), Node()
    mux = Mux([Node(), Node()])
    n = Function('~', [Node()])
    g = Function('g', [fa, fflip], fo, {mux, n})
    Wire(fflip, mux.control), Wire(mux.output, fo), Wire(fa, n.inputs[0]), Wire(n.output, mux.inputs[0]), Wire(fa, mux.inputs[1])

    output = synth.parseAndSynth(text, 'g')
    expected = g
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"
    
    fa, fflip, fo = Node(), Node(), Node()
    mux = Mux([Node(), Node()])
    n = Function('~', [Node()])
    h = Function('h', [fa, fflip], fo, {mux, n})
    Wire(fflip, mux.control), Wire(mux.output, fo), Wire(fa, n.inputs[0]), Wire(n.output, mux.inputs[0]), Wire(fa, mux.inputs[1])

    output = synth.parseAndSynth(text, 'h')
    expected = h
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"


describe('''Case Expressions''')

@it('''Correctly handles some case expressions 1''')
def _():
    text = pull('caseExpr1')

    fa, fb, fc, fd, fe, fo = Node(), Node(), Node(), Node(), Node(), Node()
    zeroA, oneA, twoA, threeA, threeA1 = Constant(Integer(0)), Constant(Integer(1)), Constant(Integer(2)), Constant(Integer(3)), Constant(Integer(3))
    muxA = Mux([Node(), Node(), Node(), Node(), Node()])
    f1 = Function('f1', [fa, fb, fc, fd, fe], fo, {zeroA, oneA, twoA, threeA, threeA1, muxA})
    Wire(zeroA.output, muxA.inputs[0]), Wire(twoA.output, muxA.inputs[1])
    Wire(threeA.output, muxA.inputs[2]), Wire(threeA1.output, muxA.inputs[3])
    Wire(oneA.output, muxA.inputs[4]), Wire(fa, muxA.control), Wire(muxA.output, fo)

    output = synth.parseAndSynth(text, 'f1')
    expected = f1
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles some case expressions 2''')
def _():
    text = pull('caseExpr1')
    fa, fb, fc, fd, fe, fo = Node(), Node(), Node(), Node(), Node(), Node()
    zeroY, oneY, twoY = Constant(Integer(0)), Constant(Integer(1)), Constant(Integer(2))
    nb, nc = Function('~', [Node()]), Function('~', [Node()])
    myb, myc = Mux([Node(), Node()]), Mux([Node(), Node()])
    f2 = Function('f2', [fa, fb, fc, fd, fe], fo, {zeroY, oneY, twoY, nb, nc, myb, myc})
    Wire(fb, nb.inputs[0]), Wire(fc, nc.inputs[0])
    Wire(nb.output, myb.control), Wire(nc.output, myc.control)
    Wire(myb.output, fo), Wire(zeroY.output, myb.inputs[0])
    Wire(myc.output, myb.inputs[1])
    Wire(oneY.output, myc.inputs[0]), Wire(twoY.output, myc.inputs[1])

    output = synth.parseAndSynth(text, 'f2')
    expected = f2
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles some case expressions 3''')
def _():
    text = pull('caseExpr1')
    fa, fb, fc, fd, fe, fo = Node(), Node(), Node(), Node(), Node(), Node()
    zeroZ, oneZ, twoZ = Constant(Integer(0)), Constant(Integer(1)), Constant(Integer(2))
    eqb, eqc = Function('==', [Node(), Node()]), Function('==', [Node(), Node()])
    mzb, mzc = Mux([Node(), Node()]), Mux([Node(), Node()])
    f3 = Function('f3', [fa, fb, fc, fd, fe], fo, {zeroZ, oneZ, twoZ, eqb, eqc, mzb, mzc})
    Wire(fd, eqb.inputs[0]), Wire(fb, eqb.inputs[1])
    Wire(eqb.output, mzb.control)
    Wire(fd, eqc.inputs[0]), Wire(fc, eqc.inputs[1])
    Wire(eqc.output, mzc.control), Wire(mzb.output, fo)
    Wire(zeroZ.output, mzb.inputs[0]), Wire(mzc.output, mzb.inputs[1])
    Wire(oneZ.output, mzc.inputs[0]), Wire(twoZ.output, mzc.inputs[1])
    
    output = synth.parseAndSynth(text, 'f3')
    expected = f3
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles some case expressions 4''')
def _():
    text = pull('caseExpr1')

    fa, fb, fc, fd, fe, fo = Node(), Node(), Node(), Node(), Node(), Node()
    ne = Function('~', [Node()])
    f4 = Function('f4', [fa, fb, fc, fd, fe], fo, {ne})
    Wire(fe, ne.inputs[0]), Wire(ne.output, fo)

    output = synth.parseAndSynth(text, 'f4')
    garbageCollection1(output)
    expected = f4
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"


describe('''Modules''')

@it('''Correctly handles a simple counter''')
def _():
    text = pull('counters')

    count = Register('Reg#(Bit#(4))')
    mux = Mux([Node(), Node()])
    add = Function('+', [Node(), Node()])
    enable = Node()
    getCount = Node()
    one = Constant(Integer(1))
    counter = Module('FourBitCounter', {'enable': enable}, {'getCount': getCount}, {count, mux, add, one})
    Wire(enable, mux.control), Wire(count.value, getCount), Wire(add.output, mux.inputs[0]), Wire(count.value, mux.inputs[1]), Wire(mux.output, count.input), Wire(count.value, add.inputs[0]), Wire(one.output, add.inputs[1])
    
    output = synth.parseAndSynth(text, 'FourBitCounter')
    expected = counter
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles a more complicated counter''')
def _():
    text = pull('counters')

    ucount = Register('Reg#(Bit#(4))')
    umux = Mux([Node(), Node()])
    uadd = Function('+', [Node(), Node()])
    uenable = Node()
    ugetCount = Node()
    uone = Constant(Integer(1))
    ucounter = Module('FourBitCounter', {'enable': uenable}, {'getCount': ugetCount}, {ucount, umux, uadd, uone})
    Wire(uenable, umux.control), Wire(ucount.value, ugetCount), Wire(uadd.output, umux.inputs[0]), Wire(ucount.value, umux.inputs[1]), Wire(umux.output, ucount.input), Wire(ucount.value, uadd.inputs[0]), Wire(uone.output, uadd.inputs[1])

    lcount = Register('Reg#(Bit#(4))')
    lmux = Mux([Node(), Node()])
    ladd = Function('+', [Node(), Node()])
    lenable = Node()
    lgetCount = Node()
    lone = Constant(Integer(1))
    lcounter = Module('FourBitCounter', {'enable': lenable}, {'getCount': lgetCount}, {lcount, lmux, ladd, lone})
    Wire(lenable, lmux.control), Wire(lcount.value, lgetCount), Wire(ladd.output, lmux.inputs[0]), Wire(lcount.value, lmux.inputs[1]), Wire(lmux.output, lcount.input), Wire(lcount.value, ladd.inputs[0]), Wire(lone.output, ladd.inputs[1])

    concat = Function('{}', [Node(), Node()])
    fifteen = Constant(Integer(15))
    eq = Function('==', [Node(), Node()])
    a = Function('&&', [Node(), Node()])
    enable = Node()
    getCount = Node()
    counter = Module('EightBitCounter', {'enable': enable}, {'getCount': getCount}, {ucounter, lcounter, concat, fifteen, eq, a})
    Wire(lgetCount, eq.inputs[0]), Wire(fifteen.output, eq.inputs[1]), Wire(eq.output, a.inputs[1]), Wire(enable, a.inputs[0]), Wire(enable, lenable), Wire(a.output, uenable), Wire(lgetCount, concat.inputs[1]), Wire(ugetCount, concat.inputs[0]), Wire(concat.output, getCount)

    output = synth.parseAndSynth(text, 'EightBitCounter')
    expected = counter
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles recursive parametric counter''')
def _():
    text = pull('counters')

    upper1, lower1 = [ synth.parseAndSynth(text, 'Counter#(0)') for i in range(2) ]

    enable1, getCount1 = Node(), Node()
    and1, eq1, concat1, one1 = Function('&&', [Node(), Node()]), Function('==', [Node(), Node()]), Function('{}', [Node(), Node()]), Constant(Integer(1))
    counter1 = Module('Counter#(1)', {'enable': enable1}, {'getCount': getCount1}, {and1, eq1, concat1, one1, upper1, lower1})
    Wire(enable1, lower1.inputs['enable']), Wire(lower1.methods['getCount'], eq1.inputs[0]), Wire(one1.output, eq1.inputs[1]), Wire(eq1.output, and1.inputs[1]), Wire(enable1, and1.inputs[0]), Wire(and1.output, upper1.inputs['enable']), Wire(upper1.methods['getCount'], concat1.inputs[0]), Wire(lower1.methods['getCount'], concat1.inputs[1]), Wire(concat1.output, getCount1)

    output = synth.parseAndSynth(text, 'Counter#(1)')
    expected = counter1
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles larger recursive parametric counter''')
def _():
    text = pull('counters')

    upper1, lower1, upper2, lower2 = [ synth.parseAndSynth(text, 'Counter#(0)') for i in range(4)]

    enable1, getCount1 = Node(), Node()
    and1, eq1, concat1, one1 = Function('&&', [Node(), Node()]), Function('==', [Node(), Node()]), Function('{}', [Node(), Node()]), Constant(Integer(1))
    lower3 = Module('Counter#(1)', {'enable': enable1}, {'getCount': getCount1}, {lower1, upper1, and1, eq1, concat1, one1})
    Wire(enable1, lower1.inputs['enable']), Wire(lower1.methods['getCount'], eq1.inputs[0]), Wire(one1.output, eq1.inputs[1]), Wire(eq1.output, and1.inputs[1]), Wire(enable1, and1.inputs[0]), Wire(and1.output, upper1.inputs['enable']), Wire(upper1.methods['getCount'], concat1.inputs[0]), Wire(lower1.methods['getCount'], concat1.inputs[1]), Wire(concat1.output, getCount1)

    enable2, getCount2 = Node(), Node()
    and2, eq2, concat2, one2 = Function('&&', [Node(), Node()]), Function('==', [Node(), Node()]), Function('{}', [Node(), Node()]), Constant(Integer(1))
    upper3 = Module('Counter#(1)', {'enable': enable2}, {'getCount': getCount2}, {lower2, upper2, and2, eq2, concat2, one2})
    Wire(enable2, lower2.inputs['enable']), Wire(lower2.methods['getCount'], eq2.inputs[0]), Wire(one2.output, eq2.inputs[1]), Wire(eq2.output, and2.inputs[1]), Wire(enable2, and2.inputs[0]), Wire(and2.output, upper2.inputs['enable']), Wire(upper2.methods['getCount'], concat2.inputs[0]), Wire(lower2.methods['getCount'], concat2.inputs[1]), Wire(concat2.output, getCount2)

    enable3, getCount3 = Node(), Node()
    and3, eq3, concat3, three = Function('&&', [Node(), Node()]), Function('==', [Node(), Node()]), Function('{}', [Node(), Node()]), Constant(Integer(3))
    counter2 = Module('Counter#(2)', {'enable': enable3}, {'getCount': getCount3}, {lower3, upper3, and3, eq3, concat3, three})
    Wire(enable3, lower3.inputs['enable']), Wire(lower3.methods['getCount'], eq3.inputs[0]), Wire(three.output, eq3.inputs[1]), Wire(eq3.output, and3.inputs[1]), Wire(enable3, and3.inputs[0]), Wire(and3.output, upper3.inputs['enable']), Wire(upper3.methods['getCount'], concat3.inputs[0]), Wire(lower3.methods['getCount'], concat3.inputs[1]), Wire(concat3.output, getCount3)

    output = synth.parseAndSynth(text, 'Counter#(2)')
    expected = counter2
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"


@it('''Handles input with default value''')
def _():
    text = pull('moduleDefault')
    
    storage = Register('Reg#(Bit#(4))')
    mux = Mux([Node(), Node()])
    add = Function('+', [Node(), Node()])
    enable = Node()
    getStorage = Node()
    one = Constant(Integer(1))
    Inner = Module('Inner', {'enable': enable}, {'getStorage': getStorage}, {storage, mux, add, one})
    Wire(enable, mux.control), Wire(storage.value, getStorage), Wire(add.output, mux.inputs[0]), Wire(storage.value, mux.inputs[1]), Wire(mux.output, storage.input), Wire(storage.value, add.inputs[0]), Wire(one.output, add.inputs[1])

    muxO = Mux([Node(), Node()])
    true = Constant(BooleanLiteral(True))
    false = Constant(BooleanLiteral(False))
    enableO = Node()
    getStorageO = Node()
    Outer = Module('Outer', {'enable': enableO}, {'getStorage': getStorageO}, {Inner, true, false, muxO})
    Wire(true.output, muxO.inputs[0]), Wire(false.output, muxO.inputs[1]), Wire(enableO, muxO.control), Wire(muxO.output, Inner.inputs['enable']), Wire(Inner.methods['getStorage'], getStorageO)

    output = synth.parseAndSynth(text, 'Outer')
    expected = Outer
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

describe('''Bit Manipulation''')

@it('''Correctly modifies and collects bits''')
def _():
    text = pull('bits1')

    fa, fo = Node(), Node()
    n1, n2, zero, one, concat = Function('~', [Node()]), Function('~', [Node()]), Function('[0]', [Node()]), Function('[1]', [Node()]), Function('{}', [Node(), Node()])
    f = Function('f', [fa], fo, {n1, n2, zero, one, concat})
    Wire(fa, zero.inputs[0]), Wire(fa, one.inputs[0]), Wire(zero.output, n1.inputs[0]), Wire(one.output, n2.inputs[0]), Wire(n1.output, concat.inputs[0]), Wire(n2.output, concat.inputs[1]), Wire(concat.output, fo)

    output = synth.parseAndSynth(text, 'f')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"
    
    ga, go = Node(), Node()
    n1, n2, zero, one, concat = Function('~', [Node()]), Function('~', [Node()]), Function('[0]', [Node()]), Function('[1]', [Node()]), Function('{}', [Node(), Node()])
    g = Function('g', [ga], go, {n1, n2, zero, one, concat})
    Wire(ga, zero.inputs[0]), Wire(ga, one.inputs[0]), Wire(zero.output, n1.inputs[0]), Wire(one.output, n2.inputs[0]), Wire(n1.output, concat.inputs[1]), Wire(n2.output, concat.inputs[0]), Wire(concat.output, go)

    output = synth.parseAndSynth(text, 'g')
    expected = g
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly modifies specific bits''')
def _():
    text = pull('bits2')

    twoone, two1, zero1 = Function('[2][1]', [Node(), Node()]), Function('[2]', [Node()]), Function('[0]', [Node()])
    n = Function('~', [Node()])
    zero2, one2 = Function('[0]', [Node()]), Function('[1]', [Node()])
    one3, zero3 = Function('[1]', [Node(), Node()]), Function('[0]', [Node(), Node()])
    fa, fo = Node(), Node()
    f = Function('f', [fa], fo, {twoone, two1, zero1, n, zero2, one2, one3, zero3})
    Wire(fa, two1.inputs[0]), Wire(two1.output, zero1.inputs[0]), Wire(zero1.output, n.inputs[0]), Wire(n.output, twoone.inputs[1]), Wire(fa, twoone.inputs[0]), Wire(twoone.output, zero2.inputs[0]), Wire(twoone.output, one2.inputs[0]), Wire(twoone.output, one3.inputs[0]), Wire(zero2.output, one3.inputs[1]), Wire(one3.output, zero3.inputs[0]), Wire(one2.output, zero3.inputs[1]), Wire(zero3.output, fo)

    output = synth.parseAndSynth(text, 'f')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly handles variable indices and slice assignment''')
def _():
    text = pull('bits3')

    fa, fi, fj, fk, fo = Node(), Node(), Node(), Node(), Node()
    s1 = Function('[1][_:_][_]', [Node(), Node(), Node(), Node(), Node()])
    s21 = Function('[_]', [Node(), Node()])
    s22 = Function('[_:2]', [Node(), Node()])
    s23 = Function('[0]', [Node()])
    n = Function('~', [Node()])
    s3 = Function('[2][3:1]', [Node(), Node()])
    six = Constant(Integer(6))
    f = Function('f', [fa, fi, fj, fk], fo, {s1, s21, s22, s23, n, s3, six})
    Wire(fa, s21.inputs[0]), Wire(s21.output, s22.inputs[0]), Wire(s22.output, s23.inputs[0]), Wire(fk, s21.inputs[1]), Wire(fj, s22.inputs[1]), Wire(s23.output, n.inputs[0]), Wire(n.output, s1.inputs[4]), Wire(fa, s1.inputs[0]), Wire(fi, s1.inputs[1]), Wire(fj, s1.inputs[2]), Wire(fk, s1.inputs[3]), Wire(s1.output, s3.inputs[0]), Wire(six.output, s3.inputs[1]), Wire(s3.output, fo)
    
    output = synth.parseAndSynth(text, 'f')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

describe('''For Loops''')

@it('''Correctly handles for loop''')
def _():
    text = pull('for')

    zero, one, two, three = Function('[0]', [Node()]), Function('[1]', [Node()]), Function('[2]', [Node()]), Function('[3]', [Node()])
    output = Constant(Integer(0))
    xor0, xor1, xor2, xor3 = Function('^', [Node(), Node()]), Function('^', [Node(), Node()]), Function('^', [Node(), Node()]), Function('^', [Node(), Node()])
    fa, fo = Node(), Node()
    f = Function('parity#(4)', [fa], fo, {zero, one, two, three, output, xor0, xor1, xor2, xor3})
    Wire(fa, zero.inputs[0]), Wire(fa, one.inputs[0]), Wire(fa, two.inputs[0]), Wire(fa, three.inputs[0])
    Wire(output.output, xor0.inputs[0]), Wire(xor0.output, xor1.inputs[0]), Wire(xor1.output, xor2.inputs[0]), Wire(xor2.output, xor3.inputs[0]), Wire(xor3.output, fo)
    Wire(zero.output, xor0.inputs[1]), Wire(one.output, xor1.inputs[1]), Wire(two.output, xor2.inputs[1]), Wire(three.output, xor3.inputs[1])

    output = synth.parseAndSynth(text, 'parity#(4)')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

describe('''Types''')

@it('''Handles typedef synonyms''')
def _():
    text = pull('synonym')

    n1, n2, n3 = Function('~', [Node()]), Function('~', [Node()]), Function('~', [Node()])
    fa, fo = Node(), Node()
    f = Function('f', [fa], fo, {n1, n2, n3})
    Wire(fa, n1.inputs[0]), Wire(n1.output, n2.inputs[0]), Wire(n2.output, n3.inputs[0]), Wire(n3.output, fo)

    output = synth.parseAndSynth(text, 'f')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

#TODO test synonyms in a module register

@it('''Handles enum types''')
def _():
    text = pull('enum')

    fa, fo = Node(), Node()
    a = Enum('Paper', {'A1', 'A2', 'A3', 'A4'})
    a1, a2, a3, a4 = Constant(a('A1')), Constant(a('A2')), Constant(a('A3')), Constant(a('A4'))
    m1, m2, m3 = Mux([Node(), Node()]), Mux([Node(), Node()]), Mux([Node(), Node()])
    eq1, eq2, eq3 = Function('==', [Node(), Node()]), Function('==', [Node(), Node()]), Function('==', [Node(), Node()])
    ea1, ea2, ea3 = Constant(a('A1')), Constant(a('A2')), Constant(a('A3'))
    permute = Function('permute', [fa], fo, {a1, a2, a3, a4, m1, m2, m3, eq1, eq2, eq3, ea1, ea2, ea3})
    Wire(eq1.output, m1.control), Wire(eq2.output, m2.control), Wire(eq3.output, m3.control)
    Wire(ea1.output, eq1.inputs[1]), Wire(ea2.output, eq2.inputs[1]), Wire(ea3.output, eq3.inputs[1])
    Wire(fa, eq1.inputs[0]), Wire(fa, eq2.inputs[0]), Wire(fa, eq3.inputs[0])
    Wire(m1.output, fo), Wire(m2.output, m1.inputs[1]), Wire(m3.output, m2.inputs[1])
    Wire(a4.output, m3.inputs[0]), Wire(a3.output, m3.inputs[1]), Wire(a1.output, m2.inputs[0]), Wire(a2.output, m1.inputs[0])

    output = synth.parseAndSynth(text, 'permute')
    expected = permute
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

#TODO test enum literals

@it('''Handles struct type literals''')
def _():
    text = pull('struct')

    a, b, o = Node(), Node(), Node()
    # Packet{data:1,index:1}'
    de = Constant(Struct('Packet', {'data': Bit(Integer(32)), 'index': Bit(Integer(16))})({'data': Integer(1), 'index': Integer(1)}))
    c = Function('combine#(1,1,1,1)', [a, b], o, {de})
    Wire(de.output, o)

    output = synth.parseAndSynth(text, 'combine#(1, 1, 1, 1)')
    expected = c
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Handles struct types''')
def _():
    text = pull('struct')

    a, b, o = Node(), Node(), Node()
    inp1, ind = Function('.data', [Node()]), Function('.index', [Node()])
    inp2, inp3 = Function('.data', [Node()]), Function('.data', [Node()])
    inpset = Function('.data', [Node(), Node()])
    r = Function('|', [Node(), Node()])
    pack = Function('Packet{}', [Node(), Node()])
    c = Function('combine#(1,1,1,2)', [a, b], o, {inp1, ind, inp2, inp3, inpset, r, pack})
    Wire(a, inp1.inputs[0]), Wire(b, ind.inputs[0]), Wire(inp1.output, pack.inputs[0]), Wire(ind.output, pack.inputs[1])
    Wire(pack.output, inpset.inputs[0]), Wire(pack.output, inp2.inputs[0]), Wire(b, inp3.inputs[0]), Wire(inp2.output, r.inputs[0]), Wire(inp3.output, r.inputs[1]), Wire(r.output, inpset.inputs[1]), Wire(inpset.output, o)

    output = synth.parseAndSynth(text, 'combine#(1, 1, 1, 2)')
    expected = c
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Handles parameterized typedef synonyms''')
def _():
    text = pull('paramTypedefs1')

    fv, fo = Node(), Node()
    gEv, gEo = Node(), Node()
    s = Function('[1]', [Node()])
    gE = Function('getEntry#(Bool,2,1)', [gEv], gEo, {s})
    Wire(gEv, s.inputs[0]), Wire(s.output, gEo)
    f = Function('f', [fv], fo, {gE})
    Wire(fv, gE.inputs[0]), Wire(gE.output, fo)

    output = synth.parseAndSynth(text, 'f')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Handles parameterized typedef structs''')
def _():
    text = pull('paramTypedefs2')

    sv, so = Node(), Node()
    gl3 = synth.parseAndSynth(text, 'getList#(3, Bit#(3))')  #TODO elaborate these expected items
    sb3 = synth.parseAndSynth(text, 'sumBitList#(3,3)')
    sumVec = Function('sumVector#(3,3)', [sv], so, {gl3, sb3})
    Wire(sv, gl3.inputs[0]), Wire(gl3.output, sb3.inputs[0]), Wire(sb3.output, so)

    output = synth.parseAndSynth(text, 'sumVector#(3,3)')
    expected = sumVec
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"


describe('''Maybe Types''')

@it('''Handles maybe input to module''')
def _():
    text = pull('maybe')

    reg = Register('Reg#(Bit#(8))')
    setCount, getCount = Node(), Node()
    fm = Function('fromMaybe', [Node(), Node()]);
    u, one = Constant(DontCareLiteral()), Constant(Integer(1))
    mux = Mux([Node(), Node()])
    add = Function('+', [Node(), Node()])
    isv = Function('isValid', [Node()])
    m = Module('SettableCounter', {'setCount': setCount}, {'getCount': getCount}, {reg, fm, u, one, mux, add, isv})
    Wire(setCount, isv.inputs[0]), Wire(isv.output, mux.control)
    Wire(setCount, fm.inputs[1]), Wire(u.output, fm.inputs[0]), Wire(fm.output, mux.inputs[0])
    Wire(reg.value, add.inputs[0]), Wire(one.output, add.inputs[1]), Wire(add.output, mux.inputs[1])
    Wire(mux.output, reg.input), Wire(reg.value, getCount)

    output = synth.parseAndSynth(text, 'SettableCounter')
    expected = m
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"
  

describe('''Advanced Modules''')

@it('''Correctly handles vectors of submodules''')
def _():
    text = pull('moduleVector')

    r00, r01, r10, r11 = Register('Reg#(Bit#(1))'), Register('Reg#(Bit#(1))'), Register('Reg#(Bit#(1))'), Register('Reg#(Bit#(1))')
    v0, v1 = VectorModule([r00, r01], "Vector#(2,Reg#(Bit#(1)))", {}, {}, {r00, r01}), VectorModule([r10, r11], "Vector#(2,Reg#(Bit#(1)))", {}, {}, {r10, r11})
    v = VectorModule([v0, v1], "Vector#(2,Vector#(2,Reg#(Bit#(1))))", {}, {}, {v0, v1})
    n0, n1, n2, n3 = Function('~', [Node()]), Function('~', [Node()]), Function('~', [Node()]), Function('~', [Node()])
    s0, s1, s2, s3 = Function('[0]', [Node()]), Function('[1]', [Node()]), Function('[2]', [Node()]), Function('[3]', [Node()])
    c = Function('{}', [Node(), Node(), Node(), Node()])
    i, o = Node(), Node()
    rev = Module('Reverse#(1)', {'in': i}, {'out': o}, {v, n0, n1, n2, n3, s0, s1, s2, s3, c})
    Wire(i, s0.inputs[0]), Wire(i, s1.inputs[0]), Wire(i, s2.inputs[0]), Wire(i, s3.inputs[0])
    Wire(s0.output, n0.inputs[0]), Wire(s1.output, n1.inputs[0]), Wire(s2.output, n2.inputs[0]), Wire(s3.output, n3.inputs[0])
    Wire(n0.output, r00.input), Wire(n1.output, r01.input), Wire(n2.output, r10.input), Wire(n3.output, r11.input)
    Wire(r00.value, c.inputs[0]), Wire(r01.value, c.inputs[1]), Wire(r10.value, c.inputs[2]), Wire(r11.value, c.inputs[3])
    Wire(c.output, o)

    output = synth.parseAndSynth(text, 'Reverse#(1)')
    expected = rev
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    revs = []
    for i in range(4):
        r00, r01, r10, r11 = Register('Reg#(Bit#(1))'), Register('Reg#(Bit#(1))'), Register('Reg#(Bit#(1))'), Register('Reg#(Bit#(1))')
        v0, v1 = VectorModule([r00, r01], "Vector#(2,Reg#(Bit#(1)))", {}, {}, {r00, r01}), VectorModule([r10, r11], "Vector#(2,Reg#(Bit#(1)))", {}, {}, {r10, r11})
        v = VectorModule([v0, v1], "Vector#(2,Vector#(2,Reg#(Bit#(1))))", {}, {}, {v0, v1})
        n0, n1, n2, n3 = Function('~', [Node()]), Function('~', [Node()]), Function('~', [Node()]), Function('~', [Node()])
        s0, s1, s2, s3 = Function('[0]', [Node()]), Function('[1]', [Node()]), Function('[2]', [Node()]), Function('[3]', [Node()])
        c = Function('{}', [Node(), Node(), Node(), Node()])
        i, o = Node(), Node()
        rev = Module('Reverse#(1)', {'in': i}, {'out': o}, {v, n0, n1, n2, n3, s0, s1, s2, s3, c})
        Wire(i, s0.inputs[0]), Wire(i, s1.inputs[0]), Wire(i, s2.inputs[0]), Wire(i, s3.inputs[0])
        Wire(s0.output, n0.inputs[0]), Wire(s1.output, n1.inputs[0]), Wire(s2.output, n2.inputs[0]), Wire(s3.output, n3.inputs[0])
        Wire(n0.output, r00.input), Wire(n1.output, r01.input), Wire(n2.output, r10.input), Wire(n3.output, r11.input)
        Wire(r00.value, c.inputs[0]), Wire(r01.value, c.inputs[1]), Wire(r10.value, c.inputs[2]), Wire(r11.value, c.inputs[3])
        Wire(c.output, o)
        revs.append(rev)

    r00, r01, r10, r11 = revs
    v0, v1 = VectorModule([r00, r01], "Vector#(2,Reverse#(1))", {}, {}, {r00, r01}), VectorModule([r10, r11], "Vector#(2,Reverse#(1))", {}, {}, {r10, r11})
    v = VectorModule([v0, v1], "Vector#(2,Vector#(2,Reverse#(1)))", {}, {}, {v0, v1})
    s0, s1, s2, s3 = Function('[3:0]', [Node()]), Function('[7:4]', [Node()]), Function('[11:8]', [Node()]), Function('[15:12]', [Node()])
    c = Function('{}', [Node(), Node(), Node(), Node()])
    i, o = Node(), Node()
    rev2 = Module('Reverse#(2)', {'in': i}, {'out': o}, {v, s0, s1, s2, s3, c})
    Wire(i, s0.inputs[0]), Wire(i, s1.inputs[0]), Wire(i, s2.inputs[0]), Wire(i, s3.inputs[0])
    Wire(s0.output, r00.inputs['in']), Wire(s1.output, r01.inputs['in']), Wire(s2.output, r10.inputs['in']), Wire(s3.output, r11.inputs['in'])
    Wire(r00.methods['out'], c.inputs[0]), Wire(r01.methods['out'], c.inputs[1]), Wire(r10.methods['out'], c.inputs[2]), Wire(r11.methods['out'], c.inputs[3])
    Wire(c.output, o)

    output = synth.parseAndSynth(text, 'Reverse#(2)')
    expected = rev2
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Handles shared modules''')
def _():
    text = pull('moduleShared')

    s1, s2 = Register('Reg#(Bit#(4))'), Register('Reg#(Bit#(4))')
    out = Node()
    input = Node()
    fifo = Module('FIFO', {'in': input}, {'out': out}, {s1, s2})
    Wire(input, s1.input), Wire(s1.value, s2.input), Wire(s2.value, out)

    output = synth.parseAndSynth(text, 'FIFO')
    expected = fifo
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    count = Register('Reg#(Bit#(4))')
    mux = Mux([Node(), Node()])
    add = Function('+', [Node(), Node()])
    enable = Node()
    one = Constant(Integer(1))
    counter = Module('FourBitCounter', {'enable': enable}, {}, {count, mux, add, one})
    Wire(enable, mux.control), Wire(add.output, mux.inputs[0])
    Wire(count.value, mux.inputs[1]), Wire(mux.output, count.input)
    Wire(count.value, add.inputs[0]), Wire(one.output, add.inputs[1])

    sumCount = Register('Reg#(Bit#(4))')
    getCount = Node()
    sumAdd = Function('+', [Node(), Node()])
    sum = Module('Sum', {}, {'getCount': getCount}, {sumCount, sumAdd})
    Wire(sumCount.value, getCount), Wire(sumAdd.output, sumCount.input)
    Wire(sumCount.value, sumAdd.inputs[0]), Wire(out, sumAdd.inputs[1])

    topEnable = Node()
    topGetCount = Node()
    top = Module('TopLevel', {'enable': topEnable}, {'getCount': topGetCount}, {fifo, counter, sum})
    Wire(count.value, input), Wire(topEnable, enable), Wire(getCount, topGetCount)

    output = synth.parseAndSynth(text, 'TopLevel')
    expected = top
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"
  
@it('''Handles module methods with arguments''')
def _():
    text = pull('moduleArgument')

    m = Register('Reg#(Vector#(4,Bit#(4)))')
    mData = Node()
    mIndx = Node()
    sliceIndx = Function('[_]', [Node(), Node(), Node()])
    mem = Module('Mem', {'data': mData, 'indx': mIndx}, {}, {m, sliceIndx})
    Wire(sliceIndx.output, m.input)
    Wire(m.value, sliceIndx.inputs[0]), Wire(mIndx, sliceIndx.inputs[1])
    Wire(mData, sliceIndx.inputs[2])

    output = synth.parseAndSynth(text, 'Mem')
    expected = mem
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    s1 = Register('Reg#(Bit#(4))')
    s2 = Register('Reg#(Bit#(4))')
    sl1, sl2 = Node(), Node()
    tData, tIndx = Node(), Node()
    o1, o2 = Node(), Node()
    sInd1 = Function('[_]', [Node(), Node()])
    sInd2 = Function('[_]', [Node(), Node()])
    gd1o, gd2o = Node(), Node()
    gd1i, gd2i = Node(), Node()
    gd1 = Function('getData', [gd1i], gd1o, {sInd1})
    Wire(gd1i, sInd1.inputs[1]), Wire(m.value, sInd1.inputs[0]), Wire(sInd1.output, gd1o)
    gd2 = Function('getData', [gd2i], gd2o, {sInd2})
    Wire(gd2i, sInd2.inputs[1]), Wire(m.value, sInd2.inputs[0]), Wire(sInd2.output, gd2o)
    top = Module('TopLevel', {'selector1': sl1, 'selector2': sl2, 'dataTop': tData, 'indxTop': tIndx}, {'out1': o1, 'out2': o2}, {mem, s1, s2, gd1, gd2})
    Wire(s1.value, o1), Wire(s2.value, o2),
    Wire(sl1, gd1.inputs[0]), Wire(sl2, gd2.inputs[0]),
    Wire(gd1.output, s1.input), Wire(gd2.output, s2.input),
    Wire(tData, mData), Wire(tIndx, mIndx)

    output = synth.parseAndSynth(text, 'TopLevel')
    expected = top
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Handles variable indexing into registers''')
def _():
    text = pull('moduleVectorVarReg')

    output = synth.parseAndSynth(text, 'Regs')

    # nodes and registers
    r = [Register('Reg#(Bit#(4))') for i in range(6)]
    v0 = VectorModule([r[0],r[1],r[2]], 'Vector#(3,Reg#(Bit#(4)))', {}, {}, {r[0],r[1],r[2]})
    v1 = VectorModule([r[3],r[4],r[5]], 'Vector#(3,Reg#(Bit#(4)))', {}, {}, {r[3],r[4],r[5]})
    v = VectorModule([v0,v1], 'Vector#(2,Vector#(3,Reg#(Bit#(4))))', {}, {}, {v0,v1})
    d = Node()
    s1, s2 = Node(), Node()
    o = Node()

    mo, mo1, mo2 = Mux([Node(), Node()]), Mux([Node(), Node(), Node()]), Mux([Node(), Node(), Node()])
    oComp = [mo, mo1, mo2]
    mi1, mi2 = Mux([Node(), Node()]), Mux([Node(), Node()])
    eq1, eq2 = Function('=', [Node(), Node()]), Function('=', [Node(), Node()])
    zero, one = Constant(Integer(0)), Constant(Integer(1))
    iComp = [mi1, mi2, eq1, eq2, zero, one]
    regs = Module('Regs', {'data': d, 'sel1': s1, 'sel2': s2}, {'out': o}, set([v] + oComp + iComp))
    Wire(s2, mo1.control), Wire(s2, mo2.control), Wire(s1, mo.control)
    Wire(mo.output, o), Wire(mo1.output, mo.inputs[0]), Wire(mo2.output, mo.inputs[1])
    for i in (0,1,2):
        Wire(r[i].value, mo1.inputs[i])
        Wire(r[3+i].value, mo2.inputs[i])
    Wire(r[0].value, mi1.inputs[1]), Wire(d, mi1.inputs[0]), Wire(r[3].value, mi2.inputs[1]), Wire(d, mi2.inputs[0])
    Wire(eq1.output, mi1.control), Wire(eq2.output, mi2.control), Wire(mi1.output, r[0].input), Wire(mi2.output, r[3].input)
    Wire(s1, eq1.inputs[0]), Wire(s1, eq2.inputs[0]), Wire(zero.output, eq1.inputs[1]), Wire(one.output, eq2.inputs[1])
    for i in (1,2,4,5):
        Wire(r[i].value, r[i].input)
    
    expected = regs
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Handles variable indexing into submodules''')
def _():
    text = pull('moduleVectorVarSub')

    output = synth.parseAndSynth(text, 'Regs')

    r1, r2 = Register('Reg#(Bit#(4))'), Register('Reg#(Bit#(4))')
    v = VectorModule([r1, r2], 'Vector#(2,Reg#(Bit#(4)))', {}, {}, {r1, r2})
    d, s, gd = Node(), Node(), Node()

    mi1, mi2, mo = Mux([Node(), Node()]), Mux([Node(), Node()]), Mux([Node(), Node()])
    oComp = [mo]
    eq1, eq2 = Function('=', [Node(), Node()]), Function('=', [Node(), Node()])
    zero, one = Constant(Integer(0)), Constant(Integer(1))
    iComp = [mi1, mi2, eq1, eq2, zero, one]
    regs = Module('Regs', {'data': d, 'sel': s}, {'getData': gd}, set([v] + oComp + iComp))
    Wire(r1.value, mo.inputs[0]), Wire(r2.value, mo.inputs[1]), Wire(s, mo.control), Wire(mo.output, gd)
    Wire(d, mi1.inputs[0]), Wire(d, mi2.inputs[0]), Wire(r1.value, mi1.inputs[1]), Wire(r2.value, mi2.inputs[1])
    Wire(mi1.output, r1.input), Wire(mi2.output, r2.input), Wire(eq1.output, mi1.control), Wire(eq2.output, mi2.control)
    Wire(s, eq1.inputs[0]), Wire(s, eq2.inputs[0]), Wire(zero.output, eq1.inputs[1]), Wire(one.output, eq2.inputs[1])

    expected = regs
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"
    output = synth.parseAndSynth(text, 'MoreRegs')

    r = []
    for i in range(2):
        r1, r2 = Register('Reg#(Bit#(4))'), Register('Reg#(Bit#(4))')
        v = VectorModule([r1, r2], 'Vector#(2,Reg#(Bit#(4)))', {}, {}, {r1, r2})
        d, s, gd = Node(), Node(), Node()

        mi1, mi2, mo = Mux([Node(), Node()]), Mux([Node(), Node()]), Mux([Node(), Node()])
        oComp = [mo]
        eq1, eq2 = Function('=', [Node(), Node()]), Function('=', [Node(), Node()])
        zero, one = Constant(Integer(0)), Constant(Integer(1))
        iComp = [mi1, mi2, eq1, eq2, zero, one]
        regs = Module('Regs', {'data': d, 'sel': s}, {'getData': gd}, set([v] + oComp + iComp))
        Wire(r1.value, mo.inputs[0]), Wire(r2.value, mo.inputs[1]), Wire(s, mo.control), Wire(mo.output, gd)
        Wire(d, mi1.inputs[0]), Wire(d, mi2.inputs[0]), Wire(r1.value, mi1.inputs[1]), Wire(r2.value, mi2.inputs[1])
        Wire(mi1.output, r1.input), Wire(mi2.output, r2.input), Wire(eq1.output, mi1.control), Wire(eq2.output, mi2.control)
        Wire(s, eq1.inputs[0]), Wire(s, eq2.inputs[0]), Wire(zero.output, eq1.inputs[1]), Wire(one.output, eq2.inputs[1])
        r.append(regs)
    
    r1, r2 = r
    v = VectorModule(r, 'Vector#(2,Regs)', {}, {}, set(r))
    d, s1, s2, gd = Node(), Node(), Node(), Node()
    two1d, two2d = Constant(Integer(2)), Constant(Integer(2))
    one1s, one2s = Constant(Integer(1)), Constant(Integer(1))
    zero1, zero2, one1, one2 = Constant(Integer(0)), Constant(Integer(0)), Constant(Integer(1)), Constant(Integer(1))
    muxr1s, muxr1d = Mux([Node(), Node()]), Mux([Node(), Node()])
    muxr2s, muxr2d = Mux([Node(), Node()]), Mux([Node(), Node()])
    eq1s, eq1d = Function('=', [Node(), Node()]), Function('=', [Node(), Node()])
    eq2s, eq2d = Function('=', [Node(), Node()]), Function('=', [Node(), Node()])
    muxo = Mux([Node(), Node()])
    comp = [muxo, one1, two2d, one2, two1d, one1s, one2s, muxr1s, muxr2s, muxr1d, muxr2d, eq1s, eq1d, eq2s, eq2d, zero1, zero2]
    mr = Module('MoreRegs', {'data': d, 'sel1': s1, 'sel2': s2}, {'getData': gd}, set([v] + comp))
    Wire(d, muxr1d.inputs[0]), Wire(d, muxr2d.inputs[0]), Wire(two1d.output, muxr1d.inputs[1]), Wire(two2d.output, muxr2d.inputs[1])
    Wire(s2, muxr1s.inputs[0]), Wire(s2, muxr2s.inputs[0]), Wire(one1s.output, muxr1s.inputs[1]), Wire(one2s.output, muxr2s.inputs[1])
    Wire(muxr1d.output, r1.inputs['data']), Wire(muxr2d.output, r2.inputs['data']), Wire(muxr1s.output, r1.inputs['sel']), Wire(muxr2s.output, r2.inputs['sel'])
    Wire(eq1d.output, muxr1d.control), Wire(eq2d.output, muxr2d.control), Wire(eq1s.output, muxr1s.control),Wire(eq2s.output, muxr2s.control)
    Wire(s1, eq1d.inputs[0]), Wire(s1, eq2d.inputs[0]), Wire(s1, eq1s.inputs[0]), Wire(s1, eq2s.inputs[0])
    Wire(zero1.output, eq1d.inputs[1]), Wire(one1.output, eq2d.inputs[1]), Wire(zero2.output, eq1s.inputs[1]), Wire(one2.output, eq2s.inputs[1])
    Wire(muxo.output, gd), Wire(r1.methods['getData'], muxo.inputs[0])
    Wire(r2.methods['getData'], muxo.inputs[1]), Wire(s1, muxo.control)

    expected = mr
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Handles multiple identical submodules with methods with arguments''')
def _():
    text = pull('moduleArgument2')

    n1 = Node()
    s1 = Register('Reg#(Bit#(2))')
    i1 = Module('Inner', {'next': n1}, {}, {s1})
    Wire(n1, s1.input)

    output = synth.parseAndSynth(text, 'Inner')
    expected = i1
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    n2 = Node()
    s2 = Register('Reg#(Bit#(2))')
    i2 = Module('Inner', {'next': n2}, {}, {s2})
    Wire(n2, s2.input)

    next1, next2, o1, o2 = Node(), Node(), Node(), Node()
    a1, a2 = Function('+', [Node(), Node()]), Function('+', [Node(), Node()])
    one1, one2 = Constant(Integer(1)), Constant(Integer(1))
    g1i, g1o, g2i, g2o = Node(), Node(), Node(), Node()
    g1 = Function('getUp', [g1i], g1o, {a1})
    g2 = Function('getUp', [g2i], g2o, {a2})
    Wire(s1.value, a1.inputs[0]), Wire(g1i, a1.inputs[1]), Wire(a1.output, g1o)
    out = Module('Outer', {'next1': next1, 'next2': next2}, {'out1': o1, 'out2': o2}, {i1, i2, g1, g2, one1, one2})
    Wire(s2.value, a2.inputs[0]), Wire(g2i, a2.inputs[1]), Wire(a2.output, g2o)
    Wire(one1.output, g1.inputs[0]), Wire(one2.output, g2.inputs[0])
    Wire(g1.output, o1), Wire(g2.output, o2), Wire(next1, n1), Wire(next2, n2)

    output = synth.parseAndSynth(text, 'Outer')
    expected = out
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

describe('''More Modules''')

@it('''Handles functions inside of a module''')
def _():
    text = pull('moduleFunction')

    gr1, gr2, s = Node(), Node(), Node()
    r = Register('Reg#(Bit#(4))')
    f1o, f2o = Node(), Node()
    f1 = Function('my_value', [], f1o)
    Wire(r.value, f1o)
    f2 = Function('my_value', [], f2o)
    Wire(r.value, f2o)
    out = Module('Outer', {'set': s}, {'getR1': gr1, 'getR2': gr2}, {r, f1, f2})
    Wire(s, r.input), Wire(f1.output, gr1), Wire(f2.output, gr2)

    output = synth.parseAndSynth(text, 'Outer')
    expected = out
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Handles modules with type parameter''')
def _():
    text = pull('moduleParameter')

    r = Register('Reg#(Maybe#(Bit#(4)))')
    m = Mux([Node(), Node()])
    inv = Constant(Invalid(Bit(IntegerLiteral(4))))
    isV = Function('isValid', [Node()])
    i, o = Node(), Node()
    b = Module('Buffer#(Bit#(4))', {'in': i}, {'out': o}, {r, m, inv, isV})
    Wire(i, m.inputs[0]), Wire(inv.output, m.inputs[1])
    Wire(isV.output, m.control), Wire(m.output, r.input)
    Wire(i, isV.inputs[0])
    Wire(r.output, o)
    
    output = synth.parseAndSynth(text, 'Buffer#(Bit#(4))')
    expected = b
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"


describe('''Handles built-ins''')

@it('''Handles log2''')
def _():
    text = pull('builtins')

    o = Node()
    four = Constant(IntegerLiteral(4))
    f = Function('constant#(8)', [], o, {four})
    Wire(four.output, o)

    output = synth.parseAndSynth(text, 'constant#(8)')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    o = Node()
    three = Constant(IntegerLiteral(3))
    f = Function('constant#(7)', [], o, {three})
    Wire(three.output, o)

    output = synth.parseAndSynth(text, 'constant#(7)')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Handles $display''')
def _():
    text = pull('builtins')

    r = Register('Reg#(Bit#(4))')
    i, o = Node(), Node()
    m = Module('Buffer', {'in': i}, {'out': o}, {r})
    Wire(i, r.input), Wire(r.output, o)
    
    output = synth.parseAndSynth(text, 'Buffer')
    garbageCollection1(output)
    expected = m
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"


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
            errorReport = traceback.format_exc()  # the text of the error message
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