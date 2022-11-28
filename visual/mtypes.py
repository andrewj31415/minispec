
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

MLiteralOperations: A class used to handle type checking/coercions before performing literal operations.
    Calls to literal operations outside of mtypes.py should go to MLiteralOperations. Also redirects some
    operations in terms of others--for instance, != is defined in terms of ==.

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
#TODO reexamine literal arithmetic for type conversions

A list of minispec operations and the names used in code:

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
^~, ~^ is bitnor.
| is bitor.
&& is booleanand.
|| is booleanor.

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

boolean_unary = set(['!'])
logical_unary = set(['~'])
arithmetic_unary = set(['+', '-'])
reduction_unary = set(['&', '|', '^'])

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
        ''' Handles equality of minispec types. Returns true if self and other are the same minispec type. '''
        if other.__class__ != MType:
            return False
        self = self.untypedef()
        other = other.untypedef()
        if self._constructor == None or other._constructor == None: #these are not created in a factory, so they are the same if and only if they are identical
            return super.__eq__(self, other)
        if self._constructor != other._constructor:  # look at the factory function
            return False
        return self.sameType(other) # remove typedef synonyms before comparing

class MLiteral(metaclass=MType):
    ''' A minispec type. Instances are minispec literals. '''
    _constructor = None
    def __init__(self):
        raise Exception("Not implemented")
    @classmethod
    def untypedef(cls):  #TODO consider renaming "untypedef" to just "class" or "getClass" ...
        ''' Return the original untypedef-ed type.
        If we run typedef Bit#(32) Word, then Word.untypedef() will give back Bit#(32). '''
        return cls
    @classmethod
    def sameType(self, other):
        ''' Returns true if self and other are the same minispec type. Assumes self and other were created in the same type factory. '''
        raise Exception("Not implemented, not created in a type factory.")
    def getHardware(self, globalsHandler):
        assert globalsHandler.isGlobalsHandler(), "Quick type check"
        constantFunc = hardware.Function(str(self), [], [], hardware.Node(str(self), self.__class__))
        if hasattr(self, 'tokensSourcedFrom'):
            constantFunc.tokensSourcedFrom += self.tokensSourcedFrom
        globalsHandler.currentComponent.addChild(constantFunc)
        return constantFunc.output
    def copy(self):
        ''' Returns a copy of self. Used for handling source support of constant values. '''
        raise Exception("Not implemented")
    def numLiterals(self) -> 'int|float':
        ''' Returns the number of possible distinct literals of this type (or math.inf), where
        distinct is defined by minispec's "==" operator.
        Used in case statements to determine when all cases are covered. '''
        raise Exception("Not Implemented")
    '''binary operations. self is assumed to be the first operand (in subtraction, divsion, etc.)
    le, gt, ge are in terms of lt and eq. neq is in terms of eq.'''
    def pow(self, other):
        raise Exception("Not Implemented")
    def mul(self, other):
        raise Exception("Not Implemented")
    def div(self, other):
        raise Exception("Not implemented")
    def mod(self, other):
        raise Exception("Not implemented")
    def add(self, other):
        raise Exception("Not Implemented")
    def sub(self, other):
        raise Exception("Not Implemented")
    def sleft(self, other):
        raise Exception("Not implemented")
    def sright(self, other):
        raise Exception("Not implemented")
    def lt(self, other):
        raise Exception("Not Implemented")
    def eq(self, other):
        raise Exception("Not Implemented")
    def bitand(self, other):
        raise Exception("Not implemented")
    def bitxor(self, other):
        raise Exception("Not implemented")
    def bitnor(self, other):
        raise Exception("Not implemented")
    def bitor(self, other):
        raise Exception("Not implemented")
    def booleanand(self, other):
        raise Exception("Not implemented")
    def booleanand(self, other):
        raise Exception("Not Implemented")
    def booleanor(self, other):
        raise Exception("Not Implemented")
    '''unary operations. notredand is in terms of redand and inv.
    notredor is in terms of redor and inv. notredxor is in terms of redxor and inv.'''
    def booleaninv(self):
        raise Exception("Not Implemented")
    def inv(self):
        raise Exception("Not Implemented")
    def redand(self):
        raise Exception("Not Implemented")
    def redor(self):
        raise Exception("Not Implemented")
    def redxor(self):
        raise Exception("Not Implemented")
    def unaryadd(self):
        raise Exception("Not Implemented")
    def neg(self):
        raise Exception("Not Implemented")

