import inspect

import antlr4
import build.MinispecPythonParser
import build.MinispecPythonLexer
import build.MinispecPythonListener
import build.MinispecPythonVisitor


'''
Implementation Agenda:

    - Parametrics (+ associated variable lookups)
    - Type handling (+ associated python type objects)
    - For loops
    - If/case statements (+ muxes)
    - Modules
    - Other files

Implemented:

    - Function calls
    - Binary operations
'''

'''
Overall specs:

ANTLR produces a parse tree ("tree" in the code). This parse tree has nodes corresponding
to different parts of the minispec grammar (packageDef, exprPrimary, returnExpr, etc.).
We will:
1. Run a tree walker through the parse tree to add static elaboration information, eg, 
  a callExpr node (corresponding to a function call) will get a pointer to the definition
  of the function being called, which will be a functionDef node.
2. Locate the module/function to synthesize, then use a visitor to go through the tree (starting
  at the module/function to synthesize) and synthesize the minispec code.

Notes:
- Scope objects will need to keep temporary and permanent values separate (think synthesizing the
  same function twice with different parameterizations).


Overall data structure:

-------------
|ANTLR4 tree|
-------------
      |
    |file node|
      |
    |function node|
      |
    |more nodes|

------------
|parsedCode|
------------
  |         |
  |         currentScope (the scope currently of interest)
allScopes
(list of all scope objects)

built-in scope
  ^ (parent pointer)
file to parse scope
  ^
various function scopes
  ...

StaticTypeListener:
  This listener detects scope information and static declarations.
  - For each function/module/file with its own scope, a scope object is created.
    This scope object is logged in parsedCode's allScopes list, is given parent pointer
    equal to the current scope, becomes the current scope (since the walker is about to bring
    the listener inside the function), and then is attached to the corresponding function/module
    def node under ".scope".
  - All static declarations are logged in the current scope (in .vars) when detected, with
    a pointer to the relevant node. This includes function/module definitions as well as
    variables (since these variables may be named constants if they are in a file/module
    scope, and these declarations will be ignored in a function scope (since function scopes
    do not declare named constants, just variables)).

SynthesizerVisitor:
  This visitor,  upon visiting a node in the parse tree, returns hardware corresponding
  to this node. Expressions return Node objects, functions/modules return full components, etc.
  - When visiting a function definition (which has its own scope) to synthesize it,
    the visitor looks up the function scope (at .scope in the node), clears the temporary
    value dictionary (.values), and does the synthesize one line (stmt) at a time. The
    current scope is stored in parsedCode.currentScope, which must be restored after finishing
    the function synthesis.

  TODO: spec has changed ^^. nodes now either mutate parsedCode.currentComponent or return Node instances
  corresponding to their value. Some nodes might return entire hardware as well.

Note:
  It seems that in a file scope, all definitions are permanent, while in a module scope,
  arbitrary stuff is allowed (variable assignment, function definitions, etc.), and in
  a function scope, only stmt (variable manipulation) is allowed, no permanent values.
  Is this something that I can rely on?
  This is important to note since in a file scope, named constants should perhaps be logged
  in some way using static elaboration; in a function scope, there are no constants; and
  in a moduleDef scope, I don't know what is going on.

Note:
  When parsing a module, we will need to handle all inputs before synthesizing functions (rules/etc.)
  so that the rules can refer to the inputs. Same with registers/submodules and module methods.

    TODO rename all parse nodes to ctx objects in documentation

'''

