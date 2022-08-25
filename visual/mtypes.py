
import literals

class MType:
    '''A minispec type'''
    pass

class Any(MType):
    '''An unknown type'''
    def __str__(self):
        return "Any"
Any = Any()

class Integer(MType):
    '''An integer type'''
    def __str__(self):
        return "Integer"
Integer = Integer()

class Bit(MType):
    '''A bit type with n bits. All bit objects must be unique.'''
    createdBits = {}  # a map n -> Bit(n)
    def __init__(self, n: 'literals.IntegerLiteral'):
        assert n.__class__ == literals.IntegerLiteral, f"A bit must be an integer literal, not {n} which is {n.__class__}"
        n = n.value #extract the value of the integer literal
        assert n not in Bit.createdBits, "All bit objects must be unique."
        self.n = n
    def __str__(self):
        return "Bit#(" + str(self.n) + ")"
    def getBit(n: 'literals.IntegerLiteral'):
        if n not in Bit.createdBits:
            Bit.createdBits[n] = Bit(n)
        return Bit.createdBits[n]

class Bool(MType):
    '''The boolean type'''
    def __str__(self):
        return "Bool"
Bool = Bool()

class Vector(MType):
    '''The Vector(k, tt) type'''
    createdVectors = {} # a map (k, tt) -> Vector(k, tt)
    def __init__(self, k: 'int', typeValue: 'MType'):
        self.k = k
        self.typeValue = typeValue
    def __str__(self):
        return "Vector#(" + str(self.k) + ", " + str(self.typeValue) + ")"