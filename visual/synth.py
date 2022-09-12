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

newline = '\n' #used to format f-strings such as "Hi{newline}there" since backslash is not allowed in f-strings

'''
Implementation Agenda:

    - Fixing parametric lookups
    - Module methods with arguments
    - Vectors of submodules (and more generally, indexing into a submodule)--use a demultiplexer
    - Shared modules/Modules with arguments
    - BSV imports of modules

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

class TemporaryScope:
    ''' Stores temporary state used in synthesis. '''
    def __init__(self):
        self.temporaryValues = {}
        
        ''' dictionary of registers, only used in a module, str is the variable name that points
        to the register in the module scope  so that:
            self.registers[someRegisterName] = self.get(self, someRegisterName) '''
        self.registers: 'dict[str, Register]' = {}
        self.nonregisterSubmodules: 'dict[str, Module]' = {}  # same as self.registers but for all other submodules. Used to assign submodule inputs.
        ''' dictionary of inputs, returns the default value ctx if there is one, or None otherwise.
        input string has the form "inner.enable" for input enable of submodule inner. '''
        self.inputsWithDefault: 'dict[str, None|"build.MinispecPythonParser.MinispecPythonParser.ExpressionContext"]' = {}
        # temporary version of inputsWithDefault used inside submodules. only stores the name of the input ("enable",
        # not "inner.enable") since the submodule does not have access to this information.
        self.currentInputsWithDefault: 'dict[str, None|"build.MinispecPythonParser.MinispecPythonParser.ExpressionContext"]' = {}
        # values to assign to each input. To assign True to inner.enable, we set .submoduleInputValues["inner.enable"] = True.
        # all None values must be replaced by the rules, so that all inputs are assigned values.
        self.submoduleInputValues: 'dict[tuple[Module|Register, str], Node|MLiteral|None]' = {}

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
    def clearTemporaryValues(self):
        '''clears temporary values used in synthesis. should be called after synthesizing a function/module.'''
        self.temporaryScope.temporaryValues = {}
    def matchParams(visitor, intValues: 'list[int]', storedParams: 'list[ctxType|str]'):
        '''returns a dictionary mapping str -> int if intValues can fit storedParams.
        returns None otherwise.'''
        if len(intValues) != len(storedParams):
            return None
        d = {}  #make sure parameters match
        for i in range(len(intValues)):
            if storedParams[i].__class__ == str:
                d[storedParams[i]] = intValues[i]
            elif visitor.visit(storedParams[i]) != intValues[i]:
                return None
        return d
    def get(self, visitor, varName: 'str', parameters: 'list[int]' = None) -> 'ctxType|Node|None':
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
        if varName in self.permanentValues:
            for storedParams, ctx in self.permanentValues[varName][::-1]: #iterate backwards through the stored values, looking for the most recent match.
                d = Scope.matchParams(visitor, parameters, storedParams)
                if d != None:
                    self.globalsHandler.parameterBindings = d
                    return ctx
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
        assert len(parameters) == 0, f"Can't assign variable {varName} dynamically with parameters"
        if self.fleeting:
            self.temporaryScope.temporaryValues[varName] = value
        else:
            if varName in self.permanentValues:
                self.temporaryScope.temporaryValues[varName] = value
            else:
                assert len(self.parents) == 1, f"Can't assign variable {varName} dynamically in a file scope"
                self.parents[0].set(value, varName, parameters)
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

class BuiltInScope(Scope):
    '''The minispec built-ins. Behaves slightly differently from other scopes.'''
    def __init__(self, globalsHandler: 'GlobalsHandler', name: 'str', parents: 'list[Scope]'):
        self.globalsHandler = globalsHandler
        self.parents = parents.copy()
        self.name = name
        # self.permanentValues = {}
        # self.temporaryValues = {}
    def set(self, value, varName: 'str', parameters: 'list[int]' = None):
        raise Exception(f"Can't set value {varName} in the built-in scope")
    def setPermanent(self, value, varName: 'str', parameters: 'list[ctxType|str]' = None):
        raise Exception(f"Can't set value {varName} permanently in the built-in scope")
    def get(self, visitor, varName: 'str', parameters: 'list[int|MType]' = None) -> 'ctxType|Node':
        '''Looks up the given name/parameter combo. Prefers current scope to parent scopes, and
        then prefers temporary values to permanent values. Returns whatever is found,
        probably a ctx object (functionDef).
        Returns a ctx object or a typeName.'''
        if varName == 'Bit':
            assert len(parameters) == 1, "bit takes exactly one parameter"
            n = parameters[0]
            return Bit(n)
        if varName == 'Vector':
            assert len(parameters) == 2, "vector takes exactly two parameters"
            k, typeValue = parameters
            return Vector(k, typeValue)
        if varName == 'Bool':
            return Bool
        if varName == 'Reg' or varName == 'RegU':
            assert len(parameters) == 1, "A register takes exactly one parameter"
            return BuiltinRegisterCtx(parameters[0])
        if varName == 'True':
            assert len(parameters) == 0, "A boolean literal has no parameters"
            return Bool(True)
        if varName == 'False':
            assert len(parameters) == 0, "A boolean literal has no parameters"
            return Bool(False)
        if varName == 'Invalid':
            assert len(parameters) == 0, "An invalid literal has no parameters"
            return Invalid(Any)
        if varName == 'Valid':
            assert len(parameters) == 0, "An valid literal has no parameters"
            functionComp = Function('Valid', [], [Node()])
            def valid(mliteral: 'MLiteral'):
                return Maybe(mliteral.__class__)(mliteral)
            raise BluespecBuiltinFunction(functionComp, valid)
        if varName == 'fromMaybe':
            assert len(parameters) == 0, "fromMaybe has no parameters"
            functionComp = Function('fromMaybe', [], [Node(), Node()])
            def fromMaybe(default: 'MLiteral', mliteral: 'MLiteral'):
                if mliteral.isValid:
                    return mliteral.value
                return default
            raise BluespecBuiltinFunction(functionComp, fromMaybe)
        if varName == 'Maybe':
            assert len(parameters) == 1, "A maybe type has exactly one parameter"
            mtype = parameters[0]
            return Maybe(mtype)
        raise MissingVariableException(f"Couldn't find variable {varName} with parameters {parameters}.")

#type annotation for context objects.
ctxType = ' | '.join([ctxType for ctxType in dir(build.MinispecPythonParser.MinispecPythonParser) if ctxType[-7:] == "Context"][:-3])


class BuiltinRegisterCtx:
    def __init__(self, mtype: 'MType'):
        self.mtype = mtype
    def accept(self, visitor):
        return visitor.visitRegister(self.mtype)


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
        self.outputNode = None  # the output node to which a return statement should go, used in functions and methods
        #TODO move outputNode to temporary scope

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
        self.globalsHandler.currentScope.setPermanent(ctx, functionName, params)
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
        if ctx.argFormals():
            raise Exception(f"Modules with arguments not currently supported{newline}{ctx.toStringTree(recog=parser)}{newline}{ctx.argFormals().toStringTree(recog=parser)}")

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
        self.globalsHandler.currentScope.setPermanent(ctx, moduleName, params)
        self.globalsHandler.enterScope(moduleScope)

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
                self.globalsHandler.currentScope.setPermanent(varInit.rhs, varName)
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
        self.globalsHandler.currentScope.setPermanent(ctx, typedefName, params)

    def enterTypeDefEnum(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefEnumContext):
        ''' Evaluate the typedef and log the appropriate variables. '''
        enumName = ctx.upperCaseIdentifier().getText()
        enumNames = []
        for element in ctx.typeDefEnumElement():
            enumNames.append(element.tag.getText())
        enumType = Enum(enumName, set(enumNames))
        self.globalsHandler.currentScope.setPermanent(enumType, enumName)
        for name in enumNames:
            self.globalsHandler.currentScope.setPermanent(enumType(name), name)

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
        self.globalsHandler.currentScope.setPermanent(ctx, typedefName, params)

    def enterBeginEndBlock(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BeginEndBlockContext):
        beginendScope = Scope(self.globalsHandler, "begin/end", [self.globalsHandler.currentScope])
        ctx.scope = beginendScope
        self.globalsHandler.enterScope(beginendScope)

    def exitBeginEndBlock(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BeginEndBlockContext):
        self.globalsHandler.exitScope()

    def enterForStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ForStmtContext):
        self.globalsHandler.currentScope.setPermanent(None, ctx.initVar.getText())

    def enterSliceExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.SliceExprContext):
        ctx.slicingIntoSubmodule = False

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
visitModuleDef: Returns the module hardware
visitModuleId: Error, this node is handled in moduleDef and should not be visited
visitModuleStmt: Error, this node is handled in moduleDef and should not be visited
visitSubmoduleDecl: No returns, mutates existing hardware
visitInputDef: No returns, mutates existing hardware
visitMethodDef: If the method has no args, no returns. If the method has args, then visiting the method is like
    calling a function and will return the output node (this has not yet been implemented).
visitRuleDef: No returns, mutates existing hardware
visitFunctionDef: Returns the function hardware
visitFunctionId: Error, this node is handled in functionDef and should not be visited
visitVarAssign: No returns, mutates existing hardware
visitMemberLvalue: a tuple ( str, tuple[Node], str ), see method for details
visitIndexLvalue: a tuple ( str, tuple[Node], str ), see method for details
visitSimpleLvalue: a tuple ( str, tuple[Node], str ), see method for details
visitSliceLvalue: a tuple ( str, tuple[Node], str ), see method for details
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

    def visitRegister(self, mtype: 'MType'):
        ''' Visiting the built-in moduleDef of a register. Return the synthesized register. '''
        return Register('Reg#(' + str(mtype) + ')')

    def visitVectorSubmodule(self, vectorType):
        ''' We have a vector submodule. We create the relevant hardware. '''
        vectorComp = VectorModule([], "", [], {}, {})  # the name can't be determined until we visit the inner modules and get their name
        previousComp = self.globalsHandler.currentComponent
        self.globalsHandler.currentComponent = vectorComp
        # TODO consider entering/exiting the builtin scope here?

        vectorizedSubmodule = vectorType._typeValue
        numCopies = vectorType._k.value
        assert numCopies >= 1, "It does not make sense to have a vector of no submodules."
        for i in range(numCopies):
            submodule = self.visit(vectorizedSubmodule)
            self.globalsHandler.currentComponent.addChild(submodule)
            vectorComp.addNumberedSubmodule(submodule)

        vectorComp.name = "Vector#(" + str(numCopies) + "," + str(submodule.name) + ")"
        self.globalsHandler.currentComponent = previousComp

        # assigning M[i][j] = value should be the same as assigning the ith submodule of M to have inputs
        # corresponding to value and j, then then having the jth input of M[i] be assigned to whichever input
        # corresponding to value. For nonconstant i,j, we will need to feed them into the appropriate muxes.

        # also, any assignment M[i][j] etc. must end with .input for some named input, or it is a register
        # and the relevant .input is implicitly ._input.

        return vectorComp

    def __init__(self, globalsHandler: 'GlobalsHandler') -> None:
        self.globalsHandler = globalsHandler
    
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
        assert ctx.typeName(), "Should have a typeName. Did the grammar change?"
        return self.visit(ctx.typeName())

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
        typeObject = self.globalsHandler.currentScope.get(self, typeName, params)
        assert typeObject != None, f"Failed to find type {typeName} with parameters {params}"
        if typeObject.__class__ == MType:
            # we have a type
            return typeObject
        if issubclass(typeObject.__class__, Component):
            # we have a module/register
            return typeObject
        if typeObject.__class__ == build.MinispecPythonParser.MinispecPythonParser.TypeDefSynonymContext or typeObject.__class__ == build.MinispecPythonParser.MinispecPythonParser.TypeDefStructContext:
            # we have a type context
            typeObject = self.visit(typeObject)
        return typeObject

    def visitPackageDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.PackageDefContext):
        raise Exception("PackageDef should only be visited during static elaboration, not synthesis")

    def visitPackageStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.PackageStmtContext):
        raise Exception("PackageStmt should only be visited during static elaboration, not synthesis")

    def visitImportDecl(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ImportDeclContext):
        raise Exception("Not implemented")

    def visitBsvImportDecl(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BsvImportDeclContext):
        raise Exception("Not implemented")

    def visitTypeDecl(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDeclContext):
        raise Exception('Handled during static elaboration. Only subtypes typeDefSynonym and typeDefStruct should be visited.')

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
            typedefScope.set(val, var)

        originalType = self.visit(ctx.typeName())

        self.globalsHandler.exitScope()
        return Synonym(originalType, typedefName)

    def visitTypeId(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeIdContext):
        raise Exception("Handled directly, should not be visited.")

    def visitTypeDefEnum(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefEnumContext):
        raise Exception("Handled during static elaboration.")

    def visitTypeDefEnumElement(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefEnumElementContext):
        raise Exception("Handled during static elaboration.")

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
            typedefScope.set(val, var)

        fields = {}
        for structMember in ctx.structMember():
            fieldTypeName = self.visit(structMember.typeName())
            fieldName = structMember.lowerCaseIdentifier().getText()
            fields[fieldName] = fieldTypeName

        self.globalsHandler.exitScope()
        return Struct(typedefName, fields)

    def visitStructMember(self, ctx: build.MinispecPythonParser.MinispecPythonParser.StructMemberContext):
        raise Exception("Handled in typeDefStruct, not visited")

    def visitVarBinding(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarBindingContext):
        typeValue = self.visit(ctx.typeName())
        for varInit in ctx.varInit():
            varName = varInit.var.getText()
            if (varInit.rhs):
                value = self.visit(varInit.rhs)
            else:
                value = None
            if value.__class__ == Node:
                value.setMType(typeValue)
            self.globalsHandler.currentScope.set(value, varName)

    def visitLetBinding(self, ctx: build.MinispecPythonParser.MinispecPythonParser.LetBindingContext):
        '''A let binding declares a variable or a concatenation of variables and optionally assigns
        them to the given expression node ("rhs").'''
        if not ctx.rhs:
            rhsValue = None
        else:
            rhsValue = self.visit(ctx.rhs)  #we expect a node corresponding to the desired value
        if len(ctx.lowerCaseIdentifier()) == 1:
            varName = ctx.lowerCaseIdentifier(0).getText() #the variable we are assigning
            self.globalsHandler.currentScope.set(rhsValue, varName)
        else:
            raise Exception("Not Implemented")
        
        # for now, we only handle the case of assigning a single variable (no concatenations).
        # nothing to return.
        #TODO handle other cases

    def visitVarInit(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarInitContext):
        raise Exception("Not visited--handled under varBinding to access typeName.")

    def visitModuleDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ModuleDefContext):
        moduleName = ctx.moduleId().name.getText()
        params = self.globalsHandler.lastParameterLookup
        if len(params) > 0:  #attach parameters to the function name if present
            moduleName += "#(" + ",".join(str(i) for i in params) + ")"
        if ctx.argFormals():
            raise Exception(f"Modules with arguments not currently supported{newline}{ctx.toStringTree(recog=parser)}{newline}{ctx.argFormals().toStringTree(recog=parser)}")

        moduleScope = ctx.scope
        previousTemporaryScope = self.globalsHandler.currentScope.temporaryScope #TODO refactor to get rid of this weird manipulation
        self.globalsHandler.enterScope(moduleScope)
        
        #bind any parameters in the module scope
        bindings = self.globalsHandler.parameterBindings
        for var in bindings:  
            val = bindings[var]
            moduleScope.set(val, var)

        moduleComponent = Module(moduleName, [], {}, {})
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
                raise Exception("moduleStmt stmt is not implemented")
            elif moduleStmt.functionDef():
                continue # Only synthesize functions when called
            else:
                raise Exception("Unknown variant. Did the grammar change?")

        # synthesize inputs, submodules, methods, and rules, in that order

        for inputDef in inputDefs:
            oldCurrentInputs = moduleScope.temporaryScope.currentInputsWithDefault
            moduleScope.temporaryScope.currentInputsWithDefault = {}
            self.visit(inputDef)
            for inputName in moduleScope.temporaryScope.currentInputsWithDefault:
                defaultValCtxOrNone = moduleScope.temporaryScope.currentInputsWithDefault[inputName]
                # copy any inputs into the parent scope, so that any parent module knows about the inputs
                previousTemporaryScope.currentInputsWithDefault[inputName] = defaultValCtxOrNone
            moduleScope.temporaryScope.currentInputsWithDefault = oldCurrentInputs
        for submoduleDecl in submoduleDecls:
            self.visit(submoduleDecl)
            # save submodule inputs with default values
            submoduleName = submoduleDecl.name.getText()
            for inputName in moduleScope.temporaryScope.currentInputsWithDefault:
                defaultExprCtx = moduleScope.temporaryScope.currentInputsWithDefault[inputName]
                moduleScope.temporaryScope.inputsWithDefault[submoduleName + "." + inputName] = defaultExprCtx
            moduleScope.temporaryScope.currentInputsWithDefault = {}
        for methodDef in methodDefs:
            if not methodDef.argFormals(): # only methodDefs with no arguments are synthesized in the module
                self.visit(methodDef)
        # evaluate default inputs
        for submoduleAndInputName in moduleScope.temporaryScope.inputsWithDefault:
            defaultCtxOrNone = moduleScope.temporaryScope.inputsWithDefault[submoduleAndInputName]
            if defaultCtxOrNone:
                moduleScope.temporaryScope.submoduleInputValues[submoduleAndInputName] = self.visit(defaultCtxOrNone)
            else:
                moduleScope.temporaryScope.submoduleInputValues[submoduleAndInputName] = None

        for ruleDef in ruleDefs:
            self.visit(ruleDef)

        # now that we have synthesized the rules, we need to collect all submodule inputs set across the rules and wire them in.
        # We can't wire in submodule inputs during the rules, since an input with a default input will confuse the first rule (since the input may or may not be set in a later rule).
        ''' Handling inputs.
        - moduleScope.nonregisterSubmodules is a dictionary mapping the variable name of a submodule to the
          corresponding component.
        - Each submodule component in moduleScope.nonregisterSubmodules has a dictionary .inputs mapping the name of the
          input to the node corresponding to the input.
        - When each submodule is synthesized, it logs all inputs and any default values in the dictionary moduleScope.inputsWithDefault,
          which maps moduleScope.inputsWithDefault[input: str] = defaultExpressionCtx or None (if there is no default).
          Specifically, when an input has a default value, it logs the default value into
          submodule.currentInputsWithDefault, and after the input is visited, this value is copied into moduleScope.inputsWithDefault
          along with name of the module.
        - The reason for separating currentInputsWithDefault and inputsWithDefault is that when a submodule is being synthesized, it
          does not know what its assigned variable name will be in the original module, and we need to log default input expressions
          under the correct submodule.
        - Before evaluating any rules, we evaluate each default value and log them in moduleScope.submoduleInputValues, along with None
          for any inputs without default values.
        - For each rule, we must begin by assigning all known (not None) submodule inputs from moduleScope.submoduleInputValues under the 
          correct name (eg set(value, "inner.enble")).
        - During each rule, some of these module inputs may be reassigned to new Nodes or MLiterals.
        - At the end of each rule, any input assignments are recorded in moduleScope.submoduleInputValues as the input
          to assign. Since bsc guarantees each input is assigned at most once, this will not override anything (note
          that we are overwriting the originally calculated default values).
        - After all rules have been evaluated, we must for each submodule input in moduleScope.submoduleInputValues, create and
          connect the relevant hardware to the relevant submodule input. We throw an error if nothing is assigned to some input.
        This strategy will need some adjustment to account for shared modules, whose inputs may be assigned in different rules across different modules,
        but this should not be much more difficult since the only issue is not making any default assignments until all modules which may assign
        inputs have made their assignments (so, default assignments are made in the module in which the shared module is declared).
        '''
        for submoduleAndInputName in moduleScope.temporaryScope.submoduleInputValues:
            value = moduleScope.temporaryScope.submoduleInputValues[submoduleAndInputName]
            #assert value != None, "All submodule inputs must be assigned"  #TODO put this assert check back in, remove the value==None continue.
            if value == None:
                continue
            if isMLiteral(value):
                value = value.getHardware(self.globalsHandler)
            assert isNode(value), "value must be hardware in order to wire in to input node"
            submoduleName, inputName = submoduleAndInputName.split('.')
            submoduleComponent: 'Module' = moduleScope.temporaryScope.nonregisterSubmodules[submoduleName]
            inputNode = submoduleComponent.inputs[inputName]
            wireIn = Wire(value, inputNode)
            self.globalsHandler.currentComponent.addChild(wireIn)
            
        self.globalsHandler.currentComponent = previousComponent #reset the current component/scope
        self.globalsHandler.exitScope()

        return moduleComponent

    def visitModuleId(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ModuleIdContext):
        ''' Handled in moduleDef '''
        raise Exception("Handled in moduleDef, should never be visited")

    def visitModuleStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ModuleStmtContext):
        raise Exception("Not accessed directly, handled in moduleDef")

    def visitSubmoduleDecl(self, ctx: build.MinispecPythonParser.MinispecPythonParser.SubmoduleDeclContext):
        ''' We have a submodule, so we synthesize it and add it to the current module.
        We also need to bind to submodule's methods somehow; methods with no args bind to
        the corresponding module output, while methods with args need to be somehow tracked as
        functions calls that can be visited and synthesized, returning their output.
        function/module analogy:
            moduleDef <-> functionDef
            submoduleDecl <-> callExpr
         '''
        moduleDef = self.visit(ctx.typeName())  # get the moduleDef ctx. Automatically extracts params.
        print('got submodule def', moduleDef, repr(moduleDef))

        moduleComponent = self.visit(moduleDef)  #synthesize the module

        self.globalsHandler.currentComponent.addChild(moduleComponent)
        submoduleName = ctx.name.getText()
        originalModuleScope = self.globalsHandler.currentScope
        originalModuleScope.setPermanent(None, submoduleName)
        originalModuleScope.set(moduleComponent, submoduleName)

        if moduleComponent.isRegister():  # log the submodule in the appropriate dictionary for handling register assignments/submodule inputs.
            originalModuleScope.temporaryScope.registers[submoduleName] = moduleComponent
        else:
            originalModuleScope.temporaryScope.nonregisterSubmodules[submoduleName] = moduleComponent

    def visitInputDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.InputDefContext):
        ''' Add the appropriate input to the module, with hardware to handle the default value.
        Bind the input in the appropriate context. (If the input is named 'in' then we bind in->Node('in').) '''
        inputName = ctx.name.getText()
        self.globalsHandler.currentScope.temporaryScope.currentInputsWithDefault[inputName] = ctx.defaultVal
        inputType = self.visit(ctx.typeName())
        inputNode = Node(inputName, inputType)
        self.globalsHandler.currentScope.setPermanent(None, inputName)
        self.globalsHandler.currentScope.set(inputNode, inputName)
        self.globalsHandler.currentComponent.addInput(inputNode, inputName)
        # I think we might need to be a little fancy with default values.
        # If an input is assigned sometimes as determined by an if statement, then there will be a mux
        # leading to the input and the other branch of the mux should be the default value.
        # Alternatively, if the input is never assigned, then the default value should be hard-coded in.
        # For now, we will not implement default values.

        # I think that just as a module keeps a list of all of its registers for reg writes, 
        # a module will also need to keep a list of all submodule inputs for handling default values.
        # The mechanism should work identically.

    def visitMethodDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.MethodDefContext):
        '''
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
        methodType = self.visit(ctx.typeName())
        if not ctx.argFormals(): # there are no arguments, so we synthesize the method inside the current module.
            if ctx.expression():
                methodName = ctx.name.getText()
                methodNode = Node(methodName, methodType)
                value = self.visit(ctx.expression())
                if isMLiteral(value):  # convert value to hardware before linking to output node
                    value = value.getHardware(self.globalsHandler)
                setWire = Wire(value, methodNode)
                self.globalsHandler.currentComponent.addChild(setWire)
                self.globalsHandler.currentComponent.addMethod(methodNode, methodName)
            else:
                methodName = ctx.name.getText()
                methodOutput = Node(methodName, methodType)  # set up the output node
                self.globalsHandler.outputNode = methodOutput
                self.globalsHandler.currentComponent.addMethod(methodOutput, methodName)
                methodScope = ctx.scope
                moduleScope = self.globalsHandler.currentScope
                self.globalsHandler.enterScope(methodScope)
                for registerName in moduleScope.temporaryScope.registers:  # bind the registers
                    register = moduleScope.temporaryScope.registers[registerName]
                    methodScope.setPermanent(None, registerName)
                    methodScope.set(register.value, registerName)
                for stmt in ctx.stmt():  # evaluate the method
                    self.visit(stmt)
                self.globalsHandler.exitScope()
                self.globalsHandler.outputNode = None  # methods can't occur inside a function, so there is no need to remember any previous output node.
        else:
            raise Exception("Not implemented")

    def visitRuleDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.RuleDefContext):
        # registers keep their original value unless modified
        ruleScope: 'Scope' = ctx.scope
        moduleScope: 'Scope' = self.globalsHandler.currentScope
        self.globalsHandler.enterScope(ruleScope)
        for registerName in moduleScope.temporaryScope.registers:
            register = moduleScope.temporaryScope.registers[registerName]
            ruleScope.setPermanent(None, registerName + ".input")
            ruleScope.setPermanent(None, registerName)
            ruleScope.set(register.value, registerName + '.input')
            ruleScope.set(register.value, registerName)
        for inputName in moduleScope.temporaryScope.submoduleInputValues:  # bind any default inputs
            value = moduleScope.temporaryScope.submoduleInputValues[inputName]
            # if value != None:  # don't need this since none values should never by referenced
            ruleScope.setPermanent(None, inputName)
            ruleScope.set(value, inputName)
        for stmt in ctx.stmt():
            self.visit(stmt)
        # wire in the register writes
        for registerName in moduleScope.temporaryScope.registers:
            register = moduleScope.temporaryScope.registers[registerName]
            value = ruleScope.get(self, registerName + ".input")
            if isMLiteral(value):  # convert value to hardware before assigning to register
                value = value.getHardware(self.globalsHandler)
            setWire = Wire(value, register.input)
            self.globalsHandler.currentComponent.addChild(setWire)
        #find any input assignments
        for inputName in moduleScope.temporaryScope.submoduleInputValues:
            newValue = ruleScope.get(self, inputName)
            moduleScope.temporaryScope.submoduleInputValues[inputName] = newValue
        self.globalsHandler.exitScope()

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
        previousOutputNode = self.globalsHandler.outputNode
        self.globalsHandler.outputNode = funcComponent.output
        # log the current component
        previousComponent = self.globalsHandler.currentComponent
        self.globalsHandler.currentComponent = funcComponent
        # synthesize the function internals
        for stmt in ctx.stmt():
            self.visit(stmt)

        self.globalsHandler.exitScope()
        self.globalsHandler.currentComponent = previousComponent #reset the current component
        self.globalsHandler.outputNode = previousOutputNode
        return funcComponent

    def visitFunctionId(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionIdContext):
        ''' Handled from functionDef '''
        raise Exception("Handled from functionDef, should never be visited")

    def visitVarAssign(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarAssignContext):
        ''' Assign the given variable to the given expression. No returns, mutates existing hardware. '''
        print('assigning var', ctx.getText())
        varList = ctx.lvalue()  #list of lhs vars
        #TODO "varList" in the Minispec grammar points to a curly brace '{', not a list of variables.
        #   This is confusing and not useful--should 'varList=' be removed from the grammar?
        if len(varList) > 1:  #I'm not sure how multiple assignments are supposed to work--
            # bsc says something about type errors and tuples. TODO figure this out, same issue holds for visitLetBinding.
            raise Exception("Not Implemented")
        lvalue = varList[0]
        value = self.visit(ctx.expression())
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
            self.globalsHandler.currentScope.set(value, varName)
            return
        # Otherwise, we convert to hardware.
        if isMLiteral(value):
            value = value.getHardware(self.globalsHandler)
        if lvalue.__class__ == build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext:
            # assign the variable, no slicing/subfields needed
            varName = lvalue.getText()
            self.globalsHandler.currentScope.set(value, varName)
            return
        # insert the field/slice/index
        # first, detect if we are setting a module input
        if lvalue.__class__ == build.MinispecPythonParser.MinispecPythonParser.MemberLvalueContext:
            prospectiveModuleName = lvalue.getText().split('[')[0].split('.')[0] # remove slices ([) and fields (.)
            print('maybe module', prospectiveModuleName)
            try:
                settingOverall = self.globalsHandler.currentScope.get(self, prospectiveModuleName)
                if settingOverall.__class__ == Module:
                    # submodule input assignment has the form
                    #   moduleName[i]...[k].inputName
                    if lvalue.lvalue().__class__ == build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext: # no slicing is present, only the input name.
                        inputName = lvalue.lowerCaseIdentifier().getText()
                        self.globalsHandler.currentScope.set(value, prospectiveModuleName + "." + inputName)
                        return
                    else:
                        # we are slicing into a module. we create the appropriate hardware.
                        return
                        raise Exception("Not implemented")  #TODO implement this
                else:
                    pass  # not a module, move on
            except MissingVariableException:
                pass  # not a module, move on
        text, nodes, varName = self.visit(lvalue)
        insertComponent = Function(text, [], [Node() for node in nodes] + [Node()])
        for i in range(len(nodes)):
            wire = Wire(nodes[i], insertComponent.inputs[i])
            self.globalsHandler.currentComponent.addChild(wire)
        newWire = Wire(value, insertComponent.inputs[len(nodes)])
        self.globalsHandler.currentComponent.addChild(insertComponent)
        self.globalsHandler.currentComponent.addChild(newWire)
        self.globalsHandler.currentScope.set(insertComponent.output, varName)


    def visitMemberLvalue(self, ctx: build.MinispecPythonParser.MinispecPythonParser.MemberLvalueContext):
        ''' Returns a tuple ( str, tuple[Node], str ) where str is the slicing text interpreted so far,
        tuple[Node] is the tuple of nodes corresponding to variable input (including the variable being updated),
        and the last str is varName, the name of the variable being updated. '''
        text, nodes, varName = self.visit(ctx.lvalue())
        text += '.' + ctx.lowerCaseIdentifier().getText()
        return (text, nodes, varName)  # no new selection input nodes since field selection is not dynamic

    def visitIndexLvalue(self, ctx: build.MinispecPythonParser.MinispecPythonParser.IndexLvalueContext):
        ''' Returns a tuple ( str, tuple[Node], str ) where str is the slicing text interpreted so far,
        tuple[Node] is the tuple of nodes corresponding to variable input (including the variable being updated),
        and the last str is varName, the name of the variable being updated. '''
        text, nodes, varName = self.visit(ctx.lvalue())
        index = self.visit(ctx.index)
        text += '['
        if isNode(index):
            nodes += (index,)
            text += '_'
        else:
            text += str(index)
        text += ']'
        return (text, nodes, varName)

    def visitSimpleLvalue(self, ctx: build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext):
        ''' Returns a tuple ( str, tuple[Node], str ) where str is the slicing text interpreted so far,
        tuple[Node] is the tuple of nodes corresponding to variable input (including the variable being updated),
        and the last str is varName, the name of the variable being updated. '''
        valueFound = self.globalsHandler.currentScope.get(self, ctx.getText())
        if valueFound == None:
            # value has not yet been initialized
            return ("", tuple(), ctx.getText())
        if isMLiteral(valueFound):
            valueFound = valueFound.getHardware(self.globalsHandler)
        return ("", (valueFound,), ctx.getText())

    def visitSliceLvalue(self, ctx: build.MinispecPythonParser.MinispecPythonParser.SliceLvalueContext):
        ''' Returns a tuple ( str, tuple[Node], str ) where str is the slicing text interpreted so far,
        tuple[Node] is the tuple of nodes corresponding to variable input (including the variable being updated),
        and the last str is varName, the name of the variable being updated. '''
        text, nodes, varName = self.visit(ctx.lvalue())
        msb = self.visit(ctx.msb)
        lsb = self.visit(ctx.lsb)
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
        return (text, nodes, varName)

    def visitOperatorExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.OperatorExprContext):
        '''This is an expression corresponding to a binary operation (which may be a unary operation,
        which may be an exprPrimary). We return the Node or MLiteral with the corresponding output value.'''
        value = self.visit(ctx.binopExpr())
        assert isNodeOrMLiteral(value), f"Received {value} from {ctx.toStringTree(recog=parser)}"
        return value

    def visitCondExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CondExprContext):
        condition = self.visit(ctx.expression(0))
        if isMLiteral(condition):
            # we select the appropriate branch
            if condition == BooleanLiteral(True):
                return self.visit(ctx.expression(1))
            else:
                if ctx.stmt(1):
                    return self.visit(ctx.expression(2))
        else:
            value1 = self.visit(ctx.expression(1))
            value2 = self.visit(ctx.expression(2))
            # since the control signal is hardware, we convert the values to hardware as well (if needed)
            if isMLiteral(value1):
                value1 = value1.getHardware(self.globalsHandler)
            if isMLiteral(value2):
                value2 = value2.getHardware(self.globalsHandler)
            muxComponent = Mux([Node('v1'), Node('v2')], Node('c'))
            for component in [muxComponent, Wire(value1, muxComponent.inputs[0]), Wire(value2, muxComponent.inputs[1]), Wire(condition, muxComponent.control)]:
                self.globalsHandler.currentComponent.addChild(component)
            return muxComponent.output
        #TODO go back through ?/if statements and make sure hardware/literal cases are handled properly.

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
        expr = self.visit(ctx.expression())
        expri: 'tuple[MLiteral|Node, MLiteral|Node]' = [] # pairs (comparisonStmt, valueToOutput)
        hasDefault = False
        for caseExprItem in ctx.caseExprItem():
            if not caseExprItem.exprPrimary():  # no selection expression, so we have a default expression.
                hasDefault = True
                defaultValue = self.visit(caseExprItem.expression())
                break
            correspondingOutput = self.visit(caseExprItem.expression())
            for comparisonStmt in caseExprItem.exprPrimary():
                expri.append((self.visit(comparisonStmt), correspondingOutput))
        if isMLiteral(expr) and all([isMLiteral(pair[0]) for pair in expri]) and ((not hasDefault) or (hasDefault and isMLiteral(defaultValue))): # case 1
            for pair in expri:
                if pair[0].eq(expr):
                    return pair[1]
            assert hasDefault, "all branches must be covered"
            return defaultValue
        if all([isMLiteral(pair[0]) for pair in expri]) and ((not hasDefault) or (hasDefault and isMLiteral(defaultValue))): # case 2
            assert not isMLiteral(expr), "We assume expr is not a literal here, so we do not have to eliminate any extra values."
            possibleOutputs = [] # including the default output, if present
            expriIndex = 0
            for i in range(len(ctx.caseExprItem()) + (-1 if hasDefault else 0)):
                caseExprItem = ctx.caseExprItem(i)
                possibleOutputs.append(expri[expriIndex][1])
                expriIndex += len(caseExprItem.exprPrimary())
            if hasDefault:
                possibleOutputs.append(defaultValue)
            mux = Mux([Node() for i in range(len(possibleOutputs))])
            for i in range(len(possibleOutputs)):  # convert all possible outputs to hardware
                possibleOutput = possibleOutputs[i]
                if isMLiteral(possibleOutput):
                    possibleOutputs[i] = possibleOutput.getHardware(self.globalsHandler)
            wires = [Wire(expr, mux.control)] + [ Wire(possibleOutputs[i], mux.inputs[i]) for i in range(len(possibleOutputs)) ]
            for component in [mux] + wires:
                self.globalsHandler.currentComponent.addChild(component)
            return mux.output
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
        nextWires = [ Wire(muxes[i+1].output, muxes[i].inputs[1]) for i in range(len(expri)-1) ]

        valueWires = []
        for i in range(len(expri)):  # create hardware for values
            value = expri[i][1]
            if isMLiteral(value):
                value = value.getHardware(self.globalsHandler)
            valueWires.append(Wire(value, muxes[i].inputs[0]))
        if isMLiteral(defaultValue):
            defaultValue = defaultValue.getHardware(self.globalsHandler)
        valueWires.append(Wire(defaultValue, muxes[-1].inputs[1]))
        
        controlWires = []
        controlComponents = []
        for i in range(len(expri)):  # create hardware for controls
            controlValue = expri[i][0]
            muxControl = muxes[i].control
            assert not (isMLiteral(controlValue) and isMLiteral(expr)), "This case should have been evaluated earlier"
            if isMLiteral(expr) and expr.__class__ == Bool:
                if expr:
                    controlWires.append(Wire(controlValue, muxControl))
                else:
                    n = Function('~', [], [Node()])
                    controlComponents.append(n)
                    controlWires.append(Wire(controlValue, n.inputs[0]))
                    controlWires.append(Wire(n.output, muxControl))
            elif isMLiteral(controlValue) and controlValue.__class__ == Bool:
                if controlValue:
                    controlWires.append(Wire(expr, muxControl))
                else:
                    n = Function('~', [], [Node()])
                    controlComponents.append(n)
                    controlWires.append(Wire(expr, n.inputs[0]))
                    controlWires.append(Wire(n.output, muxControl))
            else:
                if isMLiteral(controlValue):
                    controlValue = controlValue.getHardware(self.globalsHandler)
                eq = Function('==', [], [Node(), Node()])
                controlComponents.append(eq)
                controlWires.append(Wire(expr, eq.inputs[0]))
                controlWires.append(Wire(controlValue, eq.inputs[1]))
                controlWires.append(Wire(eq.output, muxControl))
        for component in muxes + nextWires + valueWires + controlWires + controlComponents:
                self.globalsHandler.currentComponent.addChild(component)
        return muxes[0].output if len(muxes) > 0 else defaultValue

    def visitCaseExprItem(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CaseExprItemContext):
        raise Exception("Handled in caseExpr, should not be visited")

    def visitBinopExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BinopExprContext):
        if ctx.unopExpr():  # our binary expression is actually a unopExpr.
            return self.visit(ctx.unopExpr())
        #we are either manipulating nodes/wires or manipulating integers.
        left = self.visit(ctx.left)
        right = self.visit(ctx.right)
        if not isNodeOrMLiteral(left): #we have received a ctx from constant storage, probably references to global constants that should evaluate to integers. Evaluate them.
            left = self.visit(left)
        if not isNodeOrMLiteral(right):
            right = self.visit(right)
        assert isNodeOrMLiteral(left), "left side must be literal or node"
        assert isNodeOrMLiteral(right), "right side must be literal or node"
        op = ctx.op.text
        '''Combining literals'''
        if isMLiteral(left) and isMLiteral(right): #we have two literals, so we combine them
            return {'**': MLiteralOperations.pow,
                    '*': MLiteralOperations.mul,
                    '/': MLiteralOperations.div,
                    '%': MLiteralOperations.mod,
                    '+': MLiteralOperations.add,
                    '-': MLiteralOperations.sub,
                    '<<': MLiteralOperations.sleft,
                    '>>': MLiteralOperations.sright,
                    '<': MLiteralOperations.lt,
                    '<=': MLiteralOperations.le,
                    '>': MLiteralOperations.gt,
                    '>=': MLiteralOperations.ge,
                    '==': MLiteralOperations.eq,
                    '!=': MLiteralOperations.neq,
                    '&': MLiteralOperations.bitand,
                    '^': MLiteralOperations.bitxor,
                    '^~': MLiteralOperations.bitnor,
                    '~^': MLiteralOperations.bitnor,
                    '|': MLiteralOperations.bitor,
                    '&&': MLiteralOperations.booleanand,
                    '||': MLiteralOperations.booleanor}[op](left, right)
        # convert literals to hardware
        if isMLiteral(left):
            left = left.getHardware(self.globalsHandler)
        if isMLiteral(right):
            right = right.getHardware(self.globalsHandler)
        # both left and right are nodes, so we combine them using function hardware and return the output node.
        assert left.__class__ == Node and right.__class__ == Node, "left and right should be hardware"
        binComponent = Function(op, [], [Node("l"), Node("r")])
        leftWireIn = Wire(left, binComponent.inputs[0])
        rightWireIn = Wire(right, binComponent.inputs[1])
        for component in [binComponent, leftWireIn, rightWireIn]:
            self.globalsHandler.currentComponent.addChild(component)
        return binComponent.output

        #assert False, f"binary expressions can only handle two nodes or two integers, received {left} and {right}"

    def visitUnopExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.UnopExprContext):
        ''' Return the Node or MLiteral corresponding to the expression '''
        if not ctx.op:  # our unopExpr is actually just an exprPrimary.
            value = self.visit(ctx.exprPrimary())
            if not isNodeOrMLiteral(value):
                if hasattr(value, 'isRegister') and value.isRegister():
                    value: 'Register' = value.value
                else:
                    value = self.visit(value)
            assert isNodeOrMLiteral(value), f"Received {value.__repr__()} from {ctx.exprPrimary().toStringTree(recog=parser)}"
            return value
        value = self.visit(ctx.exprPrimary())
        if not isNodeOrMLiteral(value):
            value = self.visit(value)
        assert isNodeOrMLiteral(value), f"Received {value.__repr__()} from {ctx.exprPrimary().toStringTree(recog=parser)}"
        op = ctx.op.text
        if isMLiteral(value):
            return {'!': MLiteralOperations.booleaninv,
                    '~': MLiteralOperations.inv,
                    '&': MLiteralOperations.redand,
                    '~&': MLiteralOperations.notredand,
                    '|': MLiteralOperations.redor,
                    '~|': MLiteralOperations.notredor,
                    '^': MLiteralOperations.redxor,
                    '^~': MLiteralOperations.notredxor,
                    '~^': MLiteralOperations.notredxor,
                    '+': MLiteralOperations.unaryadd,
                    '-': MLiteralOperations.neg}[op](value)
        assert value.__class__ == Node, "value should be hardware"
        unopComponenet = Function(op, [], [Node("v")])
        wireIn = Wire(value, unopComponenet.inputs[0])
        for component in [unopComponenet, wireIn]:
            self.globalsHandler.currentComponent.addChild(component)
        return unopComponenet.output

    def visitVarExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarExprContext):
        '''We are visiting a variable/function name. We look it up and return the correpsonding information
        (which may be a Node or a ctx or a tuple (ctx/Node, paramMappings), for instance).'''
        params: 'list[int]' = []
        if ctx.params():
            for param in ctx.params().param():
                value = self.visit(param) #visit the parameter and extract the corresponding expression, parsing it to an integer
                #note that params may be either integers (which can be used as-is)
                #   or variables (which need to be looked up) or expressions in integers (which need
                #   to be evaluated and must evaluate to an integer).
                assert value.__class__ == IntegerLiteral or value.__class__ == MType, f"Parameters must be an integer or a type, not {value} which is {value.__class__}"
                params.append(value)
        value = self.globalsHandler.currentScope.get(self, ctx.var.getText(), params)
        self.globalsHandler.lastParameterLookup = params
        return value

    def visitBitConcat(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BitConcatContext):
        ''' Bit concatenation is just a function. Returns the function output. '''
        toConcat = []
        for expr in ctx.expression():
            value = self.visit(expr)
            if isMLiteral(value):
                value = value.getHardware(self.globalsHandler)
            toConcat.append(value)
        inputs = []
        for node in toConcat:
            inputNode = Node()
            inputWire = Wire(node, inputNode)
            self.globalsHandler.currentComponent.addChild(inputWire)
            inputs.append(inputNode)
        sliceComponent = Function('{}', [], inputs)
        self.globalsHandler.currentComponent.addChild(sliceComponent)
        return sliceComponent.output

    def visitStringLiteral(self, ctx: build.MinispecPythonParser.MinispecPythonParser.StringLiteralContext):
        pass
        # I don't think string literals do anything--they are only for system functions (dollar-sign
        # identifiers) or for comments.

    def visitIntLiteral(self, ctx: build.MinispecPythonParser.MinispecPythonParser.IntLiteralContext):
        '''We have an integer literal, so we parse it and return it.
        Note that integer literals may be either integers or bit values. '''
        text = ctx.getText()
        if 'b' in text: #binary
            width, binValue = text.split("'b")
            assert len(width) > 0 and len(binValue) > 0, f"something went wrong with parsing {text} into width {width} and value {binValue}"
            return Bit(IntegerLiteral(int(width)))(int("0b"+binValue, 0))
        if 'h' in text: #hex value
            raise Exception("Not implemented")
        if 'd' in text: #not sure, decimal?
            raise Exception("Not implemented")
        # else we have an integer
        return IntegerLiteral(int(text))

    def visitReturnExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ReturnExprContext):
        '''This is the return expression in a function. We need to put the correct wire
        attaching the right hand side to the output of the function.'''
        rhs = self.visit(ctx.expression())  # the node with the value to return
        if isMLiteral(rhs):
            rhs = rhs.getHardware(self.globalsHandler)
        outputNode = self.globalsHandler.outputNode
        returnWire = Wire(rhs, outputNode)
        self.globalsHandler.currentComponent.addChild(returnWire)

    def visitStructExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.StructExprContext):
        structType = self.visit(ctx.typeName())
        fieldValues = {}
        packingHardware = False
        for memberBind in ctx.memberBinds().memberBind():
            fieldName = memberBind.field.getText()
            fieldValue = self.visit(memberBind.expression())
            if not isMLiteral(fieldValue):
                packingHardware = True
            fieldValues[fieldName] = fieldValue
        if packingHardware:  # at least one of the fields is hardware, so we convert all of the fields to hardware, combine them, and return the output node.
            combineComp = Function(str(structType) + "{}", [], [Node() for field in fieldValues])
            fieldList = list(fieldValues)
            for i in range(len(fieldValues)):
                fieldName = fieldList[i]
                fieldValue = fieldValues[fieldName]
                if isMLiteral(fieldValue):
                    fieldValue = fieldValue.getHardware(self.globalsHandler)
                wireIn = Wire(fieldValue, combineComp.inputs[i])
                self.globalsHandler.currentComponent.addChild(wireIn)
            self.globalsHandler.currentComponent.addChild(combineComp)
            return combineComp.output
        else:
            return structType(fieldValues)  # no hardware, just a struct literal

    def visitUndefinedExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.UndefinedExprContext):
        return DontCareLiteral()

    def visitSliceExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.SliceExprContext):
        ''' Slicing is just a function. Need to handle cases of constant/nonconstant slicing separately.
        Returns the result of slicing (the output of the slicing function). '''
        print('slicing into', ctx.getText())
        toSliceFrom = self.visit(ctx.array)
        msb = self.visit(ctx.msb) #most significant bit
        if ctx.lsb:
            lsb = self.visit(ctx.lsb) #least significant bit
        if isMLiteral(toSliceFrom) and isMLiteral(msb) and ( (not (ctx.lsb)) or (ctx.lsb and isMLiteral(lsb)) ):  # perform the slice directly
            if ctx.lsb:
                return toSliceFrom.slice(msb, lsb)
            else:
                return toSliceFrom.slice(msb)
        if isMLiteral(toSliceFrom):
            toSliceFrom = toSliceFrom.getHardware(self.globalsHandler)
        if isNode(toSliceFrom) and not ctx.slicingIntoSubmodule:  # we are slicing into an ordinary variable
            text = "["
            inNode = Node()
            inputs = [inNode]
            inWire = Wire(toSliceFrom, inNode)
            inWires = [inWire]
            if isMLiteral(msb):
                text += str(msb)
            else:
                assert isNode(msb), "Expected a node"
                text += '_'
                inNode1 = Node()
                inputs.append(inNode1)
                inWire1 = Wire(msb, inNode1)
                inWires.append(inWire1)
            if ctx.lsb:
                text += ':'
                if isMLiteral(lsb):
                    text += str(lsb)
                else:
                    assert isNode(lsb), "Expected a node"
                    text += '_'
                    inNode2 = Node()
                    inputs.append(inNode2)
                    inWire2 = Wire(lsb, inNode2)
                    inWires.append(inWire2)
            text += "]"
            sliceComponent = Function(text, [], inputs)
            self.globalsHandler.currentComponent.addChild(sliceComponent)
            for wire in inWires:
                self.globalsHandler.currentComponent.addChild(wire)
            return sliceComponent.output
        else: # we are slicing into a submodule
            ctx.parentCtx.slicingIntoSubmodule = True  # pass the information outward
            # print('dealing with slice', ctx.array.getText(), ctx.msb.getText())
            assert not ctx.lsb, f"Can't slice {ctx.getText()} into a vector of submodules"
            if not ctx.slicingIntoSubmodule:
                assert toSliceFrom.__class__ == VectorModule, "Must be vector of submodules"
            if isNode(toSliceFrom):
                # construct the next step in going inward
                print('construct next slice', ctx.getText())
                return toSliceFrom
            else:
                # innermost slice, outermost module
                print('innermost slice, outermost module', ctx.getText())
                methodValue = Node()
                import random
                toSliceFrom.addMethod(methodValue, ctx.getText()+str(random.random()))
                print('msb', msb, msb.__class__)
                if msb.__class__ == Integer:
                    targetInnerSubmodule = toSliceFrom.getNumberedSubmodule(msb.value)
                    targetNode = Node()
                    targetInnerSubmodule.addMethod(targetNode, ctx.getText()+str(random.random()))
                    print('targetting', targetInnerSubmodule.name, 'from', toSliceFrom.name)
                    wireIn = Wire(targetNode, methodValue)
                    self.globalsHandler.currentComponent.addChild(wireIn)
                else:
                    raise Exception("Variable slicing into a vector of submodules is not implemented yet")
                return methodValue


    def visitCallExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CallExprContext):
        '''We are calling a function. We synthesize the given function, wire it to the appropriate inputs,
        and return the function output node (which corresponds to the value of the function).'''
        # for now, we will assume that the fcn=exprPrimary in the callExpr must be a varExpr (with a var=anyIdentifier term).
        # this might also be a fieldExpr; I don't think there are any other possibilities with the current minispec specs.
        functionToCall = ctx.fcn.var.getText()
        functionArgs = []
        allLiterals = True # true if all function args are literals, false otherwise. used for evaluating built-ins.
        for i in range(len(ctx.expression())):
            expr = ctx.expression(i)
            exprValue = self.visit(expr) # visit the expression and get the corresponding node
            functionArgs.append(exprValue)
            if not isMLiteral(exprValue):
                allLiterals = False
        params: 'list[int]' = []
        if ctx.fcn.params():
            for param in ctx.fcn.params().param():
                value = self.visit(param) #visit the parameter and extract the corresponding expression, parsing it to an integer
                #note that params may be either integers (which can be used as-is)
                #   or variables (which need to be looked up) or expressions in integers (which need
                #   to be evaluated and must evaluate to an integer).
                assert value.__class__ == IntegerLiteral or value.__class__ == MType, f"Parameters must be an integer or a type, not {value} which is {value.__class__}"
                params.append(value)
        try:
            functionDef = self.globalsHandler.currentScope.get(self, functionToCall, params)
            self.globalsHandler.lastParameterLookup = params
            funcComponent = self.visit(functionDef)  #synthesize the function internals
        except MissingVariableException as e:
            # we have an unknown bluespec built-in function
            functionName = functionToCall
            if len(params) > 0:  #attach parameters to the function name if present
                functionName += "#(" + ",".join(str(i) for i in params) + ")"
            funcComponent = Function(functionName, [], [Node() for i in range(len(ctx.expression()))])
        except BluespecBuiltinFunction as e:
            functionComponent, evaluate = e.functionComponent, e.evalute
            if allLiterals:
                return evaluate(*functionArgs)
            funcComponent = functionComponent
        funcComponent.tokensSourcedFrom.append(ctx.getSourceInterval()[0])
        # hook up the funcComponent to the arguments passed in.
        for i in range(len(functionArgs)):
            exprValue = functionArgs[i]
            if isMLiteral(exprValue):
                exprNode = exprValue.getHardware(self.globalsHandler)
            else:
                exprNode = exprValue
            funcInputNode = funcComponent.inputs[i]
            wireIn = Wire(exprNode, funcInputNode)
            self.globalsHandler.currentComponent.addChild(wireIn)
        self.globalsHandler.currentComponent.addChild(funcComponent)
        return funcComponent.output  # return the value of this call, which is the output of the function

    def visitFieldExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FieldExprContext):
        toAccess = self.visit(ctx.exprPrimary())
        if toAccess.__class__ == Module:
            fieldToAccess = ctx.field.getText()
            return toAccess.methods[fieldToAccess]
        else:
            field = ctx.field.getText()
            if isMLiteral(toAccess):
                return toAccess.fieldBinds[field]
            fieldExtractComp = Function('.'+field, [], [Node()])
            wireIn = Wire(toAccess, fieldExtractComp.inputs[0])
            self.globalsHandler.currentComponent.addChild(fieldExtractComp)
            self.globalsHandler.currentComponent.addChild(wireIn)
            return fieldExtractComp.output

    def visitParenExpr(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ParenExprContext):
        return self.visit(ctx.expression())

    def visitMemberBinds(self, ctx: build.MinispecPythonParser.MinispecPythonParser.MemberBindsContext):
        raise Exception("Handled in structExpr, should not be visited")

    def visitMemberBind(self, ctx: build.MinispecPythonParser.MinispecPythonParser.MemberBindContext):
        raise Exception("Handled in structExpr, should not be visited")

    def visitBeginEndBlock(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BeginEndBlockContext):
        beginendScope = ctx.scope
        beginendScope.parents = [self.globalsHandler.currentScope] # in case we are in a fleeting if/case statement scope
        self.globalsHandler.enterScope(beginendScope)
        for stmt in ctx.stmt():
            self.visit(stmt)
        self.globalsHandler.exitScope()

    def visitRegWrite(self, ctx: build.MinispecPythonParser.MinispecPythonParser.RegWriteContext):
        '''To assign to a register, we put a wire from the value (rhs) to the register input.'''
        value = self.visit(ctx.rhs)
        # if isMLiteral(value):  # convert value to hardware before assigning to register
        #     value = value.getHardware(self.globalsHandler)  # I don't think we need to convert to hardware yet.
        if ctx.lhs.__class__ != build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext:
            # raise Exception("Not implemented") # this is for vectors of registers
            regName = ctx.lhs.getText()
            self.globalsHandler.currentScope.setPermanent(value, regName + ".input")
        regName = ctx.lhs.getText()
        self.globalsHandler.currentScope.set(value, regName + ".input")

    def visitStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.StmtContext):
        ''' Each variety of statement is handled separately. '''
        return self.visitChildren(ctx)

    def runIfStmt(self, condition: 'Node', ifStmt: 'build.MinispecPythonParser.MinispecPythonParser.StmtContext', elseStmt: 'build.MinispecPythonParser.MinispecPythonParser.StmtContext|None'):
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
        
        self.copyBackIfStmt(originalScope, condition, [ifScope, elseScope])

    def copyBackIfStmt(self, originalScope: 'Scope', condition: 'Node', childScopes: 'list[Scope]'):
        ''' Given if/else scopes, the original scope, and a condition node, copies the variables set in the 
        if and else scopes back into the original scope with muxes controlled by the condition node. '''
        self.globalsHandler.currentScope = originalScope
        varsToBind = set()
        for scope in childScopes:
            for var in scope.temporaryScope.temporaryValues:
                varsToBind.add(var)
        for var in varsToBind:
            values = [ scope.get(self, var) for scope in childScopes ]  # if var doesn't appear in one of these scopes, the lookup will find its original value
            # since the control signal is hardware, we convert the values to hardware as well (if needed)
            for i in range(len(values)):
                if isMLiteral(values[i]):
                    values[i] = values[i].getHardware(self.globalsHandler)
            muxComponent = Mux([ Node('v'+str(i)) for i in range(len(values)) ], Node('c'))
            wires = [ Wire(values[i], muxComponent.inputs[i]) for i in range(len(values)) ]
            for component in [muxComponent, Wire(condition, muxComponent.control)] + wires:
                self.globalsHandler.currentComponent.addChild(component)
            originalScope.set(muxComponent.output, var)

    def visitIfStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.IfStmtContext):
        condition = self.visit(ctx.expression())
        if isMLiteral(condition):
            # we select the appropriate branch
            if condition == BooleanLiteral(True):
                self.visit(ctx.stmt(0))
            else:
                if ctx.stmt(1):
                    self.visit(ctx.stmt(1))
        else:
            self.runIfStmt(condition, ctx.stmt(0), ctx.stmt(1))

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
                n = Function('~', [], [Node()])
                wIn = Wire(exprToMatch, n.inputs[0])
                for component in [n, wIn]:
                    self.globalsHandler.currentComponent.addChild(component)
                condition = n.output
        elif not isMLiteral(expr) and isMLiteral(exprToMatch) and exprToMatch.__class__ == Bool:
            if exprToMatch:
                condition = exprToMatch
            else:
                n = Function('~', [], [Node()])
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
            eqComp = Function('==', [], [Node(), Node()])
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

        self.copyBackIfStmt(originalScope, condition, [ifScope, elseScope])

        self.globalsHandler.currentScope = originalScope

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
        expr = self.visit(ctx.expression())
        allExprLiteral = isMLiteral(expr)
        allExpriLiteral = True
        expri = []  # list of pairs [self.visit(exprCtx), stmtCtx] in order that they should be considered, excluding the default case and skipping repeat literals.
        expriLiterals = [] # list of literals found when visiting each expri
        for caseStmtItem in ctx.caseStmtItem():
            for expression in caseStmtItem.expression():
                currentExpr = self.visit(expression)
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
            
            self.copyBackIfStmt(originalScope, expr, scopes)
            return
        # run the case statement as a sequence of if statements.
        self.doCaseStmtStep(expr, expri, 0, ctx.caseStmtDefaultItem())

    def visitCaseStmtItem(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CaseStmtItemContext):
        raise Exception("Handled in visitCaseStmt--not visited.")

    def visitCaseStmtDefaultItem(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CaseStmtDefaultItemContext):
        raise Exception("Handled in visitCaseStmt--not visited.")

    def visitForStmt(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ForStmtContext):
        iterVarName = ctx.initVar.getText()
        initVal = self.visit(ctx.expression(0))
        assert isMLiteral(initVal), "For loops must be unrolled before synthesis"
        self.globalsHandler.currentScope.set(initVal, iterVarName)
        checkDone = self.visit(ctx.expression(1))
        assert isMLiteral(checkDone) and checkDone.__class__ == BooleanLiteral, "For loops must be unrolled before synthesis"
        while checkDone.value:
            self.visit(ctx.stmt())
            nextIterVal = self.visit(ctx.expression(2))
            assert isMLiteral(nextIterVal), "For loops must be unrolled before synthesis"
            self.globalsHandler.currentScope.set(nextIterVal, iterVarName)
            checkDone = self.visit(ctx.expression(1))
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

