
import hardware
import build
import math # for math.inf in .numLiterals()

# A minispec type is a python classes; instances thereof represent literal values.

''' Documentation for minispec types.

MType: metaclass.
    - Handles coversion to string of minispec types: a minispec type class may have a class
      variable _name, which is returned by __str__ on a type class. __repr__ is not overridden.
    - Every minispec type maintains a class variable _constructor, which is either None or the
      factory function which produced the type. This is used to determine equality of type classes.
    - Also handles equality of minispec types: a parameterized minispec type class must have a
      class method sameType, which is called by __eq__ on a type class. This is used so that
      parameterized type classes returned by factory functions may be considered equal.
      Minispec types without a factory function are considered __eq__ if and only if they are identical.

MLiteral: base class. Has metaclass MType. All minispec types inherit from MLiteral.

Any: used for types which are not known, such as return types of bluespec builtins.

Parameterized types are created by factory functions. Equality of parameterized types is
handled by their sameType(self, other) method, which is called by the MType metaclass.
Parameterized types must override the _constructor class variable to point to their
factory function.

Typedef synonyms. Every minispec class maintains an "untypedef" class method which returns
    the original version of the class. So, given the minispec code
        typedef Word Bit#(32)
    then Word.untypedef() will return the Bit#(32) type class.

'''


'''
A list of minispec literal operations:

Binary operators:
'**','*', '/', '%', '+', '-', '<<', '>>', '<', '<=', '>', '>=', '==', '!=', '&', '^', '^~', '~^', '|', '&&', '||'

Unary operators:
'!', '~', '&', '~&', '|', '~|', '^', '^~', '~^', '+', '-'
Names for methods in code:
'!' is booleaninv.
'~' is inv.
'&' is redand.
'~&' is notredand.
'|' is redor.
'~|' is notredor.
'^' is redxor.
'^~', '~^' is notredxor.  #TODO see http://csg.csail.mit.edu/6.S078/6_S078_2012_www/resources/reference-guide.pdf page 157 for actual names, documentation
'+' is unaryadd.
'-' is neg.

Note: only boolean unary operations return booleans. Reduction operators return Bit#(1)'s.
'''

arithmetic_binary = set(['**','*', '/', '%', '+', '-', '<<', '>>'])
relational_binary = set(['<', '>', '<=', '>='])
equality_binary = set(['==', '!='])
logical_binary = set(['&', '^', '^~', '~^', '|'])
boolean_binary = set(['&&', '||'])

def numericalBinaryOperation(left: 'MLiteral', right: 'MLiteral', op: 'str') -> 'MLiteral':
    assert left.__class__ == Integer or left.isBitLiteral(), f"Expected Integer or Bit, not {left.__class__}"
    assert right.__class__ == Integer or right.isBitLiteral(), f"Expected Integer or Bit, not {right.__class__}"
    
    leftVal, rightVal = left.value, right.value
    assert leftVal.__class__ == int, f"Expected int, not {leftVal.__class__}"
    assert rightVal.__class__ == int, f"Expected int, not {leftVal.__class__}"
    if left.isBitLiteral() and right.isBitLiteral():
        assert left.n == right.n, f"Bit literals must have same width to operate, found widths {left.n} and {right.n}"
    if left.isBitLiteral():
        n = left.n
    if right.isBitLiteral():
        n = right.n
    value = None
    if op == '**':
        value = leftVal ** rightVal
    elif op == '*':
        value = leftVal * rightVal
    elif op == '/':
        value = leftVal // rightVal
    elif op == '%':
        value = leftVal % rightVal
    elif op == '+':
        value = leftVal + rightVal
    elif op == '-':
        value = leftVal - rightVal
    elif op == '<<':
        value = leftVal << rightVal
    elif op == '>>':
        value = leftVal >> rightVal
    elif op == '<':
        return Bool(leftVal < rightVal)
    elif op == '>':
        return Bool(leftVal > rightVal)
    elif op == '<=':
        return Bool(leftVal <= rightVal)
    elif op == '>=':
        return Bool(leftVal >= rightVal)
    elif op == '==':
        return Bool(leftVal == rightVal)
    elif op == '!=':
        return Bool(leftVal != rightVal)
    elif op == '&':
        raise Exception("Not implemented")
    elif op == '^':
        raise Exception("Not implemented")
    elif op == '^~' or op == '~^':
        raise Exception("Not implemented")
    elif op == '|':
        raise Exception("Not implemented")
    else:
        raise Exception(f"Unrecognized binary operation {op}")
    
    if left.isBitLiteral() or right.isBitLiteral():
        return Bit(n)(value % (2**n.value))
    return Integer(value)

