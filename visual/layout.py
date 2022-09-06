
# Calls place.js and performs layouting.

import os, sys  # see https://stackoverflow.com/questions/16780014/import-file-from-parent-directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hardware
import synth

import pathlib

minispecCodeFile = pathlib.Path(__file__).with_name("tests").joinpath("if4.ms")
minispecCode = minispecCodeFile.read_text()

# synthesizedComponent = synth.parseAndSynth(minispecCode, 'Counter#(2)')
# synthesizedComponent = synth.parseAndSynth(minispecCode, 'Outer')
# synthesizedComponent = synth.parseAndSynth(minispecCode, 'BitonicSorter8')
synthesizedComponent = synth.parseAndSynth(minispecCode, 'computeHalf')

print('done synthesizing!')

from hardware import *

fin, fo = Node(), Node()

mux = Mux([Node(), Node()])
eq = Function('==', [], [Node(), Node()])
cZero, sZero = Function('0'), Function('0')
lowBit = Function('[0]', [], [Node()])
inv = Function('Invalid')
val = Function('Valid', [], [Node()])
sftComps = []
for i in range(1,32):
    sftComps.append(Function(f'[{i}]', [], [Node()])) # from input
for i in range(31):
    sftComps.append(Function(f'[{i}]', [], [Node(), Node()])) # collect output
sftWires = [Wire(sZero.output, sftComps[31].inputs[0]), Wire(sftComps[61].output, val.inputs[0])]
for i in range(0,31):
    sftWires.append(Wire(fin, sftComps[i].inputs[0]))
    sftWires.append(Wire(sftComps[i].output, sftComps[i+31].inputs[1]))
for i in range(0,30):
    sftWires.append(Wire(sftComps[i+31].output, sftComps[i+32].inputs[0]))

computeHalf = Function('computeHalf', sftComps + sftWires + [mux, eq, cZero, sZero, lowBit, inv, val, Wire(val.output, mux.inputs[1]), Wire(inv.output, mux.inputs[0]), Wire(mux.output, fo), Wire(lowBit.output, eq.inputs[0]), Wire(cZero.output, eq.inputs[1]), Wire(eq.output, mux.control), Wire(fin, lowBit.inputs[0])], [fin], fo)

synthesizedComponent = computeHalf

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