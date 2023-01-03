
from mtypes import *

''' The hardware rep.
The hardware representation consists of two data structures:
    1. A graph of Wire and Node objects, with Wires as edges, Nodes as vertices, and each vertex having in-degree 1.
    2. A tree of Component objects.
    4. Each Component has a dictionary mapping labels to input nodes and a dictionary mapping labels to output nodes.
    4. Each Node is either an input of some Component or an output of some Component, and that component is its unique parent Component.
The graph represents the low-level structure of the hardware, while the tree represents the object-oriented minspec-hdl structure.

Notes:
    - The graph need not be connected. For instance, built-in Components such as binary operators are treated
    as black boxes, hence do not have Wires connecting their input Node(s) to their output Node.
    - The tree must be connected, with a unique root corresponding to the function or module being synthesized.
    - Every Node must have a unique parent component.
    - A Component's child Components are unordered, that is, the tree is an unordered tree.
    - The label of a Node should be something like a string or int--immutable, sortable, and hashable.

Garbage collection. We have two variations of hardware garbage collection.
    Version 1. Remove inaccessible combinatorial logic, such as functions with unused outputs.
    Version 2. Remove all unused hardware, including e.g. internal counters which are not exposed through methods.
Version 1 uses a graph search to recursively find and remove unused nodes and their associated wires+components
Version 2 uses mark-and-sweep as described below:
    - A Node is in use if
        - it is an output Node of the root Component
    - A Wire is in use if
        - its destination Node is in use
    - A Component is in use if
        - any output Node of the Component is in use
    - Any Node, Wire, or Component which is not in use is be removed.
'''


''' Private methods/fields begin with a single underscore. Type help(property) in python3 for details
of setters/getters. Slots are used to enforce which fields may be set. '''

class Node:
    ''' name: Nodes can be given a name for debugging convenience.
    mtype: Nodes may be given a type. This will eventually be used for type-related manipulations.
    _id: each Node has a unique id. 
    inWires: the set of Wires with this Node as their dst.
    outWires: the set of Wires with this Node as their src.
    parent: the Component with this Node as an input or output.
    isInput: true if the parent Component has this Node as an input, false otherwise.
    label: the label of the Node in its parent Component. '''
    _num_nodes_created = 0  # one for each node created
    __slots__ = '_name', '_mtype', '_id', '_inWires', '_outWires', '_parent', '_isInput', '_label'
    def __init__(self, name: 'str' = "", mtype: 'MType' = Any):
        self._name = name
        assert mtype.__class__ == MType, f"Expected a type, not {mtype}"
        self._mtype = mtype
        self._id = Node._num_nodes_created
        Node._num_nodes_created += 1
        self._inWires: 'set[Wire]' = set()
        self._outWires: 'set[Wire]' = set()
        self._parent: 'Component' = None
        self._isInput: bool = None
        self._label = None
    def __hash__(self):
        return hash('n' + str(self._id))
    def __repr__(self):
        return "Node(" + str(self._id) + ": " + str(self._mtype) + ")"
    def __str__(self):
        return "Node(" + str(self._name) + ": " + str(self._mtype) + ")"
    def setMType(self, value):
        self._mtype = value
    @property
    def inWires(self) -> 'set[Wire]':
        ''' The set of Wires with this Node as their dst. Mutable. '''
        return self._inWires
    @property
    def outWires(self) -> 'set[Wire]':
        ''' The set of Wires with this Node as their src. Mutable. '''
        return self._outWires
    def addInWire(self, wire: 'Wire'):
        ''' inWires is the set of Wires with this Node as their dst. '''
        assert len(self._inWires) == 0, "A Node can only be the dst of at most one Wire."
        self.inWires.add(wire)
    def addOutWire(self, wire: 'Wire'):
        ''' outWires the set of Wires with this Node as their src. '''
        self.outWires.add(wire)
    @property
    def parent(self) -> 'Component|None':
        ''' The parent Component of the Node. '''
        return self._parent
    def setParent(self, parent: 'Component', isInput: 'bool', label: 'Any'):
        ''' Sets the parent of the Node, as well as its label and whether it is an input or output.
        Used when creating a Component. '''
        assert self._parent == None, "Cannot change parent of a Node"
        self._parent = parent
        self._isInput = isInput
        self._label = label

def isNode(value):
    '''Returns whether or not value is a Node'''
    return value.__class__ == Node
def isNodeOrMLiteral(value):
    '''Returns whether or not value is a literal or a node.'''
    return isMLiteral(value) or isNode(value)

class Wire:
    ''' src and dst are Nodes.
    Adds itself to the hardware data structure when initialized. '''
    _num_wires_created = 0  # one for each Wire created
    __slots__ = '_id', '_src', '_dst', '_tokensSourcedFrom'
    def __init__(self, src: 'Node', dst: 'Node'):
        assert isNode(src), f"Must be a node, not {src} which is {src.__class__}"
        assert isNode(dst), f"Must be a node, not {dst} which is {dst.__class__}"
        assert src._parent != None, "Can only put Wire on Node in Component"
        assert dst._parent != None, "Can only put Wire on Node in Component"
        self._id = Wire._num_wires_created
        Wire._num_wires_created += 1
        self._src = src
        src.addOutWire(self)
        self._dst = dst
        dst.addInWire(self)
        self._tokensSourcedFrom: 'list[list[tuple[str, int]]]' = []
    def __hash__(self):
        return hash('w' + str(self._id))
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
    def addSourceTokens(self, tokens: 'list[tuple[str, int]]'):
        ''' Given a list of tuples (filename, token), adds the list to the collection of sources of the component. '''
        assert tokens.__class__ == list, f"unexpected token class {tokens.__class__}"
        assert all( place.__class__ == tuple for place in tokens ), f"unexpected classes of entries in tokens {[place.__class__ for place in tokens if place.__class__ != tuple]}"
        self._tokensSourcedFrom.append(tokens)
    def getSourceTokens(self) -> 'list[tuple[str, int]]':
        ''' Returns the source tokens of self. '''
        return sum(self._tokensSourcedFrom, [])
    def weight(self):
        ''' Returns an estimate of how large a Component is. '''
        return 1

