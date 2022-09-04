import inspect
from urllib.parse import parse_qsl

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

    - Structs
    - Module methods with arguments
    - Modules with arguments
    - Case statements
    - Shared modules
    - Other files (imports)
    - BSV imports

Implemented:

    - Function calls
    - Binary operations
    - Parametrics (+ associated variable lookups)
    - Type handling (+ associated python type objects)
    - Literals
    - If/case statements (+ muxes)
    - For loops
    - Modules
    - Indexing/Slicing

Notes for parametrics:
    paramFormals are used when defining functions/modules/types, and may be Integer n or
    5 (or an expression that evaluates to an integer) or 'type' X (as in creating a typedef alias of vector).
    params are used when calling functions/synth modules/invoking custom parameterized types, and may
    only be an integer or the name of a type.

'''

'''
Overall specs:

ANTLR produces a parse tree ("tree" in the code). This parse tree has nodes ("ctx" in the code) corresponding
to different parts of the minispec grammar (packageDef, exprPrimary, returnExpr, etc.).
We will:
1. Run a tree walker through the parse tree to add static elaboration information, eg, 
  collecting all scopes that arise across various files/modules and binding all declared
  functions/modules in the relevant scopes.
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
    def __init__(self, globalsHandler: 'GlobalsHandler', name: 'str', parents: 'list[Scope]'):
        self.globalsHandler = globalsHandler
        self.parents = parents.copy()
        self.name = name
        self.permanentValues = {}
        self.temporaryValues = {}
        
        ''' dictionary of registers, only used in a module, str is the variable name that points
        to the register in the module scope  so that:
            self.registers[someRegisterName] = self.get(self, someRegisterName) '''
        self.registers: 'dict[str, Register]' = {}
        self.nonregisterSubmodules = {}  # same as self.registers but for all other submodules. Used to assign submodule inputs.
        ''' dictionary of inputs with defaults, just like registers except returns the default value ctx '''
        self.inputsWithDefault: 'dict[str, "build.MinispecPythonParser.MinispecPythonParser.ExpressionContext"]' = {}
        self.currentInputsWithDefault: 'dict[str, "build.MinispecPythonParser.MinispecPythonParser.ExpressionContext"]' = {} #temporary version used by submodules with default inputs
        # values to assign to each input. To assign True to input.enable, we set .submoduleInputValues[(input, enable)] = True.
        self.submoduleInputValues: 'dict[tuple[Module|Register, str], Node|MLiteral]' = {}
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
        if len(intValues) != len(storedParams):
            return None
        d = {}  #make sure parameters match
        for i in range(len(intValues)):
            if storedParams[i].__class__ == str:
                d[storedParams[i]] = intValues[i]
            elif visitor.visit(storedParams[i]) != intValues[i]:
                return None
        return d
    def get(self, visitor, varName: 'str', parameters: 'list[int]' = None) -> 'ctxType|Node':
        '''Looks up the given name/parameter combo. Prefers current scope to parent scopes, and
        then prefers temporary values to permanent values. Returns whatever is found,
        probably a ctx object (functionDef) or a node object (variable value).
        Returns an object.
        Returns a tuple (ctx/Node, paramMappings) where paramMappings is a dictionary
        str -> int that shows how the stored parameters were mapped to match parameters to
        the stored parameters.'''
        if parameters == None:
            parameters = []
        visitor.globalsHandler.lastParameterLookup = parameters
        if varName in self.temporaryValues:
            return self.temporaryValues[varName]
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
    def __init__(self, globalsHandler: 'GlobalsHandler', name: 'str', parents: 'list[Scope]'):
        self.globalsHandler = globalsHandler
        self.parents = parents.copy()
        self.name = name
        self.permanentValues = {}
        self.temporaryValues = {}
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
        if varName == 'Reg':
            assert len(parameters) == 1, "A register takes exactly one parameter"
            return BuiltinRegisterCtx(parameters[0])
        if varName == 'True':
            assert len(parameters) == 0, "A boolean literal has no parameters"
            return Bool(True)
        if varName == 'False':
            assert len(parameters) == 0, "A boolean literal has no parameters"
            return Bool(False)
        raise Exception(f"Couldn't find variable {varName} with parameters {parameters}")

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
    def isGlobalsHandler(self):
        ''' Used by assert statements '''
        return True
    