class MLiteralOperations:
    '''class for calling operations on literals. handles typechecking and coercions.
    also redirects some operations to others, eg >= in terms of > and ==.
    For typechecking specs, see, page ~170, "Type Classes for Bit" etc.
        http://csg.csail.mit.edu/6.375/6_375_2019_www/resources/bsv-reference-guide.pdf
    '''
    def coerceArithmetic(first, second):
        if first.__class__ == IntegerLiteral and second.__class__ == BooleanLiteral:
            first = second.fromIntegerLiteral(first)
        elif first.__class__ == BooleanLiteral and second.__class__ == IntegerLiteral:
            second = first.fromIntegerLiteral(second)
        return (first, second)
    def coerceBoolean(first, second):
        assert first.__class__ == BooleanLiteral and second.__class__ == BooleanLiteral, "Boolean arithmetic requires boolean values"
        return first, second
    '''binary operations'''
    def pow(first, second):
        assert first.__class__ == IntegerLiteral and second.__class__ == IntegerLiteral, "pow can only be done with integer literals"
        return first.pow(second)
    def mul(first, second):
        first, second = MLiteralOperations.coerceArithmetic(first, second)
        return first.mul(second)
    def div(first, second):
        first, second = MLiteralOperations.coerceArithmetic(first, second)
        return first.div(second)
    def mod(first, second):
        raise Exception("Not implemented")
    def add(first, second):
        first, second = MLiteralOperations.coerceArithmetic(first, second)
        return first.add(second)
    def sub(first, second):
        first, second = MLiteralOperations.coerceArithmetic(first, second)
        return first.sub(second)
    def sleft(first, second):
        first, second = MLiteralOperations.coerceArithmetic(first, second)
        return first.sleft(second)
    def sright(first, second):
        first, second = MLiteralOperations.coerceArithmetic(first, second)
        return first.sright(second)
    def lt(first, second):
        first, second = MLiteralOperations.coerceArithmetic(first, second)
        return first.lt(second)
    def le(first, second):
        return Bool(MLiteralOperations.lt(first, second) or MLiteralOperations.eq(first, second))
    def gt(first, second):
        return MLiteralOperations.lt(second, first)
    def ge(first, second):
        return Bool(MLiteralOperations.lt(second, first) or MLiteralOperations.eq(first, second))
    def eq(first, second):
        return first.eq(second)
    def neq(first, second):
        return MLiteralOperations.booleaninv(MLiteralOperations.eq(first, second))
    def bitand(first, second):
        raise Exception("Not implemented")
    def bitxor(first, second):
        raise Exception("Not implemented")
    def bitnor(first, second):
        raise Exception("Not implemented")
    def bitor(first, second):
        raise Exception("Not implemented")
    def booleanand(first, second):
        first, second = MLiteralOperations.coerceBoolean(first, second)
        return first.booleanand(second)
    def booleanor(first, second):
        first, second = MLiteralOperations.coerceBoolean(first, second)
        return first.booleanand(second)
    '''unary operations'''
    def booleaninv(first):
        return first.booleaninv()
    def inv(first):
        return first.inv()
    def redand(first):
        return first.redand()
    def notredand(first):
        return first.redand().inv()
    def redor(first):
        return first.redor()
    def notredor(first):
        return first.redor().inv()
    def redxor(first):
        return first.redxor()
    def notredxor(first):
        return first.redxor().inv()
    def unaryadd(first):
        return first.unaryadd()
    def neg(first):
        return first.neg()


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
        def __init__(self, value: 'str', tokensSourcedFrom = None):
            ''' Create an enum literal '''
            assert value in values, f"Enum type may only take on the specified values {values}, not the given value {value}"
            self.value = value
            if tokensSourcedFrom == None:
                tokensSourcedFrom = []
            self.tokensSourcedFrom = tokensSourcedFrom.copy()
        def copy(self):
            return EnumType(self.value, self.tokensSourcedFrom.copy())
        def numLiterals(self) -> 'int|float':
            return len(values)
        @classmethod
        def sameType(self, other):
            return self._values == other._values
        def eq(self, other):
            if self.__class__ != other.__class__:
                return False
            return self.value == other.value
        def __str__(self):
            return self.value
    return EnumType

