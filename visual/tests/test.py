
# needed to import parsesynth.py
import os, sys  # see https://stackoverflow.com/questions/16780014/import-file-from-parent-directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parsesynth import *

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
    output = parseAndSynth(text, 'f')
    fa, fb, fo = Node('fa'), Node('fb'), Node('fo')
    xfa, xfb, xfo = Node('xfa'), Node('xfb'), Node('xfo')
    expected = Function("f", [Function("^", [], [xfa, xfb], xfo), Wire(fa, xfa),
                                    Wire(fb, xfb), Wire(xfo, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

@it('''One function calling another for a three-way xor''')
def _():
    text = pull('functions')
    output = parseAndSynth(text, 'g')
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

@it('''Various parameter tests''')
def _():
    text = pull('parameterize')
    output = parseAndSynth(text, 'e')
    print(output.__repr__())

    text = pull('params1')

    fa, fb, fo = Node(), Node(), Node()
    inner1, inner2, innerOut = Node(), Node(), Node()

    output = parseAndSynth(text, 'f', [2,2]) #the original f
    expected = Function('f#(2,2)', [Function('+', [], [inner1, inner2], innerOut), Wire(fa, inner1), Wire(fb, inner2), Wire(innerOut, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    output = parseAndSynth(text, 'f', [1]) #the second f
    expected = Function('f#(1)', [Wire(fa, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    output = parseAndSynth(text, 'f', [2,1]) #the third f
    expected = Function('f#(2,1)', [Wire(fb, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    output = parseAndSynth(text, 'f', [1,1]) #the fourth f
    expected = Function('f#(1,1)', [Function('f', [Wire(inner1, innerOut)], [inner1, inner2], innerOut), Wire(fa, inner2), Wire(fb, inner1), Wire(innerOut, fo)], [fa, fb], fo)
    assert output.match(expected), f"Gave incorrect hardware description.\nReceived: {output.__repr__()}\nExpected: {expected.__repr__()}"

    output = parseAndSynth(text, 'f') #the fifth f
    expected  = Function('f', [Wire(inner1, innerOut)], [inner1, inner2], innerOut)
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
                print("    √", testName, "(")
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