class MinispecStructure:
    def __init__(self, builtinScope: 'BuiltInScope', startingFile: 'Scope'):
        '''will hold all created scopes. used for lookups.'''
        self.allScopes = [builtinScope, startingFile]
        self.currentScope = startingFile
    '''def __setattr__(self, __name: str, __value: Any) -> None: #For debugging lookups.
        if __name == 'lastParameterLookup':
            for j in __value:
                print(j.__class__)
            print(__value.__repr__())
        self.__dict__[__name] = __value'''


class StaticTypeListener(build.MinispecPythonListener.MinispecPythonListener):
    def __init__(self, globalsHandler: 'GlobalsHandler', collectedScopes: 'MinispecStructure') -> None:
        self.globalsHandler = globalsHandler
        self.collectedScopes = collectedScopes

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
        self.collectedScopes.currentScope.setPermanent(ctx, functionName, params)
        functionScope = Scope(self.globalsHandler, functionName, [self.collectedScopes.currentScope])
        ctx.scope = functionScope
        self.collectedScopes.currentScope = functionScope
        self.collectedScopes.allScopes.append(functionScope)

    def exitFunctionDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionDefContext):
        '''We have defined a function, so we step back into the parent scope.'''
        assert len(self.collectedScopes.currentScope.parents) == 1, "function can only have parent scope"
        self.collectedScopes.currentScope = self.collectedScopes.currentScope.parents[0]

    def enterModuleDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ModuleDefContext):
        '''We are defining a module. We need to give this module a corresponding scope.'''
        moduleName = ctx.moduleId().name.getText() # get the name of the module
        if ctx.argFormals():
            raise Exception(f"Modules with arguments not currently supported{newline}{ctx.toStringTree(recog=parser)}{newline}{ctx.argFormals().toStringTree(recog=parser)}")
        params = []
        if ctx.moduleId().paramFormals():
            for param in ctx.moduleId().paramFormals().paramFormal():
                # each parameter is either an integer or a name.
                if param.param():  # our parameter is an actual integer or type name, which will be evaluated immediately before lookups.
                    params.append(param.param())
                elif param.intName:  # param is a variable name. extract the name.
                    params.append(param.intName.getText())
                else:
                    assert False, "parameters with typeValues are not supported yet"
        # log the module's scope
        self.collectedScopes.currentScope.setPermanent(ctx, moduleName, params)
        moduleScope = Scope(self.globalsHandler, moduleName, [self.collectedScopes.currentScope])
        ctx.scope = moduleScope
        self.collectedScopes.currentScope = moduleScope
        self.collectedScopes.allScopes.append(moduleScope)

    def exitModuleDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.ModuleDefContext):
        '''We have defined a module, so we step back into the parent scope.'''
        assert len(self.collectedScopes.currentScope.parents) == 1, "module can only have parent scope"
        self.collectedScopes.currentScope = self.collectedScopes.currentScope.parents[0]

    def enterRuleDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.RuleDefContext):
        '''Rules get a scope'''
        ruleName = ctx.name.getText()
        ruleScope = Scope(self.globalsHandler, ruleName, [self.collectedScopes.currentScope])
        ctx.scope = ruleScope
        self.collectedScopes.currentScope = ruleScope
        self.collectedScopes.allScopes.append(ruleScope)

    def exitRuleDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.RuleDefContext):
        '''We have defined a rule, so we step back into the parent scope.'''
        assert len(self.collectedScopes.currentScope.parents) == 1, "rule can only have parent scope"
        self.collectedScopes.currentScope = self.collectedScopes.currentScope.parents[0]

    def enterMethodDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.MethodDefContext):
        '''Methods get a scope'''
        methodName = ctx.name.getText()
        methodScope = Scope(self.globalsHandler, methodName, [self.collectedScopes.currentScope])
        ctx.scope = methodScope
        self.collectedScopes.currentScope = methodScope
        self.collectedScopes.allScopes.append(methodScope)

    def exitMethodDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.MethodDefContext):
        '''We have defined a method, so we step back into the parent scope.'''
        assert len(self.collectedScopes.currentScope.parents) == 1, "method can only have parent scope"
        self.collectedScopes.currentScope = self.collectedScopes.currentScope.parents[0]

    def enterVarBinding(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarBindingContext):
        '''We have found a named constant. Log it for later evaluation (since it may depend on other named constants, etc.)'''
        for varInit in ctx.varInit():
            if varInit.rhs:
                self.collectedScopes.currentScope.setPermanent(varInit.rhs, varInit.var.getText())

    def enterTypeDefSynonym(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefSynonymContext):
        ''' Log the typedef under the appropriate name. It will be evalauted when it is looked up. '''
        if ctx.typeId().paramFormals():
            raise Exception("Not implemented")
        self.collectedScopes.currentScope.setPermanent(ctx, ctx.typeId().getText())

    def enterTypeDefEnum(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefEnumContext):
        ''' Evaluate the typedef and log the appropriate variables. '''
        enumName = ctx.upperCaseIdentifier().getText()
        enumNames = []
        for element in ctx.typeDefEnumElement():
            enumNames.append(element.tag.getText())
        enumType = Enum(enumName, set(enumNames))
        self.collectedScopes.currentScope.setPermanent(enumType, enumName)
        for name in enumNames:
            self.collectedScopes.currentScope.setPermanent(enumType(name), name)

    def enterTypeDefStruct(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefStructContext):
        ''' Log the typedef under the appropriate name. It will be evalauted when it is looked up. '''
        if ctx.typeId().paramFormals():
            raise Exception("Not implemented")
        ctx.typeDefValue = None  # will point to the type object after being looked up for the first time,
        # then will be returned again on later lookups.
        self.collectedScopes.currentScope.setPermanent(ctx, ctx.typeId().getText())
        

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
visitCaseExpr: 
visitCaseExprItem: 
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

