# Minispec Visual
### This directory contains the code to produce an interactive visual html GUI from a minispec project.

The entrypoint for the visualization system is ./visual. See below for a more detailed description of the project, including installation instructions.

## Summary of directory contents:

### /elk:
A build of the ELKJS layouting library, see https://github.com/kieler/elkjs for repo. Also contains a wrapper /elk/place.js.

### /tests:
Tests for the minispec interpreter synth.py. To run all tests, run /tests/test.py.

### MinispecPython.g4:
A copy of the minispec grammar from ../src/Minipsec.g4. Has minor changes due to python keyword conflicts.

### hardware.py:
The hardware representation. Also contains code to convert the hardware rep into a JSON format that can be sent to ELKJS via /elk/place.js.

### mtypes.py:
Types used by the minispec interpreter synth.py. Includes literal types, constant folding calculations, and types corresponding to minispec modules.

### synth.py:
The minispec interpreter. Includes functions for converting minispec code into the hardware representation, as well as handling source-map support.

### template.html:
The code for the GUI. Has insertion locations for data produced by synth.py. Does not load on its own--requires data from synth.py.

### visual:
Executable python script that generates html output from the source minispec. Calls parser and interpreter functions from synth.py, passes the resulting hardware representation to ELKJS via /elk/place.js, inserts the output layout data into a copy of template.html, and puts the resulting html into a new file.

### olddraw.py:
An old implementation of the hardware representation. Used to produce a hardcoded output for testing the GUI. No longer in spec--only kept for reference.

### oldtemplate.py:
An old implementation of the html template. Used to display a hardcoded output for testing GUI features. No longer in spec--only kept for reference.

## TODO list

- Test parametric lookups
- Investigate demultiplexer design and source support for vectors of submodules
- Source support for wires and variables
- Constant folding across function boundaries
- Representing variable index manipulations in parallel
- Layouting via ELK Java
- Runtime layouting for recursive expansion using ELK JS
- Nicer error messages

## Install info (TODO give more detail)

Commands to create python3 antlr4 build (dirs may vary):

Install pip with `sudo apt install python3-pip`, then install the correct version of python antlr4 via pip with `pip install antlr4-python3-runtime==4.7.2`. Build antlr4 with (directories may vary) `java -classpath ~/minispec/antlr4.jar -Xmx500M org.antlr.v4.Tool -o ~/minispec/visual/build/ -Xexact-output-dir -Dlanguage=Python3 -visitor ~/minispec/visual/MinispecPython.g4`.

## General plan for minispec visual (TODO update plans)

Minispec visual will be a python script, useable from the command line (like synth), which will take the same inputs as synth: a starting file, a top-level module/function, and possibly a circuit element library to use (for timing computations). The python script will output an interactive html file which may be opened in a web browser.

The final program will have five parts:

1. The interpreter. The parser will read the minispec source via ANTLR's parser-generator and will then convert it into an abstract data structure. We will then unroll for loops. We will keep track of a source map along the way.

2. The synthesizer. The synthesizer will convert the abstract data structure into a data structure with actual hardware information, including modules, functions, muxes, registers, and wires. If it would be useful and would not cause performance issues, it should be possible to synthesize circuits all the way down to transistors, though this would not include optimizations.

3. The placement algorithm. The placement algorithm will determine the layout of the output. Our current synthesis program uses netlistsvg (TODO link), which in turn depends on ElkJS. ElkJS has a few different algorithm options, but they all use the same paradigm: placing all components onto a grid and rearranging via heuristics (TODO details + link). This paradigm does not seem particularly difficult to implement, and since there are quite a few minispec-specific heuristics (for instance, if the ouput of a mux leads into a register, then the mux should be placed before the register), I think it would be best to write our own implementation.  
Actually, since the Eclipse Layout Kernel (ELK) https://www.eclipse.org/elk/ includes support for nodes-within-nodes, it might be possible to use some form of ELK directly.
An online demo is here: https://rtsys.informatik.uni-kiel.de/elklive/json.html

4. The timing computations. We would like to display latency information for each component in the circuit. Since we have the minispec source for every component, it should be possible to feed the corresponding source into our existing synth program to get accurate timings. There are a few points of note to consider:

- The source for some components (like a mux) may be scattered throughout the source code.
- Timings for bluespec built-ins may be context dependent, and so will need more work. Fortunately, a lot of bluespec built-ins are things like vector manipulation that take no time.
- Optimizations between adjacent components will not be included in their separate timings. Neither will fanout effects.
- Module methods may need to be synthesized separately from their rules in order to give more accurate latency information.

5. The interface. The interface will be an html page will places for data to be filled in. The results of the placement algorithm will be inserted into the html page as javascript objects.

.md techniques:
https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet

svg path editor for icons:
https://yqnn.github.io/svg-path-editor/
