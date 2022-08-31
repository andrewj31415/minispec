
import hardware

# A minispec type is a python classes; instances thereof represent literal values.

'''We will eventually want a class whose instances represent minispec literals, including:
integers, booleans, bit values, etc.
This class (and subclasses) will describe how to operate/coerce on these values.

#TODO reexamine literal arithmetic for time conversions

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

Unary operators:
'!' | '~' | '&' | '~&' | '|' | '~|' | '^' | '^~' | '~^' | '+' | '-'
Names for methods in code:
'!' is not.
'~' is inv.
'&' is redand.
'~&' is #TODO
'|' is redor.
'~|' is #TODO
'^' is redxor
'^~' is #TODO
'~^' is #TODO
'+' is unaryadd
'-' is neg

'''

#TODO we're not implementing parameterized typedefs for a while.

def Synonym(mtype: 'MType', newName: 'str'):
    ''' Returns a class which is a synonym of the given class, with the appropriate name.
    Used for typedef synonyms. '''
    class TypeDef(mtype):
        _name = newName
        @classmethod
        def untypedef(cls):
            return mtype.untypedef()
    return TypeDef

def Enum(name: 'str', values: 'set[str]'):
    ''' Returns a class which represents an enum type. '''
    class Enum(MLiteral):
        ''' The only operations which are defined for enum literals are eq/neq #TODO check this '''
        _name = name
        def __init__(self, value: 'str'):
            ''' Create an enum literal '''
            assert value in values, f"Enum type may only take on the specified values {values}, not the given value {value}"
            self.value = value
    return Enum

def Struct(name: 'str', fields: 'dict[str:"MType"]'):
    ''' Returns a class which represents a struct type. '''
    class Struct(MLiteral):
        ''' The only operations which are defined for struct literals are eq/neq #TODO check this '''
        _name = name
        def __init__(self, fieldBinds: 'dict[str:MLiteral]'):
            assert set(fieldBinds) == set(fields), f"Must specify fields {set(fields)} but instead specified fields {set(fieldBinds)}"
            for field in fieldBinds:
                assert fieldBinds[field].untypedef() == fields[field].untypedef(), f"Received type {fieldBinds[field]} but expected type {fields[field]}"
            self.fieldBinds = fieldBinds.copy
    return Struct

class MType(type):
    ''' The type of a minispec type '''
    def __str__(self):
        ''' This method is invoked by str(Integer), etc. Used for nice printing of type classes.
        Returns self._name if _name is defined as a class variable, otherwise returns what
        __str__ would ordinarily return. '''
        try:
            return self._name
        except:
            return super.__str__(self)

class MLiteral(metaclass=MType):
    ''' A minispec type '''
    def __init__(self):
        raise Exception("Not implemented")
    @classmethod
    def untypedef(cls):  #TODO consider renaming "untypedef" to just "class" or "getClass" ...
        ''' Return the original untypedef-ed type.
        If we run typedef Bit#(32) Word, then Word.untypedef() will give back Bit#(32). '''
        return cls
    def getHardware(self, globalsHandler):
        assert globalsHandler.isGlobalsHandler(), "Quick type check"
        constantFunc = hardware.Function(str(self), [], [], hardware.Node(str(self), self.__class__))
        globalsHandler.currentComponent.addChild(constantFunc)
        return constantFunc.output
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
        first, second = MLiteral.coerceArithmetic(first, second)
        return first.lt(second)
    def le(first, second):
        raise Exception("Not implemented")
    def gt(first, second):
        raise Exception("Not implemented")
    def ge(first, second):
        raise Exception("Not implemented")
    def eq(first, second):
        return first.eq(second)
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
    '''unary operations'''
    def neg(first):
        return first.neg()

class Any(MLiteral):
    '''An unknown type'''
    _name = "Any"
    def __str__(self):
        return "Any"

class Integer(MLiteral):
    '''An integer type'''
    _name = "Integer"
    def __init__(self, value):
        ''' Create an integer literal '''
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
    '''unary operations'''
    def neg(self):
        return IntegerLiteral(-self.value)
IntegerLiteral = Integer  #useful alias

def Bit(n: 'IntegerLiteral'):
    ''' Returns a type corresponding to a bitstring Bit#(n) of length n. '''
    assert n.__class__ == IntegerLiteral, f"Bit takes integer literals, not {n} which is {n.__class__}"
    class Bit(MLiteral):
        ''' self.n: 'int' is the number of bits. self.value: 'int' is an integer 0 <= value < 2**n. '''
        _name = f"Bit#({n})"
        def __init__(self, value: 'int'):
            ''' Create a Bit#(n) literal.
            value is an integer which will be assigned (mod 2**n) to self.value.
            Value may be any integer even though bsc requires Bit#(n) literals
            to be in the range -2**(n-1), ..., (2**n)-1. '''
            self.n = n
            assert value.__class__ == int
            self.value = value % (2**n.value)
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
        def bitxnor(self, other):
            raise Exception("Not implemented")
        def bitor(self, other):
            raise Exception("Not implemented")
        def booleanand(self, other):
            raise Exception("Not implemented")
        def booleanor(self, other):
            raise Exception("Not implemented")
        '''unary operations'''
        def neg(self):
            return Bit(self.n)(-self.value)
    return Bit

class Bool(MLiteral):
    '''The boolean type'''
    _name = "Bool"
    def __init__(self, value: 'bool'):
        self.value = value
    def __repr__(self):
        return "BooleanLiteral(" + str(self.value) + ")"
    def __str__(self):
        return str(self.value)
    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return self.value == other.value
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
BooleanLiteral = Bool  #useful alias
        
def Vector(k: 'int', typeValue: 'MLiteral'):
    class Vector(MLiteral):
        '''The Vector(k, tt) type'''
        _name = f"Vector#({k}{typeValue})"
        def __init__(self, k: 'int', typeValue: 'MLiteral'):
            self.k = k
            self.typeValue = typeValue
        def __str__(self):
            return "Vector#(" + str(self.k) + ", " + str(self.typeValue) + ")"
    return Vector

class Maybe(MLiteral):
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

if __name__ == '__main__':
    #Create a synonym of Bit#(32). For testing purposes.
    Word = Synonym(Bit(Integer(32)), 'Word')
    print(Word)
    print(Word.__class__)
    print(Word.untypedef())
    a = Word(31)
    print(a)