def equalityBinaryOperation(left: 'MLiteral', right: 'MLiteral', op: 'str') -> 'Bool':
    if (left.__class__ == Integer or left.isBitLiteral()) and (right.__class__ == Integer or right.isBitLiteral()):
        # perform type coercions for integer/bit values
        return numericalBinaryOperation(left, right, op)
    if op == '==':
        assert left.__class__ == right.__class__, f"Can only compare values of the same type, found {left.__class__} and {right.__class__}"
        return left.eq(right)
    if op == '!=':
        return Bool(not equalityBinaryOperation(left, right, '==').value)
    raise Exception(f"Unrecognized binary operation {op}")

def booleanBinaryOperation(left: 'Bool', right: 'Bool', op: 'str') -> 'Bool':
    assert left.__class__ == Bool, f"Expected Bool for binary operation {op}, not {left.__class__}"
    assert right.__class__ == Bool, f"Expected Bool for binary operation {op}, not {right.__class__}"
    if op == '&&':
        return BooleanLiteral(left.value and right.value)
    if op == '||':
        return BooleanLiteral(left.value or right.value)
    raise Exception(f"Unrecognized binary operation {op}")

def binaryOperation(left: 'MLiteral', right: 'MLiteral', op: 'str') -> 'MLiteral':
    ''' Performs the specified binary operation on two literal values.
    For typechecking specs, see, page ~170, "Type Classes for Bit" etc.
        http://csg.csail.mit.edu/6.375/6_375_2019_www/resources/bsv-reference-guide.pdf '''
    if left.__class__ == DontCareLiteral or right.__class__ == DontCareLiteral:
        raise Exception("Arithmetic with don't care literals is not implemented due to entanglement")
    if op in boolean_binary:
        return booleanBinaryOperation(left, right, op)
    if op in arithmetic_binary or op in relational_binary or op in logical_binary:
        return numericalBinaryOperation(left, right, op)
    if op in equality_binary:
        return equalityBinaryOperation(left, right, op)
    raise Exception(f"Unrecognized binary operation {op}")

def unaryOperation(value: 'MLiteral', op: 'str') -> 'MLiteral':
    if op == '!':
        return value.booleaninv()
    if op == '~':
        return value.inv()
    if op == '&':
        return value.redand(),
    if op == '~&':
        return value.redand().inv(),
    if op == '|':
        return value.redor(),
    if op == '~|':
        return value.redor().inv(),
    if op == '^':
        return value.redxor(),
    if op == '^~':
        return value.redxor().inv(),
    if op == '~^':
        return value.redxor().inv(),
    if op == '+':
        return value.unaryadd(),
    if op == '-':
        return value.neg()

def binaryOperationConstantFold(left: 'MLiteral', right: 'MLiteral', op: 'str') -> 'MLiteral':
    ''' Returns the MLiteral corresponding to the operation `left` `op` `right`. '''
    assert isMLiteral(left)
    assert isMLiteral(right)
    result = binaryOperation(left, right, op)
    result.addSourceTokens(left.getSourceTokens())
    result.addSourceTokens(right.getSourceTokens())
    return result

def unaryOperationConstantFold(value: 'MLiteral', op: 'str') -> 'MLiteral':
    ''' Returns the MLiteral corresponding to the operation `op` `value`. '''
    assert isMLiteral(value)
    result = unaryOperation(value, op)
    result.addSourceTokens(value.getSourceTokens())
    return result