def isMLiteral(value):
    '''Returns whether or not value is an MLiteral'''
    return issubclass(value.__class__, MLiteral)
def isNode(value):
    '''Returns whether or not value is a Node'''
    return value.__class__ == Node
def isNodeOrMLiteral(value):
    '''Returns whether or not value is a literal or a node.'''
    return isMLiteral(value) or isNode(value)

class SynthesizerVisitor(build.MinispecPythonVisitor.MinispecPythonVisitor):
    '''Each method returns a component (module/function/etc.)
    nodes of type exprPrimary return the node corresponding to their value.
    stmt do not return anything; they mutate the current scope and the current hardware.'''

    def visitRegister(self, mtype: 'MType'):
        ''' Visiting the built-in moduleDef of a register. Return the synthesized register. '''
        return Register('Reg#(' + str(mtype) + ')')

    def __init__(self, globalsHandler: 'GlobalsHandler', collectedScopes: 'MinispecStructure') -> None:
        self.globalsHandler = globalsHandler
        self.collectedScopes = collectedScopes
    
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
        typeObject = self.collectedScopes.currentScope.get(self, typeName, params)
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
        if ctx.typeId().paramFormals():
            raise Exception("Not implemented")
        originalType = self.visit(ctx.typeName())
        return Synonym(originalType, ctx.typeId().getText())

    def visitTypeId(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeIdContext):
        raise Exception("Handled directly, should not be visited.")

    def visitTypeDefEnum(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefEnumContext):
        raise Exception("Handled during static elaboration.")

    def visitTypeDefEnumElement(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefEnumElementContext):
        raise Exception("Handled during static elaboration.")

    def visitTypeDefStruct(self, ctx: build.MinispecPythonParser.MinispecPythonParser.TypeDefStructContext):
        if not ctx.typeDefValue:
            if ctx.typeId().paramFormals():
                raise Exception("Not implemented")
            typeName = ctx.typeId().getText()
            fields = {}
            for structMember in ctx.structMember():
                fieldTypeName = self.visit(structMember.typeName())
                fieldName = structMember.lowerCaseIdentifier().getText()
                fields[fieldName] = fieldTypeName
            ctx.typeDefValue = Struct(typeName, fields)
        return ctx.typeDefValue

    def visitStructMember(self, ctx: build.MinispecPythonParser.MinispecPythonParser.StructMemberContext):
        raise Exception("Handled in typeDefStruct, not visited")

    def visitVarBinding(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarBindingContext):
        typeValue = self.visit(ctx.typeName())
        for varInit in ctx.varInit():
            varName = varInit.var.getText()
            if (varInit.rhs):
                value = self.visit(varInit.rhs)
                if value.__class__ == Node:
                    value.setMType(typeValue)
                self.collectedScopes.currentScope.set(value, varName)

    def visitLetBinding(self, ctx: build.MinispecPythonParser.MinispecPythonParser.LetBindingContext):
        '''A let binding declares a variable or a concatenation of variables and optionally assigns
        them to the given expression node ("rhs").'''
        if not ctx.rhs:
            return  #if there is no assignment, we can skip this line
        rhsNode = self.visit(ctx.rhs)  #we expect a node corresponding to the desired value
        if len(ctx.lowerCaseIdentifier()) == 1:
            varName = ctx.lowerCaseIdentifier(0).getText() #the variable we are assigning
            self.collectedScopes.currentScope.set(rhsNode, varName)
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
        # log the current scope
        previousScope = self.collectedScopes.currentScope
        self.collectedScopes.currentScope = moduleScope

        previousTemporaryValues = moduleScope.temporaryValues  # in case any submodules are recursive and change the current temporary values
        moduleScope.clearTemporaryValues() # clear the temporary values
        
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
            oldCurrentInputs = self.collectedScopes.currentScope.currentInputsWithDefault
            self.collectedScopes.currentScope.currentInputsWithDefault = {}
            self.visit(inputDef)
            for inputName in self.collectedScopes.currentScope.currentInputsWithDefault:
                defaultValCtxOrNone = self.collectedScopes.currentScope.currentInputsWithDefault[inputName]
                # copy any inputs into the parent scope, so that any parent module knows about the inputs
                previousScope.currentInputsWithDefault[inputName] = defaultValCtxOrNone
            self.collectedScopes.currentScope.currentInputsWithDefault = oldCurrentInputs
        for submoduleDecl in submoduleDecls:
            self.visit(submoduleDecl)
            # save submodule inputs with default values
            submoduleName = submoduleDecl.name.getText()
            for inputName in self.collectedScopes.currentScope.currentInputsWithDefault:
                defaultExprCtx = self.collectedScopes.currentScope.currentInputsWithDefault[inputName]
                self.collectedScopes.currentScope.inputsWithDefault[submoduleName + "." + inputName] = defaultExprCtx
            self.collectedScopes.currentScope.currentInputsWithDefault = {}
        for methodDef in methodDefs:
            if not methodDef.argFormals(): # only methodDefs with no arguments are synthesized in the module
                self.visit(methodDef)
        # evaluate default inputs
        for submoduleAndInputName in self.collectedScopes.currentScope.inputsWithDefault:
            defaultCtxOrNone = self.collectedScopes.currentScope.inputsWithDefault[submoduleAndInputName]
            if defaultCtxOrNone:
                self.collectedScopes.currentScope.submoduleInputValues[submoduleAndInputName] = self.visit(defaultCtxOrNone)
            else:
                self.collectedScopes.currentScope.submoduleInputValues[submoduleAndInputName] = None

        for ruleDef in ruleDefs:
            self.visit(ruleDef)

        # now that we have synthesized the rules, we need to collect all submodule inputs set across the rules and wire them in.
        # We can't wire in submodule inputs during the rules, since an input with a default input will confuse the first rule (since the input may or may not be set in a later rule).
        # TODO handle inputs
        ''' Handling inputs.
        - moduleScope.nonregisterSubmodules is a dictionary mapping the variable name of a submodule to the
          corresponding component.
        - Each submodule component in moduleScope.nonregisterSubmodules has a dictionary .inputs mapping the name of the
          input to the node corresponding to the input.
        - When each submodule is synthesized, it logs any default values in the dictionary moduleScope.currentInputsWithDefault,
          which maps moduleScope.currentInputsWithDefault[input: str] = defaultExpressionCtx.
        - Specifically, when an input has a default value, it logs the default value into
          submodule.currentInputsWithDefault, and after the input is visited, this value is copied into moduleScope.currentInputsWithDefault
        - Note that since currentInputsWithDefault is stored in the module scope, we have to save its previous value to avoid it being overwritten by recursive parametrics.
        - After each submodule is synthesized, moduleScope.currentInputsWithDefault is copied into moduleScope.inuptsWithDefault,
          which maps moduleScope.inuptsWithDefault[submoduleName.input] = defaultExpressionCtx.
        - The reason for separating currentInputsWithDefault and inputsWithDefault is that when a submodule is being synthesized, it
          does not know what its assigned variable name will be in the original module, and we need to log default input expressions
          under the correct submodule.
        - Before evaluating any rules, we evaluate each default value and log them in moduleScope.submoduleInputValues.
        - For each rule, we must begin by assigning all submodule inputs from moduleScope.submoduleInputValues under the 
          correct name (eg "inner.enble").
        - During each rule, some of these module inputs may be reassigned to new Nodes or MLiterals.
        - At the end of each rule, any input assignments are recorded in moduleScope.submoduleInputValues as the input
          to assign. Since bsc guarantees each input is assigned at most once, this will not override anything (note
          that we are overwriting the originally calculated default values).
        - After all rules have been evaluated, we must for each submodule input in moduleScope.submoduleInputValues, create and
          connect the relevant hardware to the relevant submodule input.
        This strategy will need some adjustment to account for shared modules, whose inputs may be assigned in different rules across different modules,
        but this should not be much more difficult since the only issue is not making any default assignments until all modules which may assign
        inputs have made their assignments (so, default assignments are made in the module in which the shared module is declared).
        
        #TODO: we need to put all submodule inputs in moduleScope.submoduleInputValues.
        # Those that have default values map to that value, while those that do not have default values map to None.
        # All of the None values must be overridden so that every input is assigned.
        # The default/None split can be done for all of currentInputsWithDefault, inputsWithDefault, and submoduleInputValues.
        '''
        for submoduleAndInputName in self.collectedScopes.currentScope.submoduleInputValues:
            value = self.collectedScopes.currentScope.submoduleInputValues[submoduleAndInputName]
            assert value != None, "All submodule inputs must be assigned"
            if isMLiteral(value):
                value = value.getHardware(self.globalsHandler)
            assert isNode(value), "value must be hardware in order to wire in to input node"
            submoduleName, inputName = submoduleAndInputName.split('.')
            submoduleComponent: 'Module' = self.collectedScopes.currentScope.nonregisterSubmodules[submoduleName]
            inputNode = submoduleComponent.inputs[inputName]
            wireIn = Wire(value, inputNode)
            self.globalsHandler.currentComponent.addChild(wireIn)
            
        moduleScope.temporaryValues = previousTemporaryValues  # in case any submodules are recursive and change the current temporary values        
        self.globalsHandler.currentComponent = previousComponent #reset the current component/scope
        self.collectedScopes.currentScope = previousScope

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

        moduleComponent = self.visit(moduleDef)  #synthesize the module
        self.globalsHandler.currentComponent.addChild(moduleComponent)
        submoduleName = ctx.name.getText()
        self.collectedScopes.currentScope.set(moduleComponent, submoduleName)

        if moduleComponent.isRegister():  # log the submodule in the appropriate dictionary for handling register assignments/submodule inputs.
            self.collectedScopes.currentScope.registers[submoduleName] = moduleComponent
        else:
            self.collectedScopes.currentScope.nonregisterSubmodules[submoduleName] = moduleComponent

    def visitInputDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.InputDefContext):
        ''' Add the appropriate input to the module, with hardware to handle the default value.
        Bind the input in the appropriate context. (If the input is named 'in' then we bind in->Node('in').) '''
        inputName = ctx.name.getText()
        self.collectedScopes.currentScope.currentInputsWithDefault[inputName] = ctx.defaultVal
        inputType = self.visit(ctx.typeName())
        inputNode = Node(inputName, inputType)
        self.collectedScopes.currentScope.set(inputNode, inputName)
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
                methodScope.clearTemporaryValues() # clear the temporary values
                for registerName in self.collectedScopes.currentScope.registers:  # bind the registers
                    register = self.collectedScopes.currentScope.registers[registerName]
                    methodScope.set(register.value, registerName)
                previousScope = self.collectedScopes.currentScope
                self.collectedScopes.currentScope = methodScope # enter the method scope
                for stmt in ctx.stmt():  # evaluate the method
                    self.visit(stmt)
                self.collectedScopes.currentScope = previousScope
                self.globalsHandler.outputNode = None  # methods can't occur inside a function, so there is no need to remember any previous output node.
        else:
            raise Exception("Not implemented")

    def visitRuleDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.RuleDefContext):
        # registers keep their original value unless modified
        ruleScope: 'Scope' = ctx.scope
        ruleScope.clearTemporaryValues() # clear the temporary values
        for registerName in self.collectedScopes.currentScope.registers:
            register = self.collectedScopes.currentScope.registers[registerName]
            ruleScope.set(register.value, registerName)
        for inputName in self.collectedScopes.currentScope.submoduleInputValues:  # bind any default inputs
            value = self.collectedScopes.currentScope.submoduleInputValues[inputName]
            # if value != None:  # don't need this since none values should never by referenced
            ruleScope.set(value, inputName)
        previousScope = self.collectedScopes.currentScope
        self.collectedScopes.currentScope = ruleScope # enter the rule scope
        for stmt in ctx.stmt():
            self.visit(stmt)
        self.collectedScopes.currentScope = previousScope
        # wire in the register writes
        for registerName in self.collectedScopes.currentScope.registers:
            register = self.collectedScopes.currentScope.registers[registerName]
            value = ruleScope.get(self, registerName)
            if isMLiteral(value):  # convert value to hardware before assigning to register
                value = value.getHardware(self.globalsHandler)
            setWire = Wire(value, register.input)
            self.globalsHandler.currentComponent.addChild(setWire)
        #find any input assignments
        for inputName in self.collectedScopes.currentScope.submoduleInputValues:
            newValue = ruleScope.get(self, inputName)
            self.collectedScopes.currentScope.submoduleInputValues[inputName] = newValue

    def visitFunctionDef(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionDefContext):
        '''Synthesizes the corresponding function and returns the entire function hardware.
        Gets any parameters from parsedCode.lastParameterLookup and
        finds parameter bindings in bindings = parsedCode.parameterBindings'''
        functionName = ctx.functionId().name.getText()
        params = self.globalsHandler.lastParameterLookup
        if len(params) > 0:  #attach parameters to the function name if present
            functionName += "#(" + ",".join(str(i) for i in params) + ")"
        functionScope = ctx.scope
        previousTemporaryValues = functionScope.temporaryValues  # in case this function is recursive parametric and changes the current temporary values
        functionScope.clearTemporaryValues() # clear the temporary values
        # log the current scope
        previousScope = self.collectedScopes.currentScope
        self.collectedScopes.currentScope = functionScope
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
        functionScope.temporaryValues = previousTemporaryValues  # in case this function is recursive and changed the current temporary values        
        self.globalsHandler.currentComponent = previousComponent #reset the current component/scope
        self.collectedScopes.currentScope = previousScope
        self.globalsHandler.outputNode = previousOutputNode
        return funcComponent

    def visitFunctionId(self, ctx: build.MinispecPythonParser.MinispecPythonParser.FunctionIdContext):
        ''' Handled from functionDef '''
        raise Exception("Handled from functionDef, should never be visited")

    def visitVarAssign(self, ctx: build.MinispecPythonParser.MinispecPythonParser.VarAssignContext):
        ''' Assign the given variable to the given expression. No returns, mutates existing hardware. '''
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
            self.collectedScopes.currentScope.set(value, varName)
            return
        # Otherwise, we convert to hardware.
        if isMLiteral(value):
            value = value.getHardware(self.globalsHandler)
        if lvalue.__class__ == build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext:
            # assign the variable, no slicing/subfields needed
            varName = lvalue.getText()
            self.collectedScopes.currentScope.set(value, varName)
            return
        # insert the field/slice/index
        # first, detect if we are setting a module input (vectors of modules are not yet implemented)
        if lvalue.__class__ == build.MinispecPythonParser.MinispecPythonParser.MemberLvalueContext:
            if lvalue.lvalue().__class__ == build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext:
                moduleName = lvalue.lvalue().getText()  #assuming we have a module
                settingOverall = self.collectedScopes.currentScope.get(self, moduleName)
                if settingOverall.__class__ == Module:  # we are, in fact, setting a module input
                    inputName = lvalue.lowerCaseIdentifier().getText()
                    # inputNode = settingOverall.inputs[inputName]
                    # inputWire = Wire(value, inputNode)
                    # self.globalsHandler.currentComponent.addChild(inputWire)
                    self.collectedScopes.currentScope.set(value, moduleName + "." + inputName)
                    return
        text, nodes, varName = self.visit(lvalue)
        insertComponent = Function(text, [], [Node() for node in nodes] + [Node()])
        for i in range(len(nodes)):
            wire = Wire(nodes[i], insertComponent.inputs[i])
            self.globalsHandler.currentComponent.addChild(wire)
        newWire = Wire(value, insertComponent.inputs[len(nodes)])
        self.globalsHandler.currentComponent.addChild(insertComponent)
        self.globalsHandler.currentComponent.addChild(newWire)
        self.collectedScopes.currentScope.set(insertComponent.output, varName)


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
        valueFound = self.collectedScopes.currentScope.get(self, ctx.getText())
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
        raise Exception("Not implemented")

    def visitCaseExprItem(self, ctx: build.MinispecPythonParser.MinispecPythonParser.CaseExprItemContext):
        raise Exception("Not implemented")

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
            return {'**': MLiteral.pow,
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
                    '||': MLiteral.booleanor}[op](left, right)
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
            #TODO fill out dict
            return {'!': MLiteral.booleaninv,
                    '~': MLiteral.inv,
                    '&': MLiteral.redand,
                    '~&': MLiteral.notredand,
                    '|': MLiteral.redor,
                    '~|': MLiteral.notredor,
                    '^': MLiteral.redxor,
                    '^~': MLiteral.notredxor,
                    '~^': MLiteral.notredxor,
                    '+': MLiteral.unaryadd,
                    '-': MLiteral.neg}[op](value)
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
                assert value.__class__ == IntegerLiteral, f"Parameters must be an integer, not {value} which is {value.__class__}"
                params.append(value)
        value = self.collectedScopes.currentScope.get(self, ctx.var.getText(), params)
        self.globalsHandler.lastParameterLookup = params
        return value

    def visitBitConcat(self, ctx: build.MinispecPythonParser.MinispecPythonParser.BitConcatContext):
        ''' Bit concatenation is just a function. Returns the function output. '''
        toConcat = []
        for expr in ctx.expression():
            toConcat.append(self.visit(expr))
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
        '''We have an integer literal, so we parse it and return it.'''
        return IntegerLiteral(int(ctx.getText()))

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
        toSliceFrom = self.visit(ctx.array)
        assert isNode(toSliceFrom), "Expected a node"
        text = "["
        inNode = Node()
        inputs = [inNode]
        inWire = Wire(toSliceFrom, inNode)
        inWires = [inWire]
        msb = self.visit(ctx.msb) #most significant bit
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
            lsb = self.visit(ctx.lsb) #least significant bit
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
                assert value.__class__ == IntegerLiteral, f"Parameters must be an integer, not {value} which is {value.__class__}"
                params.append(value)
        functionDef = self.collectedScopes.currentScope.get(self, functionToCall, params)
        self.globalsHandler.lastParameterLookup = params
        funcComponent = self.visit(functionDef)  #synthesize the function internals
        # hook up the funcComponent to the arguments passed in.
        for i in range(len(ctx.expression())):
            expr = ctx.expression()[i]
            exprNode = self.visit(expr) # visit the expression and get the corresponding node
            if isMLiteral(exprNode):
                exprNode = exprNode.getHardware(self.globalsHandler)
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
        for stmt in ctx.stmt():
            self.visit(stmt)

    def visitRegWrite(self, ctx: build.MinispecPythonParser.MinispecPythonParser.RegWriteContext):
        '''To assign to a register, we put a wire from the value (rhs) to the register input.'''
        value = self.visit(ctx.rhs)
        # if isMLiteral(value):  # convert value to hardware before assigning to register
        #     value = value.getHardware(self.globalsHandler)  # I don't think we need to convert to hardware yet.
        if ctx.lhs.__class__ != build.MinispecPythonParser.MinispecPythonParser.SimpleLvalueContext:
            raise Exception("Not implemented")
        regName = ctx.lhs.getText()
        self.collectedScopes.currentScope.set(value, regName)

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

        ifScope = Scope(self.globalsHandler, "ifScope", [self.collectedScopes.currentScope])
        elseScope = Scope(self.globalsHandler, "elseScope", [self.collectedScopes.currentScope])
        self.collectedScopes.allScopes.append(ifScope)
        self.collectedScopes.allScopes.append(elseScope)
        originalScope = self.collectedScopes.currentScope

        self.collectedScopes.currentScope = ifScope
        self.visit(ifStmt)
        if elseStmt:
            self.collectedScopes.currentScope = elseScope
            self.visit(elseStmt)
        
        self.copyBackIfStmt(originalScope, condition, [ifScope, elseScope])

    def copyBackIfStmt(self, originalScope: 'Scope', condition: 'Node', childScopes: 'list[Scope]'):
        ''' Given if/else scopes, the original scope, and a condition node, copies the variables set in the 
        if and else scopes back into the original scope with muxes controlled by the condition node. '''
        self.collectedScopes.currentScope = originalScope
        varsToBind = set()
        for scope in childScopes:
            for var in scope.temporaryValues:
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
        ifScope = Scope(self.globalsHandler, "ifScope", [self.collectedScopes.currentScope])
        elseScope = Scope(self.globalsHandler, "elseScope", [self.collectedScopes.currentScope])
        self.collectedScopes.allScopes.append(ifScope)
        self.collectedScopes.allScopes.append(elseScope)
        originalScope = self.collectedScopes.currentScope

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

        self.collectedScopes.currentScope = ifScope
        self.visit(ifStmt)

        self.collectedScopes.currentScope = elseScope
        if index + 1 < len(expri):
            self.doCaseStmtStep(expr, expri, index+1, defaultItem)
        elif defaultItem:
            self.visit(defaultItem.stmt())

        self.copyBackIfStmt(originalScope, condition, [ifScope, elseScope])

        self.collectedScopes.currentScope = originalScope

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
            # since we have already removed duplicate literals, exactly (technically at most, but "do nothing" may
            # be considered to be a statement if not all statements are covered) one expri statement will run.
            # we run each one in a separate scope and collect the results afterward using multi-width muxes.
            if isMLiteral(expr):
                expr = expr.getHardware(self.globalsHandler)
            hasDefault = ctx.caseStmtDefaultItem() != None
            scopes = []
            for i in range(len(expri) + (1 if hasDefault else 0)):
                childScope = Scope(self.globalsHandler, "childScope"+str(i), [self.collectedScopes.currentScope])
                self.collectedScopes.allScopes.append(childScope)
                scopes.append(childScope)
            originalScope = self.collectedScopes.currentScope

            for i in range(len(expri)):
                scope = scopes[i]
                exprToMatch, exprStmt = expri[i]
                self.collectedScopes.currentScope = scope
                self.visit(exprStmt)
            if hasDefault:  # run the default scope in the last scope
                scope = scopes[-1]
                self.collectedScopes.currentScope = scope
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
        self.collectedScopes.currentScope.set(initVal, iterVarName)
        checkDone = self.visit(ctx.expression(1))
        assert isMLiteral(checkDone) and checkDone.__class__ == BooleanLiteral, "For loops must be unrolled before synthesis"
        while checkDone.value:
            self.visit(ctx.stmt())
            nextIterVal = self.visit(ctx.expression(2))
            assert isMLiteral(nextIterVal), "For loops must be unrolled before synthesis"
            self.collectedScopes.currentScope.set(nextIterVal, iterVarName)
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

