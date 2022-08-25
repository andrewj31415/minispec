

from literals import *

'''Private methods/fields begin with a single underscore. See help(property) for details.
Slots are used to enforce which fields may be set.'''

class Node:
    '''name is just for convenience.
    mtype is the minispec type of the value that the node corresponds to.
    id is a unique id number for each node created.'''
    _num_nodes_created = 0  #one for each node created
    __slots__ = '_name', '_mtype', '_id'
    def __init__(self, name: 'str' = "", mtype: 'MType' = Any):
        self._name = name
        self._mtype = mtype
        self._id = Node._num_nodes_created
        Node._num_nodes_created += 1
    def __repr__(self):
        return "Node(" + str(self._id) + ": " + str(self._mtype) + ")"
    def __str__(self):
        return "Node(" + str(self._name) + ": " + str(self._mtype) + ")"

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
    __slots__ = tuple()
    def getNodeListRecursive(self):
        '''returns a list of all nodes in self in a deterministic order'''
        raise Exception("Not implemented")
    def matchStructure(self, other):
        '''returns true if self and other represent the same hardware, with the same ordering of components but not necessarily matching node identity structure'''
        raise Exception("Not implemented")
    def matchOrdered(self, other):
        '''returns true if self and other represent the same hardware, with the same ordering of components and the same node organization'''
        raise Exception("Not implemented")
    def match(self, other):
        '''returns true if self and other represent the same hardware.'''
        raise Exception("Not implemented")
    ''' Pruning. Removes unused hardware from the component. '''
    def prune(self):
        '''Removes all unused hardware.'''
        raise Exception("Not implemented")
    def inputNodes(self):
        '''Returns the set of all input nodes in self, eg a wire's src or a function's inputs.'''
        raise Exception("Not implemented")
    def outputNodes(self):
        '''Returns the set of all output nodes in self, eg a wire's dst or a function's output.'''
        raise Exception("Not implemented")
        


class Function(Component):
    ''' children is a list of components. '''
    __slots__ = '_name', '_children', '_inputs', '_output'
    def __init__(self, name: 'str', children: 'list[Component]', inputs: 'list[Node]', output: 'Node'=None):
        self.name = name
        self._children = children.copy() #copy the array but not the children themselves
        self._inputs = inputs
        if output == None:
            output = Node('_' + self.name + '_output')
        self._output = output
    @property
    def name(self):
        '''The name of the function, eg 'f' or 'combine#(1,1)' or '*'.'''
        return self._name
    @name.setter
    def name(self, name: 'str'):
        self._name = name
    @property
    def children(self):
        '''The hardware inside the function'''
        return self._children.copy()
    @children.setter
    def children(self, children: 'list[Component]'):
        raise Exception("Can't directly modify this property")
    def addChild(self, child: 'Component'):
        '''Adds the given hardware to the current function'''
        self._children.append(child)
    @property
    def inputs(self):
        '''Returns a copy of the list of input Nodes to this function'''
        return self._inputs.copy()
    @inputs.setter
    def inputs(self, inputs: 'list[Node]'):
        raise Exception("Can't directly modify this property")
    @property
    def output(self):
        '''The output Node of the function'''
        return self._output
    @output.setter
    def output(self, output: 'Node'):
        raise Exception("Can't directly modify this property")
    def __repr__(self):
        return "Function(" + self.name + ", " + self._children.__repr__() + ", " + self._inputs.__repr__() + ", " + self.output.__repr__() + ")"
    def __str__(self):
        if (len(self._children) == 0):
            return "Function " + self.name
        return "Function " + self.name + " with children " + " | ".join(str(x) for x in self._children)
    def getNodeListRecursive(self):
        '''returns a set of all nodes in self'''
        nodes = self.inputs.copy()
        nodes.append(self.output)
        for child in self._children:
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
        if len(self._children) != len(other._children):
            return False
        for i in range(len(self._children)):
            if not self._children[i].matchStructure(other._children[i]):
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
        if i >= len(self._children):
            return self.matchOrdered(other)
        for j in range(i, len(self._children)):
            if other._children[j].match(self._children[i]):
                other._children[i], other._children[j] = other._children[j], other._children[i]
                if self.matchStep(other, i+1):
                    return True
                other._children[i], other._children[j] = other._children[j], other._children[i]
        return False
    def match(self, other):
        '''returns true if self and other represent the same hardware.
        mutates other to have matching order in children lists.'''
        if self.__class__ != other.__class__:
            return False
        if self.name != other.name:
            return False
        if len(self._children) != len(other._children):
            return False
        return self.matchStep(other, 0)
    def prune(self):
        # graph search backwards from the output node
        inputs = {}  #maps nodes to the hardware for which they are an input
        outputs = {}
        for child in [self] + self.children:
            for node in child.inputNodes():
                if node not in inputs:
                    inputs[node] = set()
                if node not in outputs:
                    outputs[node] = set()
                inputs[node].add(child)
            for node in child.outputNodes():
                if node not in outputs:
                    outputs[node] = set()
                if node not in inputs:
                    inputs[node] = set()
                outputs[node].add(child)
        childrenToKeep = set()
        currentlyKeepingChildren = outputs[self.output].copy()
        nextChildren = set()
        while len(currentlyKeepingChildren) > 0:
            for child in currentlyKeepingChildren:
                for node in child.inputNodes():
                    for nextChild in outputs[node]:
                        nextChildren.add(nextChild)
            for child in currentlyKeepingChildren:
                childrenToKeep.add(child)
            currentlyKeepingChildren = nextChildren
            nextChildren = set()
        self._children = [child for child in self._children if child in childrenToKeep]
        for child in self.children:
            child.prune()
    def inputNodes(self):
        return set(self.inputs)
    def outputNodes(self):
        return {self.output}

