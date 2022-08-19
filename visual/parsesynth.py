import inspect

import antlr4
import build.MinispecPythonParser
import build.MinispecPythonLexer
import build.MinispecPythonListener
import build.MinispecPythonVisitor

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


    TODO rename all parse nodes to ctx objects in documentation

'''

class Scope:
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

'''
Functions/modules/components will have nodes. Wires will be attached to nodes.
This is convenient during synthesis because we can map variables to the node
with the corresponding value and pass the nodes around, attaching wires as needed.
'''

def sameList(l1, l2):
    '''returns true if l1 and l2 are permutations of each other, up to =='''
    if len(l1) == len(l2):
        if len(l1) == 1:
            return l1[0] == l2[0]
        for i in range(len(l1)):
            if l1[0] == l2[i]:
                l1next = l1[1:]
                l2next = l2[0:i] + l2[i+1:]
                return sameList(l1next, l2next)
        return False
    return False

class Node:
    '''name is just for convenience.'''
    def __init__(self, name="unnamed"):
        self.name = name
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
    
    '''
    pass

class Function(Component):
    ''' children is a list of components. '''
    def __init__(self, name: 'str', children: 'list[Component]', inputs: 'list[Node]'):
        self.name = name
        self.children = children
        self.inputs = inputs
        self.output = Node('_' + name + '_output')
    def __repr__(self):
        return "Function(" + self.name + ", " + self.children.__repr__() + ", " + self.inputs.__repr__() + ")"
    def __str__(self):
        if (len(self.children) == 0):
            return "Function " + self.name
        return "Function " + self.name + " with children " + " | ".join(str(x) for x in self.children)

class Wire(Component):
    ''' src and dst are Nodes.'''
    def __init__(self, src: 'Node', dst: 'Node'):
        self.src = src
        self.dst = dst
    def __repr__(self):
        return "Wire(" + self.src.__repr__() + ", " + self.dst.__repr__() + ")"
    def __str__(self):
        return "wire from " + str(self.src) + " to " + str(self.dst)

class OrganizedCircuit:
    '''Used for equality testing.
    Ordinary components contain references to nodes; an OrganizedCircuit has a map
    nodes -> functions/modules/wires containing the node
    Note: Mutation of an OrganizedCircuit or Component after creating both is undefined behavior.
    
    self.nodes is a dictionary Node node -> dictionary {Function f, Number n, list[Wire] a, Wire v} with:
        f is the function with node as an input/output
        n is the index of node in the inputs to f, or -1 if node is the output of f
        a is a list of wires with node as its src
        v is the wire with node as its dst'''
    def __init__(self, func):
        self.nodes = {}
        self.functions = set()  #wires and functions may only occur once in a component, so we log them for reference.
        self.wires = set()
        def process(component):
            if component.__class__ == Function:
                func = component
                assert func not in self.functions, "a function may only appear once"
                self.functions.add(func)
                for i in range(-1,len(func.inputs)):
                    node = func.output if i == -1 else func.inputs[i]
                    if node not in self.nodes:
                        self.nodes[node] = {'a':[]}
                    nodeLog = self.nodes[node]
                    assert 'f' not in nodeLog, "node can only be in one function"
                    nodeLog['f'] = func
                    nodeLog['n'] = i
                for child in component.children:
                    process(child)
            elif component.__class__ == Wire:
                wire = component
                assert wire not in self.wires, "a wire may only appear once"
                self.wires.add(wire)
                if wire.src not in self.nodes:
                    self.nodes[wire.src] = {'a':[]}
                srcLog = self.nodes[wire.src]
                assert wire not in srcLog['a'], "The same wire cannot be reused"
                srcLog['a'].append(wire)
                if wire.dst not in self.nodes:
                    self.nodes[wire.dst] = {'a':[]}
                dstLog = self.nodes[wire.dst]
                assert 'v' not in dstLog, "Node can only be dst of one wire"
                dstLog['v'] = wire
            else:
                assert False, "Component must have one of the given types"
        process(func)
    def __eq__(self, other):
        '''returns true if self and other correspond to the same hardware layout, with the same names'''
        if self.__class__ != other.__class__:
            return False
        selffunc, otherfunc = list(self.functions), list(other.functions)
        selfnodes, othernodes  = list(self.nodes), list(other.nodes)  #the node objects
        k = lambda node: node.name
        selfnodes.sort(key = k)
        othernodes.sort(key = k)
        selffunc.sort(key = k)
        otherfunc.sort(key = k)
        print("comparing")
        print(selfnodes)
        print(othernodes)
        print(selffunc)
        print(otherfunc)
    def __str__(self):
        return str(self.nodes)
    def toComponent(self):
        pass

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
        rightWireIn = Wire(left, binComponent.inputs[1])
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



import pathlib

textFile = pathlib.Path(__file__).with_name("tests").joinpath("functions.ms")
text = textFile.read_text()

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
output = synthesizer.visit(startingFile.get("g")) #look up the function g in the given file and synthesize it. store the result in 'output'

print()
print("output:")
print(output.__repr__())

print(OrganizedCircuit(output))

print()
print(OrganizedCircuit(output) == OrganizedCircuit(output))