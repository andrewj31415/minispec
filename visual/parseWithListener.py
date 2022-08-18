import inspect

import antlr4
import build.MinispecPythonParser
import build.MinispecPythonLexer
import build.MinispecPythonListener

'''
Two setups:

1. Decorating the existing parse tree with pointers (computed by following static typing),
with scope objects attached to functions/modules/rules/files, and then synthesize by
traveling around the tree.

2. Creating an entirely new AST (abstract syntax tree), with different classes for each
kind of minispec syntactical construct, and then synthesize in several steps manipulating
the new tree and creating a third tree whose entries are components.

'''


''' The steps are:
1. Gather types and scopes
2. Abstract away into AST
3. Synthesize
'''

# I think function and module defs should extend scope and be used as scope, while also having additional
# internal lines-of-code info and a synthesis method.

# I think we also need an additional expression class.

# We want lines and scopes to be separate since some multi-line expressions like for loops
# do not correspond to new scopes.

# used in printing. 4*indentationLevel spaces are printed before each line.
def indent(indentationLevel):
    return "    " * indentationLevel

'''
Documentation:

self.ownScope: Scope
  the scope of this line, if it has internal scope.

The Scope class.
  Lines that have internal code (modules, rules, functions, files) with their own scope have a scope object.


'''

class Line:
    '''
    A line of minispec code.
    Followed by the line self.nextLine, or the last line in a scope if self.nextLine == None.
    '''
    def __init__(self, nextLine = None):
        self.nextLine = nextLine
    def synth(self, scope):
        '''
        Synthesizes the component to hardware in the given scope.
        '''
        if (self.nextLine == None):
            return
        else:
            self.nextLine.synth(scope)
    def print(self, indentationLevel):
        '''
        Prints a visual representation of this line, indented to the given level.
        '''
        if self.nextLine != None:
            self.nextLine.print(indentationLevel)

class Expression:
    '''
    A piece of minispec code that, when synthesized, will have a value.
    Includes function calls, lone variables, and constants.
    '''
    def __init__(self):
        pass

class FuncCall(Expression):
    '''
    Calling a function.
    '''
    def __init__(self, function: 'FuncDef'):
        '''
        function points to the definition of the function being called.
        '''
        self.function = function

class Scope:
    def __init__(self, name: 'str' = "unnamed", parents: 'list[Scope]' = []):
        self.parents = parents.copy()
        '''vars is a dictionary mapping names to a value'''
        self.vars = {}
        '''same as vars but for types'''
        self.typeNames = {}
        self.name = name
    def __str__(self):
        return "Scope " + self.name
    def print(self, indentationLevel):
        '''
        Prints a visual representation of this line, indented to the given level.
        '''
        assert False, "not implemented"

class FuncDef(Line):
    def __init__(self, name: 'str' = "unnamed", parents: 'list[Scope]' = [], nextLine: "Line" = None):
        Line.__init__(self, nextLine)
        assert len(parents) == 1, "A function should have exactly one parent scope."
        self.ownScope = Scope(name, parents)
        self.lines = Line()
    def synth(self):
        pass
    def print(self, indentationLevel):
        print(indent(indentationLevel), "FuncDef with scope", self.ownScope.name)
        self.lines.print(indentationLevel + 1)
        print(indent(indentationLevel), "endfunc")
        if self.nextLine != None:
            self.nextLine.print(indentationLevel)

class FuncCall(Line):
    def __init__(self, nextLine = None):
        Line.__init__(self, nextLine)
    def synth(self):
        #TODO
        pass



builtinScope = Scope("built-ins")


class MinispecStructure:
    def __init__(self):
        '''will hold all created scopes for now'''
        self.allScopes = [builtinScope]
        self.currentScope = builtinScope
        self.lines = Line()
        self.currentLines = [self.lines] #stack trace of lines
    def nextLine(self, line):
        self.currentLines[-1].nextLine = line
        self.currentLines[-1] = line
    def print(self):
        self.lines.print(0)

parsedCode = MinispecStructure()


class MinispecListener(build.MinispecPythonListener.MinispecPythonListener):
    def enterPackageDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.PackageDefContext):
        '''The entry node to the parse tree.'''
        print(inspect.getsource(ctx.getText))
        print(ctx.getText())

    def enterFunctionDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionDefContext):
        '''We are defining a function. We create FunctionDef, then step into the function.'''
        # print("function")
        # print(inspect.getsource(ctx.getText))
        # print(ctx.getText())
        # print(ctx.typeName().getText())
        # print(ctx.functionId().getText())
        functionName = ctx.functionId().getText() # get the name of the function
        #set up and log the function as a line of code
        functionLine = FuncDef(functionName, [parsedCode.currentScope], None)
        parsedCode.nextLine(functionLine)
        parsedCode.currentLines.append(functionLine.lines) # step into the function
        #log the function's scope
        functionScope = functionLine.ownScope
        parsedCode.currentScope = functionScope
        parsedCode.allScopes.append(functionScope)
    def exitFunctionDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionDefContext):
        '''We have defined a function, so we step out of the function's code'''
        # step out of the function
        parsedCode.currentLines.pop()
        assert len(parsedCode.currentScope.parents) == 1, "function can only have parent scope"
        parsedCode.currentScope = parsedCode.currentScope.parents[0]

    def enterStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.StmtContext):
        '''A statement has several different possible types, each of which is handled differently,
        so there is no need to do anything with stmt. Statements correspond to the Line class.'''
        print("stmt", ctx.getText())
        pass
    def exitStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.StmtContext):
        pass

    def enterLetBinding(self, ctx: build.MinispecPythonParser.MinispecPythonParser.LetBindingContext):
        '''Assigning a variable/variables using the 'let' keyword.
        Followed by a series of lower case identifiers corresponding to variables, then
        an (optional) expression corresponding to the value that they should have.'''
        print("letbinding", ctx.getText())
        print(ctx.rhs.getText()) #the right hand side of the expression
        varsToSet = ctx.lowerCaseIdentifier() #list of variables that are being set
        for var in varsToSet:
            print(var.getText()) #the name of each variable. must be a lowerCaseIdentifier so can be parsed directly.
        

    def enterVarBinding(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarBindingContext):
        '''Creating a variable or variables. May or may not initialize variables.'''
        print("varbinding", ctx.getText())

    def enterReturnExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ReturnExprContext):
        '''Returning from a function. Followed by an expression.'''
        print("returning", ctx.getText())

import pathlib

textFile = pathlib.Path(__file__).with_name("tests").joinpath("functions.ms")
text = textFile.read_text()

print("text:")
print(text, "\n")
data = antlr4.InputStream(text)
lexer = build.MinispecPythonLexer.MinispecPythonLexer(data)
stream = antlr4.CommonTokenStream(lexer)
parser = build.MinispecPythonParser.MinispecPythonParser(stream)
tree = parser.packageDef()  #start parsing at the top-level packageDef rule
walker = build.MinispecPythonListener.ParseTreeWalker()

listener = MinispecListener()
walker.walk(listener, tree)  # walk the listener through the tree

print(parsedCode.allScopes)

parsedCode.print()