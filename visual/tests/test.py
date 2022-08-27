
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
tests = []  # Array[(testName: str, testFunc: ()=>{}) | categoryName: str]
def it(name: 'str'):
    def logger(func):
        tests.append((name, func))
    return logger
def describe(categoryName: 'str'):
    tests.append(categoryName)

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
    output = synth.parseAndSynth(text, 'f', [2,2]) #the original f
    expected = Function('f#(2,2)', [Function('+', [], [inner1, inner2], innerOut), Wire(fa, inner1), Wire(fb, inner2), Wire(innerOut, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Function should correctly take parameter''')
def _():
    text = pull('params1')
    fa, fb, fo = Node(), Node(), Node()
    output = synth.parseAndSynth(text, 'f', [1]) #the second f
    expected = Function('f#(1)', [Wire(fa, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Function should correctly partially specialize''')
def _():
    text = pull('params1')
    fa, fb, fo = Node(), Node(), Node()
    output = synth.parseAndSynth(text, 'f', [2,1]) #the third f
    expected = Function('f#(2,1)', [Wire(fb, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Function should correctly fully specialize''')
def _():
    text = pull('params1')
    fa, fb, fo = Node(), Node(), Node()
    inner1, inner2, innerOut = Node(), Node(), Node()
    output = synth.parseAndSynth(text, 'f', [1,1]) #the fourth f
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
    output = synth.parseAndSynth(text, 'f', [10, 0]) #the second f
    expected  = Function('f#(10,0)', [Wire(fa, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''Correctly computes fixed param from constants''')
def _():
    text = pull('params2')
    fa, fb, fo = Node(), Node(), Node()
    output = synth.parseAndSynth(text, 'f', [1, 7]) #the third f
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
    
    output = synth.parseAndSynth(text, 'g', [15])
    expected = g
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    output = synth.parseAndSynth(text, 'f')
    expected = f
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

describe("If and Case Statements")

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

    output = synth.parseAndSynth(text, 'f', [2])
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

    output = synth.parseAndSynth(text, 'f', [0])
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

describe('''For Loops''')

@it('''Correctly handles for loop''')
def _():
    text = pull('for')

    zero, one, two, three = Function('[0]', [], [Node()]), Function('[1]', [], [Node()]), Function('[2]', [], [Node()]), Function('[3]', [], [Node()])
    output = Function('0')
    xor0, xor1, xor2, xor3 = Function('^', [], [Node(), Node()]), Function('^', [], [Node(), Node()]), Function('^', [], [Node(), Node()]), Function('^', [], [Node(), Node()])
    fa, fo = Node(), Node()
    f = Function('parity#(4)', [zero, one, two, three, output, xor0, xor1, xor2, xor3, Wire(fa, zero.inputs[0]), Wire(fa, one.inputs[0]), Wire(fa, two.inputs[0]), Wire(fa, three.inputs[0]), Wire(output.output, xor0.inputs[0]), Wire(xor0.output, xor1.inputs[0]), Wire(xor1.output, xor2.inputs[0]), Wire(xor2.output, xor3.inputs[0]), Wire(xor3.output, fo), Wire(zero.output, xor0.inputs[1]), Wire(one.output, xor1.inputs[1]), Wire(two.output, xor2.inputs[1]), Wire(three.output, xor3.inputs[1])], [fa], fo)

    output = synth.parseAndSynth(text, 'parity', [4])
    expected = f
    assert expected.match(output), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

describe('''Assorted hardware''')

@it('''Correctly handles assorted hardware''')
def _():
    text = pull('assortedtests')

    output = synth.parseAndSynth(text, 'population_count', [])
    print(output.__repr__())

#run all the tests
import time
import sys
import traceback
categoryName = ""
numTestsFailed = 0
numTestsPassed = 0
failedTests = []  # Array[(category: 'str', name: 'str', error: 'str')]
testingTimeStart = time.time()
for i in range(len(tests)):
    if tests[i].__class__ == str: #we have the name of a category of tests
        categoryName = tests[i]
        print()
        print("  " + categoryName)
    else:  # we have a testName/test pair
        testName, it = tests[i]
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
print()

#report details of failing tests (if any)
for i in range(len(failedTests)):
    failedTest = failedTests[i]
    category, testName, errorMessage = failedTest
    print("  " + str(i+1) + ")", categoryName)
    print("      " + testName + ":")
    print()
    print(errorMessage)
    print()

