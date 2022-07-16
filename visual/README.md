This folder will store the visualization code.

Command to create python3 antlr (dirs may vary):
java -classpath ~/minispec/antlr4.jar -Xmx500M org.antlr.v4.Tool -o ~/minispec/visual/build/ -Xexact-output-dir -Dlanguage=Python3 -visitor ~/minispec/visual/MinispecPython.g4

General plan for minispec visual:

The final program will have four parts:

1. The interpreter. The parser will read the minispec source via ANTLR's parser-generator and will then convert it into an abstract data structure. We will then unroll for loops. We will keep track of a source map along the way.

2. The synthesizer. The synthesizer will convert the abstract data structure into a data structure with actual hardware information, including modules, functions, muxes, registers, and wires. If it would be useful and would not cause performance issues, it should be possible to synthesize circuits all the way down to transistors, though this would not include optimizations.

3. The placement algorithm. The placement algorithm will determine the layout of the output. Our current synthesis program uses netlistsvg (TODO link), which in turn depends on ElkJS. ElkJS has a few different algorithm options, but they all use the same paradigm: placing all components onto a grid and rearranging via heuristics (TODO details + link). This paradigm does not seem particularly difficult to implement, and since there are quite a few minispec-specific heuristics (for instance, if the ouput of a mux leads into a register, then the mux should be placed before the register), I think it would be best to write our own implementation.

    3a. The timing computations. We would like to display latency information for each component in the circuit. Since we have the minispec source for every component, it should be possible to feed the corresponding source into our existing synth program to get accurate timings. There are a few points of note to consider:

    - The source for some components (like a mux) may be scattered throughout the source code.
    - Timings for bluespec built-ins may be context dependent, and so will need more work. Fortunately, a lot of bluespec built-ins are things like vector manipulation that take no time.
    - Optimizations between adjacent components will not be included in their separate timings. Neither will fanout effects.
    - Module methods may need to be synthesized separately from their rules in order to give more accurate latency information.

4. The interface. The interface will be an html page will places for data to be filled in. The results of the placement algorithm will be inserted into the html page as javascript objects.

.md techniques:
https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet

svg path editor for icons:
https://yqnn.github.io/svg-path-editor/