class Mux(Component):
    __slots__ = '_inputs', '_control', '_output'
    def __init__(self, inputs: 'list[Node]', control: 'Node'=None, output: 'Node'=None):
        self._inputs = inputs
        if control == None:
            control = Node('_mux_control')
        self._control = control
        if output == None:
            output = Node('_mux_output')
        self._output = output
    @property
    def name(self):
        '''The name of the function, eg 'f' or 'combine#(1,1)' or '*'.'''
        return self._name
    @name.setter
    def name(self, name: 'str'):
        self._name = name
    @property
    def inputs(self):
        '''Returns a copy of the list of input Nodes to this mux'''
        return self._inputs.copy()
    @inputs.setter
    def inputs(self, inputs: 'list[Node]'):
        raise Exception("Can't directly modify this property")
    @property
    def control(self):
        '''The control input Node of the mux'''
        return self._control
    @control.setter
    def control(self, control: 'Node'):
        raise Exception("Can't directly modify this property")
    @property
    def output(self):
        '''The output Node of the mux'''
        return self._output
    @output.setter
    def output(self, output: 'Node'):
        raise Exception("Can't directly modify this property")
    def __repr__(self):
        return "Mux(" + self.inputs.__repr__() + ", " + self.control.__repr__() + ", " + self.output.__repr__() + ")"
    def __str__(self):
        return "Mux"
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
        if len(self.inputs) != len(other.inputs):
            return False
        return True
    def prune(self):
        pass #no children
    def inputNodes(self):
        nodes = set(self.inputs)
        nodes.add(self.control)
        return nodes
    def outputNodes(self):
        return {self.output}

class Wire(Component):
    ''' src and dst are Nodes.'''
    __slots__ = "_src", "_dst"
    def __init__(self, src: 'Node', dst: 'Node'):
        assert src is not dst, "wire must have distinct ends"
        self._src = src
        self._dst = dst
    @property
    def src(self):
        '''The source node of the wire'''
        return self._src
    @src.setter
    def src(self, src: 'Node'):
        raise Exception("Can't directly modify this property")
    @property
    def dst(self):
        '''The source node of the wire'''
        return self._dst
    @dst.setter
    def dst(self, dst: 'Node'):
        raise Exception("Can't directly modify this property")
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
    def prune(self):
        pass #no children
    def inputNodes(self):
        return {self.src}
    def outputNodes(self):
        return {self.dst}
