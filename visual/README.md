This folder will store the visualization code.

Command to create python3 antlr (dirs may vary):
java -classpath ~/minispec/antlr4.jar -Xmx500M org.antlr.v4.Tool -o ~/minispec/visual/build/ -Xexact-output-dir -Dlanguage=Python3 -visitor ~/minispec/visual/MinispecPython.g4