class Scope:
    '''
    name: for convenience only.
    self.parents: List of immediate parent scopes.
    self.permanentValues
        dict sending varName: str -> list[(parameters: tuple(int|str), ctx object)]
        last element of list is most recent.
    self.temporaryValues
        dict sending varName: str -> Node object
    '''
    def __init__(self, name: 'str', parents: 'list[Scope]'):
        self.parents = parents.copy()
        '''vars is a dictionary mapping names to permanent values.
        A function name maps to the functionDef node in the parse tree which defines the function.'''
        self.vars = {}
        '''values is a dictionary mapping names to temporary values.
        variable names map to nodes with the correct value.'''
        self.values = {}
        self.name = name
    def get(self, varName):
        if varName in self.vars:
            return self.vars[varName]
        for parent in self.parents:
            item = parent.get(varName)
            if item != None:
                return item
        return None
    def __str__(self):
        if len(self.values) == 0:
            return "Scope " + self.name
        return "Scope " + self.name + " with values " + str(self.values)
    def find(self, varName: 'str', parameters: 'list[int]' = None):
        '''Looks up the given name/parameter combo. Prefers current scope to parent scopes, and
        then prefers temporary values to permanent values. Returns whatever is found,
        probably a ctx object (functionDef) or a node object (variable value).'''
        return
    def set(self, value, varName: 'str', parameters: 'list[int]' = None):
        '''Sets the given name/parameters to the given value in temporary storage,
        overwriting the previous value (if any) in temporary storage.
        Used for assigning variables to nodes, typically with no paramters.'''
        return
    def setPermanent(self, value, varName: 'str', parameters: 'list[int|str]' = None):
        '''Sets the given name/parameters to the given value in permanent storage.
        Overrules but does not overwrite previous values with the same name.
        Used for logging declarations functions/modules; value is expected to be a ctx
        functionDef or similar.
        Note that some parameters may be unknown at the time of storing, hence the int|str type.'''
        return
    '''Note: we probably need a helper function to detect when given parameters match
    a list[int|str] description.'''



'''
Functions/modules/components will have nodes. Wires will be attached to nodes.
This is convenient during synthesis because we can map variables to the node
with the corresponding value and pass the nodes around, attaching wires as needed.
'''

class MType:
    '''A minispec type'''
    pass

class Any(MType):
    '''An unknown type'''
    pass

class Bit(MType):
    '''A bit type with n bits'''
    def __init__(self, n: 'int'):
        self.n = n

class Node:
    '''name is just for convenience.
    mtype is the minispec type of the value that the node corresponds to.'''
    def __init__(self, name: 'str' = "unnamed", mtype: 'MType' = Any()):
        self.name = name
        self.mtype = mtype
    def __repr__(self):
        return "Node(" + self.name + ")"
    def __str__(self):
        return self.name

class Component:
    '''
    Component = Function(children: list[Component], inputs: list[Node])
                + Wire(src: Node, dst: Node)

    TODO big change: Node object names no longer matter and are just for debugging.
    Thus hardware may be the same without matching node names.
    Note that function names still matter.

    Requirements:
        - No wire or function object may be reused. This does not apply two nodes.
        - A node may only be the dst of exactly one wire
        - A node must be in at most one function (as an input or output) and may appear at most once.
        - A wire's src and dst must be distinct

    Two components are the same hardware if:
        - They have the same structure
            - Wire:
            always
            - Function:
            inputs have matching names
            children may be permuted such that matching children represent the same hardware
        - Within a fixed permutation of children:
            - a pair of nodes are the same object in one if and only if they are the same object in the other.
    
    Testing for equality of hardware:
        1. Permute the children of the functions so that the nodes match
        2. Compare pairs of nodes for same-object property.
        If step 2 fails, choose a different valid permutation in step 1.
    These steps should be implemented recursively.
    eg, for step 1, compare each of the components of the second object with the first
    component of the first object; if one matches, keep going until they all match, then
    do step 2; if step 2 fails, try another first/second/etc. object.

    Note that testing for equality may mutate the second object by permuting the components.
    This should not matter since the order of the components should not matter.

    '''
    pass

