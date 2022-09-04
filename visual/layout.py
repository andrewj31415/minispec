
# Calls place.js and performs layouting.

import os, sys  # see https://stackoverflow.com/questions/16780014/import-file-from-parent-directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hardware
import synth

import pathlib

minispecCodeFile = pathlib.Path(__file__).with_name("tests").joinpath("counters.ms")
minispecCode = minispecCodeFile.read_text()

synthesizedComponent = synth.parseAndSynth(minispecCode, 'Counter#(2)')
# synthesizedComponent = synth.parseAndSynth(minispecCode, 'Outer')
# synthesizedComponent = synth.parseAndSynth(minispecCode, 'f')

# from hardware import *
# a, b, o = Node(), Node(), Node()
# inp1, ind = Function('.data', [], [Node()]), Function('.index', [], [Node()])
# inp2, inp3 = Function('.data', [], [Node()]), Function('.data', [], [Node()])
# inpset = Function('.data', [], [Node(), Node()])
# r = Function('|', [], [Node(), Node()])
# pack = Function('Packet{}', [], [Node(), Node()])
# synthesizedComponent = Function('combine#(1,1,1,2)', [inp1, ind, inp2, inp3, inpset, r, pack, Wire(a, inp1.inputs[0]), Wire(b, ind.inputs[0]), Wire(inp1.output, pack.inputs[0]), Wire(ind.output, pack.inputs[1]), Wire(pack.output, inpset.inputs[0]), Wire(pack.output, inp2.inputs[0]), Wire(b, inp3.inputs[0]), Wire(inp2.output, r.inputs[0]), Wire(inp3.output, r.inputs[1]), Wire(r.output, inpset.inputs[1]), Wire(inpset.output, o)], [a, b], o)

# upper1, lower1, upper2, lower2 = [ synth.parseAndSynth(minispecCode, 'Counter#(0)') for i in range(4)]

# enable1, getCount1 = Node(), Node()
# and1, eq1, concat1, one1 = Function('&&', [], [Node(), Node()]), Function('==', [], [Node(), Node()]), Function('{}', [], [Node(), Node()]), Function('1')
# lower3 = Module('Counter#(1)', [and1, eq1, concat1, one1, upper1, lower1, Wire(enable1, lower1.inputs['enable']), Wire(lower1.methods['getCount'], eq1.inputs[0]), Wire(one1.output, eq1.inputs[1]), Wire(eq1.output, and1.inputs[1]), Wire(enable1, and1.inputs[0]), Wire(and1.output, upper1.inputs['enable']), Wire(upper1.methods['getCount'], concat1.inputs[0]), Wire(lower1.methods['getCount'], concat1.inputs[1]), Wire(concat1.output, getCount1)], {'enable': enable1}, {'getCount': getCount1})

# enable2, getCount2 = Node(), Node()
# and2, eq2, concat2, one2 = Function('&&', [], [Node(), Node()]), Function('==', [], [Node(), Node()]), Function('{}', [], [Node(), Node()]), Function('1')
# upper3 = Module('Counter#(1)', [and2, eq2, concat2, one2, upper2, lower2, Wire(enable2, lower2.inputs['enable']), Wire(lower2.methods['getCount'], eq2.inputs[0]), Wire(one2.output, eq2.inputs[1]), Wire(eq2.output, and2.inputs[1]), Wire(enable2, and2.inputs[0]), Wire(and2.output, upper2.inputs['enable']), Wire(upper2.methods['getCount'], concat2.inputs[0]), Wire(lower2.methods['getCount'], concat2.inputs[1]), Wire(concat2.output, getCount2)], {'enable': enable2}, {'getCount': getCount2})

# enable3, getCount3 = Node(), Node()
# and3, eq3, concat3, three = Function('&&', [], [Node(), Node()]), Function('==', [], [Node(), Node()]), Function('{}', [], [Node(), Node()]), Function('3')
# counter2 = Module('Counter#(2)', [and3, eq3, concat3, three, upper3, lower3, Wire(enable3, lower3.inputs['enable']), Wire(lower3.methods['getCount'], eq3.inputs[0]), Wire(three.output, eq3.inputs[1]), Wire(eq3.output, and3.inputs[1]), Wire(enable3, and3.inputs[0]), Wire(and3.output, upper3.inputs['enable']), Wire(upper3.methods['getCount'], concat3.inputs[0]), Wire(lower3.methods['getCount'], concat3.inputs[1]), Wire(concat3.output, getCount3)], {'enable': enable3}, {'getCount': getCount3})
# synthesizedComponent = counter2

# input/output files for elk
pythonToJSFile = pathlib.Path(__file__).with_name("elk").joinpath("elkInput.txt")
JSToPythonFile = pathlib.Path(__file__).with_name("elk").joinpath("elkOutput.txt")

with pythonToJSFile.open('w') as fp: # write to a file to give to elk
    fp.write(hardware.getELK(synthesizedComponent))

os.system("node elk/place.js") # run elk

text = JSToPythonFile.read_text() # the output from elk
print()
print("received:")
print(text)