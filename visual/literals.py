
import hardware
import mtypes

'''We will eventually want a class whose instances represent minispec literals, including:
integers, booleans, bit values, etc.
This class (and subclasses) will describe how to operate/coerce on these values.

#TODO literals will eventually need to be given the appropriate mtypes
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

class MLiteral():
    '''A minispec literal'''
    '''Coercions for arithmetic operations are performed so that variant-specific
    calls always have the same class.
    mType is the type of the corresponding literal.'''
    def __init__(self, value: 'str'):
        '''Given a minispec literal as a string, return the
        appropriate literal value.'''  #TODO not sure if this method is used anywhere ...
        if value == "True" or value == "False":
            return BooleanLiteral(value)
        assert False, f"Unknown literal {value}"
    def getHardware(self, globalsHandler):
        assert globalsHandler.isGlobalsHandler(), "Quick type check"
        constantFunc = hardware.Function(str(self), [], [], hardware.Node(str(self), self.mtype))
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

class IntegerLiteral(MLiteral):
    '''self.value is an integer'''
    def __init__(self, value: 'int'):
        assert value.__class__ == int
        self.value = value
        self.mtype = mtypes.Integer
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

class BitLiteral(MLiteral):
    '''n is the number of bits. value is an integer 0 <= value < 2**n.'''
    def __init__(self, n: 'int', value: 'int'):
        '''n is the number of bits. value is any integer.'''
        assert n.__class__ == int
        assert value.__class__ == int
        self.n = n
        self.value = value % 2**n
        self.mtype = mtypes.Bit.getBit(IntegerLiteral(self.n))
    def __repr__(self):
        return "BitLiteral(" + str(self.n) + "," + str(self.value) + ")"
    def __str__(self):
        output = ""
        val = self.value
        for i in range(self.n):
            output = output + (val % 2)
            val /= 2
        return str(self.n) + "'b" + output
    def fromIntegerLiteral(self, i: 'IntegerLiteral'):
        assert -(2**(self.n-1)) <= i.toInt() < 2**self.n, "Bluespec requires Bit#(n) literals to be in range -2**(n-1),...,2**n-1."
        return BitLiteral(self.n, i.toInt())
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
    '''unary operations'''
    def neg(self):
        return BitLiteral(self.n, -self.value)

class BooleanLiteral(MLiteral):
    '''value is a boolean'''
    def __init__(self, value: 'bool'):
        self.value = value
        self.mtype = mtypes.Bool
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