class Component:
    _num_components_created = 0  #one for each component created, so each component has a unique id
    __slots__ = '_id', '_name', '_children', '_inputs', '_outputs', '_parent', '_tokensSourcedFrom', '_persistent'
    def __init__(self, name: 'str', inputs: 'dict[Any, Node]', outputs: 'dict[Any, Node]', parent: 'Component|None', children: 'set[Component]'):
        # type assertions
        assert name.__class__ == str, f'Component name must be a string, not {name.__class__}'
        assert inputs.__class__ == dict, f'Component inputs must be a dictionary, not {name.__class__}'
        for nodeKey in inputs:
            assert inputs[nodeKey].__class__ == Node, f'Component inputs must be Nodes, not {name.__class__}'
        assert outputs.__class__ == dict, f'Component outputs must be a dictionary, not {name.__class__}'
        for nodeKey in outputs:
            assert outputs[nodeKey].__class__ == Node, f'Component outputs must be Nodes, not {name.__class__}'
        assert isinstance(parent, Component) or parent == None, f'Component parent must be a Component or None, not {name.__class__}'
        assert children.__class__ == set, f'Component children must be a set, not {name.__class__}'
        for child in children:
            assert isinstance(child, Component), f'Component children must be Components, not {name.__class__}'
        # give each component a unique _id
        self._id = Component._num_components_created
        Component._num_components_created += 1
        self._name: 'str' = name
        self._children: 'set[Component]' = children
        self._inputs: 'dict[Any, Node]' = inputs
        for nodeKey in inputs:
            node = inputs[nodeKey]
            node.setParent(self, True, nodeKey)
        self._outputs: 'dict[Any, Node]' = outputs
        for nodeKey in outputs:
            node = outputs[nodeKey]
            node.setParent(self, False, nodeKey)
        self._parent: 'Component|None' = parent
        self._tokensSourcedFrom: 'list[list[tuple[str, int]]]' = []
        self._persistent: 'bool' = False
    def __repr__(self):
        return "Component(" + self._name + ", " + self._children.__repr__() + ", " + self._inputs.__repr__() + ", " + self._outputs.__repr__() + ")"
    def __hash__(self):
        return hash('c' + str(self._id))
    @property
    def name(self):
        ''' The name of the component, eg 'f' or 'combine#(1,1)' or '*'. '''
        return self._name
    @name.setter
    def name(self, name: 'str'):
        self._name = name
    @property
    def children(self):
        ''' The child Components of the Component '''
        return self._children
    def addInput(self, inputNode: 'Node', inputKey: 'Any'):
        '''Add the input with the given key'''
        assert inputNode.__class__ == Node, f"Inputs must be a Node, not {inputNode.__class__}"
        assert inputKey not in self._inputs, f"Can't overwrite existing input {inputKey}"
        inputNode.setParent(self, True, inputKey)
        self._inputs[inputKey] = inputNode
    def addOutput(self, outputNode: 'Node', outputKey: 'Any'):
        '''Add the output with the given key'''
        assert outputNode.__class__ == Node, f"Outputs must be a Node, not {outputNode.__class__}"
        assert outputKey not in self._outputs, f"Can't overwrite existing output {outputKey}"
        outputNode.setParent(self, False, outputKey)
        self._outputs[outputKey] = outputNode
    @property
    def inputs(self) -> 'dict[Any, Node]':
        ''' A copy of the inputs of the Component '''
        return self._inputs.copy()
    @property
    def outputs(self) -> 'dict[Any, Node]':
        ''' A copy of the outputs of the Component '''
        return self._outputs.copy()
    @property
    def output(self):
        ''' The output Node of the Component, if it is unique.
        Used by variants with one output, such as Function or Mux. '''
        assert len(self._outputs) == 1, "Can only return output if it is unique"
        return next(iter(self._outputs.values()))
    @property
    def parent(self) -> 'Component|None':
        ''' The parent of the component. '''
        return self._parent
    def match(self, other: 'Component|None') -> bool:
        ''' Returns true if self and other represent the same hardware. '''
        assert self != other, "cannot compare a component to itself"
        assert self._parent == None, "can only compare hardware structures at the root Component"
        assert other._parent == None, "can only compare hardware structures at the root Component"

        # we give each component a signature corresponding to the Component tree with the component as its root.
        # isomorphic trees have the same signature.
        selfSignatures: 'dict[Component, int]' = {}
        otherSignatures: 'dict[Component, int]' = {}
        def signature(comp: 'Component', signatures: 'dict[Component, int]'):
            for child in comp._children:
                signatures[child] = signature(child, signatures)
            return hash((comp._name, tuple(sorted(comp._inputs)), tuple(sorted(comp._outputs)), tuple(sorted(signatures[child] for child in comp._children))))
        selfSignatures[self] = signature(self, selfSignatures)
        otherSignatures[other] = signature(other, otherSignatures)

        if selfSignatures[self] != otherSignatures[other]:
            # the tree parts of self and other have distinct signatures, hence are not isomorphic.
            # most failing comparison tests should fail here.
            return False

        # now we try to match the trees
        selfChildMaps: 'dict[Component, list[Component]]' = {}
        otherChildMaps: 'dict[Component, list[Component]]' = {}
        # we will put the children in a convenient order, then try to match self to other by reordering self's children.
        # for each match, we will check for equality using orderedNodeEq.
        # if no matches pass orderedNodeEq, the components are different.
        def orderChildren(comp: 'Component', childMaps: 'dict[Component, list[Component]]', signatures: 'dict[Component, int]'):
            for child in comp._children:
                orderChildren(child, childMaps, signatures)
            # sort the children first by number of children with matching signiture, then by signiture (so children with the same signiture are adjacent and children with a unique signiture are first).
            # note that sorted is a stable sort.
            childMaps[comp] = sorted(sorted(comp._children, key=lambda child: signatures[child]), key=lambda child: len([c for c in comp._children if signatures[c] == signatures[child]]))
        orderChildren(self, selfChildMaps, selfSignatures)
        orderChildren(other, otherChildMaps, otherSignatures)

        selfComps: 'list[Component]' = [self]
        otherComps: 'list[Component]' = [self]
        def getAllComponents(root: 'Component', childMaps: 'dict[Component, list[Component]]', comps: 'list[Component]'):
            for child in childMaps[root]:
                comps.append(child)
                getAllComponents(child, childMaps, comps)
        getAllComponents(self, selfChildMaps, selfComps)
        getAllComponents(other, otherChildMaps, otherComps)

        selfCompsIndices: 'dict[Component, int]' = {}
        for i in range(len(selfComps)):
            selfCompsIndices[selfComps[i]] = i

        def matchStep(i):
            ''' try to match self to other by reordering the children of selfComps[i], ..., selfComps[-1].
            returns true if a match is found and false otherwise. '''
            if i >= len(selfComps):
                return Component.orderedNodeEq(self, other, selfChildMaps, otherChildMaps)
            comp = selfComps[i]
            if len(comp._children) == 0:
                return matchStep(i+1)
            return matchRemainder(i, 0)

        def matchRemainder(i, j):
            ''' try to match self by reordering the children of selfComps[i+1], ..., selfComps[-1]
            and reordering selfComps[i][j+1], ..., selfComps[i][-1].
            returns true if a match is found and false otherwise. '''
            assert i < len(selfComps), "out of range"
            comp = selfComps[i]
            if j >= len(comp.children):
                return matchStep(i+1)
            for k in range(j, len(comp._children)):
                if selfSignatures[selfChildMaps[comp][j]] != selfSignatures[selfChildMaps[comp][k]]:
                    break
                c1, c2 = selfChildMaps[comp][j], selfChildMaps[comp][k]
                selfChildMaps[comp][j], selfChildMaps[comp][k] = c2, c1

                # check and see if the node lists are consistent so far
                selfNodes: 'list[Node]' = []
                otherNodes: 'list[Node]' = []
                def getNodes(comp: 'Component', nodes: 'list[Node]'):
                    for nodeKey in sorted(comp._inputs):
                        nodes.append(comp._inputs[nodeKey])
                    for nodeKey in sorted(comp._outputs):
                        nodes.append(comp._outputs[nodeKey])
                compsPlaced = set()
                for c in range(i):
                    compsPlaced.add(selfComps[c])
                def getPlacedComponentsNodes(selfComp: 'Component', otherComp: 'Component'):
                    getNodes(selfComp, selfNodes)
                    getNodes(otherComp, otherNodes)
                    if selfComp in compsPlaced:
                        assert len(selfChildMaps[selfComp]) == len(otherChildMaps[otherComp]), 'might fail if a hash collision occurs--if this assert fails, the trees do not match.'
                        for i in range(len(selfChildMaps[selfComp])):
                            selfChild = selfChildMaps[selfComp][i]
                            otherChild = otherChildMaps[otherComp][i]
                            getPlacedComponentsNodes(selfChild, otherChild)
                    elif selfComp == comp:
                        for i in range(j+1):
                            selfChild = selfChildMaps[selfComp][i]
                            otherChild = otherChildMaps[otherComp][i]
                            getPlacedComponentsNodes(selfChild, otherChild)
                getPlacedComponentsNodes(self, other)
                if self.testNodes(selfNodes, otherNodes):
                    if matchRemainder(i, j+1):
                        return True
                selfChildMaps[comp][j], selfChildMaps[comp][k] = c1, c2
            return False
        return matchStep(0)

    def testNodes(self, selfNodes: 'list[Node]', otherNodes: 'list[Node]'):
        ''' Returns true if the graph structure of the nodes matches and false otherwise. '''
        selfNodeDict: 'dict[Node, int]' = {}
        otherNodeDict: 'dict[Node, int]' = {}
        for i in range(len(selfNodes)):
            selfNodeDict[selfNodes[i]] = i
            otherNodeDict[otherNodes[i]] = i
        # determine if the graph structure matches
        for i in range(len(selfNodes)):
            selfNode = selfNodes[i]
            otherNode = otherNodes[i]
            # check outgoing edges
            selfNodeAdjs: 'set[Node]' = {wire.dst for wire in selfNode.outWires if wire.dst in selfNodeDict}
            otherNodeAdjs: 'set[Node]' = {wire.dst for wire in otherNode.outWires if wire.dst in otherNodeDict}
            if len(selfNodeAdjs) != len(otherNodeAdjs):
                return False
            for adjNode in selfNodeAdjs:
                j = selfNodeDict[adjNode]
                if otherNodes[j] not in otherNodeAdjs:
                    return False
            for adjNode in otherNodeAdjs:
                j = otherNodeDict[adjNode]
                if selfNodes[j] not in selfNodeAdjs:
                    return False
            # check incoming edges
            selfNodeAdjs: 'set[Node]' = {wire.src for wire in selfNode.inWires if wire.src in selfNodeDict}
            otherNodeAdjs: 'set[Node]' = {wire.src for wire in otherNode.inWires if wire.src in otherNodeDict}
            if len(selfNodeAdjs) != len(otherNodeAdjs):
                return False
            for adjNode in selfNodeAdjs:
                j = selfNodeDict[adjNode]
                if otherNodes[j] not in otherNodeAdjs:
                    return False
            for adjNode in otherNodeAdjs:
                j = otherNodeDict[adjNode]
                if selfNodes[j] not in selfNodeAdjs:
                    return False
        return True

    def orderedNodeEq(self, other, selfChildMaps: 'dict[Component, list[Component]]', otherChildMaps: 'dict[Component, list[Component]]'):
        ''' Returns true if the map sending one tree to the other preserves the graph+tree structure. '''
        def verifyTree(selfComp: 'Component', otherComp: 'Component'):
            # returns True if the Component trees rooted at selfComp and otherComp are the same, including Node labels and Component names.
            if selfComp._name != otherComp._name:
                return False
            if len(selfComp._inputs) != len(otherComp._inputs):
                return False
            if len(selfComp._outputs) != len(otherComp._outputs):
                return False
            if len(selfComp._children) != len(otherComp._children):
                return False
            if set(selfComp._inputs) != set(otherComp._inputs):
                return False
            if set(selfComp._outputs) != set(otherComp._outputs):
                return False
            selfChildren = selfChildMaps[selfComp]
            otherChildren = otherChildMaps[otherComp]
            for i in range(len(selfChildren)):
                if not verifyTree(selfChildren[i], otherChildren[i]):
                    return False
            return True
        if not verifyTree(self, other):
            return False
        # at this point, we have confirmed that the tree structures match.

        # collect nodes in a deterministic order so we can determine if the graph structure matches
        selfNodes: 'list[Node]' = []
        otherNodes: 'list[Node]' = []
        def getNodes(comp: 'Component', childMaps: 'dict[Component, list[Component]]', nodes: 'list[Node]'):
            for nodeKey in sorted(comp._inputs):
                nodes.append(comp._inputs[nodeKey])
            for nodeKey in sorted(comp._outputs):
                nodes.append(comp._outputs[nodeKey])
            for child in childMaps[comp]:
                getNodes(child, childMaps, nodes)
        getNodes(self, selfChildMaps, selfNodes)
        getNodes(other, otherChildMaps, otherNodes)

        return self.testNodes(selfNodes, otherNodes)
    def addChild(self, component: 'Component'):
        assert isinstance(component, Component), f"Children of a Component must be Components, not {component.__class__}"
        assert component not in self._children, "Cannot add Component to children twice"
        assert component != self, "A Component cannot be its own child"
        self._children.add(component)
        component._parent = self
    def addSourceTokens(self, tokens: 'list[tuple[str, int]]'):
        ''' Given a list of tuples (filename, token), adds the list to the collection of sources of the component. '''
        self._tokensSourcedFrom.append(tokens)
    def getSourceTokens(self) -> 'list[tuple[str, int]]':
        ''' Returns the source tokens of self. '''
        return sum(self._tokensSourcedFrom, [])
    def getAllWires(self) -> 'set[Wire]':
        ''' Returns the set of all wires in the data structure. '''
        wires = set()
        for child in self._children:
            for wire in child.getAllWires():
                wires.add(wire)
        for nodeKey in self._inputs:
            for wire in self._inputs[nodeKey].outWires:
                wires.add(wire)
        for nodeKey in self._outputs:
            for wire in self._outputs[nodeKey].outWires:
                wires.add(wire)
        return wires
    def weight(self):
        ''' Returns an estimate of how large a Component is. '''
        return 1 + sum([c.weight() for c in self._children])

