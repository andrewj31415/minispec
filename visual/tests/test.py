
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