from typing import Callable # for annotation function calls
def parseAndSynth(text: 'str', topLevel: 'str', filename: 'str' ='', pullTextFromImport: 'Callable[[int],int]' = lambda x: 1/0) -> 'Component':
    ''' text is the text to parse and synthesize.
    topLevel is the name (including parametrics) of the function/module to synthesize.
    filename is the name of the file that text is from (no .ms).
    pullTextFromImport is a function that takes in the name of a minispec file to parse (no .ms)
    and returns the text of the given file. '''

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
    collectImports(filename, text, tree)

    walker = build.MinispecPythonListener.ParseTreeWalker()
    listener = StaticTypeListener(globalsHandler)

    for filename, text, tree in importsAndText:
        globalsHandler.currentScope = startingFile
        walker.walk(listener, tree)  # walk the listener through the tree

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
    outputDef = synthesizer.visit(ctxOfNote)  # follow the call to the function and get back the functionDef/moduleDef.
    output = synthesizer.visit(outputDef)  # visit the functionDef/moduleDef in the given file and synthesize it. store the result in 'output'

    # for scope in globalsHandler.allScopes:
    #     print(scope)

    output.prune() #remove unused components

    return output


def tokensAndWhitespace(text: 'str') -> 'list[str]':
    ''' Returns a list of all grammar tokens from ANTLR in text, including whitespace tokens. '''
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