class MType(type):
    ''' The type of a minispec type. Instances are minispec types. '''
    def __str__(self):
        ''' This method is invoked by str(Integer), etc. Used for nice printing of type classes.
        Returns self._name if _name is defined as a class variable, otherwise returns what
        __str__ would ordinarily return. '''
        try:
            return self._name
        except:
            return super.__str__(self)

    def __eq__(self, other):
        ''' Handles equality of minispec types. Returns true if self and other are the same minispec type.
        Typedefs of the same type compare to true. '''
        if other.__class__ != MType:
            return False
        self = self.untypedef()
        other = other.untypedef()
        if self._constructor == None or other._constructor == None: #these are not created in a factory, so they are the same if and only if they are identical
            return super.__eq__(self, other)
        if self._constructor != other._constructor:  # look at the factory function
            return False
        return self.sameType(other) # remove typedef synonyms before comparing

def isMLiteral(value):
    '''Returns whether or not value is an MLiteral'''
    return issubclass(value.__class__, MLiteral)

class MLiteral(metaclass=MType):
    ''' A minispec type. Instances are minispec literals. '''
    _constructor = None
    __slots__ = ()
    def __init__(self):
        raise Exception("Not implemented")
    def __eq__(self, other: 'MLiteral') -> bool:
        ''' Minispec literals have two types of equality, eq and __eq__.
        Two literals compare equally under eq if they would compare equal in minispec, while
        two literals compare equally under __eq__ if they are the same literal. Also, __eq__
        returns a python boolean, while eq returns a minispec literal.
        For example, 1'b1.eq(2'b1) is BooleanLiteral(True), but 1'b1.__eq__(2'b1) is False.
        Furthermore, eq may return a DontCareLiteral if either of the operands is a DontCareLiteral. '''
        raise Exception(f"Not implemented on class {repr(self.__class__)}")
    @classmethod
    def untypedef(cls):  #TODO consider renaming "untypedef" to just "class" or "getClass" ...
        ''' Return the original untypedef-ed type.
        If we run typedef Bit#(32) Word, then Word.untypedef() will give back Bit#(32). '''
        return cls
    @classmethod
    def sameType(self, other):
        ''' Returns true if self and other are the same minispec type. Assumes self and other were created in the same type factory. '''
        raise Exception(f"Not implemented, class {repr(self.__class__)} was not created in a type factory.")
    def getHardware(self, globalsHandler, sourceTokens: 'list[list[tuple[str, int]]]') -> 'hardware.Node':
        assert globalsHandler.isGlobalsHandler(), "Quick type check"
        constantFunc = hardware.Constant(self)
        for tokens in sourceTokens:
            constantFunc.addSourceTokens(tokens)
        globalsHandler.currentComponent.addChild(constantFunc)
        return constantFunc.output
    def copy(self) -> 'MLiteral':
        ''' Returns a copy of self. Used for handling source support of constant values. '''
        print(f"Cannot copy literals of type {self.__class__}")
        raise Exception("Not implemented")
    def __bool__(self):
        raise Exception("Minispec literal values cannot be converted implicitly to python bool values since a DontCareLiteral could be present.")
    def isBitLiteral(self):
        ''' used for type checking '''
        return False
    def numLiterals(self) -> 'int|float':
        ''' Returns the number of possible distinct literals of this type (or math.inf), where
        distinct is defined by minispec's "==" operator.
        Used in case statements to determine when all cases are covered. '''
        raise Exception("Not Implemented")
    def eq(self, other: 'MLiteral') -> 'BooleanLiteral|DontCareLiteral':
        ''' Returns Bool(True) if self and other represent the same minispec value.
        Returns DontCareLiteral() if either self or other is a DontCareLiteral.
        Requires self and other to have the same class. '''
        raise Exception(f"Not implemented on class {repr(self.__class__)}")
    '''unary operations. notredand is in terms of redand and inv.
    notredor is in terms of redor and inv. notredxor is in terms of redxor and inv.'''
    def booleaninv(self) -> 'MLiteral':
        raise Exception(f"Not implemented on class {repr(self.__class__)}")
    def inv(self) -> 'MLiteral':
        raise Exception(f"Not implemented on class {repr(self.__class__)}")
    def redand(self) -> 'MLiteral':
        raise Exception(f"Not implemented on class {repr(self.__class__)}")
    def redor(self) -> 'MLiteral':
        raise Exception(f"Not implemented on class {repr(self.__class__)}")
    def redxor(self) -> 'MLiteral':
        raise Exception(f"Not implemented on class {repr(self.__class__)}")
    def unaryadd(self) -> 'MLiteral':
        raise Exception(f"Not implemented on class {repr(self.__class__)}")
    def neg(self) -> 'MLiteral':
        raise Exception(f"Not implemented on class {repr(self.__class__)}")

