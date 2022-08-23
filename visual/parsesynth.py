import inspect

import antlr4
import build.MinispecPythonParser
import build.MinispecPythonLexer
import build.MinispecPythonListener
import build.MinispecPythonVisitor


'''
Implementation Agenda:

    - Parametrics (+ associated variable lookups)

Notes for parametrics:
    paramFormals are used when defining functions/modules/types, and may be Integer n or
    5 (or an expression that evaluates to an integer) or 'type' X (as in creating a typedef alias of vector).
    params are used when calling functions/synth modules/invoking custom parameterized types, and may
    only be an integer or the name of a type.

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
        dict sending varName: str -> list[(parameters: list[int|str], ctx object)]
        last element of list is most recent.
        a function name maps to the functionDef node in the parse tree which defines the function.
    self.temporaryValues
        dict sending varName: str -> Node object
        variable names map to nodes with the correct value.
    permanentValues are for static information, while temporaryValues are for information during synthesis.
    '''
    def __init__(self, name: 'str', parents: 'list[Scope]'):
        self.parents = parents.copy()
        self.name = name
        self.permanentValues = {}
        self.temporaryValues = {}
    def __str__(self):
        if len(self.permanentValues) == 0 and len(self.temporaryValues) == 0:
            return "Scope " + self.name
        output = "Scope " + self.name + " with parents " + ", ".join([parent.name for parent in self.parents]) + " with permanent values"
        for varName in self.permanentValues:
            output += "\n  " + varName + ": "
            for ex in self.permanentValues[varName]:
                output += "\n    " + "params: " + str(ex[0]) + " and value: " + str(ex[1].__class__)
        output += "\nand temporary values"
        for varName in self.temporaryValues:
            output += "\n  " + varName + ": " + str(self.temporaryValues[varName])
        return output
    def clearTemporaryValues(self):
        '''clears temporary values used in synthesis. should be called after synthesizing a function/module.'''
        self.temporaryValues = {}
    def matchParams(visitor, intValues: 'list[int]', storedParams: 'list[ctxType|str]'):
        '''returns a dictionary mapping str -> int if intValues can fit storedParams.
        returns None otherwise.'''
        print('comparing', intValues, storedParams)
        if len(intValues) != len(storedParams):
            return None
        d = {}  #make sure parameters match
        for i in range(len(intValues)):
            if storedParams[i].__class__ == str:
                d[storedParams[i]] = intValues[i]
            elif visitor.visit(storedParams[i]) != intValues[i]:
                return None
        return d
    def get(self, visitor, varName: 'str', parameters: 'list[int]' = None) -> 'ctxType|Node|tuple[ctxType,dict]':
        '''Looks up the given name/parameter combo. Prefers current scope to parent scopes, and
        then prefers temporary values to permanent values. Returns whatever is found,
        probably a ctx object (functionDef) or a node object (variable value).
        Returns an object.
        Returns a tuple (ctx/Node, paramMappings) where paramMappings is a dictionary
        str -> int that shows how the stored parameters were mapped to match parameters to
        the stored parameters.'''
        if parameters == None:
            parameters = []
        if varName in self.temporaryValues:
            return self.temporaryValues[varName]
        if varName in self.permanentValues:
            for storedParams, ctx in self.permanentValues[varName][::-1]: #iterate backwards through the stored values, looking for the most recent match.
                d = Scope.matchParams(visitor, parameters, storedParams)
                if d != None:
                    return (ctx, d)
        for parent in self.parents:
            output = parent.get(visitor, varName, parameters)
            if output != None:
                return output
        return None
    def set(self, value, varName: 'str', parameters: 'list[int]' = None):
        '''Sets the given name/parameters to the given value in temporary storage,
        overwriting the previous value (if any) in temporary storage.
        Used for assigning variables to nodes, typically with no paramters.
        Currently ignores parameters.'''
        if parameters == None:
            parameters = []
        self.temporaryValues[varName] = value
    def setPermanent(self, value, varName: 'str', parameters: 'list[ctxType|str]' = None):
        '''Sets the given name/parameters to the given value in permanent storage.
        Overrules but does not overwrite previous values with the same name.
        Used for logging declarations functions/modules; value is expected to be a ctx
        functionDef or similar.
        Note that some parameters may be unknown at the time of storing, hence the ctx|str type.
        str corresponds to a value that must be fed it; ctx corresponds to a fixed value that can
        be compiled to an int.'''
        if parameters == None:
            parameters = []
        if varName not in self.permanentValues:
            self.permanentValues[varName] = []
        self.permanentValues[varName].append((parameters, value))
    '''Note: we probably need a helper function to detect when given parameters match
    a list[int|str] description.'''