class Function(Component):
    ''' children is a list of components. '''
    def __init__(self, name: 'str', children: 'list[Component]', inputs: 'list[Node]', output: 'Node'=None):
        self.name = name
        self.children = children
        self.inputs = inputs
        if output == None:
            self.output = Node('_' + name + '_output')
        else:
            self.output = output
    def __repr__(self):
        return "Function(" + self.name + ", " + self.children.__repr__() + ", " + self.inputs.__repr__() + ")"
    def __str__(self):
        if (len(self.children) == 0):
            return "Function " + self.name
        return "Function " + self.name + " with children " + " | ".join(str(x) for x in self.children)
    def getNodeListRecursive(self):
        '''returns a set of all nodes in self'''
        nodes = self.inputs.copy()
        nodes.append(self.output)
        for child in self.children:
            nodes = nodes + child.getNodeListRecursive()
        return nodes
    def matchStructure(self, other):
        '''returns true if self and other represent the same hardware, with the same ordering of components but not necessarily matching node identity structure'''
        if self.__class__ != other.__class__:
            return False
        if self.name != other.name:
            return False
        if len(self.inputs) != len(other.inputs):
            return False
        if len(self.children) != len(other.children):
            return False
        for i in range(len(self.children)):
            if not self.children[i].matchStructure(other.children[i]):
                return False
        return True
    def matchOrdered(self, other):
        '''returns true if self and other represent the same hardware, with the same ordering of components and the same node organization'''
        if not self.matchStructure(other):
            return False
        selfnodes = self.getNodeListRecursive()
        othernodes = other.getNodeListRecursive()
        if len(selfnodes) != len(othernodes):
            return False
        for i in range(len(selfnodes)):
            for j in range(i):
                if selfnodes[i] is selfnodes[j] and othernodes[i] is not othernodes[j]:
                    return False
                if selfnodes[i] is not selfnodes[j] and othernodes[i] is othernodes[j]:
                    return False
        return True
    def matchStep(self, other, i):
        '''tries to make self and other match by permuting other[i],...,other[-1].
        assumes self and other have the same length of children lists.
        mutates other to have matching order in children lists, even if the comparison fails.'''
        if i >= len(self.children):
            return self.matchOrdered(other)
        for j in range(i, len(self.children)):
            if other.children[j].match(self.children[i]):
                other.children[i], other.children[j] = other.children[j], other.children[i]
                if self.matchStep(other, i+1):
                    return True
                other.children[i], other.children[j] = other.children[j], other.children[i]
        return False
    def match(self, other):
        '''returns true if self and other represent the same hardware.
        mutates other to have matching order in children lists.'''
        if self.__class__ != other.__class__:
            return False
        if len(self.children) != len(other.children):
            return False
        return self.matchStep(other, 0)


class Wire(Component):
    ''' src and dst are Nodes.'''
    def __init__(self, src: 'Node', dst: 'Node'):
        assert src is not dst, "wire must have distinct ends"
        self.src = src
        self.dst = dst
    def __repr__(self):
        return "Wire(" + self.src.__repr__() + ", " + self.dst.__repr__() + ")"
    def __str__(self):
        return "wire from " + str(self.src) + " to " + str(self.dst)
    def getNodeListRecursive(self):
        '''returns a list of all nodes in self in a deterministic order'''
        return [self.src, self.dst]
    def matchStructure(self, other):
        '''returns true if self and other represent the same hardware, with the same ordering of components but not necessarily matching node identity structure'''
        return self.__class__ == other.__class__
    def matchOrdered(self, other):
        '''returns true if self and other represent the same hardware, with the same ordering of components and the same node organization'''
        return self.matchStructure(other)
    def match(self, other):
        '''returns true if self and other represent the same hardware.'''
        return self.matchOrdered(other)