class Function(Component):
    __slots__ = '_inputList', 'inputNames'
    def __init__(self, name: 'str', inputs: 'list[Node]' = None, output: 'Node' = None, children: 'set[Component]' = None):
        if inputs == None:
            inputs = []
        if output == None:
            output = Node()
        assert output.__class__ == Node, f"Function output must be Node, not {output.__class__}"
        if children == None:
            children = set()
        Component.__init__(self, name, {i : inputs[i] for i in range(len(inputs))}, {0: output}, None, children)
        self._inputList: 'list[Node]' = inputs
        self.inputNames = []
    @property
    def inputs(self):
        '''Returns a copy of the list of input Nodes to this function'''
        return self._inputList.copy()

class Mux(Component):
    __slots__ = '_control', '_inputNames'
    def __init__(self, inputs: 'list[Node]', control: 'Node'=None, output: 'Node'=None):
        if control == None:
            control = Node('_mux_control')
        self._control = control
        if output == None:
            output = Node('_mux_output')
        inputDict = {i : inputs[i] for i in range(len(inputs))}
        inputDict[-1] = self._control
        Component.__init__(self, "_mux", inputDict, {0: output}, None, set())
        self._inputNames = None
    @property
    def inputs(self):
        '''Returns a copy of the list of input Nodes to the mux'''
        return [self._inputs[i] for i in range(len(self._inputs)-1)]
    @property
    def control(self):
        '''The control input Node of the mux'''
        return self._control
    @property
    def inputNames(self):
        return self._inputNames
    @inputNames.setter
    def inputNames(self, inputNames: 'list[str]'):
        assert(len(inputNames) == len(self._inputs) - 1), f"Wrong number of mux input labels--expected {len(self._inputs) - 1}, got {len(inputNames)}"
        self._inputNames = inputNames

