

from literals import *

class Node:
    '''name is just for convenience.
    mtype is the minispec type of the value that the node corresponds to.
    id is a unique id number for each node created.'''
    id = 0  #one for each node created
    def __init__(self, name: 'str' = "", mtype: 'MType' = Any):
        self.name = name
        self.mtype = mtype
        self.id = Node.id
        Node.id += 1
    def __repr__(self):
        return "Node(" + str(self.id) + ": " + str(self.mtype) + ")"
    def __str__(self):
        return "Node(" + str(self.name) + ": " + str(self.mtype) + ")"

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
            output = Node('_' + self.name + '_output')
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

class Mux(Component):
    def __init__(self, inputs: 'list[Node]', control: 'Node'=None, output: 'Node'=None):
        self.name = "mux"
        self.inputs = inputs
        if control == None:
            control = Node('_' + self.name + '_control')
        self.control = control
        if output == None:
            output = Node('_' + self.name + '_output')
        self.output = output
    def __repr__(self):
        return "Mux(" + self.name + ", " + self.inputs.__repr__() + ", " + self.control.__repr__() + ", " + self.output.__repr__() + ")"
    def __str__(self):
        if (len(self.children) == 0):
            return "Function " + self.name
        return "Function " + self.name + " with children " + " | ".join(str(x) for x in self.children)
    def getNodeListRecursive(self):
        '''returns a set of all nodes in self'''
        nodes = self.inputs.copy()
        nodes.append(self.output)
        nodes.append(self.control)
        return nodes
    def matchStructure(self, other):
        '''returns true if self and other represent the same hardware, with the same ordering of components but not necessarily matching node identity structure'''
        if self.__class__ != other.__class__:
            return False
        if self.name != other.name:
            return False
        if len(self.inputs) != len(other.inputs):
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
    def match(self, other):
        '''returns true if self and other represent the same hardware.
        mutates other to have matching order in children lists.'''
        if self.__class__ != other.__class__:
            return False
        if self.name != other.name:
            return False
        return True

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
