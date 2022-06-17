# To install the correct version of antlr:  pip install antlr4-python3-runtime==4.9.3

import inspect

import antlr4
import build.MinispecPythonParser
import build.MinispecPythonLexer
import build.MinispecPythonVisitor

class MinispecVisitor(build.MinispecPythonVisitor.MinispecPythonVisitor):
    def visitPackageDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.PackageDefContext):
        print("Hello!")
        print(dir(ctx))
        # see https://stackoverflow.com/questions/23092081/antlr4-visitor-pattern-on-simple-arithmetic-example
        # for examples
    def visitReturnExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ReturnExprContext):
        pass

text = """function Bit#(1) f(Bit#(1) a, Bit#(1) b);
    let x = a ^ b;
    return x;
endfunction"""
data = antlr4.InputStream(text)
print(data)
lexer = build.MinispecPythonLexer.MinispecPythonLexer(data)
print(dir(lexer))
print(inspect.getsource(antlr4.Lexer))

stream = antlr4.CommonTokenStream(lexer)
print(stream)
print(inspect.getsource(antlr4.CommonTokenStream))
parser = build.MinispecPythonParser.MinispecPythonParser(stream)

tree = parser.packageDef()

visitor = MinispecVisitor()
visitor.visitPackageDef(parser)