class Constant(Component):
    __slots__ = '_value'
    def __init__(self, value: 'MLiteral'):
        assert isMLiteral(value), f"Value of Constant must be MLiteral, not {value.__class__}"
        self._value = value
        Component.__init__(self, str(self.value), {}, {'c0': Node()}, None, set())
    @property
    def value(self) -> 'MLiteral':
        '''The value of the constant'''
        return self._value

class Module(Component):
    __slots__ = 'metadata'
    def __init__(self, name: 'str', inputs: 'dict[str, Node]' = None, methods: 'dict[str, Node]' = None, children: 'set[Component]' = None):
        if inputs == None:
            inputs = {}
        if methods == None:
            methods = {}
        if children == None:
            children = set()
        Component.__init__(self, name, inputs, methods, None, children)
    @property
    def methods(self) -> 'dict[str, Node]':
        ''' A copy of the methods of the module '''
        return self._outputs.copy()
    def addMethod(self, methodNode: 'Node', methodKey: 'str'):
        self.addOutput(methodNode, methodKey)
    def isRegister(self):
        return False

class Register(Module):
    __slots__ = ()
    def __init__(self, name: 'str'):
        Module.__init__(self, name, {'_input':Node('input')}, {'_value':Node('value')})
    def isRegister(self):
        return True
    @property
    def input(self):
        '''The input node to the register'''
        return self._inputs['_input']
    @input.setter
    def input(self, value: 'Node'):
        raise Exception("Can't directly modify this property")
    @property
    def value(self):
        '''The node with the value of the register'''
        return self._outputs['_value']
    @value.setter
    def value(self, value: 'Node'):
        raise Exception("Can't directly modify this property")