def parseAndSynth(text, topLevel):

    builtinScope = Scope("built-ins", [])
    startingFile = Scope("startingFile", [builtinScope])

    class MinispecStructure:
        def __init__(self):
            '''will hold all created scopes. used for lookups.'''
            self.allScopes = [builtinScope, startingFile]
            self.currentScope = startingFile
            self.currentComponent = None  # a function/module component. used during synthesis.

    parsedCode = MinispecStructure()

    class StaticTypeListener(build.MinispecPythonListener.MinispecPythonListener):
        def enterPackageDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.PackageDefContext):
            '''The entry node to the parse tree.'''
            print(inspect.getsource(ctx.getText))
            print(ctx.getText())

        def enterFunctionDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionDefContext):
            '''We are defining a function. We need to give this function a corresponding scope.'''
            # print("function")
            # print(inspect.getsource(ctx.getText))
            # print(ctx.getText())
            # print(ctx.typeName().getText())
            # print(ctx.functionId().getText())
            functionName = ctx.functionId().getText() # get the name of the function
            print("defining a function", functionName)
            #log the function's scope
            parsedCode.currentScope.vars[functionName] = ctx
            functionScope = Scope(functionName, [parsedCode.currentScope])
            ctx.scope = functionScope
            parsedCode.currentScope = functionScope
            parsedCode.allScopes.append(functionScope)
        def exitFunctionDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionDefContext):
            '''We have defined a function, so we step back into the parent scope.'''
            assert len(parsedCode.currentScope.parents) == 1, "function can only have parent scope"
            parsedCode.currentScope = parsedCode.currentScope.parents[0]
        
        def enterVarExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarExprContext):
            print("got a var", ctx.getText())

    class SynthesizerVisitor(build.MinispecPythonVisitor.MinispecPythonVisitor):
        '''Each method returns a component (module/function/etc.)
        nodes of type exprPrimary return the node corresponding to their value.
        stmt do not return anything; they mutate the current scope and the current hardware.'''
        def visitFunctionDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionDefContext):
            print("synth function", ctx.functionId().getText())
            print(ctx.getText())
            functionName = ctx.functionId().getText()
            print()
            functionScope = ctx.scope
            functionScope.values = {} # clear the temporary values
            # extract arguments to function and set up the input nodes
            inputNodes = []
            for arg in ctx.argFormals().argFormal():
                argType = arg.typeName() # typeName parse tree node
                argName = arg.argName.getText() # name of the variable
                argNode = Node(argName)
                functionScope.values[argName] = argNode
                inputNodes.append(argNode)
            print(functionScope)
            funcComponent = Function(functionName, [], inputNodes)
            # log the current component/scope
            previousComponent = parsedCode.currentComponent
            parsedCode.currentComponent = funcComponent
            previousScope = parsedCode.currentScope
            parsedCode.currentScope = functionScope
            # synthesize the function internals
            for stmt in ctx.stmt():
                print("Found a statement!")
                print(stmt.toStringTree(recog=parser))
                self.visit(stmt)
                print("Left statement")
            parsedCode.currentComponent = previousComponent #reset the current component/scope
            parsedCode.currentScope = previousScope
            return funcComponent

        def visitCallExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CallExprContext):
            '''We are calling a function. We synthesize the given function, wire it to the appropriate inputs,
            and return the function output node (which corresponds to the value of the function).'''
            print("calling", ctx.getText())
            # for now, we will assume that the fcn=exprPrimary in the callExpr must be a varExpr (with a var=anyIdentifier term).
            # this might also be a fieldExpr; I don't think there are any other possibilities with the current minispec specs.
            functionToCall = ctx.fcn.var.getText()
            functionDef = parsedCode.currentScope.get(functionToCall)  # look up the function to call
            print("visiting func def")
            funcComponent = self.visit(functionDef)  #synthesize the function internals
            print("visited func def")
            # hook up the funcComponent to the arguments passed in.
            for i in range(len(ctx.expression())):
                expr = ctx.expression()[i]
                exprNode = self.visit(expr) # visit the expression and get the corresponding node
                funcInputNode = funcComponent.inputs[i]
                wireIn = Wire(exprNode, funcInputNode)
                parsedCode.currentComponent.children.append(wireIn)
            parsedCode.currentComponent.children.append(funcComponent)
            return funcComponent.output  # return the value of this call, which is the output of the function

        def visitOperatorExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.OperatorExprContext):
            '''This is an expression corresponding to a binary operation (which may be a unary operation,
            which may be an exprPrimary). We return the node with the corresponding output value.'''
            return self.visit(ctx.binopExpr())

        def visitBinopExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BinopExprContext):
            if ctx.unopExpr():  # our binary expression is actually a unopExpr.
                return self.visit(ctx.unopExpr())
            print("doing a binary skip")
            left = self.visit(ctx.left)
            right = self.visit(ctx.right)
            op = ctx.op.text
            binComponent = Function(op, [], [Node("l"), Node("r")])
            leftWireIn = Wire(left, binComponent.inputs[0])
            rightWireIn = Wire(right, binComponent.inputs[1])
            for component in [binComponent, leftWireIn, rightWireIn]:
                parsedCode.currentComponent.children.append(component)
            return binComponent.output

        def visitUnopExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.UnopExprContext):
            if not ctx.op:  # our unopExpr is actually just an exprPrimary.
                return self.visit(ctx.exprPrimary())
            return self.visitChildren(ctx)

        def visitVarExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarExprContext):
            '''We are visiting a variable/function name. We look it up and return the correpsonding information
            (which may be a Node or a node, for instance).'''
            print(ctx.var.getText())
            return parsedCode.currentScope.values[ctx.var.getText()]

        def visitLetBinding(self, ctx: build.MinispecPythonParser.MinispecPythonParser.LetBindingContext):
            '''A let binding declares a variable or a concatenation of variables and optionally assigns
            them to the given expression node ("rhs").'''
            if not ctx.rhs:
                return  #if there is no assignment, we can skip this line
            rhsNode = self.visit(ctx.rhs)  #we expect a node corresponding to the desired value
            varName = ctx.lowerCaseIdentifier(0).getText() #the variable we are assigning
            parsedCode.currentScope.values[varName] = rhsNode
            # for now, we only handle the case of assigning a single variable (no concatenations).
            # nothing to return.
            
        def visitReturnExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ReturnExprContext):
            '''This is the return expression in a function. We need to put the correct wire
            attaching the right hand side to the output of the function.'''
            rhs = self.visit(ctx.expression())  # the node with the value to return
            returnWire = Wire(rhs, parsedCode.currentComponent.output)
            parsedCode.currentComponent.children.append(returnWire)

    print("text:")
    print(text, "\n")
    data = antlr4.InputStream(text)
    lexer = build.MinispecPythonLexer.MinispecPythonLexer(data)
    stream = antlr4.CommonTokenStream(lexer)
    parser = build.MinispecPythonParser.MinispecPythonParser(stream)
    tree = parser.packageDef()  #start parsing at the top-level packageDef rule (so "tree" is the root of the parse tree)
    print(tree.toStringTree(recog=parser)) #prints the parse tree in lisp form (see https://www.antlr.org/api/Java/org/antlr/v4/runtime/tree/Trees.html )

    walker = build.MinispecPythonListener.ParseTreeWalker()
    listener = StaticTypeListener()
    walker.walk(listener, tree)  # walk the listener through the tree

    print()
    print("synthesizing")
    synthesizer = SynthesizerVisitor()
    ctxToSynth = startingFile.get(topLevel)
    assert ctxToSynth != None, "Failed to find topLevel function/module"
    output = synthesizer.visit(ctxToSynth) #look up the function in the given file and synthesize it. store the result in 'output'
    return output

