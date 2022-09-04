
# Calls place.js and performs layouting.

import os, sys  # see https://stackoverflow.com/questions/16780014/import-file-from-parent-directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hardware
import synth

import pathlib

minispecCodeFile = pathlib.Path(__file__).with_name("tests").joinpath("caseExpr1.ms")
minispecCode = minispecCodeFile.read_text()

# synthesizedComponent = synth.parseAndSynth(minispecCode, 'Counter#(2)')
# synthesizedComponent = synth.parseAndSynth(minispecCode, 'Outer')
# synthesizedComponent = synth.parseAndSynth(minispecCode, 'f')

from hardware import *
fa, fb, fc, fd, fe, fo = Node(), Node(), Node(), Node(), Node(), Node()

concat = Function('{}', [], [Node(), Node(), Node(), Node()])
zeroA, oneA, twoA, threeA = Function('0'), Function('1'), Function('2'), Function('3')
muxA = Mux([Node(), Node(), Node(), Node()])
xWires = [Wire(zeroA.output, muxA.inputs[0]), Wire(twoA.output, muxA.inputs[1]), Wire(threeA.output, muxA.inputs[2]), Wire(oneA.output, muxA.inputs[3]), Wire(fa, muxA.control), Wire(muxA.output, concat.inputs[0])]

zeroY, oneY, twoY = Function('0'), Function('1'), Function('2')
nb, nc = Function('~', [], [Node(), Node()]), Function('~', [], [Node(), Node()])
myb, myc = Mux([Node(), Node()]), Mux([Node(), Node()])
yWires = [Wire(fb, nb.inputs[0]), Wire(fc, nc.inputs[0]), Wire(nb.output, myb.control), Wire(nc.output, myc.control), Wire(myb.output, concat.inputs[1]), Wire(zeroY.output, myb.inputs[0]), Wire(myc.output, myb.inputs[1]), Wire(oneY.output, myc.inputs[0]), Wire(twoY.output, myc.inputs[1])]

zeroZ, oneZ, twoZ = Function('0'), Function('1'), Function('2')
eqb, eqc = Function('==', [], [Node(), Node()]), Function('==', [], [Node(), Node()])
mzb, mzc = Mux([Node(), Node()]), Mux([Node(), Node()])
zWires = [Wire(fd, eqb.inputs[0]), Wire(fb, eqb.inputs[1]), Wire(eqb.output, mzb.control), Wire(fd, eqc.inputs[0]), Wire(fc, eqc.inputs[1]), Wire(eqc.output, mzc.control), Wire(mzb.output, concat.inputs[2]), Wire(zeroZ.output, mzb.inputs[0]), Wire(mzc.output, mzb.inputs[1]), Wire(oneZ.output, mzc.inputs[0]), Wire(twoZ.output, mzc.inputs[1])]

ne = Function('~', [], [Node(), Node()])
wWires = [Wire(fe, ne.inputs[0]), Wire(ne.output, concat.inputs[3])]

f = Function('f', [concat, zeroA, oneA, twoA, threeA, muxA, zeroY, oneY, twoY, nb, nc, myb, myc, zeroZ, oneZ, twoZ, eqb, eqc, mzb, mzc, ne] + xWires + yWires + zWires + wWires + [Wire(concat.output, fo)], [fa, fb, fc, fd, fe], fo)

synthesizedComponent = f

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