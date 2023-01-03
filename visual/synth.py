import inspect

import antlr4
import build.MinispecPythonParser
import build.MinispecPythonLexer
import build.MinispecPythonListener
import build.MinispecPythonVisitor

from hardware import *
from mtypes import *

#sets up parser for use in debugging:
#now ctx.toStringTree(recog=parser) will work properly.
data = antlr4.InputStream("")
lexer = build.MinispecPythonLexer.MinispecPythonLexer(data)
stream = antlr4.CommonTokenStream(lexer)
parser = build.MinispecPythonParser.MinispecPythonParser(stream)

def extractOriginalText(ctx) -> str:
    ''' Given an antlr4 ctx object, returns the corresponding original text. '''
    # from https://stackoverflow.com/questions/16343288/how-do-i-get-the-original-text-that-an-antlr4-rule-matched
    token_source = ctx.start.getTokenSource()
    input_stream = token_source.inputStream
    start, stop  = ctx.start.start, ctx.stop.stop
    return input_stream.getText(start, stop)
def getLineNumber(ctx) -> int:
    token_source = ctx.start.getTokenSource()
    input_stream = token_source.inputStream
    start, stop  = ctx.start.start, ctx.stop.stop
    return ctx.start.line

def decorateForErrorCatching(func):
    ''' Given a function func(self, ctx, ...), returns the function with a wrapper
    that catches errors, prints the text corresponding to ctx, and rethrows
    any errors. '''
    def newFunc(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if not hasattr(e, '___already_caught'):  # if we have no yet caught the error, print the current context.
                ctx = args[1]
                errorText = '  Note: Error occurred when synthesizing\n    ' + extractOriginalText(ctx) + '\non line ' + str(getLineNumber(ctx)) + ' of file ' + getSourceFilename(ctx)
                if hasattr(e, 'add_note'):  # we are in Python 3.11 and can add notes to error messages
                    e.add_note(errorText)
                else:
                    print(errorText)
                # TODO look into printing just the current line (+ file name) instead of the full ctx.
                e.___already_caught = True  # mark in the error that we have already caught it at least once
            raise e
    return newFunc

newline = '\n' #used to format f-strings such as "Hi{newline}there" since backslash is not allowed in f-strings

'''
Implementation Agenda:

    - Fixing parametric lookups
    - Vectors of submodules (and more generally, indexing into a submodule)--use a demultiplexer
    - BSV imports of modules
    - Multiple return statements

Implemented:

    - Function calls
    - Binary operations
    - Parametrics (+ associated variable lookups)
    - Type handling (+ associated python type objects)
    - Literals
    - If/ternary statements (+ muxes)
    - For loops
    - Modules
    - Indexing/Slicing
    - Typedef structs/synonyms/enums
    - Case statements
    - Case expressions
    - parameterized typedefs
    - imports of other files
    - Shared modules/Modules with arguments
    - Module methods with arguments

'''

'''
Overall specs:

ANTLR produces a parse tree ("tree" in the code). This parse tree has nodes ("ctx" in the code) corresponding
to different parts of the minispec grammar (packageDef, exprPrimary, returnExpr, etc.).
We will:
1. Run a tree walker through the parse tree to add static elaboration information, eg, 
  collecting all scopes that arise across various files/modules and binding all declared
  functions/modules/variables in the relevant scopes.
2. Locate the module/function to synthesize, then use a visitor to go through the tree
  (starting at the module/function to synthesize) and synthesize the minispec code into
  a hardware representation (see hardware.py).

Notes:
- Scope objects keep temporary and permanent values separate (think synthesizing the
  same module twice with different parameterizations).

Overall data structures:

-------------
|ANTLR4 tree|
-------------
      |
    |file ctx|
      |
    |function ctx|
      |
    |more ctx|

---------------------
| Synthesis Visitor |
---------------------
  |             |
  |           collectedScopes
  |             |       |
  |             |    currentScope (the scope currently of interest)
  |           allScopes
  |           (list of all scope objects, useful for debugging)
  |
globalsHandler:
        currentComponent: the function/module component currently being synthesized.
                            if wires or other components are created during synthesis,
                            they will be added to the current component via .addChild.
        parameterBindings: a dictionary str -> int telling functions which parameters
                            have been bound. Should be set whenever calling a function.
        lastParameterLookup:  a list consisting of the last integer values used to look up
                                a call to a parametric function. Should be set whenever calling a function.
                                Used to determine how to name the function in the corresponding
                                component. #TODO: use for parametric modules as well.
        outputNode: The output node of the function or method currently being synthesized.
                    Return statements attach their value to the node here.
  

Each scope has a parent pointer or list of parent pointers.
Only files have a list of parent pointers; files have one parent pointer for
each ms file imported. All other scopes have one parent pointer.
Arrangement of scopes:

built-in scope
  ^ (parent pointer)
other files
  ^ ^ ^
file to parse scope
  ^
various function/module scopes
  ... etc.

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
  This visitor,  upon visiting a ctx node in the parse tree, mutates existing hardware and possibly
  returns hardware corresponding to the ctx. Expressions return Node/MLiteral objects,
  functions/modules return full components, etc. A full listing of returns is just before
  the code for the visitor.
  - When visiting a function definition (which has its own scope) to synthesize it,
    the visitor looks up the function scope (at .scope in the node), clears the temporary
    value dictionary (.values), and does the synthesize one line (stmt) at a time. The
    current scope is stored in self.collectedScopes.currentScope, which must be restored after finishing
    the function synthesis.

Note:
  It seems that in a file scope, all definitions are permanent, while in a module scope,
  arbitrary stuff is allowed (variable assignment, function definitions, etc.), and in
  a function scope, only stmt (variable manipulation) is allowed, no permanent values.
  Is this something that I can rely on?
  This is important to note since in a file scope, named constants should perhaps be logged
  in some way using static elaboration; in a function scope, there are no constants; and
  in a moduleDef scope, I don't know what is going on.

'''

class MValue:
    ''' A value in a minispec program. Used to track source support.
    May be a Node, an MLiteral, a Register, a PartiallyIndexedModule, an antlr ctx object, etc.
    TODO make a full list of variants '''
    __slots__ = '_value', '_tokensSourcedFrom'
    def __init__(self, value: 'Any'):
        assert value.__class__ != MValue, "Cannot have an MValue inside of an MValue"
        self._value: 'Any' = value
        self._tokensSourcedFrom: 'list[list[tuple[str, int]]]' = []
    @property
    def value(self):
        return self._value
    def addSourceTokens(self, tokens: 'list[tuple[str, int]]'):
        ''' Given a list of tuples (filename, token), adds the list to the collection of sources of the component. '''
        assert tokens.__class__ == list, f"unexpected token class {tokens.__class__}"
        assert all( place.__class__ == tuple for place in tokens ), f"unexpected classes of entries in tokens {[place.__class__ for place in tokens if place.__class__ != tuple]}"
        self._tokensSourcedFrom.append(tokens)
    def getSourceTokens(self) -> 'list[tuple[str, int]]':
        ''' Returns the source tokens of self, flattened. '''
        return sum(self._tokensSourcedFrom, [])
    def copy(self) -> 'MValue':
        v = MValue(self.value)
        for token in self._tokensSourcedFrom:
            v.addSourceTokens(token)
        return v
    def isLiteralValue(self):
        return isMLiteral(self.value)
    def getHardware(self, globalsHandler) -> 'Node':
        assert globalsHandler.isGlobalsHandler(), "Quick type check"
        assert self.isLiteralValue(), "Can only convert literal value to hardware"
        return self.value.getHardware(globalsHandler, self._tokensSourcedFrom)

class TemporaryScope:
    ''' Stores temporary state used in synthesis. '''
    def __init__(self):
        self.temporaryValues = {}

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

    If fleeting, then the scope does not pass local assignments up the scope chain.
    '''
    def __init__(self, globalsHandler: 'GlobalsHandler', name: 'str', parents: 'list[Scope]', fleeting: 'bool' = False):
        self.globalsHandler = globalsHandler
        self.globalsHandler.allScopes.append(self)
        self.parents = parents.copy()
        self.name = name
        self.permanentValues = {}
        self.temporaryScope = TemporaryScope()
        self.temporaryScopeStack = [] # stores old temporary scopes (but not the current self.temporaryScope)
        self.fleeting = fleeting
    def popTemporaryScope(self):
        ''' Restores the previous temporary scope. Discards the current temporary scope. '''
        self.temporaryScope = self.temporaryScopeStack.pop()
    def pushTemporaryScope(self):
        ''' Creates a new temporary scope and stores the previous temporary scope. '''
        self.temporaryScopeStack.append(self.temporaryScope)
        self.temporaryScope = TemporaryScope()
    def __str__(self):
        if len(self.permanentValues) == 0 and len(self.temporaryScope.temporaryValues) == 0:
            return "Scope " + self.name
        output = "Scope " + self.name + " with parents " + ", ".join([parent.name for parent in self.parents]) + " with permanent values"
        for varName in self.permanentValues:
            output += "\n  " + varName + ": "
            for ex in self.permanentValues[varName]:
                output += "\n    " + "params: " + str(ex[0]) + " and value: " + str(ex[1].__class__)
        output += "\nand temporary values"
        for varName in self.temporaryScope.temporaryValues:
            output += "\n  " + varName + ": " + str(self.temporaryScope.temporaryValues[varName])
        return output
    def matchParams(visitor, intValues: 'list[int]', storedParams: 'list[ctxType|str]'):
        '''returns a dictionary mapping str -> int if intValues can fit storedParams.
        returns None otherwise.'''
        if len(intValues) != len(storedParams):
            return None
        d = {}  #make sure parameters match
        for i in range(len(intValues)):
            if storedParams[i].__class__ == str:
                d[storedParams[i]] = intValues[i]
            elif visitor.visit(storedParams[i]).value != intValues[i]:
                return None
        return d
    def get(self, visitor, varName: 'str', parameters: 'list[int]' = None) -> 'MValue|None':
        '''Looks up the given name/parameter combo. Prefers current scope to parent scopes, and
        then prefers temporary values to permanent values. Returns whatever is found,
        probably a ctx object (functionDef) or a node object (variable value).
        Returns None for an uninitialized variable.'''
        assert varName.__class__ == str, f"varName must be a string, not {varName} which is {varName.__class__}"
        if parameters == None:
            parameters = []
        visitor.globalsHandler.lastParameterLookup = parameters
        if varName in self.temporaryScope.temporaryValues:
            return self.temporaryScope.temporaryValues[varName]
        best: 'None|tuple' = None
        if varName in self.permanentValues:
            for storedParams, ctx in self.permanentValues[varName]: #iterate through the stored values, looking for the earliest, most specialized match.
                d = Scope.matchParams(visitor, parameters, storedParams)
                if d != None:
                    if best == None or len(d) < len(best[0]):
                        best = (d, ctx)
        if best != None:
            d, ctx = best
            self.globalsHandler.parameterBindings = d
            return ctx
        for parent in self.parents:
            output = parent.get(visitor, varName, parameters)
            if output != None:
                return output
        return None
    def set(self, value: 'MValue', varName: 'str'):
        '''Sets the given name/parameters to the given value in temporary storage,
        overwriting the previous value (if any) in temporary storage.
        Used for assigning variables to nodes, typically with no paramters.
        Currently ignores parameters.'''
        assert value.__class__ == MValue, f"Values must be MValue, not {value.__class__}"
        if self.fleeting:
            self.temporaryScope.temporaryValues[varName] = value
        else:
            if varName in self.permanentValues:
                self.temporaryScope.temporaryValues[varName] = value
            else:
                assert len(self.parents) == 1, f"Can't assign variable {varName} dynamically in a file scope"
                self.parents[0].set(value, varName)
    def setPermanent(self, value: 'MValue|None', varName: 'str', parameters: 'list[ctxType|str]' = None):
        '''Sets the given name/parameters to the given value in permanent storage.
        Overrules but does not overwrite previous values with the same name.
        Used for logging declarations functions/modules; value is expected to be a ctx
        functionDef or similar.
        Note that some parameters may be unknown at the time of storing, hence the ctx|str type.
        str corresponds to a value that must be fed it; ctx corresponds to a fixed value that can
        be compiled to an int.'''
        assert value.__class__ == MValue or value == None, f"Values must be MValue or None, not {value.__class__}"
        if parameters == None:
            parameters = []
        if varName not in self.permanentValues:
            self.permanentValues[varName] = []
        self.permanentValues[varName].append((parameters, value))
    '''Note: we probably need a helper function to detect when given parameters match
    a list[int|str] description.'''

class MissingVariableException(Exception):
    ''' Thrown by the builtin scope when a variable is not found.
    Can be caught if a variable might be a bluespec builtin. '''
    pass

class BluespecBuiltinFunction(Exception):
    ''' Thrown when a bluespec builtin function is found.
    self.functionComponent is the hardware corresponding to the function.
    self.evaluate is a function that takes input literals to whatever the corresponding function would output.
        so Valid is a builtin function that can be foled if a literal is fed in '''
    def __init__(self, functionComponent, evaluate):
        ''' self.functionComponent is the hardware corresponding to the function.
        self.evaluate is a function that takes input literals to whatever the corresponding function would output.
        so Valid is a builtin function that can be foled if a literal is fed in '''
        self.functionComponent = functionComponent
        self.evalute = evaluate

assumedBuiltinOrImport = set()  # the set of function names for which we have issued warning messages
class BuiltInScope(Scope):
    '''The minispec built-ins. Behaves slightly differently from other scopes.'''
    def __init__(self, globalsHandler: 'GlobalsHandler', name: 'str', parents: 'list[Scope]'):
        self.globalsHandler = globalsHandler
        self.parents = parents.copy()
        self.name = name
        # self.permanentValues = {}
        # self.temporaryValues = {}
    def set(self, value, varName: 'str'):
        raise Exception(f"Can't set value {varName} in the built-in scope")
    def setPermanent(self, value, varName: 'str', parameters: 'list[ctxType|str]' = None):
        raise Exception(f"Can't set value {varName} permanently in the built-in scope")
    def get(self, visitor, varName: 'str', parameters: 'list[int|MType]' = None) -> 'MValue|Node':
        '''Looks up the given name/parameter combo. Prefers current scope to parent scopes, and
        then prefers temporary values to permanent values. Returns whatever is found,
        probably a ctx object (functionDef).
        Returns a ctx object or a typeName.'''
        if parameters == None:
            parameters = []
        visitor.globalsHandler.lastParameterLookup = parameters
        if varName == 'Integer':
            assert len(parameters) == 0, "integer takes no parameters"
            return MValue(IntegerLiteral)
        if varName == 'Bit':
            assert len(parameters) == 1, "bit takes exactly one parameter"
            n = parameters[0]
            return MValue(Bit(n))
        if varName == 'Vector':
            assert len(parameters) == 2, "vector takes exactly two parameters"
            k, typeValue = parameters
            return MValue(Vector(k, typeValue))
        if varName == 'Bool':
            return MValue(Bool)
        if varName == 'Reg' or varName == 'RegU':
            # TODO make RegU read as RegU in output diagrams. Update relevant tests as well.
            assert len(parameters) == 1, "A register takes exactly one parameter"
            return MValue(BuiltinRegisterCtx(parameters[0]))
        if varName == 'True':
            assert len(parameters) == 0, "A boolean literal has no parameters"
            return MValue(Bool(True))
        if varName == 'False':
            assert len(parameters) == 0, "A boolean literal has no parameters"
            return MValue(Bool(False))
        if varName == 'Invalid':
            assert len(parameters) == 0, "An invalid literal has no parameters"
            return MValue(Invalid(Any))
        if varName == 'Valid':
            assert len(parameters) == 0, "An valid literal has no parameters"
            functionComp = Function('Valid', [Node()])
            def valid(mliteral: 'MLiteral'):
                return Maybe(mliteral.__class__)(mliteral)
            raise BluespecBuiltinFunction(functionComp, valid)
        if varName == 'fromMaybe':
            assert len(parameters) == 0, "fromMaybe has no parameters"
            functionComp = Function('fromMaybe', [Node(), Node()])
            def fromMaybe(default: 'MLiteral', mliteral: 'MLiteral'):
                if mliteral.isValid:
                    return mliteral.value
                return default
            raise BluespecBuiltinFunction(functionComp, fromMaybe)
        if varName == 'Maybe':
            assert len(parameters) == 1, "A maybe type has exactly one parameter"
            mtype = parameters[0]
            return MValue(Maybe(mtype))
        if varName == 'log2':
            assert len(parameters) == 0, "log base 2 has no parameters"
            functionComp = Function('log2', [Node()])
            def log2(n: 'MLiteral'):
                assert n.__class__ == IntegerLiteral, "Can only take log of integer"
                return IntegerLiteral(n.value.bit_length())
            raise BluespecBuiltinFunction(functionComp, log2)
        if varName == '$format' or varName == "$write" or varName == "$finish" or varName == "$display":
            return MValue(UnsynthesizableComponent())
        if varName not in assumedBuiltinOrImport:
            print(f"Warning: assuming {varName} is a Bluespec built-in or import")
            assumedBuiltinOrImport.add(varName)
        raise MissingVariableException(f"Couldn't find variable {varName} with parameters {parameters}.")

#type annotation for context objects.
ctxType = ' | '.join([ctxType for ctxType in dir(build.MinispecPythonParser.MinispecPythonParser) if ctxType[-7:] == "Context"][:-3])


class BuiltinRegisterCtx:
    def __init__(self, mtype: 'MType'):
        self.mtype = mtype
    def accept(self, visitor):
        return visitor.visitRegister(self.mtype)


class ModuleWithMetadata:
    ''' During synthesis, a module has extra data that needs to be carried around.
    This includes its input values, any default input values, and any methods with arguments. '''
    def __init__(self, visitor: 'SynthesizerVisitor', module: 'Module', inputsWithDefaults: 'dict[str, None|"build.MinispecPythonParser.MinispecPythonParser.ExpressionContext"]', methodsWithArguments: 'dict[str, tuple[build.MinispecPythonParser.MinispecPythonParser.MethodDefContext, Scope]]'):
        '''hey'''
        self.module: 'Module' = module
        self.inputValues: 'dict[str, Node|MLiteral|None]' = {}

        # save submodule inputs with default values
        for inputName in inputsWithDefaults:
            defaultCtxOrNone = inputsWithDefaults[inputName]
            # evaluate default input if it is not None
            if defaultCtxOrNone:
                self.inputValues[inputName] = visitor.visit(defaultCtxOrNone).value
            elif self.module.isRegister():
                # a register's default value is its own value
                self.inputValues[inputName] = self.module.value
            else:
                self.inputValues[inputName] = None

        self.methodsWithArguments = methodsWithArguments
        # TODO methodsWithArguments must keep track of scopes as well so that references to identical modules do not get mixed up.

    def synthesizeInputs(self, globalsHandler: 'GlobalsHandler'):
        ''' Synthesizes the connections between the input values to the module (in inputsWithDefaults)
        and the actual module inputs of self.module.
        Called during visitModuleDef after synthesizing all submodules and rules of the parent modules. '''
        submoduleName = self.module.name
        for inputName in self.inputValues:
            value = self.inputValues[inputName]
            assert value != None, f"All submodule inputs must be assigned--missing input {inputName} on {submoduleName}"
            if isMLiteral(value):
                value = MValue(value).getHardware(globalsHandler)
            if hasattr(self.module, 'isRegister') and self.module.isRegister():
                inputNode = self.module.input
            else:
                inputNode = self.module.inputs[inputName]
            Wire(value, inputNode)

        if self.module.__class__ == VectorModule:
            # synthesize inputs for vectors of submodules, too
            for module in self.module.numberedSubmodules:
                module.metadata.synthesizeInputs(globalsHandler)

    def setInput(self, inputName: 'str', newValue: 'MLiteral|Node|None'):
        ''' Given the name of an input and the value to assign, assigns that value. '''
        if self.module.__class__ == VectorModule:
            if inputName[0] == "[":
                inputIndex = int(inputName.split(']')[0][1:])
                restOfName = "]".join(inputName.split(']')[1:])
                self.module.numberedSubmodules[inputIndex].metadata.setInput(restOfName, newValue)
                return

        assert inputName in self.inputValues, "All inputs should be known at initialization."
        self.inputValues[inputName] = newValue

    def getInput(self, inputName: 'str') -> 'MLiteral|Node|None':
        ''' Given the name of an input, returns the corresponding value. '''
        if self.module.__class__ == VectorModule:
            if inputName[0] == "[":
                inputIndex = int(inputName.split(']')[0][1:])
                restOfName = "]".join(inputName.split(']')[1:])
                return self.module.numberedSubmodules[inputIndex].metadata.getInput(restOfName)

        return self.inputValues[inputName]

    def getAllInputs(self) -> 'set[str]':
        ''' Returns the set of all names of all inputs to this module.
        The elements of the set returned by this function are precisely the strings
        which may be used as 'inputName' for getInput and setInput. '''
        allInputs = set(self.inputValues)
        if self.module.__class__ == VectorModule:
            for i in range(len(self.module.numberedSubmodules)):
                for inputName in self.module.numberedSubmodules[i].metadata.getAllInputs():
                    allInputs.add(f"[{i}]{inputName}")
        return allInputs

class PartiallyIndexedModule:
    ''' A module that has been indexed into. If M is a vector of modules, then
    if we feed M[a][b].in into the interpreter, the interpreter will turn M[a] into
    PartiallyIndexedModule(M, (a,)) and will recursively turn M[a][b] into PartiallyIndexedModule(M, (a,b)).
    Finally, accessing .in will generate the relevant hardware components. '''
    def __init__(self, module: 'VectorModule', indexes: 'tuple[Node|MLiteral]' = tuple()):
        assert module.__class__ == VectorModule, "Can only index into a vector of submodules"
        self.module = module
        self.indexes = indexes
    def indexFurther(self, globalsHandler: 'GlobalsHandler', indx: 'Node|MLiteral') -> 'PartiallyIndexedModule|Node':
        ''' Returns the result of indexing further into the module. May be another PartiallyIndexedModule
        or a Node (if we have indexed far enough to select a register from a vector of registers). '''
        # TODO case of indexing further into a vector of registers should generate circuitry--make sure this works.
        if self.module.isVectorOfRegisters() and len(self.indexes) + 1 == self.module.depth():
            allIndices = self.indexes + (indx,)
            # we have picked out a register value; generate the corresponding hardware.
            muxInputs = []
            for submodule in self.module.numberedSubmodules:
                if submodule.__class__ == Register:
                    # self is a vector of registers
                    muxInputs.append(submodule.value)
                else:
                    # self is a vector of vectors
                    currentLevel = PartiallyIndexedModule(submodule)
                    for tempIndex in allIndices[1:]:
                        currentLevel = currentLevel.indexFurther(globalsHandler, tempIndex)
                    muxInputs.append(currentLevel)
            mux = Mux([Node() for i in muxInputs])
            mux.inputNames = [str(i) for i in range(len(muxInputs))]
            for i in range(len(muxInputs)):
                Wire(muxInputs[i], mux.inputs[i])
            Wire(allIndices[0], mux.control)
            globalsHandler.currentComponent.addChild(mux)
            return mux.output
        return PartiallyIndexedModule(self.module, self.indexes + (indx,))
    def getInput(self, globalsHandler: 'GlobalsHandler', inputName: 'str') -> 'Node|MLiteral':
        ''' Returns the corresponding input. '''
        assert len(self.indexes) == self.module.depth(), "Must have enough indices to select a nonvector submodule"
        muxInputs = []
        for submodule in self.module.numberedSubmodules:
            if submodule.__class__ == Module:
                # self is a vector of ordinary modules
                muxInputs.append(submodule.methods[inputName])
            else:
                # self is a vector of vectors
                currentLevel = PartiallyIndexedModule(submodule)
                for tempIndex in self.indexes:
                    currentLevel = currentLevel.indexFurther(globalsHandler, tempIndex)
                muxInputs.append(currentLevel)
        mux = Mux([Node() for i in muxInputs])
        mux.inputNames = [str(i) for i in range(len(muxInputs))]
        for i in range(len(muxInputs)):
            Wire(muxInputs[i], mux.inputs[i])
        Wire(self.indexes[0], mux.control)
        globalsHandler.currentComponent.addChild(mux)
        return mux.output

class BluespecModuleWithMetadata:
    ''' An imported bluespec module must be recognizable, with methods for creating inputs/methods dynamically
    as they are encountered. A bluespec module's default inputs are functions labeled with a ? (not don't care
    symbols). '''
    def __init__(self, module: 'Module', homeScope: 'Scope'):
        self.module: Module = module
        self.homeScope = homeScope  # the scope in which this module was created. used for creating module inputs.
        self.inputValues: 'dict[str, Node|MLiteral|None]' = {}
    def getMethod(self, fieldToAccess: 'str'):
        ''' Given the name of a method, returns the corresponding node.
        Dynamically creates the node if it does not exist. '''
        if (fieldToAccess not in self.module.methods):
            self.module.addMethod(Node(), fieldToAccess)
        return self.module.methods[fieldToAccess]
    def getMethodWithArguments(self, globalsHandler: 'GlobalsHandler', fieldToAccess: 'str', functionArgs: 'list[Node|MLiteral]', ctx):
        ''' Given the name of a method with arguments, as well as the arguments themselves,
        creates the corresponding hardware and returns the output node.
        fieldToAccess is the name of the method, functionArgs is a list of input nodes/literals.'''
        if '_'+fieldToAccess not in self.module.methods:
            self.module.addMethod(Node(), '_'+fieldToAccess)
        methodComponent = Function(fieldToAccess, [Node() for i in range(1+len(functionArgs))])
        methodComponent.addSourceTokens([(getSourceFilename(ctx), ctx.getSourceInterval()[0])])
        methodComponent._persistent = True
        for i in range(len(functionArgs)):
            exprValue = functionArgs[i]
            if isMLiteral(exprValue):
                exprNode = exprValue.getHardware(globalsHandler)
            else:
                exprNode = exprValue
            funcInputNode = methodComponent.inputs[i]
            Wire(exprNode, funcInputNode)
        funcInputNode = methodComponent.inputs[-1]
        Wire(self.module.methods['_'+fieldToAccess], funcInputNode)
        globalsHandler.currentComponent.addChild(methodComponent)
        return methodComponent.output
    def createInput(self, fieldToAccess: 'str', nameOfSubodule: 'str'):
        ''' Given the name of an input and the local name of the module, creates the corresponding input.
        Dynamically creates the input if it does not exist. '''
        if (fieldToAccess not in self.module.inputs):
            self.module.addInput(Node(), fieldToAccess)
            # TODO replace the DontCareLiteral with something representing an 'unknown' literal, since
            # this value represents an unknown default input.
            self.homeScope.setPermanent(MValue(DontCareLiteral()), nameOfSubodule + '.' + fieldToAccess)
            self.inputValues[fieldToAccess] = DontCareLiteral()
    def setInput(self, inputName: 'str', newValue: 'MLiteral|Node|None'):
        ''' Given the name of an input and the value to assign, assigns that value. '''
        assert inputName in self.inputValues, "Inputs must have been created before they can be set"
        self.inputValues[inputName] = newValue
    def getAllInputs(self) -> 'set[str]':
        ''' Returns the set of all names of all inputs to this module.
        The elements of the set returned by this function are precisely the strings
        which may be used as 'inputName' for getInput and setInput. '''
        allInputs = set(self.inputValues)
        return allInputs
    def synthesizeInputs(self, globalsHandler: 'GlobalsHandler'):
        for inputName in self.inputValues:
            value = self.inputValues[inputName]
            if isMLiteral(value):
                value = value.getHardware(globalsHandler)
            inputNode = self.module.inputs[inputName]
            Wire(value, inputNode)

class UnsynthesizableComponent:
    ''' Used to represent strings, etc. Any interpretation process that encounters an
    UnsynthesizableComponent should stop and return another UnsynthesizableComponent. '''
    def __init__(self):
        pass
    def accept(self, visitor):
        return MValue(self)

'''
Functions/modules/components will have nodes. Wires will be attached to nodes.
This is convenient during synthesis because we can map variables to the node
with the corresponding value and pass the nodes around, attaching wires as needed.
'''

class GlobalsHandler:
    def __init__(self):
        self.currentComponent: 'Function|Module' = None  # a function/module component. used during synthesis.
        self.parameterBindings = {}
        '''self.parameterBindings is a dictionary str -> int telling functions which parameters
        have been bound. Should be set whenever calling a function.'''
        self.lastParameterLookup = []
        '''self.lastParameterLookup is a list consisting of the last integer values used to look up
        a function call. Should be set whenever calling a function. Used to determine how to name
        the function in the corresponding component.'''

        self.allScopes: 'list[Scope]' = []
        self.currentScope: 'Scope' = None

        self.scopeStack = []
    def isGlobalsHandler(self):
        ''' Used by assert statements '''
        return True
    def popScope(self):
        self.currentScope = self.scopeStack.pop()
    def pushScope(self, scope):
        self.scopeStack.append(self.currentScope)
        self.currentScope = scope
    def enterScope(self, newScope: 'Scope'):
        ''' Saves previous scope (and if the current scope is the same as the new scope, saves
        any corresponding temporary state).
        Sets up given scope with empty temporary state and enters it. '''
        newScope.pushTemporaryScope()
        self.pushScope(newScope)
    def exitScope(self):
        ''' Restores previous scope (and if the current scope is the same as the previous scope,
        restores any corresponding temporary state).
        Discards current scope and any corresponding temporary state. '''
        self.currentScope.popTemporaryScope()
        self.popScope()


class StaticTypeListener(build.MinispecPythonListener.MinispecPythonListener):
    def __init__(self, globalsHandler: 'GlobalsHandler') -> None:
        self.globalsHandler = globalsHandler

    def enterPackageDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.PackageDefContext):
        '''The entry node to the parse tree.'''

    def enterFunctionDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionDefContext):
        '''We are defining a function. We need to give this function a corresponding scope.'''
        functionName = ctx.functionId().name.getText() # get the name of the function

        functionScope = Scope(self.globalsHandler, functionName, [self.globalsHandler.currentScope])
        ctx.scope = functionScope
        params = []
        if ctx.functionId().paramFormals():
            for param in ctx.functionId().paramFormals().paramFormal():
                # each parameter is either an integer or a name.
                if param.param():  # our parameter is an actual integer or type name, which will be evaluated immediately before lookups.
                    params.append(param.param())
                elif param.intName:  # param is a variable name. extract the name.
                    varName = param.intName.getText()
                    params.append(varName)
                    functionScope.setPermanent(None, varName)  # bind the parameter
                else: # param is a type name. extract and bind the name.
                    varName = param.typeValue.getText()
                    params.append(varName)
                    functionScope.setPermanent(None, varName)  # bind the parameter
        #log the function's scope
        self.globalsHandler.currentScope.setPermanent(MValue(ctx), functionName, params)
        self.globalsHandler.enterScope(functionScope)
        # bind function arguments to None in permanentValues
        if ctx.argFormals():
            for argFormal in ctx.argFormals().argFormal():
                functionScope.setPermanent(None, argFormal.argName.getText())

    def exitFunctionDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionDefContext):
        '''We have defined a function, so we step back into the parent scope.'''
        self.globalsHandler.exitScope()

    def enterModuleDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ModuleDefContext):
        '''We are defining a module. We need to give this module a corresponding scope.'''
        moduleName = ctx.moduleId().name.getText() # get the name of the module

        moduleScope = Scope(self.globalsHandler, moduleName, [self.globalsHandler.currentScope])
        ctx.scope = moduleScope
        params = []
        if ctx.moduleId().paramFormals():
            for param in ctx.moduleId().paramFormals().paramFormal():
                # each parameter is either an integer or a name.
                if param.param():  # our parameter is an actual integer or type name, which will be evaluated immediately before lookups.
                    params.append(param.param())
                elif param.intName:  # param is a variable name. extract the name.
                    varName = param.intName.getText()
                    params.append(varName)
                    moduleScope.setPermanent(None, varName)  # bind the parameter
                else: # param is a type name. extract and bind the name.
                    varName = param.typeValue.getText()
                    params.append(varName)
                    moduleScope.setPermanent(None, varName)  # bind the parameter
        # log the module's scope
        self.globalsHandler.currentScope.setPermanent(MValue(ctx), moduleName, params)
        self.globalsHandler.enterScope(moduleScope)
        
        # bind module arguments to None in permanentValues
        if ctx.argFormals():
            for argFormal in ctx.argFormals().argFormal():
                moduleScope.setPermanent(None, argFormal.argName.getText())

    def exitModuleDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ModuleDefContext):
        '''We have defined a module, so we step back into the parent scope.'''
        self.globalsHandler.exitScope()

    def enterRuleDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.RuleDefContext):
        '''Rules get a scope'''
        ruleName = ctx.name.getText()
        ruleScope = Scope(self.globalsHandler, ruleName, [self.globalsHandler.currentScope])
        ctx.scope = ruleScope
        self.globalsHandler.enterScope(ruleScope)

    def exitRuleDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.RuleDefContext):
        '''We have defined a rule, so we step back into the parent scope.'''
        self.globalsHandler.exitScope()

    def enterMethodDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.MethodDefContext):
        '''Methods get a scope'''
        methodName = ctx.name.getText()
        methodScope = Scope(self.globalsHandler, methodName, [self.globalsHandler.currentScope])
        ctx.scope = methodScope
        self.globalsHandler.enterScope(methodScope)

    def exitMethodDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.MethodDefContext):
        '''We have defined a method, so we step back into the parent scope.'''
        self.globalsHandler.exitScope()

    def enterVarBinding(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarBindingContext):
        '''We have found a named constant. Log it for later evaluation (since it may depend on other named constants, etc.)'''
        for varInit in ctx.varInit():
            varName = varInit.var.getText()
            if varInit.rhs:
                self.globalsHandler.currentScope.setPermanent(MValue(varInit.rhs), varName)
            else:
                self.globalsHandler.currentScope.setPermanent(None, varName)

    def enterLetBinding(self, ctx: build.MinispecPythonParser.MinispecPythonParser.LetBindingContext):
        for identifier in ctx.lowerCaseIdentifier():
            varName = identifier.getText()
            self.globalsHandler.currentScope.setPermanent(None, varName)

    def enterTypeDefSynonym(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefSynonymContext):
        ''' Log the typedef under the appropriate name. It will be evalauted when it is looked up. '''
        typedefName = ctx.typeId().name.getText()
        typeDefScope = Scope(self.globalsHandler, typedefName, [self.globalsHandler.currentScope])
        ctx.scope = typeDefScope  # used for evaluating parameters
        params = []
        if ctx.typeId().paramFormals():
            for param in ctx.typeId().paramFormals().paramFormal():
                # each parameter is either an integer or a name.
                if param.param():  # our parameter is an actual integer or type name, which will be evaluated immediately before lookups.
                    params.append(param.param())
                elif param.intName:  # param is a variable name. extract and bind the name.
                    varName = param.intName.getText()
                    params.append(varName)
                    typeDefScope.setPermanent(None, varName)  # bind the parameter
                else: # param is a type name. extract and bind the name.
                    varName = param.typeValue.getText()
                    params.append(varName)
                    typeDefScope.setPermanent(None, varName)  # bind the parameter
        self.globalsHandler.currentScope.setPermanent(MValue(ctx), typedefName, params)

    def enterTypeDefEnum(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefEnumContext):
        ''' Evaluate the typedef and log the appropriate variables. '''
        enumName = ctx.upperCaseIdentifier().getText()
        enumNames = []
        for element in ctx.typeDefEnumElement():
            enumNames.append(element.tag.getText())
        enumType = Enum(enumName, set(enumNames))
        self.globalsHandler.currentScope.setPermanent(MValue(enumType), enumName)
        for name in enumNames:
            self.globalsHandler.currentScope.setPermanent(MValue(enumType(name)), name)

    def enterTypeDefStruct(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefStructContext):
        ''' Log the typedef under the appropriate name. It will be evalauted when it is looked up. '''
        typedefName = ctx.typeId().name.getText()
        typeDefScope = Scope(self.globalsHandler, typedefName, [self.globalsHandler.currentScope])
        ctx.scope = typeDefScope  # used for evaluating parameters
        params = []
        if ctx.typeId().paramFormals():
            for param in ctx.typeId().paramFormals().paramFormal():
                # each parameter is either an integer or a name.
                if param.param():  # our parameter is an actual integer or type name, which will be evaluated immediately before lookups.
                    params.append(param.param())
                elif param.intName:  # param is a variable name. extract and bind the name.
                    varName = param.intName.getText()
                    params.append(varName)
                    typeDefScope.setPermanent(None, varName)  # bind the parameter
                else: # param is a type name. extract and bind the name.
                    varName = param.typeValue.getText()
                    params.append(varName)
                    typeDefScope.setPermanent(None, varName)  # bind the parameter
        self.globalsHandler.currentScope.setPermanent(MValue(ctx), typedefName, params)

    def enterBeginEndBlock(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BeginEndBlockContext):
        beginendScope = Scope(self.globalsHandler, "begin/end", [self.globalsHandler.currentScope])
        ctx.scope = beginendScope
        self.globalsHandler.enterScope(beginendScope)

    def exitBeginEndBlock(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BeginEndBlockContext):
        self.globalsHandler.exitScope()

    def enterForStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ForStmtContext):
        self.globalsHandler.currentScope.setPermanent(None, ctx.initVar.getText())

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
visitTypeName: Returns the relevant type object or a module ctx (if the type is a module type)
visitPackageDef: Error, should only be visited by the static information listener
visitPackageStmt: Error, should only be visited by the static information listener
visitImportDecl: 
visitBsvImportDecl: 
visitTypeDecl: 
visitTypeDefSynonym: 
visitTypeId: 
visitTypeDefEnum: 
visitTypeDefEnumElement: 
visitTypeDefStruct: 
visitStructMember: 
visitVarBinding: No returns, binds the given variables to the right-hand-sides in the appropriate scope
visitLetBinding: No returns, binds the given variable as appropriate in the current scope
visitVarInit: Not visited, varInits are handled in visitVarBinding since only varBinding has access to the assigned typeName ctx.
visitModuleDef: Returns a module with metadata object.
visitModuleId: Error, this node is handled in moduleDef and should not be visited
visitModuleStmt: Error, this node is handled in moduleDef and should not be visited
visitSubmoduleDecl: Returns the module hardware.
visitInputDef: Returns a tuple (inputName, defaultCtx), where defaultCtx is None if the input has no default value
visitMethodDef: If the method has no args, no returns. If the method has args, then visiting the method is like
    calling a function and will return the output node (this has not yet been implemented).
visitRuleDef: No returns, mutates existing hardware
visitFunctionDef: Returns the function hardware
visitFunctionId: Error, this node is handled in functionDef and should not be visited
visitVarAssign: No returns, mutates existing hardware
visitMemberLvalue: a tuple ( str, tuple[Node], str, tokensSourcedFrom ), see method for details
visitIndexLvalue: a tuple ( str, tuple[Node], str, tokensSourcedFrom ), see method for details
visitSimpleLvalue: a tuple ( str, tuple[Node], str, tokensSourcedFrom ), see method for details
visitSliceLvalue: a tuple ( str, tuple[Node], str, tokensSourcedFrom ), see method for details
visitOperatorExpr: Node or MLiteral corresponding to the value of the expression
visitCondExpr: Node or MLiteral corresponding to the value of the expression
visitCaseExpr: Node or MLiteral corresponding to the value of the expression
visitCaseExprItem: Error, handled in caseExpr
visitBinopExpr: Node or MLiteral corresponding to the value of the expression
visitUnopExpr: Node or MLiteral corresponding to the value of the expression
visitVarExpr: Returns the result upon looking up the variable name and associated parameters.
visitBitConcat: Returns the result (node) of concatenation
visitStringLiteral: No returns, does nothing
visitIntLiteral: Corresponding MLiteral
visitReturnExpr: Nothing, mutates current function hardware
visitStructExpr: Node or MLiteral corresponding to the value of the expression
visitUndefinedExpr: Corresponding MLiteral
visitSliceExpr: Returns the result (node) upon slicing
visitCallExpr: Returns the output node of the function call or a literal (if the function gets constant-folded --constant-folding through functions is not yet implemented.)
    Note that constant-folding elimination of function components occurs here, not in functionDef, so that the function to synthesize is not eliminated.
visitFieldExpr: 
visitParenExpr: Node or MLiteral corresponding to the value of the expression
visitMemberBinds: Error, this node is handled in structExpr and should not be visited
visitMemberBind: Error, this node is handled in structExpr and should not be visited
visitBeginEndBlock: No returns, mutates existing hardware
visitRegWrite: No returns, mutates existing hardware
visitStmt: No returns, mutates existing hardware
visitIfStmt: No returns, mutates existing hardware
visitCaseStmt: 
visitCaseStmtItem: 
visitCaseStmtDefaultItem: 
visitForStmt: No returns, mutates existing hardware
'''