if __name__ == '__main__':

    import pathlib

    textFile = pathlib.Path(__file__).with_name("tests").joinpath("functions.ms")
    text = textFile.read_text()

    output = parseAndSynth(text, 'g')

    print()
    print("output:")
    print(output.__repr__())

    ga, gb, gc, go = Node('ga'), Node('gb'), Node('gc'), Node('go')
    fa, fb, fo = Node('fa'), Node('fb'), Node('fo')
    xfa, xfb, xfo = Node('xfa'), Node('xfb'), Node('xfo')
    xga, xgb, xgo = Node('xga'), Node('xgb'), Node('xgo')

    expected = Function("g", [Function("f", [Function("^", [], [xfa, xfb], xfo),
                                            Wire(fa, xfa), Wire(fb, xfb), Wire(xfo, fo)], [fa, fb], fo),
                            Function("^", [], [xga, xgb], xgo),
                            Wire(ga, xga), Wire(gb, xgb), Wire(xgo, fa), Wire(gc, fb), Wire(fo, go)], [ga, gb, gc], go)


    # expected = Function("f", [Function("^", [], [xfa, xfb], xfo), Wire(fa, xfa),
    #                             Wire(fb, xfb), Wire(xfo, fo)], [fa, fb], fo)

    print()
    print("testing correctness:")
    print(output.__repr__())
    print(expected.__repr__())
    print(output.match(expected))