def parseAndSynth(text, topLevel) -> 'Component':

    tree = getParseTree(text)

    globalsHandler = GlobalsHandler()

    builtinScope = BuiltInScope(globalsHandler, "built-ins", [])
    startingFile = Scope(globalsHandler, "startingFile", [builtinScope])

    collectedScopes = MinispecStructure(builtinScope, startingFile) #collects scopes

    walker = build.MinispecPythonListener.ParseTreeWalker()
    listener = StaticTypeListener(globalsHandler, collectedScopes)
    walker.walk(listener, tree)  # walk the listener through the tree

    # for scope in collectedScopes.allScopes:
    #     print(scope)

    synthesizer = SynthesizerVisitor(globalsHandler, collectedScopes)

    topLevel = f'''
function Bool _();
    return {topLevel};
endfunction
'''

    topLevelParseTree = getParseTree(topLevel)
    ctxOfNote = topLevelParseTree.packageStmt(0).functionDef().stmt(0).exprPrimary().expression().binopExpr().unopExpr().exprPrimary()
    outputDef = synthesizer.visit(ctxOfNote)  # follow the call to the function and get back the functionDef/moduleDef.
    output = synthesizer.visit(outputDef)  # visit the functionDef/moduleDef in the given file and synthesize it. store the result in 'output'

    # for scope in collectedScopes.allScopes:
    #     print(scope)

    output.prune() #remove unused components

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