class SynthesizerVisitor(build.MinispecPythonVisitor.MinispecPythonVisitor):
    '''Each method returns a component (module/function/etc.)
    nodes of type exprPrimary return the node corresponding to their value.
    stmt do not return anything; they mutate the current scope and the current hardware.'''

    # @decorateForErrorCatching
    def visit(self, ctx) -> 'MValue':
        value = ctx.accept(self)
        if ctx.__class__ != build.MinispecPythonParser.MinispecPythonParser.IndexLvalueContext:
            if ctx.__class__ != build.MinispecPythonParser.MinispecPythonParser.MemberLvalueContext:
                if ctx.__class__ != build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext:
                    if ctx.__class__ != build.MinispecPythonParser.MinispecPythonParser.SliceLvalueContext:
                        assert value.__class__ == MValue or value == None, f"Visited {ctx.__class__} and unexpectedly received value of type {value.__class__}"
        return value

    def visitModuleForSynth(self, moduleCtx, params: 'list[MLiteral|MType]', args: 'list[MLiteral|Module]') -> 'ModuleWithMetadata':
        ''' Redirects to one of visitModuleDef, visitRegister, or visitVectorSubmodule as apporpriate.
        Passes params and args as necessary. Returns the corresponding output. '''
        if moduleCtx.__class__ == build.MinispecPythonParser.MinispecPythonParser.ModuleDefContext:
            return self.visitModuleDef(moduleCtx, params, args)
        elif moduleCtx.__class__ == BuiltinRegisterCtx:
            return self.visitRegister(params[0])
        elif moduleCtx.__class__ == BuiltinVectorCtx:
            return self.visitVectorSubmodule(moduleCtx, params)
        else:
            raise Exception(f"Unexpected class {moduleCtx.__class__} of object {moduleCtx}")

    def visitRegister(self, mtype: 'MType'):
        ''' Visiting the built-in moduleDef of a register. Return the synthesized register. '''
        registerComponent = Register('Reg#(' + str(mtype) + ')')
        registerInputsWithDefault = {'input': None}  # the register default input will actually be its own value, but there is no corresponding ctx node so we put None here.
        registerMethodsWithArguments = {}  # registers have no methods with arguments
        moduleWithMetadata: ModuleWithMetadata = ModuleWithMetadata(self, registerComponent, registerInputsWithDefault, registerMethodsWithArguments)
        registerComponent.metadata = moduleWithMetadata
        return moduleWithMetadata

    def visitVectorSubmodule(self, vectorType, params):
        ''' We have a vector submodule. We create the relevant hardware and return the corresponding vector module. '''
        vectorComp = VectorModule([], "", {}, {}, set())  # the name can't be determined until we visit the inner modules and get their name
        previousComp = self.globalsHandler.currentComponent
        self.globalsHandler.currentComponent = vectorComp
        # TODO consider entering/exiting the builtin scope here?

        numCopies: 'int' = params[0].value
        submoduleType: 'ModuleType' = params[1]

        vectorizedSubmodule = submoduleType._moduleCtx  # the module context of the submodule
        assert numCopies >= 1, "It does not make sense to have a vector of no submodules."
        for i in range(numCopies):
            # submoduleWithMetadata = self.visit(vectorizedSubmodule)
            submoduleWithMetadata = self.visitModuleForSynth(vectorizedSubmodule, submoduleType._params, [])
            submodule = submoduleWithMetadata.module
            self.globalsHandler.currentComponent.addChild(submodule)
            vectorComp.addNumberedSubmodule(submodule)

        vectorComp.name = "Vector#(" + str(numCopies) + "," + str(submodule.name) + ")"
        self.globalsHandler.currentComponent = previousComp

        # assigning M[i][j] = value should be the same as assigning the ith submodule of M to have inputs
        # corresponding to value and j, then then having the jth input of M[i] be assigned to whichever input
        # corresponding to value. For nonconstant i,j, we will need to feed them into the appropriate muxes.

        # also, any assignment M[i][j] etc. must end with .input for some named input, or it is a register
        # and the relevant .input is implicitly ._input.

        vectorInputsWithDefault = {}
        vectorMethodsWithArguments = {}  # vectors of submodules have no methods with arguments
        moduleWithMetadata: ModuleWithMetadata = ModuleWithMetadata(self, vectorComp, vectorInputsWithDefault, vectorMethodsWithArguments)
        vectorComp.metadata = moduleWithMetadata

        return moduleWithMetadata

    def __init__(self, globalsHandler: 'GlobalsHandler') -> None:
        self.globalsHandler = globalsHandler
    
    @decorateForErrorCatching
    def visitLowerCaseIdentifier(self, ctx: build.MinispecPythonParser.MinispecPythonParser.LowerCaseIdentifierContext):
        raise Exception("Not implemented")

    @decorateForErrorCatching
    def visitUpperCaseIdentifier(self, ctx: build.MinispecPythonParser.MinispecPythonParser.UpperCaseIdentifierContext):
        raise Exception("Not implemented")

    @decorateForErrorCatching
    def visitIdentifier(self, ctx: build.MinispecPythonParser.MinispecPythonParser.IdentifierContext):
        raise Exception("Not implemented")

    @decorateForErrorCatching
    def visitAnyIdentifier(self, ctx: build.MinispecPythonParser.MinispecPythonParser.AnyIdentifierContext):
        raise Exception("Not implemented")

    @decorateForErrorCatching
    def visitArg(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ArgContext):
        raise Exception("Not implemented")
    
    @decorateForErrorCatching
    def visitArgs(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ArgsContext):
        raise Exception("Not implemented")

    @decorateForErrorCatching
    def visitArgFormal(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ArgFormalContext):
        raise Exception("Not implemented")

    @decorateForErrorCatching
    def visitArgFormals(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ArgFormalsContext):
        raise Exception("Not implemented")

    @decorateForErrorCatching
    def visitParam(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ParamContext):
        if ctx.intParam:
            return self.visit(ctx.intParam)
        assert ctx.typeName(), "Should have a typeName. Did the grammar change?"
        return self.visit(ctx.typeName())

    @decorateForErrorCatching
    def visitParams(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ParamsContext):
        raise Exception("Not implemented")

    @decorateForErrorCatching
    def visitParamFormal(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ParamFormalContext):
        raise Exception("Not implemented")

    @decorateForErrorCatching
    def visitParamFormals(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ParamFormalsContext):
        raise Exception("Not implemented")

    @decorateForErrorCatching
    def visitTypeName(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeNameContext):
        params = []
        if ctx.params():  #evaluate the type parameters, if any
            for param in ctx.params().param():
                # TODO create a separate type for module types ("module type", takes a module and parameter info?)
                # create this separate type when looking up module types as parameters.
                paramValue = self.visit(param).value
                # if param.__class__ == build.MinispecPythonParser.MinispecPythonParser.ModuleDefContext:
                #     param = ModuleType()
                params.append(paramValue)
        typeName = ctx.name.getText()
        typeObject = self.globalsHandler.currentScope.get(self, typeName, params).value
        assert typeObject != None, f"Failed to find type {typeName} with parameters {params}"
        if typeObject.__class__ == build.MinispecPythonParser.MinispecPythonParser.ModuleDefContext or typeObject.__class__ == BuiltinRegisterCtx:
            return MValue(ModuleType(typeObject, self.globalsHandler.lastParameterLookup))
        if typeObject.__class__ == MType:
            # we have a type
            return MValue(typeObject)
        if issubclass(typeObject.__class__, Component):
            # we have a module/register
            return MValue(typeObject)
        if typeObject.__class__ == build.MinispecPythonParser.MinispecPythonParser.TypeDefSynonymContext or typeObject.__class__ == build.MinispecPythonParser.MinispecPythonParser.TypeDefStructContext:
            # we have a type context
            typeObject = self.visit(typeObject).value
        return MValue(typeObject)

    @decorateForErrorCatching
    def visitPackageDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.PackageDefContext):
        raise Exception("PackageDef should only be visited during static elaboration, not synthesis")

    @decorateForErrorCatching
    def visitPackageStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.PackageStmtContext):
        raise Exception("PackageStmt should only be visited during static elaboration, not synthesis")

    @decorateForErrorCatching
    def visitImportDecl(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ImportDeclContext):
        raise Exception("Not implemented")

    @decorateForErrorCatching
    def visitBsvImportDecl(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BsvImportDeclContext):
        raise Exception("Not implemented")

    @decorateForErrorCatching
    def visitTypeDecl(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDeclContext):
        raise Exception('Handled during static elaboration. Only subtypes typeDefSynonym and typeDefStruct should be visited.')

    @decorateForErrorCatching
    def visitTypeDefSynonym(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefSynonymContext):
        ''' We look up the original type, then construct and return a synonym. '''
        typedefName = ctx.typeId().name.getText()
        params = self.globalsHandler.lastParameterLookup
        if len(params) > 0:  #attach parameters to the function name if present
            typedefName += "#(" + ",".join(str(i) for i in params) + ")"

        typedefScope = ctx.scope
        self.globalsHandler.enterScope(typedefScope)

        bindings = self.globalsHandler.parameterBindings
        for var in bindings:  
            val = bindings[var]
            # if val.__class__ != int: #val is a type, so we unroll it
            #     val = self.visit(val)
            typedefScope.set(MValue(val), var)

        originalType = self.visit(ctx.typeName()).value

        self.globalsHandler.exitScope()
        return MValue(Synonym(originalType, typedefName))

    @decorateForErrorCatching
    def visitTypeId(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeIdContext):
        raise Exception("Handled directly, should not be visited.")

    @decorateForErrorCatching
    def visitTypeDefEnum(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefEnumContext):
        raise Exception("Handled during static elaboration.")

    @decorateForErrorCatching
    def visitTypeDefEnumElement(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefEnumElementContext):
        raise Exception("Handled during static elaboration.")

    @decorateForErrorCatching
    def visitTypeDefStruct(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefStructContext):
        typedefName = ctx.typeId().name.getText()
        params = self.globalsHandler.lastParameterLookup
        if len(params) > 0:  #attach parameters to the function name if present
            typedefName += "#(" + ",".join(str(i) for i in params) + ")"

        typedefScope = ctx.scope
        self.globalsHandler.enterScope(typedefScope)

        bindings = self.globalsHandler.parameterBindings
        for var in bindings:  
            val = bindings[var]
            # if val.__class__ != int: #val is a type, so we unroll it
            #     val = self.visit(val)
            typedefScope.set(MValue(val), var)

        fields = {}
        for structMember in ctx.structMember():
            fieldTypeName = self.visit(structMember.typeName()).value
            fieldName = structMember.lowerCaseIdentifier().getText()
            fields[fieldName] = fieldTypeName

        self.globalsHandler.exitScope()
        return MValue(Struct(typedefName, fields))

    @decorateForErrorCatching
    def visitStructMember(self, ctx: build.MinispecPythonParser.MinispecPythonParser.StructMemberContext):
        raise Exception("Handled in typeDefStruct, not visited")

    @decorateForErrorCatching
    def visitVarBinding(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarBindingContext):
        try:
            typeValue = self.visit(ctx.typeName()).value
        except MissingVariableException:
            typeValue = Any
        for varInit in ctx.varInit():
            varName = varInit.var.getText()
            if (varInit.rhs):
                value = self.visit(varInit.rhs).value
            else:
                value = None
            if value.__class__ == Node:
                value.setMType(typeValue)
            self.globalsHandler.currentScope.set(MValue(value), varName)

    @decorateForErrorCatching
    def visitLetBinding(self, ctx: build.MinispecPythonParser.MinispecPythonParser.LetBindingContext):
        '''A let binding declares a variable or a concatenation of variables and optionally assigns
        them to the given expression node ("rhs").'''
        if not ctx.rhs:
            rhsValue = None
        else:
            rhsValue = self.visit(ctx.rhs).value  #we expect a node corresponding to the desired value
        if len(ctx.lowerCaseIdentifier()) == 1:
            varName = ctx.lowerCaseIdentifier(0).getText() #the variable we are assigning
            self.globalsHandler.currentScope.set(MValue(rhsValue), varName)
        else:
            raise Exception("Not Implemented")
        
        # for now, we only handle the case of assigning a single variable (no concatenations).
        # nothing to return.
        #TODO handle other cases

    @decorateForErrorCatching
    def visitVarInit(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarInitContext):
        raise Exception("Not visited--handled under varBinding to access typeName.")

    @decorateForErrorCatching
    def visitModuleDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ModuleDefContext, params: 'list[MLiteral|MType]', arguments: 'list[MLiteral|Module]'):
        ''' arguments is a list of arguments to the module.
        
        returns a tuple containing the module hardware and a dictionary moduleInputsWithDefaults of default inputs. '''

        moduleName = ctx.moduleId().name.getText()
        # params = self.globalsHandler.lastParameterLookup
        if len(params) > 0:  #attach parameters to the function name if present
            moduleName += "#(" + ",".join(str(i) for i in params) + ")"

        moduleCtxScope: Scope = ctx.scope
        moduleScope = Scope(self.globalsHandler, moduleName, [moduleCtxScope.parents[0]])
        previousCtxParent = moduleCtxScope.parents
        moduleCtxScope.parents = [moduleScope]
        self.globalsHandler.enterScope(moduleCtxScope)

        # dictionary of shared modules available to this module, but which are not submodules
        sharedSubmodules: 'dict[str, ModuleWithMetadata]' = {}
        if ctx.argFormals():
            for i in range(len(ctx.argFormals().argFormal())):
                arg = ctx.argFormals().argFormal(i)
                argName = arg.argName.getText()
                argValue = arguments[i]
                if argValue.__class__ == ModuleWithMetadata:
                    sharedSubmodules[argName] = argValue
                    argValue = argValue.module
                moduleScope.setPermanent(MValue(argValue), argName)
                moduleScope.set(MValue(argValue), argName)
                moduleCtxScope.set(MValue(argValue), argName)
        
        #bind any parameters in the module scope
        bindings = self.globalsHandler.parameterBindings
        for var in bindings:
            val = bindings[var]
            moduleScope.setPermanent(MValue(val), var)
            moduleScope.set(MValue(val), var)
            moduleCtxScope.set(MValue(val), var)

        moduleComponent = Module(moduleName)
        moduleComponent.addSourceTokens([(getSourceFilename(ctx), ctx.moduleId().getSourceInterval()[0])])
        # log the current component
        previousComponent = self.globalsHandler.currentComponent
        self.globalsHandler.currentComponent = moduleComponent

        # synthesize the module internals

        inputDefs = []
        submoduleDecls = []
        methodDefs = []
        ruleDefs = []

        for moduleStmt in ctx.moduleStmt():
            if moduleStmt.inputDef():
                inputDefs.append(moduleStmt.inputDef())
            elif moduleStmt.submoduleDecl():
                submoduleDecls.append(moduleStmt.submoduleDecl())
            elif moduleStmt.methodDef():
                methodDefs.append(moduleStmt.methodDef())
            elif moduleStmt.ruleDef():
                ruleDefs.append(moduleStmt.ruleDef())
            elif moduleStmt.stmt():
                # TODO this might mess up order of interpretation?
                self.visit(moduleStmt.stmt())
                # raise Exception("moduleStmt stmt is not implemented")
            elif moduleStmt.functionDef():
                continue # Only synthesize functions when called
            else:
                raise Exception("Unknown variant. Did the grammar change?")

        # synthesize inputs, submodules, methods, and rules, in that order
        
        # Stores the name of the input ("enable", not "inner.enable") since the submodule does not have access to this information.
        # Maps the name of the input to the context with the default value, if it exists. Otherwise maps the name of the input to None.
        moduleInputsWithDefaults: 'dict[str, None|"build.MinispecPythonParser.MinispecPythonParser.ExpressionContext"]' = {}
        for inputDef in inputDefs:
            inputName, defaultValCtxOrNone = self.visitInputDef(inputDef, moduleScope)
            moduleInputsWithDefaults[inputName] = defaultValCtxOrNone  # collect inputs along with default values
        
        ''' dictionary of registers, only used in a module, str is the variable name that points
        to the register in the module scope so that:
            self.registers[someRegisterName].module = self.get(self, someRegisterName).value '''
        registers: 'dict[str, ModuleWithMetadata]' = {}
        # Holds all submodules, including registers
        submodules: 'dict[str, ModuleWithMetadata]' = {}

        for submoduleDecl in submoduleDecls:
            submoduleWithMetadata: ModuleWithMetadata = self.visitSubmoduleDecl(submoduleDecl, registers, submodules, moduleScope)
            submoduleName = submoduleDecl.name.getText()
            # log the submodule in the relevant scope
            moduleScope.setPermanent(MValue(submoduleWithMetadata.module), submoduleName)
            moduleScope.set(MValue(submoduleWithMetadata.module), submoduleName)

        moduleMethodsWithArguments: 'dict[str, tuple[build.MinispecPythonParser.MinispecPythonParser.MethodDefContext, Scope]]' = {}
        for methodDef in methodDefs:
            methodName = methodDef.name.getText()
            if methodDef.argFormals():
                # only methodDefs with no arguments are synthesized in the module
                pass
                moduleMethodsWithArguments[methodName] = (methodDef, moduleScope)
            else:
                self.visitMethodDef(methodDef, moduleScope)

        for ruleDef in ruleDefs:
            self.visitRuleDef(ruleDef, registers, submodules, sharedSubmodules)

        # now that we have synthesized the rules, we need to collect all submodule inputs set across the rules and wire them in.
        # We can't wire in submodule inputs during the rules, since an input with a default input will confuse the first rule (since the input may or may not be set in a later rule).
        for submoduleName in submodules:
            submoduleWithMetadata: ModuleWithMetadata = submodules[submoduleName]
            submoduleWithMetadata.synthesizeInputs(self.globalsHandler)

        self.globalsHandler.currentComponent = previousComponent #reset the current component/scope
        self.globalsHandler.exitScope()
        moduleCtxScope.parents = previousCtxParent

        moduleWithMetadata: ModuleWithMetadata = ModuleWithMetadata(self, moduleComponent, moduleInputsWithDefaults, moduleMethodsWithArguments)
        moduleComponent.metadata = moduleWithMetadata

        return moduleWithMetadata

    @decorateForErrorCatching
    def visitModuleId(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ModuleIdContext):
        ''' Handled in moduleDef '''
        raise Exception("Handled in moduleDef, should never be visited")

    @decorateForErrorCatching
    def visitModuleStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ModuleStmtContext):
        raise Exception("Not accessed directly, handled in moduleDef")

    @decorateForErrorCatching
    def visitSubmoduleDecl(self, ctx: build.MinispecPythonParser.MinispecPythonParser.SubmoduleDeclContext, registers: 'dict[str, Register]', submodules: 'dict[str, ModuleWithMetadata]', moduleScope: 'Scope'):
        ''' We have a submodule, so we synthesize it and add it to the current module.
        We also need to bind to submodule's methods somehow; methods with no args bind to
        the corresponding module output, while methods with args need to be somehow tracked as
        functions calls that can be visited and synthesized, returning their output.
        function/module analogy:
            moduleDef <-> functionDef
            submoduleDecl <-> callExpr

        registers is a dictionary mapping register names to the corresponding register hardware.

        Returns the component corresponding to the submodule.
        '''
        
        # submoduleInputsWithDefault maps input names to the corresponding default ctx or none if there is no default value
        # only stores the name of the input ("enable",
        # not "inner.enable") since the submodule does not have access to what it will be called in the original module.
        # submoduleInputsWithDefault: 'dict[str, None|"build.MinispecPythonParser.MinispecPythonParser.ExpressionContext"]' = {}

        submoduleName = ctx.name.getText()
        try:
            submoduleType = self.visit(ctx.typeName()).value  # get the moduleDef ctx. Automatically extracts params.
            submoduleDef = submoduleType._moduleCtx
            submoduleParams = submoduleType._params
        except MissingVariableException as e:
            # we have an unknown bluespec built-in module
            moduleName = ctx.typeName().getText()
            moduleComponent = Module(moduleName)
            self.globalsHandler.currentComponent.addChild(moduleComponent)
            moduleWithMetadata = BluespecModuleWithMetadata(moduleComponent, moduleScope)
            moduleComponent.metadata = moduleWithMetadata
            moduleComponent.addSourceTokens([(getSourceFilename(ctx), ctx.name.getSourceInterval()[0])])
            submodules[submoduleName] = moduleWithMetadata
            return moduleWithMetadata
            # TODO add params to module name (built-in parameterized modules)
            # if len(params) > 0:  #attach parameters to the function name if present
                # functionName += "#(" + ",".join(str(i) for i in params) + ")"
            # funcComponent = Function(functionName, [], [Node() for i in range(len(ctx.expression()))])


        # TODO handle arguments for vectors of submodules
        # TODO registers currently ignore their arguments since reset circuitry is not currently generated.
        submoduleArguments = []
        if ctx.args():
            for arg in ctx.args().arg():
                value = self.visit(arg.expression()).value
                if isinstance(value, Module):
                    submoduleArguments.append(value.metadata)
                else:
                    submoduleArguments.append(value)

        moduleWithMetadata = self.visitModuleForSynth(submoduleDef, submoduleParams, submoduleArguments)
        moduleComponent = moduleWithMetadata.module
        moduleComponent.addSourceTokens([(getSourceFilename(ctx), ctx.name.getSourceInterval()[0])])
        self.globalsHandler.currentComponent.addChild(moduleComponent)

        submodules[submoduleName] = moduleWithMetadata

        if moduleComponent.isRegister():  # log the submodule in the appropriate dictionary for handling register assignments/submodule inputs.
            registers[submoduleName] = moduleWithMetadata

        return moduleWithMetadata

    @decorateForErrorCatching
    def visitInputDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.InputDefContext, parentScope: Scope):
        ''' Add the appropriate input to the module, with hardware to handle the default value.
        Bind the input in the appropriate context. (If the input is named 'in' then we bind in->Node('in').)
        Returns a tuple (inputName, defaultCtx), where defaultCtx is None if the input has no default value. '''
        inputName = ctx.name.getText()
        inputType = self.visit(ctx.typeName()).value
        inputNode = Node(inputName, inputType)
        parentScope.setPermanent(None, inputName)
        parentScope.set(MValue(inputNode), inputName)
        self.globalsHandler.currentComponent.addInput(inputNode, inputName)
        return (inputName, ctx.defaultVal)

    @decorateForErrorCatching
    def visitMethodDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.MethodDefContext, parentScope: 'Scope'):
        '''
        registers is a dictionary mapping register names to the corresponding register hardware.
        parentScope is the scope held by the Module object that this method belongs to.

        I think methods with arguments need to be handled separately from methods without arguments.
        - No args:
          This can be a bunch of wires/functions inside the module, synthesized with the module,
          such that the output of the method is a single output node of the module.
          So each method with no args gets synthesized once, with the module.
        - With args:
          A function outside of the module, wherever it gets called from. Synthsized each time
          it is called. For each register that the method calls from, we make the register value
          into a method with no args exactly once (this would need to be kept track of).
        - Things to check:
          What does minispec do with a top-level module with methods with arguments?
            Does it synthesize each one once, or does it leave them out?
        When we synthesize a methodDef with args, we should return the output to the synthesized method.
        When there are no args, there is no need to return anything.
        '''

        methodScope = ctx.scope
        try:
            methodType = self.visit(ctx.typeName()).value
        except MissingVariableException:
            methodType = Any
        methodName = ctx.name.getText()
        methodOutputNode = Node(methodName, methodType)  # set up the output node
        if not ctx.argFormals():
            # if there are no method arguments, synthesize the method here and add it to the module.
            self.globalsHandler.currentComponent.addMethod(methodOutputNode, methodName)
        if ctx.argFormals():
            # we are synthesizing the method from elsewhere, and we need to reattach the parent scope to the original module.
            moduleCtxScope: Scope = methodScope.parents[0]
            previousCtxParent = moduleCtxScope.parents
            moduleCtxScope.parents = [parentScope]
        self.globalsHandler.enterScope(methodScope)
        self.globalsHandler.currentScope.setPermanent(None, '-return')

        if ctx.argFormals():
            # we have a method with args. We create a component for it which we return at the end.
            # We also set up its arguments.
            # construct the input nodes
            inputNodes = []
            for arg in ctx.argFormals().argFormal():
                argType = self.visit(arg.typeName()).value # typeName parse tree node
                argName = arg.argName.getText() # name of the variable
                argNode = Node(argName, argType)
                methodScope.setPermanent(None, argName) # TODO consider should this line be done in the walker before synthesis?
                methodScope.set(MValue(argNode), argName)
                inputNodes.append(argNode)
            # set up and log the method component
            methodComponent = Function(methodName, inputNodes, methodOutputNode)
            methodComponent.addSourceTokens([(getSourceFilename(ctx), ctx.name.getSourceInterval()[0])])
            previousComponent = self.globalsHandler.currentComponent
            self.globalsHandler.currentComponent = methodComponent

        # there are no arguments, so we synthesize the method inside the current module.
        if ctx.expression():
            # the method is a single-line expression.
            value = self.visit(ctx.expression()).value
            if isMLiteral(value):  # convert value to hardware before linking to output node
                value = value.getHardware(self.globalsHandler)
            Wire(value, methodOutputNode)
        else:
            # the method is a multi-line sequence of statements with a return statement at the end.
            for stmt in ctx.stmt():  # evaluate the method
                self.visit(stmt)
        
            # collect the return value
            returnValue = self.globalsHandler.currentScope.get(self, '-return').value
            if returnValue.__class__ != UnsynthesizableComponent:
                if isMLiteral(returnValue):
                    returnValue = returnValue.getHardware(self.globalsHandler)
                Wire(returnValue, methodOutputNode)

        if ctx.argFormals():
            self.globalsHandler.currentComponent = previousComponent  #reset the current component
        self.globalsHandler.exitScope()
        if ctx.argFormals():
            moduleCtxScope.parents = previousCtxParent  # reset the module scope parents
        if ctx.argFormals():
            # if we have a method with arguments, we return the corresponding component.
            return MValue(methodComponent)

    @decorateForErrorCatching
    def visitRuleDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.RuleDefContext, registers: 'dict[str, Register]', submodules: 'dict[str, ModuleWithMetadata]', sharedSubmodules: 'dict[str, ModuleWithMetadata]'):
        ''' Synthesize the update rule. registers is a dictionary mapping register names to the corresponding register hardware. '''
        ruleScope: 'Scope' = ctx.scope
        self.globalsHandler.enterScope(ruleScope)
        # bind register outputs
        for registerName in registers:
            register = registers[registerName].module
            ruleScope.setPermanent(None, registerName)
            ruleScope.set(MValue(register.value), registerName)
        # bind any default inputs, including registers (which default to their own value)
        for submoduleName in submodules:
            for inputName in submodules[submoduleName].getAllInputs():
                fullInputName = submoduleName + '.' + inputName
                value = submodules[submoduleName].getInput(inputName)
                # if value != None:  # don't need this since none values should never by referenced
                ruleScope.setPermanent(None, fullInputName)
                ruleScope.set(MValue(value), fullInputName)
        for submoduleName in sharedSubmodules:
            for inputName in sharedSubmodules[submoduleName].getAllInputs():
                fullInputName = submoduleName + '.' + inputName
                value = sharedSubmodules[submoduleName].getInput(inputName)
                # if value != None:  # don't need this since none values should never by referenced
                ruleScope.setPermanent(None, fullInputName)
                ruleScope.set(MValue(value), fullInputName)
        for stmt in ctx.stmt():
            self.visit(stmt)
        # find any submodule input assignments, including register writes
        for submoduleName in submodules:
            for inputName in submodules[submoduleName].getAllInputs():
                fullInputName = submoduleName + '.' + inputName
                newValue = ruleScope.get(self, fullInputName).value
                submodules[submoduleName].setInput(inputName, newValue)
        for submoduleName in sharedSubmodules:
            for inputName in sharedSubmodules[submoduleName].getAllInputs():
                fullInputName = submoduleName + '.' + inputName
                newValue = ruleScope.get(self, fullInputName).value
                sharedSubmodules[submoduleName].setInput(inputName, newValue)
        self.globalsHandler.exitScope()

    @decorateForErrorCatching
    def visitFunctionDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionDefContext):
        '''Synthesizes the corresponding function and returns the entire function hardware.
        Gets any parameters from parsedCode.lastParameterLookup and
        finds parameter bindings in bindings = parsedCode.parameterBindings'''
        functionName = ctx.functionId().name.getText()
        params = self.globalsHandler.lastParameterLookup
        if len(params) > 0:  #attach parameters to the function name if present
            functionName += "#(" + ",".join(str(i) for i in params) + ")"
        functionScope = ctx.scope
        self.globalsHandler.enterScope(functionScope)
        
        #bind any parameters in the function scope
        bindings = self.globalsHandler.parameterBindings
        for var in bindings:  
            val = bindings[var]
            functionScope.set(MValue(val), var)
        # extract arguments to function and set up the input nodes
        inputNodes = []
        inputNames = []
        if ctx.argFormals():
            # a function with no arguments is still meaningful--if it is defined in a
            # module, it still has access to the module registers/inputs.
            for arg in ctx.argFormals().argFormal():
                argType = self.visit(arg.typeName()).value # typeName parse tree node
                argName = arg.argName.getText() # name of the variable
                argNode = Node(argName, argType)
                functionScope.set(MValue(argNode), argName)
                inputNodes.append(argNode)
                inputNames.append(argName)
        funcComponent = Function(functionName, inputNodes)
        funcComponent.inputNames = inputNames
        funcComponent.addSourceTokens([(getSourceFilename(ctx), ctx.functionId().getSourceInterval()[0])])
        self.globalsHandler.currentScope.setPermanent(None, '-return')
        # log the current component
        previousComponent = self.globalsHandler.currentComponent
        self.globalsHandler.currentComponent = funcComponent
        # synthesize the function internals
        for stmt in ctx.stmt():
            self.visit(stmt)

        returnValue = self.globalsHandler.currentScope.get(self, '-return')
        if isMLiteral(returnValue.value):
            returnValueNode = returnValue.getHardware(self.globalsHandler)
        else:
            returnValueNode = returnValue.value
        Wire(returnValueNode, funcComponent.output)

        self.globalsHandler.exitScope()
        self.globalsHandler.currentComponent = previousComponent #reset the current component
        return MValue(funcComponent)

    @decorateForErrorCatching
    def visitFunctionId(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionIdContext):
        ''' Handled from functionDef '''
        raise Exception("Handled from functionDef, should never be visited")

    @decorateForErrorCatching
    def visitVarAssign(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarAssignContext):
        ''' Assign the given variable to the given expression. No returns, mutates existing hardware. '''
        varList = ctx.lvalue()  #list of lhs vars
        #TODO "varList" in the Minispec grammar points to a curly brace '{', not a list of variables.
        #   This is confusing and not useful--should 'varList=' be removed from the grammar?
        if len(varList) > 1:  #I'm not sure how multiple assignments are supposed to work--
            # bsc says something about type errors and tuples. TODO figure this out, same issue holds for visitLetBinding.
            raise Exception("Not Implemented")
        lvalue = varList[0]
        value = self.visit(ctx.expression()).value
        if value.__class__ == UnsynthesizableComponent:
            return MValue(UnsynthesizableComponent())
        assert isNodeOrMLiteral(value), f"Received {value} from {ctx.toStringTree(recog=parser)}"
        # We have one of:
        #   1. An ordinary variable -- assign with .set to the relevant node.
        #   2. A module input -- wire the relevant node to the given input.
        #   3. A sliced/fielded variable -- create hardware for slicing, with input from
        #      the relevant node, then assign the outer variable to the result.
        if lvalue.__class__ == build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext:
            # we have a single variable to assign, no slicing/subfields needed
            # we don't visit the simplelvalue context since simplelvalue automatically produces hardware
            #   for slicing/indexing/etc. (as all other remaining cases require this).
            varName = ctx.var.getText()
            self.globalsHandler.currentScope.set(MValue(value), varName)
            return
        # Otherwise, we convert to hardware.
        if isMLiteral(value):
            value = MValue(value).getHardware(self.globalsHandler)
        if lvalue.__class__ == build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext:
            # assign the variable, no slicing/subfields needed
            varName = lvalue.getText()
            self.globalsHandler.currentScope.set(MValue(value), varName)
            return
        # insert the field/slice/index
        # first, detect if we are setting a module input
        if lvalue.__class__ == build.MinispecPythonParser.MinispecPythonParser.MemberLvalueContext:
            prospectiveModuleName = lvalue.getText().split('[')[0].split('.')[0] # remove slices ([) and fields (.)
            try:
                settingOverall = self.globalsHandler.currentScope.get(self, prospectiveModuleName).value
                # submodule input assignment has the form
                #   moduleName[i]...[k].inputName
                # TODO the [i]...[k] should only be present when the __class__ is VectorModule--remove this case
                # from the == Module case.
                if settingOverall.__class__ == Module:
                    if settingOverall.metadata.__class__ == ModuleWithMetadata:
                        # no slicing is present, only the input name.
                        assert lvalue.lvalue().__class__ == build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext, "Can only slice into a vector of modules"
                        inputName = lvalue.lowerCaseIdentifier().getText()
                        self.globalsHandler.currentScope.set(MValue(value), prospectiveModuleName + "." + inputName)
                        return
                    elif settingOverall.metadata.__class__ == BluespecModuleWithMetadata:
                        if lvalue.lvalue().__class__ == build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext: # no slicing is present, only the input name.
                            # we are setting an input to a bluespec imported module
                            inputName = lvalue.lowerCaseIdentifier().getText()
                            settingOverall.metadata.createInput(inputName, prospectiveModuleName)
                            self.globalsHandler.currentScope.set(MValue(value), prospectiveModuleName + "." + inputName)
                            return
                        else:
                            # we are slicing into a module, which must be a bluespec built-in (since otherwise it would be a VectorModule)
                            raise Exception("Not implemented")  #TODO implement this
                    else:
                        # Should never run--all cases of metadata should be covered.
                        raise Exception("Not implemented")
                elif settingOverall.__class__ == VectorModule:
                    if lvalue.__class__ == build.MinispecPythonParser.MinispecPythonParser.MemberLvalueContext:
                        inputName = lvalue.lowerCaseIdentifier().getText()
                        indexValues: 'list[MLiteral|Node]' = []
                        # iterate through the indices and visit them
                        currentLvalue = lvalue.lvalue()
                        while currentLvalue.__class__ != build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext:
                            if currentLvalue.__class__ == build.MinispecPythonParser.MinispecPythonParser.IndexLvalueContext:
                                indexValues.append(self.visit(currentLvalue.index).value)
                            else:
                                print(currentLvalue.__class__)
                                raise Exception("Not implemented")  # I don't think this case can occur.
                            currentLvalue = currentLvalue.lvalue()
                        # for indexValue in indexValues:
                        #     if indexValue.__class__ != IntegerLiteral:
                        #         raise Exception("Variable indexing into submodules is not implemented")
                        # nameToSet = currentLvalue.getText() + "."
                        # for indexValue in indexValues[::-1]:
                        #     nameToSet += f'[{indexValue.value}]'
                        # nameToSet += inputName
                        # self.globalsHandler.currentScope.set(MValue(value), nameToSet)
                        '''Start of variable assignment'''
                        regName = currentLvalue.getText()
                        outermostVector = self.globalsHandler.currentScope.get(self, regName).value
                        regName += "."
                        regsToWrite = [regName]
                        # collect the register names to write to
                        for k in range(len(indexValues)):
                            indexValue = indexValues[len(indexValues) - 1 - k]
                            oldRegsToWrite = regsToWrite
                            regsToWrite = []
                            if indexValue.__class__ == IntegerLiteral:
                                # fixed index value
                                for i in range(len(oldRegsToWrite)):
                                    regName = oldRegsToWrite[i] + f'[{indexValue.value}]'
                                    regsToWrite.append(regName)
                            else:
                                # variable index value
                                currentVector = outermostVector
                                for j in range(k):
                                    currentVector = currentVector.numberedSubmodules[0]
                                numSubmodules = len(currentVector.numberedSubmodules)
                                for j in range(numSubmodules):
                                    for i in range(len(oldRegsToWrite)):
                                        regName = oldRegsToWrite[i] + f'[{j}]'
                                        regsToWrite.append(regName)
                        # assign the correct values
                        for i in range(len(regsToWrite)):
                            regName = regsToWrite[i]
                            val = value
                            oldVal = self.globalsHandler.currentScope.get(self, regName + inputName).value
                            if isMLiteral(oldVal):
                                oldVal = MValue(oldVal).getHardware(self.globalsHandler)
                            # create the relevant hardware
                            for k in range(len(indexValues)):
                                indexValue = indexValues[len(indexValues) - 1 - k]
                                if indexValue.__class__ == IntegerLiteral:
                                    # fixed index value
                                    pass
                                else:
                                    # variable index value, create a mux
                                    mux = Mux([Node(), Node()])
                                    mux.inputNames = [str(BooleanLiteral(True)), str(BooleanLiteral(False))]
                                    eq = Function('=', [Node(), Node()])
                                    regIndex = regName.split(']')[k].split('[')[1]
                                    const = MValue(IntegerLiteral(int(regIndex))).getHardware(self.globalsHandler)
                                    Wire(eq.output, mux.control)
                                    Wire(indexValue, eq.inputs[0])
                                    Wire(const, eq.inputs[1])
                                    Wire(val, mux.inputs[0])
                                    Wire(oldVal, mux.inputs[1])
                                    for component in [mux, eq]:
                                        self.globalsHandler.currentComponent.addChild(component)
                                    val = mux.output
                            self.globalsHandler.currentScope.set(MValue(val), regName + inputName)

                        '''End of variable assignment'''
                        return
                    else:
                        raise Exception("Not implemented")  #TODO implement this TODO Can this case ever occur?
                else:
                    pass  # not a module, move on
            except MissingVariableException:
                pass  # not a module, move on
        text, nodes, varName, tokensSourcedFrom = self.visit(lvalue)
        insertComponent = Function(text, [Node() for node in nodes] + [Node()])
        insertComponent.addSourceTokens(tokensSourcedFrom)
        for i in range(len(nodes)):
            Wire(nodes[i], insertComponent.inputs[i])
        Wire(value, insertComponent.inputs[len(nodes)])
        self.globalsHandler.currentComponent.addChild(insertComponent)
        self.globalsHandler.currentScope.set(MValue(insertComponent.output), varName)

    @decorateForErrorCatching
    def visitMemberLvalue(self, ctx: build.MinispecPythonParser.MinispecPythonParser.MemberLvalueContext):
        ''' Returns a tuple ( str, tuple[Node], str, tokensSourcedFrom ) where str is the slicing text interpreted so far,
        tuple[Node] is the tuple of nodes corresponding to variable input (including the variable being updated),
        and the last str is varName, the name of the variable being updated. '''
        text, nodes, varName, tokensSourcedFrom = self.visit(ctx.lvalue())
        text += '.' + ctx.lowerCaseIdentifier().getText()
        tokensSourcedFrom.append((getSourceFilename(ctx), ctx.lowerCaseIdentifier().getSourceInterval()[0]))
        return (text, nodes, varName, tokensSourcedFrom)  # no new selection input nodes since field selection is not dynamic

    @decorateForErrorCatching
    def visitIndexLvalue(self, ctx: build.MinispecPythonParser.MinispecPythonParser.IndexLvalueContext):
        ''' Returns a tuple ( str, tuple[Node], str, tokensSourcedFrom ) where str is the slicing text interpreted so far,
        tuple[Node] is the tuple of nodes corresponding to variable input (including the variable being updated),
        and the last str is varName, the name of the variable being updated. '''
        text, nodes, varName, tokensSourcedFrom = self.visit(ctx.lvalue())
        index = self.visit(ctx.index).value
        text += '['
        if isNode(index):
            nodes += (index,)
            text += '_'
        else:
            text += str(index)
        text += ']'
        tokensSourcedFrom.append((getSourceFilename(ctx), ctx.index.getSourceInterval()[0]-1))
        tokensSourcedFrom.append((getSourceFilename(ctx), ctx.index.getSourceInterval()[-1]+1))
        return (text, nodes, varName, tokensSourcedFrom)

    @decorateForErrorCatching
    def visitSimpleLvalue(self, ctx: build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext):
        ''' Returns a tuple ( str, tuple[Node], str, tokensSourcedFrom ) where str is the slicing text interpreted so far,
        tuple[Node] is the tuple of nodes corresponding to variable input (including the variable being updated),
        and the last str is varName, the name of the variable being updated. '''
        valueFound = self.globalsHandler.currentScope.get(self, ctx.getText()).value
        if valueFound == None:
            # value has not yet been initialized
            return ("", tuple(), ctx.getText(), [])
        if isMLiteral(valueFound):
            valueFound = MValue(valueFound).getHardware(self.globalsHandler)
        return ("", (valueFound,), ctx.getText(), [])

    @decorateForErrorCatching
    def visitSliceLvalue(self, ctx: build.MinispecPythonParser.MinispecPythonParser.SliceLvalueContext):
        ''' Returns a tuple ( str, tuple[Node], str, tokensSourcedFrom ) where str is the slicing text interpreted so far,
        tuple[Node] is the tuple of nodes corresponding to variable input (including the variable being updated),
        and the last str is varName, the name of the variable being updated. '''
        text, nodes, varName, tokensSourcedFrom = self.visit(ctx.lvalue())
        msb = self.visit(ctx.msb).value
        lsb = self.visit(ctx.lsb).value
        text += '['
        if isNode(msb):
            nodes += (msb,)
            text += '_'
        else:
            text += str(msb)
        text += ':'
        if isNode(lsb):
            nodes += (lsb,)
            text += '_'
        else:
            text += str(lsb)
        text += ']'
        # TODO source map
        return (text, nodes, varName, tokensSourcedFrom)

    @decorateForErrorCatching
    def visitOperatorExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.OperatorExprContext):
        '''This is an expression corresponding to a binary operation (which may be a unary operation,
        which may be an exprPrimary). We return the Node or MLiteral with the corresponding output value.'''
        value = self.visit(ctx.binopExpr())
        # removed assertion since this may return a module when parsing a shared module.
        # assert isNodeOrMLiteral(value), f"Received {value} from {ctx.toStringTree(recog=parser)}"
        return value

    @decorateForErrorCatching
    def visitCondExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CondExprContext):
        condition = self.visit(ctx.expression(0)).value
        if condition.__class__ == UnsynthesizableComponent:
            return UnsynthesizableComponent()
        if isMLiteral(condition):
            # we select the appropriate branch
            if condition == BooleanLiteral(True):
                return self.visit(ctx.expression(1))
            else:
                if ctx.stmt(1):
                    return self.visit(ctx.expression(2))
        else:
            value1 = self.visit(ctx.expression(1)).value
            value2 = self.visit(ctx.expression(2)).value
            if value1.__class__ == UnsynthesizableComponent:
                return MValue(UnsynthesizableComponent())
            if value2.__class__ == UnsynthesizableComponent:
                return MValue(UnsynthesizableComponent())
            # since the control signal is hardware, we convert the values to hardware as well (if needed)
            if isMLiteral(value1):
                value1 = value1.getHardware(self.globalsHandler)
            if isMLiteral(value2):
                value2 = value2.getHardware(self.globalsHandler)
            muxComponent = Mux([Node('v1'), Node('v2')], Node('c'))
            muxComponent.inputNames = [str(BooleanLiteral(True)), str(BooleanLiteral(False))]
            muxComponent.addSourceTokens([(getSourceFilename(ctx), ctx.condQmark.tokenIndex)])
            muxComponent.addSourceTokens([(getSourceFilename(ctx), ctx.condColon.tokenIndex)])
            Wire(value1, muxComponent.inputs[0]), Wire(value2, muxComponent.inputs[1]), Wire(condition, muxComponent.control)
            self.globalsHandler.currentComponent.addChild(muxComponent)
            return MValue(muxComponent.output)
        #TODO go back through ?/if statements and make sure hardware/literal cases are handled properly.

    @decorateForErrorCatching
    def visitCaseExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CaseExprContext):
        # Similar to caseStmt, only simpler, with one variable assignment instead of arbitrary statements to execute
        ''' We evaluate the case statement into one or more muxes, with the following optimizations:
        1. If the expression to the case statement is an MLiteral (or evaluates to one, say as a parameter), and if
          the expressions for all of the selection expressions are MLiterals, we evaluate and return only the correct
          branch of the case statement.
        2. If all of the selection expressions are MLiterals but the case expression is not, we synthesize to a
          wide mux with one input for each possible output.
        3. If one or more of the selection expressions is not an MLiteral, we synthesize to a sequence of muxes
          controlled by components of the form (case expression hardware == selection expression hardware). If
          exactly one of the expressions is a boolean literal, we skip the "==" component. If both expressions
          are literals, we determine if that branch is always or never taken (depending on whether or not the
          literals are equal) and optimize away the corresponding mux. If the case expression is a literal and
          is wire in to several muxes, we instantiate it into hardware several times, one for each mux.
        '''
        #TODO in caseExpr and caseStmt, if a default is included but all possible inputs are already present (as literals), skip the default input.
        expr = self.visit(ctx.expression()).value
        expri: 'list[tuple[MLiteral|Node, MLiteral|Node]]' = [] # pairs (comparisonStmt, valueToOutput)
        hasDefault = False
        for caseExprItem in ctx.caseExprItem():
            if not caseExprItem.exprPrimary():  # no selection expression, so we have a default expression.
                hasDefault = True
                defaultValue = self.visit(caseExprItem.expression()).value
                break
            correspondingOutput = self.visit(caseExprItem.expression()).value
            for comparisonStmt in caseExprItem.exprPrimary():
                expri.append((self.visit(comparisonStmt).value, correspondingOutput))
        if isMLiteral(expr) and all([isMLiteral(pair[0]) for pair in expri]) and ((not hasDefault) or (hasDefault and isMLiteral(defaultValue))): # case 1
            for pair in expri:
                if pair[0].eq(expr):
                    return MValue(pair[1])
            assert hasDefault, "all branches must be covered"
            return MValue(defaultValue)
        if all([isMLiteral(pair[0]) for pair in expri]) and ((not hasDefault) or (hasDefault and isMLiteral(defaultValue))): # case 2
            assert not isMLiteral(expr), "We assume expr is not a literal here, so we do not have to eliminate any extra values."
            possibleOutputs = [] # including the default output, if present
            for pair in expri:
                possibleOutputs.append(pair[1])
            if hasDefault:
                possibleOutputs.append(defaultValue)
            mux = Mux([Node() for i in range(len(possibleOutputs))])
            mux.inputNames = [str(pair[0]) for pair in expri] + (['default'] if hasDefault else [])
            mux.addSourceTokens([(getSourceFilename(ctx), ctx.getSourceInterval()[0])])
            mux.addSourceTokens([(getSourceFilename(ctx), ctx.getSourceInterval()[-1])])
            for i in range(len(possibleOutputs)):  # convert all possible outputs to hardware
                possibleOutput = possibleOutputs[i]
                if isMLiteral(possibleOutput):
                    possibleOutputs[i] = MValue(possibleOutput).getHardware(self.globalsHandler)
            wires = [Wire(expr, mux.control)] + [ Wire(possibleOutputs[i], mux.inputs[i]) for i in range(len(possibleOutputs)) ]
            for component in [mux]:
                self.globalsHandler.currentComponent.addChild(component)
            return MValue(mux.output)
        # case 3
        muxes = []
        newExpri = [] #prune some literals if possible
        for pair in expri:
            if isMLiteral(expr) and isMLiteral(pair[0]):
                if expr.eq(pair[0]):
                    hasDefault = True # since this expri will always work, we discard any default value
                    defaultValue = pair[1]
                    break
                else:
                    continue
            else:
                newExpri.append(pair)
        if not hasDefault:  # transform to guarantee a default value. this is valid since every case expression must always return something.
            hasDefault = True
            defaultValue = newExpri[-1][1]
            newExpri = newExpri[:-1]
        expri = newExpri

        # at this point, each entry of expri will run and there is a default value.
        muxes = [Mux([Node(), Node()]) for i in range(len(expri))]
        # TODO mux inputNames
        for mux in muxes:
            mux.addSourceTokens([(getSourceFilename(ctx), ctx.getSourceInterval()[0])])
            mux.addSourceTokens([(getSourceFilename(ctx), ctx.getSourceInterval()[-1])])
        nextWires = [ Wire(muxes[i+1].output, muxes[i].inputs[1]) for i in range(len(expri)-1) ]

        valueWires = []
        for i in range(len(expri)):  # create hardware for values
            value = expri[i][1]
            if isMLiteral(value):
                value = MValue(value).getHardware(self.globalsHandler)
            valueWires.append(Wire(value, muxes[i].inputs[0]))
        if isMLiteral(defaultValue):
            defaultValue = MValue(defaultValue).getHardware(self.globalsHandler)
        valueWires.append(Wire(defaultValue, muxes[-1].inputs[1]))
        
        controlWires = []
        controlComponents = []
        for i in range(len(expri)):  # create hardware for controls
            controlValue = expri[i][0]
            muxControl = muxes[i].control
            assert not (isMLiteral(controlValue) and isMLiteral(expr)), "This case should have been evaluated earlier"
            if isMLiteral(expr) and expr.__class__ == Bool:
                # TODO mux input names instead of inverting
                if expr:
                    controlWires.append(Wire(controlValue, muxControl))
                else:
                    n = Function('~', [Node()])
                    controlComponents.append(n)
                    controlWires.append(Wire(controlValue, n.inputs[0]))
                    controlWires.append(Wire(n.output, muxControl))
            elif isMLiteral(controlValue) and controlValue.__class__ == Bool:
                # TODO mux input names instead of inverting
                if controlValue:
                    controlWires.append(Wire(expr, muxControl))
                else:
                    n = Function('~', [Node()])
                    controlComponents.append(n)
                    controlWires.append(Wire(expr, n.inputs[0]))
                    controlWires.append(Wire(n.output, muxControl))
            else:
                if isMLiteral(controlValue):
                    controlValue = MValue(controlValue).getHardware(self.globalsHandler)
                eq = Function('==', [Node(), Node()])
                controlComponents.append(eq)
                controlWires.append(Wire(expr, eq.inputs[0]))
                controlWires.append(Wire(controlValue, eq.inputs[1]))
                controlWires.append(Wire(eq.output, muxControl))
                muxes[i].inputNames = [str(BooleanLiteral(True)), str(BooleanLiteral(False))]
        for component in muxes + controlComponents:
                self.globalsHandler.currentComponent.addChild(component)
        return MValue(muxes[0].output) if len(muxes) > 0 else MValue(defaultValue)

    @decorateForErrorCatching
    def visitCaseExprItem(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CaseExprItemContext):
        raise Exception("Handled in caseExpr, should not be visited")

    @decorateForErrorCatching
    def visitBinopExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BinopExprContext):
        if ctx.unopExpr():  # our binary expression is actually a unopExpr.
            return self.visit(ctx.unopExpr())
        #we are either manipulating nodes/wires or manipulating integers.
        leftValue = self.visit(ctx.left)
        rightValue = self.visit(ctx.right)
        left = leftValue.value
        right = rightValue.value
        if not isNodeOrMLiteral(left): #we have received a ctx from constant storage, probably references to global constants that should evaluate to integers. Evaluate them.
            leftValue = self.visit(ctx.left)
            left = leftValue.value
            if left.__class__ == UnsynthesizableComponent:
                return MValue(UnsynthesizableComponent())
        if not isNodeOrMLiteral(right):
            rightValue = self.visit(ctx.right)
            right = rightValue.value
            if right.__class__ == UnsynthesizableComponent:
                return MValue(UnsynthesizableComponent())
        assert isNodeOrMLiteral(left), f"left side must be literal or node, not {left} which is {left.__class__}"
        assert isNodeOrMLiteral(right), f"right side must be literal or node, not {right} which is {right.__class__}"
        op = ctx.op.text
        '''Combining literals'''
        if isMLiteral(left) and isMLiteral(right): #we have two literals, so we combine them
            result = MValue(binaryOperation(left, right, op))
            result.addSourceTokens([(getSourceFilename(ctx), ctx.op.tokenIndex)])
            return result
        # convert literals to hardware
        if isMLiteral(left):
            left = leftValue.getHardware(self.globalsHandler)
        if isMLiteral(right):
            right = rightValue.getHardware(self.globalsHandler)
        # both left and right are nodes, so we combine them using function hardware and return the output node.
        assert left.__class__ == Node and right.__class__ == Node, "left and right should be hardware"
        binComponent = Function(op, [Node("l"), Node("r")])
        binComponent.addSourceTokens([(getSourceFilename(ctx), ctx.op.tokenIndex)])
        Wire(left, binComponent.inputs[0])
        Wire(right, binComponent.inputs[1])
        for component in [binComponent]:
            self.globalsHandler.currentComponent.addChild(component)
        return MValue(binComponent.output)

        #assert False, f"binary expressions can only handle two nodes or two integers, received {left} and {right}"

    @decorateForErrorCatching
    def visitUnopExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.UnopExprContext):
        ''' Return the Node or MLiteral corresponding to the expression '''
        if not ctx.op:  # our unopExpr is actually just an exprPrimary.
            value = self.visit(ctx.exprPrimary()).value
            if not isNodeOrMLiteral(value):
                if hasattr(value, 'isRegister') and value.isRegister():
                    value = value.value
                elif isinstance(value, Module):  # we have found a module, such as a shared module.
                    return MValue(value)
                elif value.__class__ == UnsynthesizableComponent:
                    return MValue(UnsynthesizableComponent())
                else:
                    # we have a ctx object, so we visit it
                    value = self.visit(value).value
                    if value.__class__ == Function:
                        # we visitied a ctx object which was a function, so the corresponding value is the output.
                        self.globalsHandler.currentComponent.addChild(value)
                        value = value.output
            assert isNodeOrMLiteral(value), f"Received {value.__repr__()} from {ctx.exprPrimary().toStringTree(recog=parser)}"
            return MValue(value)
        value = self.visit(ctx.exprPrimary()).value
        if hasattr(value, 'isRegister') and value.isRegister():
            value = value.value
        assert isNodeOrMLiteral(value), f"Received {value.__repr__()} from {ctx.exprPrimary().toStringTree(recog=parser)}"
        op = ctx.op.text
        if isMLiteral(value):
            result = MValue(unaryOperation(value, op))
            result.addSourceTokens([(getSourceFilename(ctx), ctx.op.tokenIndex)])
            return result
        assert value.__class__ == Node, "value should be hardware"
        unopComponenet = Function(op, [Node("v")])
        unopComponenet.addSourceTokens([(getSourceFilename(ctx), ctx.op.tokenIndex)])
        Wire(value, unopComponenet.inputs[0])
        self.globalsHandler.currentComponent.addChild(unopComponenet)
        return MValue(unopComponenet.output)

    @decorateForErrorCatching
    def visitVarExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarExprContext):
        '''We are visiting a variable/function name. We look it up and return the correpsonding information
        (which may be a Node or a ctx or a tuple (ctx/Node, paramMappings), for instance).'''
        params: 'list[int]' = []
        if ctx.params():
            for param in ctx.params().param():
                value = self.visit(param).value #visit the parameter and extract the corresponding expression, parsing it to an integer
                #note that params may be either integers (which can be used as-is)
                #   or variables (which need to be looked up) or expressions in integers (which need
                #   to be evaluated and must evaluate to an integer).
                assert value.__class__ == IntegerLiteral or value.__class__ == MType, f"Parameters must be an integer or a type, not {value} which is {value.__class__}"
                params.append(value)
        value = self.globalsHandler.currentScope.get(self, ctx.var.getText(), params).copy()  # make a copy so we don't mutate the original value when we add source tokens
        value.addSourceTokens([(getSourceFilename(ctx), ctx.getSourceInterval()[0])])
        self.globalsHandler.lastParameterLookup = params
        return value

    @decorateForErrorCatching
    def visitBitConcat(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BitConcatContext):
        ''' Bit concatenation is just a function. Returns the function output. '''
        toConcat = []
        for expr in ctx.expression():
            value = self.visit(expr).value
            if isMLiteral(value):
                value = MValue(value).getHardware(self.globalsHandler)
            toConcat.append(value)
        inputs = []
        wires: 'list[tuple[Node, Node]]' = []
        for node in toConcat:
            inputNode = Node()
            wires.append((node, inputNode))
            inputs.append(inputNode)
        sliceComponent = Function('{}', inputs)
        sliceComponent.addSourceTokens([(getSourceFilename(ctx), ctx.expression(0).getSourceInterval()[0]-1)])
        for src, dst in wires:
            Wire(src, dst)
        for expr in ctx.expression():
            sliceComponent.addSourceTokens([(getSourceFilename(ctx), expr.getSourceInterval()[-1]+1)])
        self.globalsHandler.currentComponent.addChild(sliceComponent)
        return MValue(sliceComponent.output)

    @decorateForErrorCatching
    def visitStringLiteral(self, ctx: build.MinispecPythonParser.MinispecPythonParser.StringLiteralContext):
        return MValue(UnsynthesizableComponent())
        # I don't think string literals do anything--they are only for system functions (dollar-sign
        # identifiers) or for comments.

    @decorateForErrorCatching
    def visitIntLiteral(self, ctx: build.MinispecPythonParser.MinispecPythonParser.IntLiteralContext):
        '''We have an integer literal, so we parse it and return it.
        Note that integer literals may be either integers or bit values. '''
        text = ctx.getText()
        tokensSourcedFrom = [(getSourceFilename(ctx), ctx.getSourceInterval()[0])]
        if text[0] == "'":
            # unsized literal, integer type
            # must check for hex values first since b and d are legitimate hex digits
            if 'h' in text: #hex value
                i = IntegerLiteral(int("0x"+text[2:], 0))
            elif 'b' in text: #binary
                i = IntegerLiteral(int("0b"+text[2:], 0))
            elif 'd' in text: #decimal value
                i = IntegerLiteral(int(text[2:]))
            else:
                raise Exception("Error: literal missing base indicator.")
        # must check for hex values first since b and d are legitimate hex digits
        elif 'h' in text: #hex value
            # TODO test this branch
            width, binValue = text.split("'h")
            assert len(width) > 0 and len(binValue) > 0, f"something went wrong with parsing {text} into width {width} and value {binValue}"
            i = Bit(IntegerLiteral(int(width)))(int("0x"+binValue, 0))
        elif 'b' in text: #binary
            width, binValue = text.split("'b")
            assert len(width) > 0 and len(binValue) > 0, f"something went wrong with parsing {text} into width {width} and value {binValue}"
            i = Bit(IntegerLiteral(int(width)))(int("0b"+binValue, 0))
        elif 'd' in text: #decimal value
            width, decValue = text.split("'d")
            assert len(width) > 0 and len(decValue) > 0, f"something went wrong with parsing {text} into width {width} and value {decValue}"
            i = Bit(IntegerLiteral(int(width)))(int(decValue))
        else:
            # else we have an ordinary decimal integer
            i = IntegerLiteral(int(text))
        iValue = MValue(i)
        iValue.addSourceTokens(tokensSourcedFrom)
        return iValue

    @decorateForErrorCatching
    def visitReturnExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ReturnExprContext):
        '''This is the return expression in a function. We keep track of return values
        by assigning them to `-return`. The `-` character was chosen because it cannot
        be used in minispec variable names.'''
        rhs = self.visit(ctx.expression()).value  # the value to return
        self.globalsHandler.currentScope.set(MValue(rhs), '-return')

    @decorateForErrorCatching
    def visitStructExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.StructExprContext):
        fieldValues = {}
        packingHardware = False
        try:
            structType = self.visit(ctx.typeName()).value
        except MissingVariableException:
            packingHardware = True
            structType = ctx.typeName().getText()
        for memberBind in ctx.memberBinds().memberBind():
            fieldName = memberBind.field.getText()
            fieldValue = self.visit(memberBind.expression()).value
            if not isMLiteral(fieldValue):
                packingHardware = True
            fieldValues[fieldName] = fieldValue
        if packingHardware:  # at least one of the fields is hardware, so we convert all of the fields to hardware, combine them, and return the output node.
            combineComp = Function(str(structType) + "{}", [Node() for field in fieldValues])
            combineComp.addSourceTokens([(getSourceFilename(ctx), ctx.typeName().getSourceInterval()[0])])
            fieldList = list(fieldValues)
            for i in range(len(fieldValues)):
                fieldName = fieldList[i]
                fieldValue = fieldValues[fieldName]
                if isMLiteral(fieldValue):
                    fieldValue = MValue(fieldValue).getHardware(self.globalsHandler)
                Wire(fieldValue, combineComp.inputs[i])
            self.globalsHandler.currentComponent.addChild(combineComp)
            return MValue(combineComp.output)
        else:
            return MValue(structType(fieldValues))  # no hardware, just a struct literal

    @decorateForErrorCatching
    def visitUndefinedExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.UndefinedExprContext):
        tokensSourcedFrom = [(getSourceFilename(ctx), ctx.getSourceInterval()[0])]
        d = DontCareLiteral()
        dValue = MValue(d)
        dValue.addSourceTokens(tokensSourcedFrom)
        return dValue

    @decorateForErrorCatching
    def visitSliceExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.SliceExprContext):
        ''' Slicing is just a function. Need to handle cases of constant/nonconstant slicing separately.
        Returns the result of slicing (the output of the slicing function).
        topLevel is true if this is the outermost slice in a nested slice (such as m[a][b][c]).'''
        toSliceFrom = self.visit(ctx.array).value
        if toSliceFrom.__class__ == Register:
            toSliceFrom = toSliceFrom.value
        msb = self.visit(ctx.msb).value #most significant bit
        if toSliceFrom.__class__ == PartiallyIndexedModule:
            # slicing further into a vector of module
            return MValue(toSliceFrom.indexFurther(self.globalsHandler, msb))
        if toSliceFrom.__class__ == VectorModule:
            # slicing into a vector of modules
            if not isMLiteral(msb):
                return MValue(PartiallyIndexedModule(toSliceFrom).indexFurther(self.globalsHandler, msb))
            return MValue(toSliceFrom.getNumberedSubmodule(msb.value))
        if ctx.lsb:
            lsb = self.visit(ctx.lsb).value #least significant bit
        if isMLiteral(toSliceFrom) and isMLiteral(msb) and ( (not (ctx.lsb)) or (ctx.lsb and isMLiteral(lsb)) ):  # perform the slice directly
            if ctx.lsb:
                return MValue(toSliceFrom.slice(msb, lsb))
            else:
                return MValue(toSliceFrom.slice(msb))
        if isMLiteral(toSliceFrom):
            toSliceFrom = toSliceFrom.getHardware(self.globalsHandler)
        # TODO refactor assert we have a node at this point
        if isNode(toSliceFrom):  # we are slicing into an ordinary variable
            text = "["
            inNode = Node()
            inputs = [inNode]
            wires: 'list[tuple[Node, Node]]' = [(toSliceFrom, inNode)]
            if isMLiteral(msb):
                text += str(msb)
            else:
                assert isNode(msb), "Expected a node"
                text += '_'
                inNode1 = Node()
                inputs.append(inNode1)
                wires.append((msb, inNode1))
            if ctx.lsb:
                text += ':'
                if isMLiteral(lsb):
                    text += str(lsb)
                else:
                    assert isNode(lsb), "Expected a node"
                    text += '_'
                    inNode2 = Node()
                    inputs.append(inNode2)
                    wires.append((lsb, inNode2))
            text += "]"
            sliceComponent = Function(text, inputs)
            for src, dst in wires:
                Wire(src, dst)
            sliceComponent.addSourceTokens([(getSourceFilename(ctx), ctx.msb.getSourceInterval()[0]-1)])
            if ctx.lsb:
                sliceComponent.addSourceTokens([(getSourceFilename(ctx), ctx.lsb.getSourceInterval()[-1]+1)])
            sliceComponent.addSourceTokens([(getSourceFilename(ctx), ctx.msb.getSourceInterval()[-1]+1)])
            self.globalsHandler.currentComponent.addChild(sliceComponent)
            return MValue(sliceComponent.output)
        else: # we are slicing into a submodule
            #TODO this code never runs?
            if msb.__class__ != IntegerLiteral:
                print(toSliceFrom.__class__)
                raise Exception("Variable slicing into modules is not implemented")
            return MValue(toSliceFrom.getNumberedSubmodule(msb.value))

    @decorateForErrorCatching
    def visitCallExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CallExprContext):
        '''We are calling a function. We synthesize the given function, wire it to the appropriate inputs,
        and return the function output node (which corresponds to the value of the function).'''
        # for now, we will assume that the fcn=exprPrimary in the callExpr must be a varExpr (with a var=anyIdentifier term).
        # this might also be a fieldExpr; I don't think there are any other possibilities with the current minispec specs.
        functionArgs = []
        allLiterals = True # true if all function args are literals, false otherwise. used for evaluating built-ins.
        for i in range(len(ctx.expression())):
            expr = ctx.expression(i)
            exprValue = self.visit(expr).value # visit the expression and get the corresponding node
            if exprValue.__class__ == UnsynthesizableComponent:
                return MValue(UnsynthesizableComponent())
            functionArgs.append(exprValue)
            if not isMLiteral(exprValue):
                allLiterals = False
        if ctx.fcn.__class__ == build.MinispecPythonParser.MinispecPythonParser.VarExprContext:
            # function call
            params: 'list[int]' = []
            if ctx.fcn.params():
                for param in ctx.fcn.params().param():
                    value = self.visit(param).value #visit the parameter and extract the corresponding expression, parsing it to an integer
                    #note that params may be either integers (which can be used as-is)
                    #   or variables (which need to be looked up) or expressions in integers (which need
                    #   to be evaluated and must evaluate to an integer).
                    assert value.__class__ == IntegerLiteral or value.__class__ == MType, f"Parameters must be an integer or a type, not {value} which is {value.__class__}"
                    params.append(value)
            functionToCall = ctx.fcn.var.getText()
            try:
                functionDef = self.globalsHandler.currentScope.get(self, functionToCall, params).value
                if functionDef.__class__ == UnsynthesizableComponent:
                    return MValue(UnsynthesizableComponent())
                self.globalsHandler.lastParameterLookup = params
                funcComponent = self.visit(functionDef).value  #synthesize the function internals
            except MissingVariableException as e:
                # we have an unknown bluespec built-in function
                functionName = functionToCall
                if len(params) > 0:  #attach parameters to the function name if present
                    functionName += "#(" + ",".join(str(i) for i in params) + ")"
                funcComponent = Function(functionName, [Node() for i in range(len(ctx.expression()))])
            except BluespecBuiltinFunction as e:
                functionComponent, evaluate = e.functionComponent, e.evalute
                if allLiterals:
                    return MValue(evaluate(*functionArgs))
                funcComponent = functionComponent
            funcComponent.addSourceTokens([(getSourceFilename(ctx), ctx.getSourceInterval()[0])])
            # hook up the funcComponent to the arguments passed in.
            for i in range(len(functionArgs)):
                exprValue = functionArgs[i]
                if isMLiteral(exprValue):
                    exprNode = MValue(exprValue).getHardware(self.globalsHandler)
                else:
                    exprNode = exprValue
                funcInputNode = funcComponent.inputs[i]
                Wire(exprNode, funcInputNode)
            self.globalsHandler.currentComponent.addChild(funcComponent)
            return MValue(funcComponent.output)  # return the value of this call, which is the output of the function
        elif ctx.fcn.__class__ == build.MinispecPythonParser.MinispecPythonParser.FieldExprContext:
            # module method with arguments
            toAccess = self.visit(ctx.fcn.exprPrimary()).value
            fieldToAccess = ctx.fcn.field.getText()
            if toAccess.metadata.__class__ == BluespecModuleWithMetadata:
                if len(functionArgs) == 0:
                    # this is actually just an ordinary method of the module, being called as `module.method()` instead of `module.method`.
                    raise Exception("Not implemented")
                return MValue(toAccess.metadata.getMethodWithArguments(self.globalsHandler, fieldToAccess, functionArgs, ctx.fcn.field))
            else:
                if len(functionArgs) == 0:
                    # this is actually just an ordinary method of the module, being called as `module.method()` instead of `module.method`.
                    # TODO make sure methods with no arguments are properly registered, etc.
                    return MValue(toAccess.methods[fieldToAccess])
                moduleWithMetadata: ModuleWithMetadata = toAccess.metadata
                methodDef, parentScope = moduleWithMetadata.methodsWithArguments[fieldToAccess]
                methodComponent = self.visitMethodDef(methodDef, parentScope).value
                methodComponent.addSourceTokens([(getSourceFilename(ctx), ctx.fcn.field.getSourceInterval()[0])])
                # hook up the methodComponent to the arguments passed in.
                for i in range(len(functionArgs)):
                    exprValue = functionArgs[i]
                    if isMLiteral(exprValue):
                        exprNode = MValue(exprValue).getHardware(self.globalsHandler)
                    else:
                        exprNode = exprValue
                    funcInputNode = methodComponent.inputs[i]
                    Wire(exprNode, funcInputNode)
                self.globalsHandler.currentComponent.addChild(methodComponent)
                return MValue(methodComponent.output)
        else:
            raise Exception(f"Unexpected lhs of function call {ctx.fcn.__class__}")

    @decorateForErrorCatching
    def visitFieldExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FieldExprContext):
        toAccess = self.visit(ctx.exprPrimary()).value
        field = ctx.field.getText()
        if toAccess.__class__ == PartiallyIndexedModule:
            return MValue(toAccess.getInput(self.globalsHandler, field))
        if toAccess.__class__ == Module:
            field = ctx.field.getText()
            if toAccess.metadata.__class__ == BluespecModuleWithMetadata:
                return MValue(toAccess.metadata.getMethod(field))
            return MValue(toAccess.methods[field])
        if toAccess.__class__ == Register:
            # we have a register containing a struct, extract its value.
            toAccess = toAccess.value
        if isMLiteral(toAccess):
            return MValue(toAccess.fieldBinds[field])
        fieldExtractComp = Function('.'+field, [Node()])
        fieldExtractComp.addSourceTokens([(getSourceFilename(ctx), ctx.field.getSourceInterval()[0])])
        Wire(toAccess, fieldExtractComp.inputs[0])
        self.globalsHandler.currentComponent.addChild(fieldExtractComp)
        return MValue(fieldExtractComp.output)

    @decorateForErrorCatching
    def visitParenExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ParenExprContext):
        return self.visit(ctx.expression())

    @decorateForErrorCatching
    def visitMemberBinds(self, ctx: build.MinispecPythonParser.MinispecPythonParser.MemberBindsContext):
        raise Exception("Handled in structExpr, should not be visited")

    @decorateForErrorCatching
    def visitMemberBind(self, ctx: build.MinispecPythonParser.MinispecPythonParser.MemberBindContext):
        raise Exception("Handled in structExpr, should not be visited")

    @decorateForErrorCatching
    def visitBeginEndBlock(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BeginEndBlockContext):
        beginendScope = ctx.scope
        beginendScope.parents = [self.globalsHandler.currentScope] # in case we are in a fleeting if/case statement scope
        self.globalsHandler.enterScope(beginendScope)
        for stmt in ctx.stmt():
            self.visit(stmt)
        self.globalsHandler.exitScope()

    @decorateForErrorCatching
    def visitRegWrite(self, ctx: build.MinispecPythonParser.MinispecPythonParser.RegWriteContext):
        '''To assign to a register, we put a wire from the value (rhs) to the register input.
        We don't create the wire here, since the register write might have occurred during an if statement--
        the wires are created at the end of the rule, in visitRuleDef.'''
        value = self.visit(ctx.rhs).value
        if ctx.lhs.__class__ == build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext:
            # ordinary register, no vectors
            regName = ctx.lhs.getText()
            self.globalsHandler.currentScope.set(MValue(value), regName + ".input")
            return
        # writing to a vector of registers
        # TODO test this more thoroughly and make sure it works
        indexes = []
        currentlvalue = ctx.lhs
        while currentlvalue.__class__ == build.MinispecPythonParser.MinispecPythonParser.IndexLvalueContext:
            indexValue = self.visit(currentlvalue.index).value
            indexes.append(indexValue)
            currentlvalue = currentlvalue.lvalue()
        assert currentlvalue.__class__ == build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext, "Unrecognized format for assignment to vector of registers"
        regName = currentlvalue.getText()
        outermostVector = self.globalsHandler.currentScope.get(self, regName).value
        regName += "."
        regsToWrite = [regName]
        # collect the register names to write to
        for k in range(len(indexes)):
            indexValue = indexes[len(indexes) - 1 - k]
            oldRegsToWrite = regsToWrite
            regsToWrite = []
            if indexValue.__class__ == IntegerLiteral:
                # fixed index value
                for i in range(len(oldRegsToWrite)):
                    regName = oldRegsToWrite[i] + f'[{indexValue.value}]'
                    regsToWrite.append(regName)
            else:
                # variable index value
                currentVector = outermostVector
                for j in range(k):
                    currentVector = currentVector.numberedSubmodules[0]
                numSubmodules = len(currentVector.numberedSubmodules)
                for j in range(numSubmodules):
                    for i in range(len(oldRegsToWrite)):
                        regName = oldRegsToWrite[i] + f'[{j}]'
                        regsToWrite.append(regName)
        # collect the values to assign
        vals = []
        for i in range(len(regsToWrite)):
            val = value
            if isMLiteral(val):
                val = MValue(val).getHardware(self.globalsHandler)
            vals.append(val)
        # assign the correct values
        for k in range(len(indexes)):
            indexValue = indexes[len(indexes) - 1 - k]
            if indexValue.__class__ == IntegerLiteral:
                # fixed index value, no corresponding hardware
                continue
            for i in range(len(regsToWrite)):
                # variable index, create the corresponding hardware
                regName = regsToWrite[i]
                oldVal = self.globalsHandler.currentScope.get(self, regName + "input").value
                val = vals[i]
                # variable index value, create a mux
                mux = Mux([Node(), Node()])
                # TODO mux inputNames
                eq = Function('=', [Node(), Node()])
                regIndex = regName.split(']')[k].split('[')[1]
                const = MValue(IntegerLiteral(int(regIndex))).getHardware(self.globalsHandler)
                Wire(eq.output, mux.control)
                Wire(indexValue, eq.inputs[0])
                Wire(const, eq.inputs[1])
                Wire(val, mux.inputs[0])
                Wire(oldVal, mux.inputs[1])
                for component in [mux, eq]:
                    self.globalsHandler.currentComponent.addChild(component)
                val = mux.output
                vals[i] = val
        for i in range(len(regsToWrite)):
            regName = regsToWrite[i]
            self.globalsHandler.currentScope.set(MValue(vals[i]), regName + "input")

    @decorateForErrorCatching
    def visitStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.StmtContext):
        ''' Each variety of statement is handled separately. '''
        return self.visitChildren(ctx)

    def runIfStmt(self, condition: 'Node', ifStmt: 'build.MinispecPythonParser.MinispecPythonParser.StmtContext', elseStmt: 'build.MinispecPythonParser.MinispecPythonParser.StmtContext|None', ctx):
        ''' Creates hardware corresponding to the if statement
        if (condition)
          ifStmt
        else
          elseStmt
        If elseStmt is None, does not run the elseStmt.
        Use in visitIfStmt and visitCaseStmt. '''
        # we run both branches in separate scopes, then combine

        ifScope = Scope(self.globalsHandler, "ifScope", [self.globalsHandler.currentScope], fleeting=True)
        elseScope = Scope(self.globalsHandler, "elseScope", [self.globalsHandler.currentScope], fleeting=True)
        originalScope = self.globalsHandler.currentScope

        self.globalsHandler.currentScope = ifScope
        self.visit(ifStmt)
        if elseStmt:
            self.globalsHandler.currentScope = elseScope
            self.visit(elseStmt)
        
        tokensSourcedFrom = [(getSourceFilename(ctx), ctx.getSourceInterval()[0])]
        # TODO source for 'else' token
        self.copyBackIfStmt(originalScope, condition, [ifScope, elseScope], [BooleanLiteral(True), BooleanLiteral(False)], tokensSourcedFrom)

    def copyBackIfStmt(self, originalScope: 'Scope', condition: 'Node', childScopes: 'list[Scope]', conditionLiterals: 'list[MLiteral]', tokensSourcedFrom = None):
        ''' Given a collection of child scopes, the original scope, and a condition node, copies the variables set in the 
        child scopes back into the original scope with muxes controlled by the condition node.
        conditionLiterals is the list of MLiterals which indicate which child scope would be selected. '''
        self.globalsHandler.currentScope = originalScope
        varsToBind = set()
        for scope in childScopes:
            for var in scope.temporaryScope.temporaryValues:
                varsToBind.add(var)
        for var in varsToBind:
            values = [ scope.get(self, var).value for scope in childScopes ]  # if var doesn't appear in one of these scopes, the lookup will find its original value
            # since the control signal is hardware, we convert the values to hardware as well (if needed)
            for i in range(len(values)):
                if isMLiteral(values[i]):
                    values[i] = MValue(values[i]).getHardware(self.globalsHandler)
            muxComponent = Mux([ Node('v'+str(i)) for i in range(len(values)) ], Node('c'))
            muxComponent.inputNames = [str(value) for value in conditionLiterals]
            if tokensSourcedFrom:
                muxComponent.addSourceTokens(tokensSourcedFrom)
            for i in range(len(values)):
                Wire(values[i], muxComponent.inputs[i])
            Wire(condition, muxComponent.control)
            self.globalsHandler.currentComponent.addChild(muxComponent)
            originalScope.set(MValue(muxComponent.output), var)

    @decorateForErrorCatching
    def visitIfStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.IfStmtContext):
        condition = self.visit(ctx.expression()).value
        if isMLiteral(condition):
            # we select the appropriate branch
            if condition == BooleanLiteral(True):
                self.visit(ctx.stmt(0))
            else:
                if ctx.stmt(1):
                    self.visit(ctx.stmt(1))
        else:
            self.runIfStmt(condition, ctx.stmt(0), ctx.stmt(1), ctx)

    def doCaseStmtStep(self, expr: 'Node|MLiteral', expri: 'list', index: 'int', defaultItem: 'None|build.MinispecPythonParser.MinispecPythonParser.CaseStmtDefaultItemContext') -> None:
        ifScope = Scope(self.globalsHandler, "ifScope", [self.globalsHandler.currentScope], fleeting=True)
        elseScope = Scope(self.globalsHandler, "elseScope", [self.globalsHandler.currentScope], fleeting=True)
        originalScope = self.globalsHandler.currentScope

        exprToMatch = expri[index][0]
        ifStmt = expri[index][1]

        # set up the if/else condition.
        # we create an equality tester to compare the expr and the exprToMatch and pass in the output node.
        # if they are booleans and one is a literal, we feed the non-boolean in directly (or inverted) to avoid boolean laundering.
        # if both are literals, we evaluate directly.
        if isMLiteral(expr) and isMLiteral(exprToMatch):
            #TODO test short-circuiting literals early
            # two cases: expr and exprToMatch agree, in which case the case statement ends here and there is no branching, 
            # or expr and exprToMatch do not agree, which should not happen since we have already removed nonmatching literals when constructing expri.
            assert expr.eq(exprToMatch)
            self.visit(ifStmt)  # run this in the original scope since there is no branching, then end the case statement.
            return
        elif isMLiteral(expr) and not isMLiteral(exprToMatch) and expr.__class__ == Bool:
            if expr:
                condition = exprToMatch
            else:
                n = Function('~', [Node()])
                wIn = Wire(exprToMatch, n.inputs[0])
                for component in [n, wIn]:
                    self.globalsHandler.currentComponent.addChild(component)
                condition = n.output
        elif not isMLiteral(expr) and isMLiteral(exprToMatch) and exprToMatch.__class__ == Bool:
            if exprToMatch:
                condition = exprToMatch
            else:
                n = Function('~', [Node()])
                wIn = Wire(expr, n.inputs[0])
                for component in [n, wIn]:
                    self.globalsHandler.currentComponent.addChild(component)
                condition = n.output
        else:  # neither are boolean literals
            if isMLiteral(expr):
                exprHardware: 'Node' = expr.getHardware(self.globalsHandler)
            else:
                exprHardware: 'Node' = expr
            if isMLiteral(exprToMatch):
                exprToMatch = exprToMatch.getHardware(self.globalsHandler)
            eqComp = Function('==', [Node(), Node()])
            wire1 = Wire(exprHardware, eqComp.output)
            wire2 = Wire(exprToMatch, eqComp.output)
            for component in [eqComp, wire1, wire2]:
                self.globalsHandler.currentComponent.addChild(component)
            condition = eqComp.output

        self.globalsHandler.currentScope = ifScope
        self.visit(ifStmt)

        self.globalsHandler.currentScope = elseScope
        if index + 1 < len(expri):
            self.doCaseStmtStep(expr, expri, index+1, defaultItem)
        elif defaultItem:
            self.visit(defaultItem.stmt())

        self.copyBackIfStmt(originalScope, condition, [ifScope, elseScope], [BooleanLiteral(True), BooleanLiteral(False)])

        self.globalsHandler.currentScope = originalScope

    @decorateForErrorCatching
    def visitCaseStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CaseStmtContext):
        ''' The case statement:
        case (expr)
          expr1: stmt1;
          expr2: stmt2;
          ...
          default: stmt0;
        endcase
        is equivalent to:
        value = expr;
        if (value == expr1)
            stmt1
        else if (value == expr2):
            stmt2
        ...
        else stmt0;
        Because of the nested if statments, the default clause criteria will be extracted naturally from the nested if statements.
        If there is no default statement, there is no final else statement. (In an inline case expr, and only in an inline case expr, the final clause becomes the final else statement if there is no default clause.)
        Optimizations: if all expr evaluate to literals, we only run the correct branch.
        If all expri evaluate to literals and all possibilities are covered, we run each branch in parallel
        and use multi-input muxes.
        '''
        expr = self.visit(ctx.expression()).value
        allExprLiteral = isMLiteral(expr)
        allExpriLiteral = True
        expri = []  # list of pairs [self.visit(exprCtx), stmtCtx] in order that they should be considered, excluding the default case and skipping repeat literals.
        expriLiterals = [] # list of literals found when visiting each expri
        for caseStmtItem in ctx.caseStmtItem():
            for expression in caseStmtItem.expression():
                currentExpr = self.visit(expression).value
                if isMLiteral(currentExpr):
                    for otherLiteral in expriLiterals:
                        if currentExpr.__class__ == otherLiteral.__class__  and currentExpr.eq(otherLiteral):
                            # we have a duplicate literal which will never be reached, so we discard it
                            continue
                    if isMLiteral(expr) and not expr.eq(currentExpr):
                        # we have a branch of the case statement which will never run, so we skip it
                        continue
                    expriLiterals.append(currentExpr)
                else:
                    allExprLiteral = False
                    allExpriLiteral = False
                expri.append([currentExpr, caseStmtItem.stmt()])
        if allExprLiteral:  # we can fold the case statement and select only the relevant branch
            for comp, stmt in expri:
                if expr.eq(comp):
                    self.visit(stmt)
                    return
            # nothing matched, so we do the default statement if there is one, otherwise do nothing.
            if ctx.caseStmtDefaultItem():
                self.visit(ctx.caseStmtDefaultItem().stmt())
            return
        if allExpriLiteral:  
            # - since we have already removed duplicate literals, exactly (technically at most, but "do nothing" may
            # - be considered to be a statement if not all statements are covered) one expri statement will run.
            # - we run each one in a separate scope and collect the results afterward using multi-width muxes.
            # - we need to determine if there is an implicit default "do nothing"--specifically, if there is no
            #   default statement given and not all possible literals are covered, we need to have an extra default
            #   scope that corresponds to no expri statement running.
            if isMLiteral(expr):
                expr = expr.getHardware(self.globalsHandler)
            hasDefault = ctx.caseStmtDefaultItem() != None
            numLiteralsNeeded = min([literal[0].numLiterals() for literal in expri])
            numLiteralsPresent = len(expri)
            # it is possible for a default statement to be present and needed, present and not needed, not present and needed, or not present and not needed.
            # hasDefault is true if a default statement is present.
            # coversAllCases is true if the cases in expri cover all of the cases, and false if a default statement is needed.
            if numLiteralsPresent == numLiteralsNeeded:
                coversAllCases = True
            else:
                assert numLiteralsPresent < numLiteralsNeeded, "Something has gone wrong with counting literals"
                coversAllCases = False
            scopes = []
            for i in range(len(expri) + (0 if coversAllCases else 1)):
                childScope = Scope(self.globalsHandler, "childScope"+str(i), [self.globalsHandler.currentScope], fleeting=True)
                scopes.append(childScope)
            originalScope = self.globalsHandler.currentScope

            for i in range(len(expri)):
                scope = scopes[i]
                exprToMatch, exprStmt = expri[i]
                # self.globalsHandler.enterScope(scope)
                self.globalsHandler.currentScope = scope
                self.visit(exprStmt)
            if hasDefault and numLiteralsPresent < numLiteralsNeeded:  # run the default scope in the last scope
                scope = scopes[-1]
                # self.globalsHandler.enterScope(scope)
                self.globalsHandler.currentScope = scope
                self.visit(ctx.caseStmtDefaultItem().stmt())
            
            tokensSourcedFrom = [(getSourceFilename(ctx), ctx.getSourceInterval()[0]), (getSourceFilename(ctx), ctx.getSourceInterval()[-1])]
            self.copyBackIfStmt(originalScope, expr, scopes, [str(pair[0]) for pair in expri] + ([] if coversAllCases else ['default']), tokensSourcedFrom)
            return
        # run the case statement as a sequence of if statements.
        self.doCaseStmtStep(expr, expri, 0, ctx.caseStmtDefaultItem())

    @decorateForErrorCatching
    def visitCaseStmtItem(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CaseStmtItemContext):
        raise Exception("Handled in visitCaseStmt--not visited.")

    @decorateForErrorCatching
    def visitCaseStmtDefaultItem(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CaseStmtDefaultItemContext):
        raise Exception("Handled in visitCaseStmt--not visited.")

    @decorateForErrorCatching
    def visitForStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ForStmtContext):
        iterVarName = ctx.initVar.getText()
        initVal = self.visit(ctx.expression(0)).value
        assert isMLiteral(initVal), "For loops must be unrolled before synthesis"
        self.globalsHandler.currentScope.set(MValue(initVal), iterVarName)
        checkDone = self.visit(ctx.expression(1)).value
        assert isMLiteral(checkDone) and checkDone.__class__ == BooleanLiteral, "For loops must be unrolled before synthesis"
        while checkDone.value:
            self.visit(ctx.stmt())
            nextIterVal = self.visit(ctx.expression(2)).value
            assert isMLiteral(nextIterVal), "For loops must be unrolled before synthesis"
            self.globalsHandler.currentScope.set(MValue(nextIterVal), iterVarName)
            checkDone = self.visit(ctx.expression(1)).value
            assert isMLiteral(checkDone) and checkDone.__class__ == BooleanLiteral, "For loops must be unrolled before synthesis"
        

