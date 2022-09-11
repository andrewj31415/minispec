
# Calls place.js and performs layouting.

import os, sys  # see https://stackoverflow.com/questions/16780014/import-file-from-parent-directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hardware
import synth

import pathlib

minispecFileName = "assortedtests"
# minispecFileName = "counters"

minispecCodeFile = pathlib.Path(__file__).with_name("tests").joinpath(f"{minispecFileName}.ms")
minispecCode = minispecCodeFile.read_text()

# synthesizedComponent = synth.parseAndSynth(minispecCode, 'Counter#(2)')
# synthesizedComponent = synth.parseAndSynth(minispecCode, 'Outer')
# synthesizedComponent = synth.parseAndSynth(minispecCode, 'RegisterFile')
synthesizedComponent = synth.parseAndSynth(minispecCode, 'alu')

print('done synthesizing!')

# from hardware import *
# fa, fo = Node(), Node()
# synthesizedComponent = Function('f', [Wire(fa, fo)], [fa], fo)

# input/output files for elk
pythonToJSFile = pathlib.Path(__file__).with_name("elk").joinpath("elkInput.txt")
JSToPythonFile = pathlib.Path(__file__).with_name("elk").joinpath("elkOutput.txt")

with pythonToJSFile.open('w') as fp: # write to a file to give to elk
    fp.write(hardware.getELK(synthesizedComponent))

os.system("node elk/place.js") # run elk

elkOutput = JSToPythonFile.read_text() # the output from elk
print()
print("received:")
print(elkOutput)

templateFile = pathlib.Path(__file__).with_name('template.html')
template = templateFile.read_text()

templateParts = template.split("/* Python data goes here */")
numInsertionPoints = 2
assert len(templateParts) == numInsertionPoints + 1, f"Expected {numInsertionPoints+1} segments from {numInsertionPoints} insertion points but found {len(templateParts)} segments instead."

sourcesInfo = f'''sources.set("{minispecFileName}", {{
    tokens: {synth.tokensAndWhitespace(minispecCode)}
}});'''

elementsToPlace = f'''elementsToPlace = {elkOutput}'''

template = templateParts[0] + sourcesInfo + templateParts[1] + elementsToPlace + templateParts[2]

output = pathlib.Path(__file__).with_name('sample.html')
output.open("w").write(template)