class VectorModule(Module):
    __slots__ = 'numberedSubmodules'
    def __init__(self, numberedSubmodules: 'list[Module]', *args):
        ''' Same as initializing a module, just with an extra numberedSubmodules field at the beginning '''
        self.numberedSubmodules: 'list[Module]' = numberedSubmodules
        super().__init__(*args)
    def addNumberedSubmodule(self, submodule: 'Module'):
        self.numberedSubmodules.append(submodule)
    def getNumberedSubmodule(self, num: 'int'):
        ''' Returns the nth submodule of a vector of submodules (possibly a register) '''
        return self.numberedSubmodules[num]
    def depth(self) -> int:
        ''' Returns the number of layers of vectors of submodules. '''
        if self.numberedSubmodules[0].__class__ == VectorModule:
            return 1 + self.numberedSubmodules[0].depth()
        return 1
    def isVectorOfRegisters(self) -> bool:
        ''' Returns true if the innermost modules of this vector of modules are registers. '''
        if self.numberedSubmodules[0].__class__ == VectorModule:
            return self.numberedSubmodules[0].isVectorOfRegisters
        return self.numberedSubmodules[0].isRegister()

class Demux(Component):
    # currently unused
    __slots__ = ()
    pass

class Splitter(Component):
    # currently unused
    __slots__ = ()
    pass


def garbageCollection1(root: 'Component'):
    ''' Garbage collection version 1: removes inaccessible combinatorial logic.
    - A Node is garbage collected if
        - its out-degree is zero, it is an output of its parent Component, and its parent
          Component's `_persistant` flag is not set
        - its parent component is garbage collected
    - A Wire is garbage collected if
        - its destination Node is garbage collected
    - A Component is garbage collected if
        - a Node or child Component of the Component is garbage collected, no Node of the
          component is the source of a Wire, and the Component has no child components
        - it has no Nodes or child Components '''
    if not root._persistent:
        for nodeKey in root._outputs.copy():
            node = root._outputs[nodeKey]
            if len(node.outWires) == 0:
                gc1node(node)
    for child in root.children.copy():
        # if len(child.children) == 0 and len(child._inputs) == 0 and len(child._outputs) == 0:
        #     root.children.remove(child)
        # else:
        #     garbageCollection1(child)
        garbageCollection1(child)

def gc1component(component: 'Component'):
    for nodeKey, node in component._inputs.copy().items():
        assert len(node.outWires) == 0, "Cannot garbage collect a Component with Nodes which are sources"
    for nodeKey, node in component._outputs.copy().items():
        assert len(node.outWires) == 0, "Cannot garbage collect a Component with Nodes which are sources"
    assert len(component.children) == 0, "Cannot garbage collect a Component with children"
    assert component.parent != None, "Cannot remove the root Component"
    component.parent.children.remove(component)
    component._parent = None
    for nodeKey, node in component._inputs.copy().items():
        gc1node(node)
    for nodeKey, node in component._outputs.copy().items():
        gc1node(node)

def gc1wire(wire: 'Wire'):
    node = wire.src
    node.outWires.remove(wire)
    if len(node.outWires) == 0:
        if not node._isInput:
            gc1node(node)

def gc1node(node: 'Node'):
    assert len(node.outWires) == 0, "Cannot garbage collect a Node which is a source"
    if node._isInput:
        del node.parent._inputs[node._label]
    else:
        del node.parent._outputs[node._label]
    for wire in node.inWires:
        gc1wire(wire)
    component = node.parent
    if component.parent != None:
        if all(len(node.outWires) == 0 for nodeKey, node in component._inputs.items()):
            if all(len(node.outWires) == 0 for nodeKey, node in component._outputs.items()):
                if len(component.children) == 0:
                    gc1component(component)

