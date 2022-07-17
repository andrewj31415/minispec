# To install the correct version of antlr:  pip install antlr4-python3-runtime==4.9.3

# More antlr4 documentation:
# https://github.com/ericvergnaud/antlr4/tree/dev/runtime/Python3/src/antlr4

import inspect

import antlr4
import build.MinispecPythonParser
import build.MinispecPythonLexer
import build.MinispecPythonVisitor

class MinispecVisitor(build.MinispecPythonVisitor.MinispecPythonVisitor):
    def visitPackageDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.PackageDefContext):
        print("Hello!")
        print(dir(ctx))
        print("ctx attribute")
        print(ctx.packageStmt)
        print(inspect.getsource(ctx.packageStmt))
        print(ctx.packageStmt())
        print("text")
        print(ctx.getText())
        print("children")
        for child in ctx.getChildren():
            print(child)
        #print(self.visit(ctx.packageStmt()))
        #self.visit(ctx.packageStmt())
        # see https://stackoverflow.com/questions/23092081/antlr4-visitor-pattern-on-simple-arithmetic-example
        # and https://stackoverflow.com/questions/15610183/if-else-statements-in-antlr-using-listeners
        # for examples
    def visitPackageStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.PackageStmtContext):
        '''print("visiting package stmt")
        print("ctx dir:")
        print(dir(ctx))
        print([ c for c in ctx.getChildren() ])
        print(ctx.functionDef)
        #print(help(ctx.getToken))
        print(build.MinispecPythonParser.MinispecPythonParser.PackageStmtContext)
        print(inspect.getsource(build.MinispecPythonParser.MinispecPythonParser.PackageStmtContext))
        print(inspect.getsource(antlr4.ParserRuleContext))
        print(ctx.getTokens(build.MinispecPythonParser.MinispecPythonParser.functionDef))
        print('start')
        for child in ctx.getChildren():
            print(1)
        print('hi')'''
    def visitReturnExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ReturnExprContext):
        pass

text = """function Bit#(1) f(Bit#(1) a, Bit#(1) b);
    let x = a ^ b;
    return x;
endfunction"""
data = antlr4.InputStream(text)
print(data)
lexer = build.MinispecPythonLexer.MinispecPythonLexer(data)
print("lexer dir and source")
print(dir(lexer))
print(inspect.getsource(antlr4.Lexer))

stream = antlr4.CommonTokenStream(lexer)
print("stream and source")
print(stream)
print(inspect.getsource(antlr4.CommonTokenStream))
parser = build.MinispecPythonParser.MinispecPythonParser(stream)

#compare with https://github.com/cjhahaha/calculANTLR-python3/blob/master/main.py
tree = parser.packageDef()

visitor = MinispecVisitor()
visitor.visit(tree)
#visitor.visitPackageDef(parser)

'''print("antlr4 parser source")
print(inspect.getsource(antlr4.Parser))'''