def Synonym(mtype: 'MType', newName: 'str'):
    ''' Returns a class which is a synonym of the given class, with the appropriate name.
    Used for typedef synonyms. '''
    class TypeDef(mtype):
        _name = newName
        _constructor = Synonym
        @classmethod
        def untypedef(cls):
            return mtype.untypedef()
        @classmethod
        def sameType(self, other):
            raise Exception("Typedef synonyms should be extracted before calling this method.")
    return TypeDef

def Enum(name: 'str', values: 'set[str]'):
    ''' Returns a class which represents an enum type. '''
    class EnumType(MLiteral):
        ''' value is the tag of the enum instance to create. Must be one of the types in the enum.
        The only operations which are defined for enum literals are eq/neq #TODO check this '''
        _name = name
        _constructor = Enum
        _values = values
        def __init__(self, value: 'str'):
            ''' Create an enum literal '''
            assert value in values, f"Enum type may only take on the specified values {values}, not the given value {value}"
            self.value = value
        def __eq__(self, other):
            if self.__class__ != other.__class__:
                return False
            return self.value == other.value
        def copy(self):
            c = EnumType(self.value)
            for tokenArray in self.getSourceTokensNotFlat():
                c.addSourceTokens(tokenArray)
            return c
        def numLiterals(self) -> 'int|float':
            return len(values)
        @classmethod
        def sameType(self, other):
            return self._values == other._values
        def eq(self, other):
            assert self.__class__ == other.__class__, f"Can only compare values of the same type, found {self.__class__} and {other.__class__}"
            return Bool(self.value == other.value)
        def __str__(self):
            return self.value
    return EnumType

def Struct(name: 'str', fields: 'dict[str, MType]'):
    ''' Returns a class which represents a struct type.
    fields is a dict[str:MType] mapping a field name to the type the field should have. '''
    class StructType(MLiteral):
        ''' The only operations which are defined for struct literals are eq/neq #TODO check this '''
        _name = name
        _constructor = Struct
        _fields = fields
        def __init__(self, fieldBinds: 'dict[str, MLiteral]'):
            assert set(fieldBinds) == set(fields), f"Must specify fields {set(fields)} but instead specified fields {set(fieldBinds)}"
            for field in fieldBinds:
                pass #TODO modify this to allow implicit conversion Integer -> Bit#(n).
                #assert fieldBinds[field].__class__.untypedef() == fields[field].untypedef(), f"Received type {fieldBinds[field].__class__} but expected type {fields[field]}"
            self.fieldBinds = fieldBinds.copy()
        def copy(self):
            c = StructType(self.fieldBinds.copy())
            for tokenArray in self.getSourceTokensNotFlat():
                c.addSourceTokens(tokenArray)
            return c
        def numLiterals(self) -> 'int|float':
            fieldTypeList = [ fields[field] for field in fields ]
            return math.prod([ fieldType.numLiteral() for fieldType in fieldTypeList ])
        @classmethod
        def sameType(self, other):
            if set(self._fields) != set(other._fields):
                return False
            for field in self._fields:
                if self._fields[field] != other._fields[field]:
                    return False
            return True
        def __str__(self):
            return name + "{" + ",".join([str(field) + ":" + str(self.fieldBinds[field]) for field in self.fieldBinds]) + "}"
        def __eq__(self, other):
            if self.__class__ != other.__class__:
                return False
            if set(self.fieldBinds) != set(other.fieldBinds):
                return False
            return all( self.fieldBinds[field] == other.fieldBinds[field] for field in self.fieldBinds )
        def eq(self, other):
            assert self.__class__ == other.__class__, f"Can only compare values of the same type, found {self.__class__} and {other.__class__}"
            for field in self.fieldBinds:
                if self.fieldBinds[field].eq(other.fieldBinds[field]) == Bool(False):
                    return Bool(False)
            return Bool(True)
        def neq(self, other):
            return self.eq(other).booleaninv()
    return StructType