'''
Some helpful ELK examples:
https://rtsys.informatik.uni-kiel.de/elklive/elkgraph.html?compressedContent=OYJwhgDgFgBA4gRgFABswE8D2BXALjAbRgGcBLALwFMAuGAZjoAYAaeugNhgF0kA7TACaUAyhUoA6AMaZexXOFK9cxWgCICAOQDyAEQCiAfQAyAQQBCeo8NYBZAJIa7NgKo2DwuwC09XVUiiklOAgklDoABJgvAIoisC0DgDCRs76BonhdkY6AEp6GkhgKMCYIKS4UAC2tKXA4pSSsRDEEpQoANbiaOhBlAJ8mEYYOLi0AGZFLQNCMNJKYIpBMADeSACQ3SOE62sQmGS4pDK0AEwsMGc7ZFSnAJzsrCe3jOs8a-xColRSMnIKSioYOptGlTBYrLYHE5XO4vD4-GsAkEwCEwpForFePEYEkUmkMllcvl1h8RGJxJVFKRKthqkCABR0E7iFgAFnYLIAlAi2p0IGABAI4moCLhMBAALwclgoShjXAShAs5gAI0wuDFlUVyrKwCgCqVjF862I-MkcXEpI0ghoMBeGzAKraMCMCDUc1wC14QVUKx2mzw2zWwb2ByOvFoCBOrNYAFYdmtrrbWQAOR7IYNvd42oZOlDEcQQNCSSiVShKEXhdL5AAqehyrAAagYa1oAAqsBwefTGtYAXxJNpgellZaUCD9wYD+AICdD5XDkdYTITSbuMZgsboOyzpK+Ejmfy9yhFIMMYMs1hg9kcLjcHm8vcRgWCoQiURiwpxGmSqUMBOyPICmDPdyUpXhqVpNR6ROFNlROaVuX9R1nSME41BHUty1wBBfVWYMHSwQNZwIxMxFoFMHguDMCPnQ5jjtOMEyzbMhFzNoCyLMASzHUYgQIKtElresmxbdtOw0bt4R2Ad+0HGZMN4k5J0IrYSJDfYFwYhBWBTeMCLXC5bg3WN7TWXcbX3H5ZHkY9AWBXRz3MS9IVvGEH2k4MkVfNEP0xbFcT-dJMkA4kQMssCqRpOlVBguCWBOAB2LkEQdPMXToDDR2wk48ITacgwM8iYEo9ME12TT6IjRiYHYZiE1Jdj80LYssIrfjBOEhsYGbVsO2-KSn1k2TSWHbKlDoFSCvUiqw201gEDofTg0Mp4N0SmiLM+clD1sxQT34s9jGciFryhO9YUfVLvJRN90U-LEEh-PF-xColgNYslvnAyCYri+DksYJCpxQlAXVZLK2twOg8oI6bysM0rqPKujFxquqCJYxrQc41reMrasNDrbrevEga7B7VLhvkygxqh1kpuGYi50qtGdIuRgMZW4q1t07dMx2UDvl2-4Doc0ETqvG9oXvOEnxu1F3wxL9AvxN6gMFiLvqiqCGVggGUuQ9KjFjSHeNZWGQaImcEeKpGThojS5uq84ufMhqcxxlruKhgmhKJkSerE-quwpzy5LkgcgA
https://snyk.io/advisor/npm-package/elkjs/example
http://rtsys.informatik.uni-kiel.de/elklive/examples.html

The top link shows how to create adjacent (sub)nodes, which will be useful for bit manipulation.
Here is another adjacent subnode link:
https://github.com/kieler/elkjs/issues/111
'''

''' The ELK JSON format.
A JSON object is an acyclic nested system of dictionaries with string keys:
    JSON = dict[str, JSON|str|int]
There is a standard encoding of JSON objects into strings.
Both python and javascript have methods for converting JSON strings back into the corresponding system of (in
python) dictionaries or (in javascript) objects. In python, the `json.dumps` method (from `import json`) converts
a JSON dictionary into the corrseponding string; in javascript, the corresponding method is `JSON.stringify` and
the reverse method is `JSON.parse`. Furthermore, as used in template.html, the output of javascript's JSON.stringify
method is legitimate javascript code, which is placed into the html output directly and when run, recreates the
original JSON system of objects.
    ELKJS accepts as input a JSON object which describes the nodes and edges of a graph. ELKJS then returns the same
JSON object (not sure if copied or mutated) annotated with layouting info--in the case of a node/port, coordinates and size
information, and in the case of an edge, a collection of start/end coordinates of segments.
    In ELKJS, every node and every edge must have a unique id, so that they may be identified by the library.
We also use the ids to store additional information not used by the layouter, such as source map information.
This is to avoid possible collisions between the layouter's object attributes and our object attributes, and
uses the fact that ELKJS is known to preserve id information.
The id of an object is then:
    <unique id created as component/wire creation> + '|' + <stringified json object with additional info>
The unique id created for each component/wire does not contain a '|' and is guaranteed to be unique via a
class variable counter that is incremented each time an instance is created. It has not been tested whether
or not longer node names may possibly slow down layout generation.
    In the html template, the portion of the id past the '|' is parsed into a JSON object to read off any
properties that go beyond ELK's layouting data.
    The `separators=(',', ':')` input to json.dumps tells python not to insert whitespace into the output
json, which somewhat reduces the file size.
'''