def Struct(name: 'str', fields: 'dict[str:MType]'):
    ''' Returns a class which represents a struct type.
    fields is a dict[str:MType] mapping a field name to the type the field should have. '''
    class StructType(MLiteral):
        ''' The only operations which are defined for struct literals are eq/neq #TODO check this '''
        _name = name
        _constructor = Struct
        _fields = fields
        def __init__(self, fieldBinds: 'dict[str:MLiteral]', tokensSourcedFrom = None):
            assert set(fieldBinds) == set(fields), f"Must specify fields {set(fields)} but instead specified fields {set(fieldBinds)}"
            for field in fieldBinds:
                pass #TODO modify this to allow implicit conversion Integer -> Bit#(n).
                #assert fieldBinds[field].__class__.untypedef() == fields[field].untypedef(), f"Received type {fieldBinds[field].__class__} but expected type {fields[field]}"
            self.fieldBinds = fieldBinds.copy()
            # TODO do structs ever get source tokens?
            if tokensSourcedFrom == None:
                tokensSourcedFrom = []
            self.tokensSourcedFrom = tokensSourcedFrom.copy()
        def copy(self):
            return StructType(self.fieldBinds.copy(), self.tokensSourcedFrom.copy())
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
        def eq(self, other):
            if self.__class__ != other.__class__:
                return Bool(False)
            if set(self.fieldBinds) != set(other.fieldBinds):
                return Bool(False)
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
    _name = "Integer"
    def __init__(self, value, tokensSourcedFrom = None):
        ''' Create an integer literal '''
        assert value.__class__ == int, f"Expected int, not {value} which is {value.__class__}"
        self.value = value
        if tokensSourcedFrom == None:
            tokensSourcedFrom = []
        self.tokensSourcedFrom = tokensSourcedFrom.copy()
    def copy(self):
        return Integer(self.value, self.tokensSourcedFrom.copy())
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
    '''binary operations'''
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
        return IntegerLiteral(self.value << other.value)
    def sright(self, other):
        return IntegerLiteral(self.value >> other.value)
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
    def bitnor(self, other):
        raise Exception("Not implemented")
    def bitor(self, other):
        raise Exception("Not implemented")
    def booleanand(self, other):
        raise Exception("Not implemented")
    def booleanor(self, other):
        raise Exception("Not implemented")
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
            return BitLiteral(self.value)
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
        def fromIntegerLiteral(self, i: 'IntegerLiteral'):
            assert -(2**(self.n-1)) <= i.toInt() < 2**self.n, "Bluespec requires Bit#(n) literals to be in range -2**(n-1),...,2**n-1."
            return Bit(self.n)(i.toInt())
        '''binary operations'''
        def pow(self, other):
            raise Exception("Not implemented")
        def mul(self, other):
            raise Exception("Not implemented")
        def div(self, other):
            raise Exception("Not implemented")
        def mod(self, other):
            raise Exception("Not implemented")
        def add(self, other):
            return Bit(max(self.n, other.n))(self.value + other.value)
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
        def bitnor(self, other):
            raise Exception("Not implemented")
        def bitor(self, other):
            raise Exception("Not implemented")
        def booleanand(self, other):
            raise Exception("Not implemented")
        def booleanor(self, other):
            raise Exception("Not implemented")
        '''unary operations'''
        def booleaninv(self):
            raise Exception("Not implemented")
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
        self.value = value
    def copy(self):
        return Bool(self.value)
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
        return self.value
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
        return self == other
    def neq(self, other):
        raise Exception("Not implemented")
    def bitand(self, other):
        raise Exception("Not implemented")
    def bitxor(self, other):
        raise Exception("Not implemented")
    def bitnor(self, other):
        raise Exception("Not implemented")
    def bitor(self, other):
        raise Exception("Not implemented")
    def booleanand(self, other):
        return BooleanLiteral(self.value and other.value)
    def booleanor(self, other):
        return BooleanLiteral(self.value or other.value)
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
        '''unary operations'''
        def booleaninv(self):
            raise Exception("Not implemented")
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
            if value == None:
                self.isValid = False
            else:
                self.isValid = True
                #assert value.__class__ == mtype, "Type of value does not match type of maybe" #TODO incorporate any types
                self.value = value
        def __str__(self):
            if not self.isValid:
                return "Invalid"
            return "Valid(" + str(self.value) + ")"
        def eq(self, other):
            if self.__class__ != other.__class__:
                return False
            if (not self.isValid) and (not other.isValid): # both invalid
                return True
            return self.value == other.value

    return MaybeType

def Invalid(mtype: 'MType'):
    return Maybe(mtype)()

class DontCareLiteral(MLiteral):
    '''only one kind, "?" '''
    def __init__(self):
        pass
    def __str__(self):
        return '?'
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
    def bitnor(self, other):
        return self
    def bitor(self, other):
        return self
    def booleanand(self, other):
        return self
    def booleanor(self, other):
        return self
    '''unary operations'''
    def booleaninv(self):
        return self
    def inv(self):
        return self
    def redand(self):
        return self
    def redor(self):
        return self
    def redxor(self):
        return self
    def unaryadd(self):
        return self
    def neg(self):
        return self

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