class Any(MLiteral):
    '''An unknown type'''
    _name = "Any"
    def __str__(self):
        return "Any"

class Integer(MLiteral):
    '''An integer type. Has value value.'''
    __slots__ = 'value'
    _name = "Integer"
    def __init__(self, value):
        ''' Create an integer literal '''
        assert value.__class__ == int, f"Expected int, not {value} which is {value.__class__}"
        self.value = value
    def copy(self):
        c = Integer(self.value)
        for tokenArray in self.getSourceTokensNotFlat():
            c.addSourceTokens(tokenArray)
        return c
    def numLiterals(self) -> 'int|float':
        return math.inf
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
    def toInt(self) -> int:
        '''Returns the python integer represented by self'''
        return self.value
    def eq(self, other):
        assert self.__class__ == other.__class__, f"Can only compare values of the same type, found {self.__class__} and {other.__class__}"
        return BooleanLiteral(self.value == other.value)
    '''unary operations'''
    def booleaninv(self):
        raise Exception("Not implemented")
    def inv(self):
        return IntegerLiteral(-self.value)
    def redand(self):
        raise Exception("Not implemented")
    def redor(self):
        raise Exception("Not implemented")
    def redxor(self):
        raise Exception("Not implemented")
    def unaryadd(self):
        return self
    def neg(self):
        return IntegerLiteral(-self.value)
    def slice(self, msb, lsb=None):
        return Bit(IntegerLiteral(1+self.value.bit_length()))(self.value).slice(msb, lsb)

IntegerLiteral = Integer  #useful alias

