
# Calls place.js and performs layouting.

import os, sys  # see https://stackoverflow.com/questions/16780014/import-file-from-parent-directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hardware
import synth

import pathlib

minispecCodeFile = pathlib.Path(__file__).with_name("tests").joinpath("moduleDefault.ms")
minispecCode = minispecCodeFile.read_text()

# synthesizedComponent = synth.parseAndSynth(minispecCode, 'Counter#(3)')
synthesizedComponent = synth.parseAndSynth(minispecCode, 'Outer')
# synthesizedComponent = synth.parseAndSynth(minispecCode, 'f')

# from hardware import *
# a, b, o = Node(), Node(), Node()
# inp1, ind = Function('.data', [], [Node()]), Function('.index', [], [Node()])
# inp2, inp3 = Function('.data', [], [Node()]), Function('.data', [], [Node()])
# inpset = Function('.data', [], [Node(), Node()])
# r = Function('|', [], [Node(), Node()])
# pack = Function('Packet{}', [], [Node(), Node()])
# synthesizedComponent = Function('combine#(1,1,1,2)', [inp1, ind, inp2, inp3, inpset, r, pack, Wire(a, inp1.inputs[0]), Wire(b, ind.inputs[0]), Wire(inp1.output, pack.inputs[0]), Wire(ind.output, pack.inputs[1]), Wire(pack.output, inpset.inputs[0]), Wire(pack.output, inp2.inputs[0]), Wire(b, inp3.inputs[0]), Wire(inp2.output, r.inputs[0]), Wire(inp3.output, r.inputs[1]), Wire(r.output, inpset.inputs[1]), Wire(inpset.output, o)], [a, b], o)

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