def getParseTree(text: 'str') -> 'build.MinispecPythonParser.MinispecPythonParser.PackageDefContext':
    ''' Given text minispec code, return the corresponding parse tree. '''
    data = antlr4.InputStream(text)
    lexer = build.MinispecPythonLexer.MinispecPythonLexer(data)
    stream = antlr4.CommonTokenStream(lexer)
    parser = build.MinispecPythonParser.MinispecPythonParser(stream)
    tree = parser.packageDef()  #start parsing at the top-level packageDef rule (so "tree" is the root of the parse tree)
    #print(tree.toStringTree(recog=parser)) #prints the parse tree in lisp form (see https://www.antlr.org/api/Java/org/antlr/v4/runtime/tree/Trees.html )
    return tree

def getSourceFilename(node: 'ctxType') -> 'str':
    ''' Given a parse node, returns the filename that the parse node came from (no .ms).
    Uses the fact that parseAndSynth sets the root of each tree to have attribute
    `filename` which is the desired filename. '''
    if node.parentCtx != None:
        return getSourceFilename(node.parentCtx)
    if hasattr(node, 'filename'):
        return node.filename
    # TODO handle sources that point back to the command line, as in the `32` in `visual Adder.ms "add#(32)"`.
    return "unknown_filename"

from typing import Callable # for annotation function calls
def parseAndSynth(text: 'str', topLevel: 'str', filename: 'str' ='', pullTextFromImport: 'Callable[[int],int]' = lambda x: 1/0, sourceFilesCollect: 'list[tuple[str, str]]' = []) -> 'Component':
    ''' text is the text to parse and synthesize.
    topLevel is the name (including parametrics) of the function/module to synthesize.
    filename is the name of the file that text is from (no .ms).
    pullTextFromImport is a function that takes in the name of a minispec file to parse (no .ms)
    and returns the text of the given file.
    sourceFilesCollect is a mutable list that will be appended with tuples (filename, text) for all
    files imported, including the original source file.'''

    tree = getParseTree(text)

    globalsHandler = GlobalsHandler()

    builtinScope = BuiltInScope(globalsHandler, "built-ins", [])
    startingFile = Scope(globalsHandler, "startingFile", [builtinScope])

    namesAlreadyImported: 'set[str]' = {filename} # list of filenames already imported. used to ensure each file is imported exactly once.
    importsAndText: 'list[tuple[str, str, ctxType]]' = []  # list of tuples consisting of filenames (no .ms), their text, and the base node of the corresponding parse tree.
    # earlier files are later in the import tree and should be imported sooner.
    def collectImports(filename, text, tree):
        ''' Given a file to import, visits all imports called by that file, adds them to namesAlreadyImported
        and importsAndText, then adds itself to importsAndText. '''
        for packageStmt in tree.packageStmt():
            toImport = packageStmt.importDecl()
            if toImport:
                for identifier in toImport.identifier():
                    importFilename = identifier.getText()
                    if importFilename not in namesAlreadyImported:
                        namesAlreadyImported.add(importFilename)
                        importText = pullTextFromImport(importFilename)
                        importTree = getParseTree(importText)
                        collectImports(importFilename, importText, importTree)
        importsAndText.append((filename, text, tree))
        sourceFilesCollect.append((filename, text))
    collectImports(filename, text, tree)

    # statically analyze each parse tree under the same globals handler
    walker = build.MinispecPythonListener.ParseTreeWalker()
    listener = StaticTypeListener(globalsHandler)
    for filename, text, tree in importsAndText:
        globalsHandler.currentScope = startingFile
        walker.walk(listener, tree)  # walk the listener through the tree
        tree.filename = filename  # so the tree knows what file it came from--used by getSourceFilename.

    # for scope in globalsHandler.allScopes:
    #     print(scope)

    synthesizer = SynthesizerVisitor(globalsHandler)

    topLevel = f'''
function Bool _();
    return {topLevel};
endfunction
'''

    topLevelParseTree = getParseTree(topLevel)
    ctxOfNote = topLevelParseTree.packageStmt(0).functionDef().stmt(0).exprPrimary().expression().binopExpr().unopExpr().exprPrimary()
    outputDef = synthesizer.visit(ctxOfNote).value  # follow the call to the function and get back the functionDef/moduleDef.
    if outputDef.__class__ == build.MinispecPythonParser.MinispecPythonParser.ModuleDefContext:
        moduleArgs = []
        moduleParams = globalsHandler.lastParameterLookup  # TODO refactor to handle multiple layers of parameters
        output = synthesizer.visitModuleDef(outputDef, moduleParams, moduleArgs).module  # visit the functionDef/moduleDef in the given file and synthesize it. store the result in 'output'
    elif outputDef.__class__ == build.MinispecPythonParser.MinispecPythonParser.FunctionDefContext:
        output = synthesizer.visit(outputDef).value  # visit the functionDef/moduleDef in the given file and synthesize it. store the result in 'output'
    else:
        raise Exception(f"Expected module or function, not {outputDef.__class__}")


    # for scope in globalsHandler.allScopes:
    #     print(scope)

    # output.prune() #remove unused components
    output._persistent = True

    return output


def tokensAndWhitespace(text: 'str') -> 'list[str]':
    ''' Returns a list of all grammar tokens from ANTLR in text, including whitespace
    tokens and the final <EOF> token. '''
    data = antlr4.InputStream(text)
    lexer = build.MinispecPythonLexer.MinispecPythonLexer(data)
    stream = antlr4.CommonTokenStream(lexer)
    stream.getText() # mutates stream somehow to populate stream.tokens ... not sure exactly what is going here.
    tokenTextList = [token.text for token in stream.tokens]
    return tokenTextList


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