def getELK(component: 'Component') -> 'dict[str, Any]':
    ''' Converts given component into the ELK JSON format, see https://rtsys.informatik.uni-kiel.de/elklive/json.html '''
    
    componentELKs: 'dict[Component, dict[str, Any]]' = {}  # maps components to the corresponding json object
    componentELK = toELK(component, componentELKs)
    
    # Place edges with closest common ancestor of their src/dst Nodes
    for wire in component.getAllWires():
        edge = wireToELK(wire)
        sourceNode: 'Node' = wire.src
        targetNode: 'Node' = wire.dst
        # determine if the edge goes from the left side of a node to the right side directly,
        # which confuses the layouting library
        sourceParent: 'Component' = sourceNode.parent
        targetParent: 'Component' = targetNode.parent
        isDirectEdge = sourceParent == targetParent and sourceNode._isInput and not targetNode._isInput
        if isDirectEdge:
            # break the edge into two edges with a zero-size node in the middle
            middleNode = toELK(Function(""))
            middleNode['width'] = 0
            middleNode['height'] = 0
            assert len(edge['sources']) == 1, f"Unexpected edge {edge} with too many source nodes"
            assert len(edge['targets']) == 1, f"Unexpected edge {edge} with too many target nodes"
            edge1 = { 'id': 'part1_'+edge['id'], 'sources': [ edge['sources'][0] ], 'targets': [ middleNode['id'] ] }
            edge2 = { 'id': 'part2_'+edge['id'], 'sources': [ middleNode['id'] ], 'targets': [ edge['targets'][0] ] }
            if "edges" not in sourceParent:
                sourceParent['edges'] = []
            sourceParent['edges'].append(edge1)
            sourceParent['edges'].append(edge2)
            if "children" not in sourceParent:
                sourceParent['children'] = []
            sourceParent['children'].append(middleNode)
            continue
        # we have an ordinary edge, move it to the correct parent
        if not sourceNode._isInput:
            sourceParent = sourceParent.parent
        # collect the parents of the source node
        currentELK: 'Component' = sourceParent
        sourceParents: 'list[Component]' = [currentELK]
        while currentELK.parent != None:
            currentELK = currentELK.parent
            sourceParents.append(currentELK)
        if targetNode._isInput:
            targetParent = targetParent.parent
        # collect the parents of the target node
        currentELK = targetParent
        while currentELK not in sourceParents:
            assert currentELK.parent != None, "Can't find common ancestor for edge source/target"
            currentELK = currentELK.parent
        elk = componentELKs[currentELK]
        if "edges" not in elk:
            elk["edges"] = []
        elk["edges"].append(edge)

    # # Removes nodes corresponding to vectors of submodules/registers, dumping their children and edges into the outer modules.
    # def eliminateVectorModules(componentELK, parentELK):
    #     if "children" in componentELK:
    #         for child in componentELK["children"].copy():  # copy since the children may mutate componentELK's child list
    #             eliminateVectorModules(child, componentELK)
    #     if 'isVectorModule' in componentELK:
    #         if componentELK['isVectorModule'] and parentELK != None:
    #             if 'ports' not in componentELK or len(componentELK['ports']) == 0:
    #                 parentELK["children"].remove(componentELK)
    #                 # lift children and edges
    #                 if "children" in componentELK:
    #                     parentELK["children"] += componentELK["children"]
    #                 if "edges" in componentELK:
    #                     parentELK["edges"] += componentELK["edges"]
    # eliminateVectorModules(componentELK, None)


    # perhaps see https://snyk.io/advisor/npm-package/elkjs/example

    return { 'id': 'root',
             'layoutOptions': { 'algorithm': 'layered',
                                 # 'elk.layered.nodePlacement.strategy': 'SIMPLE',
                                 'hierarchyHandling': 'INCLUDE_CHILDREN' },
             'children': [ componentELK ],
             'edges': [] }

def weightAdjust(weight):
    ''' Given the 'weight' of a component, returns the amount of space to reserve for the label of the element. '''
    return 30*weight**0.25

def elkID(item: 'Component|Node') -> str:
    ''' Returns a unique id for the node or component for use in ELK '''
    if item.__class__ == Node:
        return f'n{item._id}'
    elif issubclass(item.__class__, Component):
        return f"c{item._id}"
    elif item.__class__ == Wire:
        return f"w{item._id}"
    raise Exception(f"Unrecognized class {item.__class__}.")

def setName(nodeELK: 'dict[str, Any]', name: 'str', height: 'float'):
    ''' Sets nodeELK to have a label `name` taking up `height` space at the top of the node. '''
    if 'properties' not in nodeELK:
        nodeELK['properties'] = {}
    nodeELK['properties']['elk.padding'] = f'[top={height+12},left=12,bottom=12,right=12]'  # the default padding is 12, see https://www.eclipse.org/elk/reference/options/org-eclipse-elk-padding.html. info on padding: https://github.com/kieler/elkjs/issues/27

def setPortLabel(nodeELK: 'dict[str, Any]', text: 'str', width: 'float', height: 'float'):
    nodeELK['labels'] = [ { 'text': text } ]
    nodeELK['width'] = width
    nodeELK['height'] = height

def nodeToELK(item: 'Node', properties: 'dict[str, Any]' = None) -> 'dict[str, Any]':
    assert item.__class__ == Node, "Requires a Node"
    jsonObj = { 'id': elkID(item), 'width': 0, 'height': 0, 'properties': properties }
    return jsonObj

def wireToELK(item: 'Wire'):
    assert item.__class__ == Wire, "Requires a Wire"
    jsonObj = { 'id': elkID(item), 'sources': [ elkID(item.src) ], 'targets': [ elkID(item.dst) ] }
    assert item in item.src.outWires, "Expected Wire to be in the outWires of its src"
    if len(item.src.outWires) == 1:
        jsonObj['properties'] = {}
        jsonObj['properties']['org.eclipse.elk.layered.priority.direction'] = 10
    return jsonObj