class BuiltInScope(Scope):
    '''The minispec built-ins. Behaves slightly differently from other scopes.'''
    def __init__(self, name: 'str', parents: 'list[Scope]'):
        self.parents = parents.copy()
        self.name = name
        self.permanentValues = {}
        self.temporaryValues = {}
    def get(self, visitor, varName: 'str', parameters: 'list[int]' = None) -> 'ctxType|Node|tuple[ctxType,dict]':
        '''Looks up the given name/parameter combo. Prefers current scope to parent scopes, and
        then prefers temporary values to permanent values. Returns whatever is found,
        probably a ctx object (functionDef) or a node object (variable value).
        Returns an object.
        Returns a tuple (object, paramMappings) where paramMappings is a dictionary
        str -> int that shows how the stored parameters were mapped to match parameters to
        the stored parameters.'''
        if varName == 'Bit':
            assert len(parameters) == 1, "bit takes exactly one parameter"
            n = parameters[0]
            if n not in Bit.createdBits:
                Bit.createdBits[n] = Bit(n)
            return Bit.createdBits[n]
        if varName == 'Vector':
            assert len(parameters) == 2, "vector takes exactly two parameters"
            k, typeValue = parameters
            if (k, typeValue) not in Vector.createdVectors:
                Vector.createdVectors[(k, typeValue)] = Vector(k, typeValue)
            return Vector.createdVectors[(k, typeValue)]

#type annotation for context objects.
ctxType = ' | '.join([ctxType for ctxType in dir(build.MinispecPythonParser.MinispecPythonParser) if ctxType[-7:] == "Context"][:-3])

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
    def __str__(self):
        return "Any"

class Bit(MType):
    '''A bit type with n bits. All bit objects must be unique.'''
    createdBits = {}  # a map n -> Bit(n)
    def __init__(self, n: 'IntegerLiteral'):
        assert n.__class__ == IntegerLiteral, f"A bit must be an integer literal, not {n} which is {n.__class__}"
        n = n.value #extract the value of the integer literal
        assert n not in Bit.createdBits, "All bit objects must be unique."
        self.n = n
    def __str__(self):
        return "Bit#(" + str(self.n) + ")"

class Bool(MType):
    '''The boolean type'''
    def __str__(self):
        return "Bool"

class Vector(MType):
    '''The Vector(k, tt) type'''
    createdVectors = {} # a map (k, tt) -> Vector(k, tt)
    def __init__(self, k: 'int', typeValue: 'MType'):
        self.k = k
        self.typeValue = typeValue
    def __str__(self):
        return "Vector#(" + str(self.k) + ", " + str(self.typeValue) + ")"

'''We will eventually want a class whose instances represent minispec literals, including:
integers, booleans, bit values, etc.
This class (and subclasses) will describe how to operate/coerce on these values.

#TODO finish implementing literals.
#Still need to decide exactly how creation/conversion will work.

Binary operators:
'**','*', '/', '%', '+', '-', '<<', '>>', '<', '<=', '>', '>=', '==', '!=', '&', '^', '^~', '~^', '|', '&&', '||'
Names for methods in code:
** is pow.
* is mul.
/ is div.
% is mod.
+ is add.
- is sub.
<< is sleft.
>> is sright.
< is lt.
<= is le, in terms of lt, eq
> is gt, in terms of lt
>= is ge, in terms of lt, eq
== is eq.
!= is neq, in terms of eq
& is bitand.
^ is bitxor.
^~ is #TODO bitxnor?
~^ is #TODO
| is bitor.
&& is booleanand.
|| is booleanor.

'''

class MLiteral():
    '''A minispec literal'''
    '''Coercions for arithmetic operations are performed so that variant-specific
    calls always have the same class.'''
    def __init__(self, value: 'str'):
        '''Given a minispec literal as a string, return the
        appropriate literal value.'''
        if value == "True" or value == "False":
            return BooleanLiteral(value)
        assert False, f"Unknown literal {value}"
    def coerceArithmetic(first, second):
        if first.__class__ == IntegerLiteral and second.__class__ == BooleanLiteral:
            first = second.fromIntegerLiteral(first)
        elif first.__class__ == BooleanLiteral and second.__class__ == IntegerLiteral:
            second = first.fromIntegerLiteral(second)
        return (first, second)
    def coerceBoolean(first, second):
        assert first.__class__ == BooleanLiteral and second.__class__ == BooleanLiteral, "Boolean arithmetic requires boolean values"
        return first, second
    def pow(first, second):
        raise Exception("Not implemented")
    def mul(first, second):
        first, second = MLiteral.coerceArithmetic(first, second)
        return first.mul(second)
    def div(first, second):
        raise Exception("Not implemented")
    def mod(first, second):
        raise Exception("Not implemented")
    def add(first, second):
        first, second = MLiteral.coerceArithmetic(first, second)
        return first.add(second)
    def sub(first, second):
        first, second = MLiteral.coerceArithmetic(first, second)
        return first.sub(second)
    def sleft(first, second):
        raise Exception("Not implemented")
    def sright(first, second):
        raise Exception("Not implemented")
    def lt(first, second):
        raise Exception("Not implemented")
    def le(first, second):
        raise Exception("Not implemented")
    def gt(first, second):
        raise Exception("Not implemented")
    def ge(first, second):
        raise Exception("Not implemented")
    def eq(first, second):
        raise Exception("Not implemented")
    def neq(first, second):
        raise Exception("Not implemented")
    def bitand(first, second):
        raise Exception("Not implemented")
    def bitxor(first, second):
        raise Exception("Not implemented")
    def bitxnor(first, second):
        raise Exception("Not implemented")
    def bitor(first, second):
        raise Exception("Not implemented")
    def booleanand(first, second):
        raise Exception("Not implemented")
    def booleanand(first, second):
        first, second = MLiteral.coerceBoolean(first, second)
        return first.booleanand(second)
    def booleanor(first, second):
        first, second = MLiteral.coerceBoolean(first, second)
        return first.booleanand(second)

