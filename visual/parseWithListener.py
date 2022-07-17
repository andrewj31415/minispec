import inspect

import antlr4
import build.MinispecPythonParser
import build.MinispecPythonLexer
import build.MinispecPythonListener

class MinispecListener(build.MinispecPythonListener.MinispecPythonListener):
    def enterPackageDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.PackageDefContext):
        print(inspect.getsource(ctx.getText))
        print(ctx.getText())


text = """function Bit#(1) f(Bit#(1) a, Bit#(1) b);
    let x = a ^ b;
    return x;
endfunction"""
data = antlr4.InputStream(text)
lexer = build.MinispecPythonLexer.MinispecPythonLexer(data)
stream = antlr4.CommonTokenStream(lexer)
parser = build.MinispecPythonParser.MinispecPythonParser(stream)
tree = parser.packageDef()  #start parsing at the top-level packageDef rule
walker = build.MinispecPythonListener.ParseTreeWalker()

listener = MinispecListener()
walker.walk(listener, tree)  # walk the listener through the tree