def Bit(n: 'IntegerLiteral'):
    ''' Returns a type corresponding to a bitstring Bit#(n) of length n. '''
    assert n.__class__ == IntegerLiteral, f"Bit takes integer literals, not {n} which is {n.__class__}"
    class BitLiteral(MLiteral):
        ''' self.n: 'int' is the number of bits. self.value: 'int' is an integer 0 <= value < 2**n. '''
        _name = f"Bit#({n})"
        _constructor = Bit
        _n = n
        def __init__(self, value: 'int'):
            ''' Create a Bit#(n) literal.
            value is an integer which will be assigned (mod 2**n) to self.value.
            Value may be any integer even though bsc requires Bit#(n) literals
            to be in the range -2**(n-1), ..., (2**n)-1. '''
            self.n = n
            assert value.__class__ == int, f"Expected int, not {value} which is {value.__class__}"
            self.value = value % (2**n.value)
        def copy(self):
            c = BitLiteral(self.value)
            for tokenArray in self.getSourceTokensNotFlat():
                c.addSourceTokens(tokenArray)
            return c
        def isBitLiteral(self):
            return True
        def numLiterals(self) -> 'int|float':
            return 2**n.value
        @classmethod
        def sameType(self, other):
            return self._n == other._n
        def __repr__(self):
            return "BitLiteral(" + str(self.n) + "," + str(self.value) + ")"
        def __str__(self):
            output = ""
            val = self.value
            for i in range(self.n.value):
                output = str(val % 2) + output
                val //= 2
            return str(self.n) + "'b" + output
        def __eq__(self, other):
            if self.__class__ != other.__class__:
                return False
            return self.value == other.value
        def fromIntegerLiteral(self, i: 'IntegerLiteral'):
            assert -(2**(self.n-1)) <= i.toInt() < 2**self.n, "Bluespec requires Bit#(n) literals to be in range -2**(n-1),...,2**n-1."
            return Bit(self.n)(i.toInt())
        def eq(self, other):
            assert self.__class__ == other.__class__, f"Can only compare values of the same type, found {self.__class__} and {other.__class__}"
            return BooleanLiteral(self.value == other.value)
        '''unary operations'''
        def booleaninv(self):
            raise Exception("Not implemented")
        def inv(self):
            return Bit(self.n)(~self.value)
        def redand(self):
            raise Exception("Not implemented")
        def redor(self):
            raise Exception("Not implemented")
        def redxor(self):
            raise Exception("Not implemented")
        def unaryadd(self):
            raise Exception("Not implemented")
        def neg(self):
            return Bit(self.n)(-self.value)
        ''' other operations '''
        def slice(self, msb, lsb=None):
            if lsb:
                raise Exception("Not implemented")
            else:
                return Bit(IntegerLiteral(1))((self.value//(2**msb.value)) % 2)
    return BitLiteral
BitLiteral = Bit #useful synonym

class Bool(MLiteral):
    '''The boolean type'''
    _name = "Bool"
    def __init__(self, value: 'bool'):
        assert value.__class__ == bool, "Boolean literals must have boolean value"
        self.value = value
    def copy(self):
        c = Bool(self.value)
        for tokenArray in self.getSourceTokensNotFlat():
            c.addSourceTokens(tokenArray)
        return c
    def numLiterals(self) -> 'int|float':
        return 2
    def __repr__(self):
        return "BooleanLiteral(" + str(self.value) + ")"
    def __str__(self):
        return str(self.value)
    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return self.value == other.value
    def __bool__(self):
        # raise Exception("Minispec Boolean values cannot be converted implicitly to python bool values since any occurrence of a minispec Boolean value could contain a DontCareLiteral instead")
        return self.value
    def eq(self, other):
        assert self.__class__ == other.__class__, f"Can only compare values of the same type, found {self.__class__} and {other.__class__}"
        return self == other
    '''Unary operations'''
    def booleaninv(self):
        return BooleanLiteral(not self.value)
    def inv(self):
        raise Exception("Not implemented")
    def redand(self):
        raise Exception("Not implemented")
    def redor(self):
        raise Exception("Not implemented")
    def redxor(self):
        raise Exception("Not implemented")
    def unaryadd(self):
        raise Exception("Not implemented")
    def neg(self):
        raise Exception("Not implemented")
BooleanLiteral = Bool  #useful alias
        
def Vector(k: 'int', typeValue: 'MType'):
    class VectorType(MLiteral):
        '''The Vector(k, tt) type'''
        _name = f"Vector#({k},{typeValue})"
        _constructor = Vector
        _k = k
        _typeValue = typeValue
        def __init__(self):
            self.k = k
            self.typeValue = typeValue
        def numLiterals(self) -> 'int|float':
            return typeValue.numLiterals() ** k
        @classmethod
        def sameType(self, other):
            return self._k == other._k and self._typeValue == other._typeValue
        def __str__(self):
            return "Vector#(" + str(self.k) + ", " + str(self.typeValue) + ")"
        @classmethod
        def accept(cls, visitor):  #note that accept is called on Vector the class, not an instance of vector.
            ''' If the vector is being visited as a type, redirect it to synthesizing a vector. '''
            return visitor.visitVectorSubmodule(cls)
    VectorType._moduleCtx = BuiltinVectorCtx(typeValue)  # since this is also a ModuleType object
    VectorType._params = [k, typeValue]
    # TODO refactor the vector type into a separate type object and ctx parse node object
    return VectorType

class BuiltinVectorCtx:
    def __init__(self, vectorType: 'MType'):
        self.vectorType = vectorType
    def accept(self, visitor):
        return visitor.visitVectorSubmodule(self.vectorType)

# TODO should ModuleType only be a class, no wrapper needed?
def ModuleType(moduleCtx, params: 'list[MLiteral|MType]'):
    ''' Returns the type corresponding to the given module context (parse node) with the
    given parameters (params is a list of module parameters). '''
    if moduleCtx.__class__ == build.MinispecPythonParser.MinispecPythonParser.ModuleDefContext:
        if moduleCtx.moduleId().paramFormals():
            assert len(params) == len(moduleCtx.moduleId().paramFormals().paramFormal()), "Module must have the correct number of parameters"
        else:
            assert len(params) == 0, "Module with no parameters must have no parameters"
    # elif moduleCtx.__class__ == synth.BuiltinRegisterCtx:
    #TODO work out importing synth
    #     assert len(params) == 1, "Registers take one parameter"
    if moduleCtx.__class__ == build.MinispecPythonParser.MinispecPythonParser.ModuleDefContext:
        name = f"{moduleCtx.moduleId().name.getText()}" if len(params) == 0 else f"{moduleCtx.moduleId().name.getText()}#({','.join([str(param) for param in params])})"
    else:
        name = f"Register#({str(params[0])})"
    class ModuleType(MLiteral):
        ''' The type of the given module. There should be no instances of this type--the actual instances
        are really instances of the corresponding hardware module class, which are not literal values.
        The two types (ModuleType and Module) are kept separate to keep the type representation and the hardware
        representation seperate, despite representing the same object. TODO decide whether or not to merge them?
        TODO should we pass around a module's ModuleType with its metadata? '''
        _name = name
        _moduleCtx = moduleCtx
        _params = params
        def __init__(self):
            pass
    return ModuleType

def Maybe(mtype: 'MType'):
    ''' mtype is the type of the Maybe minispec type '''
    class MaybeType(MLiteral):
        '''value is the value if valid, None if invalid'''
        _name = "Maybe#(" + str(mtype) + ")"
        _constructor = Maybe
        _mtype = mtype
        def __init__(self, value: 'mtype' = None):
            self.value = value
            if value == None:
                self.isValid = False
            else:
                self.isValid = True
                #assert value.__class__ == mtype, "Type of value does not match type of maybe" #TODO incorporate Any types
        def __str__(self):
            if not self.isValid:
                return "Invalid"
            return "Valid(" + str(self.value) + ")"
        def __eq__(self, other):
            if self.__class__ != other.__class__:
                return False
            if self.isValid != other.isValid:
                return False
            return self.value == other.value
        def copy(self):
            c = MaybeType(self.value)
            for tokenArray in self.getSourceTokensNotFlat():
                c.addSourceTokens(tokenArray)
            return c
        def eq(self, other):
            assert self.__class__ == other.__class__, f"Can only compare values of the same type, found {self.__class__} and {other.__class__}"
            if (not self.isValid) and (not other.isValid): # both invalid
                return Bool(True)
            return Bool(self.value == other.value)
        @classmethod
        def sameType(self, other):
            return True
            # TODO handle Any values
            # return self._mtype == other._mtype

    return MaybeType

def Invalid(mtype: 'MType'):
    return Maybe(mtype)()

class DontCareLiteral(MLiteral):
    '''only one kind, "?" '''
    def __init__(self):
        pass
    def __str__(self):
        return '?'
    def __eq__(self, other):
        return self.__class__ == other.__class__
    def eq(self, other):
        # TODO figure out what happens to ? values in case/if statements/expressions
        assert self.__class__ == other.__class__, f"Can only compare values of the same type, found {self.__class__} and {other.__class__}"
        raise Exception("Arithmetic with don't care literals is not implemented due to entanglement")
    '''unary operations'''
    def booleaninv(self):
        raise Exception("Arithmetic with don't care literals is not implemented due to entanglement")
    def inv(self):
        raise Exception("Arithmetic with don't care literals is not implemented due to entanglement")
    def redand(self):
        raise Exception("Arithmetic with don't care literals is not implemented due to entanglement")
    def redor(self):
        raise Exception("Arithmetic with don't care literals is not implemented due to entanglement")
    def redxor(self):
        raise Exception("Arithmetic with don't care literals is not implemented due to entanglement")
    def unaryadd(self):
        raise Exception("Arithmetic with don't care literals is not implemented due to entanglement")
    def neg(self):
        raise Exception("Arithmetic with don't care literals is not implemented due to entanglement")

if __name__ == '__main__':
    # #Create a synonym of Bit#(32). For testing purposes.
    # Word = Synonym(Bit(Integer(32)), 'Word')
    # print(Word)
    # print(Word.__class__)
    # print(Word.untypedef())
    # a = Word(31)
    # print(a)

    #Create Maybe type. For testing purposes.
    m = Maybe(Bit(IntegerLiteral(2)))
    print(m)

    b = Bit(IntegerLiteral(2))
    c = Bit(IntegerLiteral(2))
    print(b == c) #True
    d = Bit(IntegerLiteral(3))
    print(b == d) #False
    e = Bool
    print(e == b) #False