class IntegerLiteral(MLiteral):
    '''self.value is an integer'''
    def __init__(self, value: 'int'):
        assert value.__class__ == int
        self.value = value
    def __repr__(self):
        return "IntegerLiteral(" + str(self.value) + ")"
    def __str__(self):
        return str(self.value)
        #return "IntegerLiteral(" + str(self.value) + ")" #possibly useful for debugging purposes
    def __eq__(self, other):
        if other.__class__ != self.__class__:
            return False
        return self.value == other.value
    def __hash__(self):
        return hash(self.value)
    def toInt(self):
        '''Returns the python integer represented by self'''
        return self.value
    def pow(self, other):
        return IntegerLiteral(self.value ** other.value)
    def mul(self, other):
        return IntegerLiteral(self.value * other.value)
    def div(self, other):
        return IntegerLiteral(self.value // other.value)
    def mod(self, other):
        return IntegerLiteral(self.value % other.value)
    def add(self, other):
        return IntegerLiteral(self.value + other.value)
    def sub(self, other):
        return IntegerLiteral(self.value - other.value)
    def sleft(self, other):
        raise Exception("Not implemented")
    def sright(self, other):
        raise Exception("Not implemented")
    def lt(self, other):
        return BooleanLiteral(self.value < other.value)
    def le(self, other):
        return BooleanLiteral(self.value <= other.value)
    def gt(self, other):
        return BooleanLiteral(self.value > other.value)
    def ge(self, other):
        return BooleanLiteral(self.value >= other.value)
    def eq(self, other):
        return BooleanLiteral(self.value == other.value)
    def neq(self, other):
        return BooleanLiteral(self.value != other.value)
    def bitand(self, other):
        raise Exception("Not implemented")
    def bitxor(self, other):
        raise Exception("Not implemented")
    def bitxnor(self, other):
        raise Exception("Not implemented")
    def bitor(self, other):
        raise Exception("Not implemented")
    def booleanand(self, other):
        raise Exception("Not implemented")
    def booleanor(self, other):
        raise Exception("Not implemented")

class BitLiteral(MLiteral):
    '''n is the number of bits. value is an integer 0 <= value < 2**n.'''
    def __init__(self, n: 'int', value: 'int'):
        assert n.__class__ == int
        assert value.__class__ == int
        self.n = n
        self.value = value % 2**n
    def __repr__(self):
        return "BitLiteral(" + str(self.n) + "," + str(self.value) + ")"
    def __str__(self):
        output = ""
        val = self.value
        for i in range(self.n):
            output = output + (val % 2)
            val /= 2
        return str(self.n) + "'b" + output
    def fromIntegerLiteral(self, i):
        return BitLiteral(self.n, i.toInt())
    def pow(self, other):
        raise Exception("Not implemented")
    def mul(self, other):
        raise Exception("Not implemented")
    def div(self, other):
        raise Exception("Not implemented")
    def mod(self, other):
        raise Exception("Not implemented")
    def add(self, other):
        return BitLiteral(max(self.n, other.n), self.value + other.value)
    def sub(self, other):
        raise Exception("Not implemented")
    def sleft(self, other):
        raise Exception("Not implemented")
    def sright(self, other):
        raise Exception("Not implemented")
    def lt(self, other):
        return BooleanLiteral(self.value < other.value)
    def le(self, other):
        return BooleanLiteral(self.value <= other.value)
    def gt(self, other):
        return BooleanLiteral(self.value > other.value)
    def ge(self, other):
        return BooleanLiteral(self.value >= other.value)
    def eq(self, other):
        return BooleanLiteral(self.value == other.value)
    def neq(self, other):
        return BooleanLiteral(self.value != other.value)
    def bitand(self, other):
        raise Exception("Not implemented")
    def bitxor(self, other):
        raise Exception("Not implemented")
    def bitxnor(self, other):
        raise Exception("Not implemented")
    def bitor(self, other):
        raise Exception("Not implemented")
    def booleanand(self, other):
        raise Exception("Not implemented")
    def booleanor(self, other):
        raise Exception("Not implemented")

class BooleanLiteral(MLiteral):
    '''value is a boolean'''
    def __init__(self, value: 'bool'):
        self.value = value
    def __repr__(self):
        return "BooleanLiteral(" + str(self.value) + ")"
    def __str__(self):
        return str(self.value)
    def pow(self, other):
        raise Exception("Not implemented")
    def mul(self, other):
        raise Exception("Not implemented")
    def div(self, other):
        raise Exception("Not implemented")
    def mod(self, other):
        raise Exception("Not implemented")
    def add(self, other):
        raise Exception("Not implemented")
    def sub(self, other):
        raise Exception("Not implemented")
    def sleft(self, other):
        raise Exception("Not implemented")
    def sright(self, other):
        raise Exception("Not implemented")
    def lt(self, other):
        raise Exception("Not implemented")
    def le(self, other):
        raise Exception("Not implemented")
    def gt(self, other):
        raise Exception("Not implemented")
    def ge(self, other):
        raise Exception("Not implemented")
    def eq(self, other):
        raise Exception("Not implemented")
    def neq(self, other):
        raise Exception("Not implemented")
    def bitand(self, other):
        raise Exception("Not implemented")
    def bitxor(self, other):
        raise Exception("Not implemented")
    def bitxnor(self, other):
        raise Exception("Not implemented")
    def bitor(self, other):
        raise Exception("Not implemented")
    def booleanand(self, other):
        return BooleanLiteral(self.value and other.value)
    def booleanor(self, other):
        return BooleanLiteral(self.value or other.value)

class MaybeLiteral(MLiteral):
    '''value is Valid or Invalid'''
    #TODO figure out how to implement Valid
    def pow(self, other):
        raise Exception("Not implemented")
    def mul(self, other):
        raise Exception("Not implemented")
    def div(self, other):
        raise Exception("Not implemented")
    def mod(self, other):
        raise Exception("Not implemented")
    def add(self, other):
        raise Exception("Not implemented")
    def sub(self, other):
        raise Exception("Not implemented")
    def sleft(self, other):
        raise Exception("Not implemented")
    def sright(self, other):
        raise Exception("Not implemented")
    def lt(self, other):
        raise Exception("Not implemented")
    def le(self, other):
        raise Exception("Not implemented")
    def gt(self, other):
        raise Exception("Not implemented")
    def ge(self, other):
        raise Exception("Not implemented")
    def eq(self, other):
        raise Exception("Not implemented")
    def neq(self, other):
        raise Exception("Not implemented")
    def bitand(self, other):
        raise Exception("Not implemented")
    def bitxor(self, other):
        raise Exception("Not implemented")
    def bitxnor(self, other):
        raise Exception("Not implemented")
    def bitor(self, other):
        raise Exception("Not implemented")
    def booleanand(self, other):
        raise Exception("Not implemented")
    def booleanor(self, other):
        raise Exception("Not implemented")

class DontCareLiteral(MLiteral):
    '''only one kind, "?" '''
    def __init__(self):
        pass
    # Returns itself for all binary operations
    def pow(self, other):
        return self
    def mul(self, other):
        return self
    def div(self, other):
        return self
    def mod(self, other):
        return self
    def add(self, other):
        return self
    def sub(self, other):
        return self
    def sleft(self, other):
        return self
    def sright(self, other):
        return self
    def lt(self, other):
        return self
    def le(self, other):
        return self
    def gt(self, other):
        return self
    def ge(self, other):
        return self
    def eq(self, other):
        return self
    def neq(self, other):
        return self
    def bitand(self, other):
        return self
    def bitxor(self, other):
        return self
    def bitxnor(self, other):
        return self
    def bitor(self, other):
        return self
    def booleanand(self, other):
        return self
    def booleanor(self, other):
        return self

class Node:
    '''name is just for convenience.
    mtype is the minispec type of the value that the node corresponds to.
    id is a unique id number for each node created.'''
    id = 0  #one for each node created
    def __init__(self, name: 'str' = "", mtype: 'MType' = Any()):
        self.name = name
        self.mtype = mtype
        self.id = Node.id
        Node.id += 1
    def __repr__(self):
        return "Node(" + str(self.id) + ": " + str(self.mtype) + ")"
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
        return "Function(" + self.name + ", " + self.children.__repr__() + ", " + self.inputs.__repr__() + ", " + self.output.__repr__() + ")"
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
        if self.name != other.name:
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

def parseAndSynth(text, topLevel, topLevelParameters: 'list[int]' = None):
    if topLevelParameters == None:
        topLevelParameters = []

    builtinScope = BuiltInScope("built-ins", [])
    startingFile = Scope("startingFile", [builtinScope])

    class MinispecStructure:
        def __init__(self):
            '''will hold all created scopes. used for lookups.'''
            self.allScopes = [builtinScope, startingFile]
            self.currentScope = startingFile
            self.currentComponent = None  # a function/module component. used during synthesis.
            self.parameterBindings = {}
            '''self.parameterBindings is a dictionary str -> int telling functions which parameters
            have been bound. Should be set whenever calling a function.'''
            self.lastParameterLookup = []
            '''self.lastParameterLookup is a list consisting of the last integer values used to look up
            a function call. Should be set whenever calling a function. Used to determine how to name
            the function in the corresponding component.'''
        def reset(self):
            self.__init__()
        def __setattr__(self, __name: str, __value: Any) -> None:
            if __name == 'lastParameterLookup':
                for j in __value:
                    print(j.__class__)
                print(__value.__repr__())
            self.__dict__[__name] = __value


    parsedCode = MinispecStructure()

    class StaticTypeListener(build.MinispecPythonListener.MinispecPythonListener):
        def enterPackageDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.PackageDefContext):
            '''The entry node to the parse tree.'''

        def enterFunctionDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionDefContext):
            '''We are defining a function. We need to give this function a corresponding scope.'''
            functionName = ctx.functionId().name.getText() # get the name of the function
            params = []
            if ctx.functionId().paramFormals():
                for param in ctx.functionId().paramFormals().paramFormal():
                    # each parameter is either an integer or a name.
                    if param.param():  # our parameter is an actual integer or type name, which will be evaluated immediately before lookups.
                        params.append(param.param())
                    elif param.intName:  # param is a variable name. extract the name.
                        params.append(param.intName.getText())
                    else:
                        assert False, "parameters with typeValues are not supported yet"
            #log the function's scope
            parsedCode.currentScope.setPermanent(ctx, functionName, params)
            functionScope = Scope(functionName, [parsedCode.currentScope])
            ctx.scope = functionScope
            parsedCode.currentScope = functionScope
            parsedCode.allScopes.append(functionScope)

        def exitFunctionDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionDefContext):
            '''We have defined a function, so we step back into the parent scope.'''
            assert len(parsedCode.currentScope.parents) == 1, "function can only have parent scope"
            parsedCode.currentScope = parsedCode.currentScope.parents[0]

        def enterVarBinding(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarBindingContext):
            '''We have found a named constant. Log it for later evaluation (since it may depend on other named constants, etc.)'''
            for varInit in ctx.varInit():
                if varInit.rhs:
                    parsedCode.currentScope.setPermanent(varInit.rhs, varInit.var.getText())


    '''
    Documentation for SynthesizerVisitor visit method return types:

    visitLowerCaseIdentifier: 
    visitUpperCaseIdentifier: 
    visitIdentifier: 
    visitAnyIdentifier: 
    visitArg: 
    visitArgs: 
    visitArgFormal: 
    visitArgFormals: 
    visitParam: 
    visitParams: 
    visitParamFormal: 
    visitParamFormals: 
    visitTypeName: 
    visitPackageDef: 
    visitPackageStmt: 
    visitImportDecl: 
    visitBsvImportDecl: 
    visitTypeDecl: 
    visitTypeDefSynonym: 
    visitTypeId: 
    visitTypeDefEnum: 
    visitTypeDefEnumElement: 
    visitTypeDefStruct: 
    visitStructMember: 
    visitVarBinding: 
    visitLetBinding: 
    visitVarInit: 
    visitModuleDef: 
    visitModuleId: 
    visitModuleStmt: 
    visitSubmoduleDecl: 
    visitInputDef: 
    visitMethodDef: 
    visitRuleDef: 
    visitFunctionDef: Returns the function hardware
    visitFunctionId: 
    visitVarAssign: 
    visitMemberLvalue: 
    visitIndexLvalue: 
    visitSimpleLvalue: 
    visitSliceLvalue: 
    visitOperatorExpr: Node or MLiteral corresponding to the value of the expression
    visitCondExpr: 
    visitCaseExpr: 
    visitCaseExprItem: 
    visitBinopExpr: Node or MLiteral corresponding to the value of the expression
    visitUnopExpr: Node or MLiteral corresponding to the value of the expression
    visitVarExpr: 
    visitBitConcat: 
    visitStringLiteral: 
    visitIntLiteral: Corresponding MLiteral
    visitReturnExpr: Nothing, mutates current function hardware
    visitStructExpr: 
    visitUndefinedExpr: Corresponding MLiteral
    visitSliceExpr: 
    visitCallExpr: Returns the output node of the function call or a literal (if the function gets constant-folded)
        Note that constant-folding elimination of function components occurs here, not in functionDef, so that the function to synthesize is not eliminated.
    visitFieldExpr: 
    visitParenExpr: Node or MLiteral corresponding to the value of the expression
    visitMemberBinds: 
    visitMemberBind: 
    visitBeginEndBlock: 
    visitRegWrite: 
    visitStmt: No returns since stmt mutates existing hardware
    visitIfStmt: 
    visitCaseStmt: 
    visitCaseStmtItem: 
    visitCaseStmtDefaultItem: 
    visitForStmt: 
    
    
    '''

    def isMLiteral(value):
        '''Returns whether or not value is an MLiteral'''
        return issubclass(value.__class__, MLiteral)
    def isNodeOrMLiteral(value):
        '''Returns whether or not value is a literal or a node.'''
        return isMLiteral(value) or value.__class__ == Node

    class SynthesizerVisitor(build.MinispecPythonVisitor.MinispecPythonVisitor):
        '''Each method returns a component (module/function/etc.)
        nodes of type exprPrimary return the node corresponding to their value.
        stmt do not return anything; they mutate the current scope and the current hardware.'''
        
        def visitLowerCaseIdentifier(self, ctx: build.MinispecPythonParser.MinispecPythonParser.LowerCaseIdentifierContext):
            raise Exception("Not implemented")

        def visitUpperCaseIdentifier(self, ctx: build.MinispecPythonParser.MinispecPythonParser.UpperCaseIdentifierContext):
            raise Exception("Not implemented")

        def visitIdentifier(self, ctx: build.MinispecPythonParser.MinispecPythonParser.IdentifierContext):
            raise Exception("Not implemented")

        def visitAnyIdentifier(self, ctx: build.MinispecPythonParser.MinispecPythonParser.AnyIdentifierContext):
            raise Exception("Not implemented")

        def visitArg(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ArgContext):
            raise Exception("Not implemented")
        
        def visitArgs(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ArgsContext):
            raise Exception("Not implemented")

        def visitArgFormal(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ArgFormalContext):
            raise Exception("Not implemented")

        def visitArgFormals(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ArgFormalsContext):
            raise Exception("Not implemented")

        def visitParam(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ParamContext):
            if ctx.intParam:
                return self.visit(ctx.intParam)
            assert False, "typeName lookups are not yet supported"

        def visitParams(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ParamsContext):
            raise Exception("Not implemented")

        def visitParamFormal(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ParamFormalContext):
            raise Exception("Not implemented")

        def visitParamFormals(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ParamFormalsContext):
            raise Exception("Not implemented")

        def visitTypeName(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeNameContext):
            params = []
            if ctx.params():  #evaluate the type parameters, if any
                for param in ctx.params().param():
                    params.append(self.visit(param))
            typeName = ctx.name.getText()
            typeObject = parsedCode.currentScope.get(self, typeName, params)
            assert typeObject != None, f"Failed to find type {typeName} with parameters {params}"
            return typeObject

        def visitPackageDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.PackageDefContext):
            raise Exception("Not implemented")

        def visitPackageStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.PackageStmtContext):
            raise Exception("Not implemented")

        def visitImportDecl(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ImportDeclContext):
            raise Exception("Not implemented")

        def visitBsvImportDecl(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BsvImportDeclContext):
            raise Exception("Not implemented")

        def visitTypeDecl(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDeclContext):
            raise Exception("Not implemented")

        def visitTypeDefSynonym(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefSynonymContext):
            raise Exception("Not implemented")

        def visitTypeId(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeIdContext):
            raise Exception("Not implemented")

        def visitTypeDefEnum(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefEnumContext):
            raise Exception("Not implemented")

        def visitTypeDefEnumElement(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefEnumElementContext):
            raise Exception("Not implemented")

        def visitTypeDefStruct(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefStructContext):
            raise Exception("Not implemented")

        def visitStructMember(self, ctx: build.MinispecPythonParser.MinispecPythonParser.StructMemberContext):
            raise Exception("Not implemented")

        def visitVarBinding(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarBindingContext):
            raise Exception("Not implemented")

        def visitLetBinding(self, ctx: build.MinispecPythonParser.MinispecPythonParser.LetBindingContext):
            '''A let binding declares a variable or a concatenation of variables and optionally assigns
            them to the given expression node ("rhs").'''
            if not ctx.rhs:
                return  #if there is no assignment, we can skip this line
            rhsNode = self.visit(ctx.rhs)  #we expect a node corresponding to the desired value
            varName = ctx.lowerCaseIdentifier(0).getText() #the variable we are assigning
            parsedCode.currentScope.set(rhsNode, varName)
            # for now, we only handle the case of assigning a single variable (no concatenations).
            # nothing to return.

        def visitVarInit(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarInitContext):
            raise Exception("Not implemented")

        def visitModuleDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ModuleDefContext):
            raise Exception("Not implemented")

        def visitModuleId(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ModuleIdContext):
            raise Exception("Not implemented")

        def visitModuleStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ModuleStmtContext):
            raise Exception("Not implemented")

        def visitSubmoduleDecl(self, ctx: build.MinispecPythonParser.MinispecPythonParser.SubmoduleDeclContext):
            raise Exception("Not implemented")

        def visitInputDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.InputDefContext):
            raise Exception("Not implemented")

        def visitMethodDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.MethodDefContext):
            raise Exception("Not implemented")

        def visitRuleDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.RuleDefContext):
            raise Exception("Not implemented")

        def visitFunctionDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionDefContext):
            '''Synthesizes the corresponding function and returns the entire function hardware.
            Gets any parameters from parsedCode.lastParameterLookup and
            finds parameter bindings in bindings = parsedCode.parameterBindings'''
            functionName = ctx.functionId().name.getText()
            params = parsedCode.lastParameterLookup
            if len(params) > 0:  #attach parameters to the function name if present
                functionName += "#(" + ",".join(str(i) for i in params) + ")"
            functionScope = ctx.scope
            functionScope.clearTemporaryValues # clear the temporary values
            # log the current scope
            previousScope = parsedCode.currentScope
            parsedCode.currentScope = functionScope
            #bind any parameters in the function scope
            bindings = parsedCode.parameterBindings
            for var in bindings:  
                val = bindings[var]
                functionScope.set(val, var)
            # extract arguments to function and set up the input nodes
            inputNodes = []
            for arg in ctx.argFormals().argFormal():
                argType = self.visit(arg.typeName()) # typeName parse tree node
                argName = arg.argName.getText() # name of the variable
                argNode = Node(argName, argType)
                functionScope.set(argNode, argName)
                inputNodes.append(argNode)
            funcComponent = Function(functionName, [], inputNodes)
            # log the current component
            previousComponent = parsedCode.currentComponent
            parsedCode.currentComponent = funcComponent
            # synthesize the function internals
            for stmt in ctx.stmt():
                self.visit(stmt)
            parsedCode.currentComponent = previousComponent #reset the current component/scope
            parsedCode.currentScope = previousScope
            return funcComponent

        def visitFunctionId(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionIdContext):
            raise Exception("Not implemented")

        def visitVarAssign(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarAssignContext):
            raise Exception("Not implemented")

        def visitMemberLvalue(self, ctx: build.MinispecPythonParser.MinispecPythonParser.MemberLvalueContext):
            raise Exception("Not implemented")

        def visitIndexLvalue(self, ctx: build.MinispecPythonParser.MinispecPythonParser.IndexLvalueContext):
            raise Exception("Not implemented")

        def visitSimpleLvalue(self, ctx: build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext):
            raise Exception("Not implemented")

        def visitSliceLvalue(self, ctx: build.MinispecPythonParser.MinispecPythonParser.SliceLvalueContext):
            raise Exception("Not implemented")

        def visitOperatorExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.OperatorExprContext):
            '''This is an expression corresponding to a binary operation (which may be a unary operation,
            which may be an exprPrimary). We return the Node or MLiteral with the corresponding output value.'''
            value = self.visit(ctx.binopExpr())
            assert isNodeOrMLiteral(value)
            return value

        def visitCondExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CondExprContext):
            raise Exception("Not implemented")

        def visitCaseExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CaseExprContext):
            raise Exception("Not implemented")

        def visitCaseExprItem(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CaseExprItemContext):
            raise Exception("Not implemented")

        def visitBinopExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BinopExprContext):
            if ctx.unopExpr():  # our binary expression is actually a unopExpr.
                return self.visit(ctx.unopExpr())
            #we are either manipulating nodes/wires or manipulating integers.
            left = self.visit(ctx.left)
            right = self.visit(ctx.right)
            if left.__class__ == tuple: #we have received a pair (ctx, params) from constant storage, probably references to global constants that should evaluate to integers. Evaluate them.
                left = self.visit(left[0])
            if right.__class__ == tuple:
                right = self.visit(right[0])
            assert isNodeOrMLiteral(left), "left side must be literal or node"
            assert isNodeOrMLiteral(right), "right side must be literal or node"
            op = ctx.op.text
            '''Combining literals'''
            if isMLiteral(left) and isMLiteral(right): #we have two literals, so we combine them
                return { '**': MLiteral.pow,
                '*': MLiteral.mul,
                '/': MLiteral.div,
                '%': MLiteral.mod,
                '+': MLiteral.add,
                '-': MLiteral.sub,
                '<<': MLiteral.sleft,
                '>>': MLiteral.sright,
                '<': MLiteral.lt,
                '<=': MLiteral.le,
                '>': MLiteral.gt,
                '>=': MLiteral.ge,
                '==': MLiteral.eq,
                '!=': MLiteral.neq,
                '&': MLiteral.bitand,
                '^': MLiteral.bitxor,
                '^~': MLiteral.bitxnor,
                '~^': MLiteral.bitxnor,
                '|': MLiteral.bitor,
                '&&': MLiteral.booleanand,
                '||': MLiteral.booleanor }[op](left, right)
            # convert literals to hardware
            if isMLiteral(left):
                constantFunc = Function(str(left), [], [], Node())
                parsedCode.currentComponent.children.append(constantFunc)
                left = constantFunc.output
            if isMLiteral(right):
                constantFunc = Function(str(right), [], [], Node())
                parsedCode.currentComponent.children.append(constantFunc)
                right = constantFunc.output
            # both left and right are nodes, so we combine them using function hardware and return the output node.
            assert left.__class__ == Node and right.__class__ == Node, "left and right should be hardware"
            binComponent = Function(op, [], [Node("l"), Node("r")])
            leftWireIn = Wire(left, binComponent.inputs[0])
            rightWireIn = Wire(right, binComponent.inputs[1])
            for component in [binComponent, leftWireIn, rightWireIn]:
                parsedCode.currentComponent.children.append(component)
            return binComponent.output

            #assert False, f"binary expressions can only handle two nodes or two integers, received {left} and {right}"

        def visitUnopExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.UnopExprContext):
            if not ctx.op:  # our unopExpr is actually just an exprPrimary.
                value = self.visit(ctx.exprPrimary())
                if value.__class__ == tuple:
                    value = self.visit(value[0])
                assert isNodeOrMLiteral(value), f"Received {value.__repr__()} from {ctx.exprPrimary().toStringTree(recog=parser)}"
                return value
            #return self.visitChildren(ctx)

        def visitVarExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarExprContext):
            '''We are visiting a variable/function name. We look it up and return the correpsonding information
            (which may be a Node or a ctx or a tuple (ctx/Node, paramMappings), for instance).'''
            return parsedCode.currentScope.get(self, ctx.var.getText())

        def visitBitConcat(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BitConcatContext):
            raise Exception("Not implemented")

        def visitStringLiteral(self, ctx: build.MinispecPythonParser.MinispecPythonParser.StringLiteralContext):
            raise Exception("Not implemented")

        def visitIntLiteral(self, ctx: build.MinispecPythonParser.MinispecPythonParser.IntLiteralContext):
            '''We have an integer literal, so we parse it and return it.'''
            return IntegerLiteral(int(ctx.getText()))

        def visitReturnExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ReturnExprContext):
            '''This is the return expression in a function. We need to put the correct wire
            attaching the right hand side to the output of the function.'''
            rhs = self.visit(ctx.expression())  # the node with the value to return
            returnWire = Wire(rhs, parsedCode.currentComponent.output)
            parsedCode.currentComponent.children.append(returnWire)

        def visitStructExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.StructExprContext):
            raise Exception("Not implemented")

        def visitUndefinedExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.UndefinedExprContext):
            raise Exception("Not implemented")

        def visitSliceExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.SliceExprContext):
            raise Exception("Not implemented")

        def visitCallExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CallExprContext):
            '''We are calling a function. We synthesize the given function, wire it to the appropriate inputs,
            and return the function output node (which corresponds to the value of the function).'''
            # for now, we will assume that the fcn=exprPrimary in the callExpr must be a varExpr (with a var=anyIdentifier term).
            # this might also be a fieldExpr; I don't think there are any other possibilities with the current minispec specs.
            functionToCall = ctx.fcn.var.getText()
            params: 'list[int]' = []
            if ctx.fcn.params():
                for param in ctx.fcn.params().param():
                    value = self.visit(param) #visit the parameter and extract the corresponding expression, parsing it to an integer
                    #note that params may be either integers (which can be used as-is)
                    #   or variables (which need to be looked up) or expressions in integers (which need
                    #   to be evaluated and must evaluate to an integer).
                    assert value.__class__ == IntegerLiteral
                    params.append(value)
            funcAndBinds = parsedCode.currentScope.get(self, functionToCall, params)
            functionDef = funcAndBinds[0]  # look up the function to call
            bindings = funcAndBinds[1]
            parsedCode.parameterBindings = bindings
            parsedCode.lastParameterLookup = params
            funcComponent = self.visit(functionDef)  #synthesize the function internals
            # hook up the funcComponent to the arguments passed in.
            for i in range(len(ctx.expression())):
                expr = ctx.expression()[i]
                exprNode = self.visit(expr) # visit the expression and get the corresponding node
                funcInputNode = funcComponent.inputs[i]
                wireIn = Wire(exprNode, funcInputNode)
                parsedCode.currentComponent.children.append(wireIn)
            parsedCode.currentComponent.children.append(funcComponent)
            return funcComponent.output  # return the value of this call, which is the output of the function

        def visitFieldExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FieldExprContext):
            raise Exception("Not implemented")

        def visitParenExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ParenExprContext):
            return self.visit(ctx.expression())

        def visitMemberBinds(self, ctx: build.MinispecPythonParser.MinispecPythonParser.MemberBindsContext):
            raise Exception("Not implemented")

        def visitMemberBind(self, ctx: build.MinispecPythonParser.MinispecPythonParser.MemberBindContext):
            raise Exception("Not implemented")

        def visitBeginEndBlock(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BeginEndBlockContext):
            raise Exception("Not implemented")

        def visitRegWrite(self, ctx: build.MinispecPythonParser.MinispecPythonParser.RegWriteContext):
            raise Exception("Not implemented")

        def visitStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.StmtContext):
            #TODO figure out why we are visiting stmt and adjust as appropriate
            return self.visitChildren(ctx)

        def visitIfStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.IfStmtContext):
            raise Exception("Not implemented")

        def visitCaseStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CaseStmtContext):
            raise Exception("Not implemented")

        def visitCaseStmtItem(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CaseStmtItemContext):
            raise Exception("Not implemented")

        def visitCaseStmtDefaultItem(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CaseStmtDefaultItemContext):
            raise Exception("Not implemented")

        def visitForStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ForStmtContext):
            raise Exception("Not implemented")

    data = antlr4.InputStream(text)
    lexer = build.MinispecPythonLexer.MinispecPythonLexer(data)
    stream = antlr4.CommonTokenStream(lexer)
    parser = build.MinispecPythonParser.MinispecPythonParser(stream)
    tree = parser.packageDef()  #start parsing at the top-level packageDef rule (so "tree" is the root of the parse tree)
    #print(tree.toStringTree(recog=parser)) #prints the parse tree in lisp form (see https://www.antlr.org/api/Java/org/antlr/v4/runtime/tree/Trees.html )

    walker = build.MinispecPythonListener.ParseTreeWalker()
    listener = StaticTypeListener()
    walker.walk(listener, tree)  # walk the listener through the tree

    # for scope in parsedCode.allScopes:
    #     print(scope)

    synthesizer = SynthesizerVisitor()

    topLevelParameters = [IntegerLiteral(i) for i in topLevelParameters]
    ctxToSynth = startingFile.get(synthesizer, topLevel, topLevelParameters)
    assert ctxToSynth != None, "Failed to find topLevel function/module"
    # log parameters in the appropriate global
    functionDef = ctxToSynth[0]  # look up the function to call
    bindings = ctxToSynth[1]
    parsedCode.parameterBindings = bindings
    parsedCode.lastParameterLookup = topLevelParameters

    output = synthesizer.visit(functionDef) #look up the function in the given file and synthesize it. store the result in 'output'
    
    # for scope in parsedCode.allScopes:
    #     print(scope)

    parsedCode.reset()
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