def toELK(item: 'Component', componentELKs: 'dict[Component, dict[str, Any]]', properties: 'dict[str, Any]' = None) -> 'dict[str, Any]':
    ''' Converts the node or component into the ELK JSON format as a python object. 
    See https://www.eclipse.org/elk/documentation/tooldevelopers/graphdatastructure/jsonformat.html 
    See https://github.com/kieler/elkjs/issues/27 for some examples.
    See https://www.eclipse.org/elk/documentation/tooldevelopers/graphdatastructure/coordinatesystem.html
    for information about the ELK coordinate system. '''
    if not properties:
        properties = {}
    assert item.__class__ != Node, "Use nodeToELK instead"
    assert item.__class__ != Wire, "Use wireToELK instead"
    itemWeightAdjusted = weightAdjust(item.weight())
    if item.__class__ == Function:
        ports = []
        ind = len(item.inputs)
        for i in range(len(item.inputs)):
            node = item.inputs[i]
            nodeELK = nodeToELK(node, {'port.side': 'WEST', 'port.index': ind})
            if item.inputNames:
                setPortLabel(nodeELK, item.inputNames[i], itemWeightAdjusted, 0.5*itemWeightAdjusted)
            ports.append(nodeELK)
            ind -= 1  # elk indexes nodes clockwise from the top, so the index decrements.
        ports.append( nodeToELK(item.output, {'port.side': 'EAST', 'port.index': 0}) )
        jsonObj = { 'id': elkID(item),
                    'ports': ports,
                    'children': [ toELK(child, componentELKs) for child in item.children ],
                    'properties': { 'portConstraints': 'FIXED_ORDER' } }  # info on layout options: https://www.eclipse.org/elk/reference/options.html
        setName(jsonObj, item.name, itemWeightAdjusted)
        if len(item.children) == 0 or not any(child.__class__ == Function for child in item.children): # in case a function has only a wire from input to output
            jsonObj['width'] = 15
            jsonObj['height'] = 15
        jsonObj['i'] = {'name': item.name,
                        'weight': weightAdjust(item.weight()),
                        'numSubcomponents': item.weight(),
                        'tokensSourcedFrom': item.getSourceTokens()}
    elif item.__class__ == Constant:
        jsonObj = { 'id': elkID(item),
                    'ports': [ nodeToELK(item.output, {'port.side': 'EAST'}) ],
                    'properties': { 'portConstraints': 'FIXED_SIDE' },
                    'width': 15,
                    'height': 15 }
        jsonObj['i'] = {'name': str(item.value),
                        'weight':weightAdjust(item.weight()),
                        'numSubcomponents': item.weight(),
                        'tokensSourcedFrom':item.getSourceTokens()}
    elif item.__class__ == Mux:
        ports = []
        for i in range(len(item.inputs)):
            node = item.inputs[i]
            nodeELK = nodeToELK(node, {'port.side': 'WEST'})
            if item.inputNames:
                setPortLabel(nodeELK, item.inputNames[i], 0, 0)
            ports.append(nodeELK)
        ports.append( nodeToELK(item.control, {'port.side': 'SOUTH'}) )
        ports.append( nodeToELK(item.output, {'port.side': 'EAST'}) )
        jsonObj = { 'id': elkID(item),
                    'ports': ports,
                    'width': 10,
                    'height': 10 * len(item.inputs),
                    'properties': { 'portConstraints': 'FIXED_SIDE' } }  # info on layout options: https://www.eclipse.org/elk/reference/options.html
        jsonObj['isMux'] = True
        jsonObj['i'] = {'name': '',
                        'weight': weightAdjust(item.weight()),
                        'numSubcomponents': item.weight(),
                        'isMux': True,
                        'tokensSourcedFrom':item.getSourceTokens()}
    elif item.__class__ == Module or item.__class__ == Register or item.__class__ == VectorModule:
        ports = []
        for nodeName in item.inputs:
            node = item.inputs[nodeName]
            nodeELK = nodeToELK(node, {'port.side': 'WEST'})
            if item.__class__ == Module:
                setPortLabel(nodeELK, nodeName, itemWeightAdjusted, 0.5*itemWeightAdjusted)
            ports.append(nodeELK)
        for nodeName in item.methods:
            node = item.methods[nodeName]
            nodeELK = nodeToELK(node, {'port.side': 'EAST'})
            if item.__class__ == Module:
                setPortLabel(nodeELK, nodeName, itemWeightAdjusted, 0.5*itemWeightAdjusted)
            ports.append(nodeELK)
        jsonObj = { 'id': elkID(item),
                    'ports': ports,
                    'children': [ toELK(child, componentELKs) for child in item.children ],
                    'properties': { 'portConstraints': 'FIXED_SIDE' } }  # info on layout options: https://www.eclipse.org/elk/reference/options.html
        setName(jsonObj, item.name, itemWeightAdjusted)
        if len(item.children) == 0:
            jsonObj['width'] = 15
            jsonObj['height'] = 15
        if item.__class__ == VectorModule:
            jsonObj['isVectorModule'] = True
        jsonObj['i'] = {'name':item.name,
                        'weight':weightAdjust(item.weight()),
                        'numSubcomponents': item.weight(),
                        'tokensSourcedFrom':item.getSourceTokens()}
    else:
        raise Exception(f"Unrecognized class {item.__class__} of item {item}.")
    componentELKs[item] = jsonObj
    return jsonObj


if __name__ == '__main__':
    print("hi")

    c = Function('f', [Node(), Node(), Node()])
    d = Function('f', [Node(), Node(), Node()])
    print(c.match(d))  # True

    e = Function('f', [Node(), Node()])
    print(c.match(e))  # False