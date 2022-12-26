

from mtypes import *
import json

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

def getELK(component: 'Component') -> str:
    ''' Converts given component into the ELK JSON format, see https://rtsys.informatik.uni-kiel.de/elklive/json.html '''
    componentELK = toELK(component)

    # consider a pass to set certain edges to go forwards:
    # https://eclipse.org/elk/reference/options/org-eclipse-elk-layered-priority-direction.html

    # Collects edges with unique starting ports and sets ELK to prioritize having these edges go forward
    portsFound = {}
    portsRepeated = set()
    def collectEdgesWithUniqueStarts(componentELK):
        if "children" in componentELK:
            for child in componentELK["children"]:
                collectEdgesWithUniqueStarts(child)
        if "edges" in componentELK:
            for edge in componentELK["edges"]:
                sourceNode = edge["sources"][0]
                if sourceNode in portsRepeated:
                    pass
                elif sourceNode in portsFound:
                    portsRepeated.add(sourceNode)
                    del portsFound[sourceNode]
                else:
                    portsFound[sourceNode] = edge
    collectEdgesWithUniqueStarts(componentELK)
    for sourceNode in portsFound:
        edge = portsFound[sourceNode]
        if 'properties' not in edge:
            edge['properties'] = {}
        edge['properties']['layered.priority.direction'] = 10

    # Removes nodes corresponding to vectors of submodules/registers, dumping their children and edges into the outer modules.
    def eliminateVectorModules(componentELK, parentELK):
        if "children" in componentELK:
            for child in componentELK["children"].copy():  # copy since the children may mutate componentELK's child list
                eliminateVectorModules(child, componentELK)
        if 'isVectorModule' in componentELK:
            if componentELK['isVectorModule'] and parentELK != None:
                if 'ports' not in componentELK or len(componentELK['ports']) == 0:
                    parentELK["children"].remove(componentELK)
                    # lift children and edges
                    if "children" in componentELK:
                        parentELK["children"] += componentELK["children"]
                    if "edges" in componentELK:
                        parentELK["edges"] += componentELK["edges"]
    eliminateVectorModules(componentELK, None)

    # Collect all ports and mark parent pointers
    def getPorts(componentELK, portsToComponents):
        if "children" in componentELK:
            for child in componentELK["children"]:
                child["parent"] = componentELK
                getPorts(child, portsToComponents)
        if "ports" in componentELK:
            for port in componentELK["ports"]:
                portsToComponents[port["id"]] = (componentELK, port)
    portsToComponents = {}  # Maps port ids to a tuple (corresponding component, port)
    getPorts(componentELK, portsToComponents)

    # Move nonhierarchical edges to be children of the closest common ancestor
    def liftEdges(componentELK):
        if "edges" in componentELK:
            for edge in componentELK["edges"].copy():  # copies the list since we may be removing edges from it
                assert len(edge["sources"]) == 1
                assert len(edge["targets"]) == 1
                sourceNode = edge["sources"][0]
                targetNode = edge["targets"][0]
                # determine if the edge goes from the left side of a node to the right side directly,
                # which confuses the layouting library
                sourceParent, sourcePort = portsToComponents[sourceNode]
                targetParent, targetPort = portsToComponents[targetNode]
                isDirectEdge = sourceParent == targetParent and sourcePort["properties"]["port.side"] == "WEST" and targetPort["properties"]["port.side"]
                if isDirectEdge:
                    # break the edge into two edges with a zero-size node in the middle
                    middleNode = toELK(Function(""))
                    middleNode['parent'] = componentELK
                    middleNode['width'] = 0
                    middleNode['height'] = 0
                    assert len(edge['sources']) == 1, f"Unexpected edge {edge} with too many source nodes"
                    assert len(edge['targets']) == 1, f"Unexpected edge {edge} with too many target nodes"
                    edge1 = { 'id': 'part1_'+edge['id'], 'sources': [ edge['sources'][0] ], 'targets': [ middleNode['id'] ] }
                    edge2 = { 'id': 'part2_'+edge['id'], 'sources': [ middleNode['id'] ], 'targets': [ edge['targets'][0] ] }
                    componentELK['edges'].remove(edge)
                    if "edges" not in sourceParent:
                        sourceParent['edges'] = []
                    sourceParent['edges'].append(edge1)
                    sourceParent['edges'].append(edge2)
                    if "children" not in sourceParent:
                        sourceParent['children'] = []
                    sourceParent['children'].append(middleNode)
                    continue
                # we have an ordinary edge, move it to the correct parent
                if sourcePort["properties"]["port.side"] == "EAST":
                    sourceParent = sourceParent["parent"]
                # collect the parents of the source node
                currentELK = sourceParent
                sourceParents = [currentELK]
                while "parent" in currentELK:
                    currentELK = currentELK["parent"]
                    sourceParents.append(currentELK)
                if targetPort["properties"]["port.side"] == "WEST":
                    targetParent = targetParent["parent"]
                # collect the parents of the target node
                currentELK = targetParent
                while currentELK not in sourceParents:
                    assert "parent" in currentELK, "Can't find common ancestor for edge source/target"
                    currentELK = currentELK["parent"]
                componentELK["edges"].remove(edge)
                if "edges" not in currentELK:
                    currentELK["edges"] = []
                currentELK["edges"].append(edge)
        if "children" in componentELK:
            for child in componentELK["children"]:
                liftEdges(child)
    liftEdges(componentELK)

    # Remove parent pointers (since JSON can't have circular references)
    def removeParents(componentELK):
        if "children" in componentELK:
            for child in componentELK["children"]:
                del child["parent"]
                removeParents(child)
    removeParents(componentELK)

    # perhaps see https://snyk.io/advisor/npm-package/elkjs/example

    return json.dumps( { 'id': 'root',
                        'layoutOptions': { 'algorithm': 'layered',
                                            # 'elk.layered.nodePlacement.strategy': 'SIMPLE',
                                            'hierarchyHandling': 'INCLUDE_CHILDREN' },
                        'children': [ componentELK ],
                        'edges': [] }, separators=(',', ':') )

def weightAdjust(weight):
    ''' Given the 'weight' of a component, returns the amount of space to reserve for the label of the element. '''
    return 30*weight**0.25

def elkID(item: 'Component|Node') -> str:
    ''' Returns a unique id for the node or component for use in ELK '''
    if item.__class__ == Node:
        return f'node{item._id}'
    elif issubclass(item.__class__, Component):
        if item.__class__ == Mux:
            return f"component{item._id}|{json.dumps({'name':'', 'weight':weightAdjust(item.weight()), 'numSubcomponents': item.weight(), 'tokensSourcedFrom':item.getSourceTokens()}, separators=(',', ':'))}"
        if item.__class__ == Wire:
            return f"component{item._id}|{json.dumps({'name':''}, separators=(',', ':'))}"
        if item.__class__ == Function:
            return f"component{item._id}|{json.dumps({'name':item.name, 'weight':weightAdjust(item.weight()), 'numSubcomponents': item.weight(), 'tokensSourcedFrom':item.getSourceTokens()}, separators=(',', ':'))}"
        if item.__class__ == Module or item.__class__ == Register or item.__class__ == VectorModule:
            return f"component{item._id}|{json.dumps({'name':item.name, 'weight':weightAdjust(item.weight()), 'numSubcomponents': item.weight(), 'tokensSourcedFrom':item.getSourceTokens()}, separators=(',', ':'))}"
        return f"component{item._id}|{json.dumps({'name':item.name}, separators=(',', ':'))}"
    raise Exception(f"Unrecognized class {item.__class__}.")

def setName(nodeELK: 'dict[str, Any]', name: 'str', height: 'float'):
    ''' Sets nodeELK to have a label `name` taking up `height` space at the top of the node. '''
    if 'labels' not in nodeELK:
        nodeELK['labels'] = []
    nodeELK['labels'].append({ 'text': name,
                                'properties': {"nodeLabels.placement": "[H_LEFT, V_TOP, INSIDE]"} })
    if 'properties' not in nodeELK:
        nodeELK['properties'] = {}
    nodeELK['properties']['elk.padding'] = f'[top={height+12},left=12,bottom=12,right=12]'  # the default padding is 12, see https://www.eclipse.org/elk/reference/options/org-eclipse-elk-padding.html. info on padding: https://github.com/kieler/elkjs/issues/27

def setPortLabel(nodeELK: 'dict[str, Any]', text: 'str', width: 'float', height: 'float'):
    nodeELK['labels'] = [ { 'text': text,
                            'properties': {"nodeLabels.placement": "[H_LEFT, V_TOP, INSIDE]"} } ]
    nodeELK['width'] = width
    nodeELK['height'] = height


def toELK(item: 'Component|Node', properties: 'dict[str, Any]' = None) -> 'dict[str, Any]':
    ''' Converts the node or component into the ELK JSON format as a python object. 
    See https://www.eclipse.org/elk/documentation/tooldevelopers/graphdatastructure/jsonformat.html 
    See https://github.com/kieler/elkjs/issues/27 for some examples.
    See https://www.eclipse.org/elk/documentation/tooldevelopers/graphdatastructure/coordinatesystem.html
    for information about the ELK coordinate system. '''
    if not properties:
        properties = {}
    if item.__class__ == Node:
        jsonObj = { 'id': elkID(item), 'width': 0, 'height': 0, 'properties': properties }
        return jsonObj
    itemWeightAdjusted = weightAdjust(item.weight())
    if item.__class__ == Function:
        ports = []
        ind = len(item.inputs)
        for i in range(len(item.inputs)):
            node = item.inputs[i]
            nodeELK = toELK(node, {'port.side': 'WEST', 'port.index': ind})
            if item.inputNames:
                setPortLabel(nodeELK, item.inputNames[i], itemWeightAdjusted, 0.5*itemWeightAdjusted)
            ports.append(nodeELK)
            ind -= 1  # elk indexes nodes clockwise from the top, so the index decrements.
        ports.append( toELK(item.output, {'port.side': 'EAST', 'port.index': 0}) )
        jsonObj = { 'id': elkID(item),
                    'ports': ports,
                    'children': [ toELK(child) for child in item.children if child.__class__ != Wire ],
                    'edges': [ toELK(child) for child in item.children if child.__class__ == Wire ],
                    'properties': { 'portConstraints': 'FIXED_ORDER' } }  # info on layout options: https://www.eclipse.org/elk/reference/options.html
        setName(jsonObj, item.name, itemWeightAdjusted)
        if len(item.children) == 0 or not any(child.__class__ == Function for child in item.children): # in case a function has only a wire from input to output
            jsonObj['width'] = 15
            jsonObj['height'] = 15
        return jsonObj
    if item.__class__ == Mux:
        ports = []
        for i in range(len(item.inputs)):
            node = item.inputs[i]
            nodeELK = toELK(node, {'port.side': 'WEST'})
            if item.inputNames:
                setPortLabel(nodeELK, item.inputNames[i], 0, 0)
                nodeELK['isMuxLabel'] = True
            ports.append(nodeELK)
        ports.append( toELK(item.control, {'port.side': 'SOUTH'}) )
        ports.append( toELK(item.output, {'port.side': 'EAST'}) )
        jsonObj = { 'id': elkID(item),
                    'ports': ports,
                    'width': 10,
                    'height': 10 * len(item.inputs),
                    'properties': { 'portConstraints': 'FIXED_SIDE' } }  # info on layout options: https://www.eclipse.org/elk/reference/options.html
        jsonObj['isMux'] = True
        return jsonObj
    if item.__class__ == Module or item.__class__ == Register or item.__class__ == VectorModule:
        ports = []
        for nodeName in item.inputs:
            node = item.inputs[nodeName]
            nodeELK = toELK(node, {'port.side': 'WEST'})
            if item.__class__ == Module:
                setPortLabel(nodeELK, nodeName, itemWeightAdjusted, 0.5*itemWeightAdjusted)
            ports.append(nodeELK)
        for nodeName in item.methods:
            node = item.methods[nodeName]
            nodeELK = toELK(node, {'port.side': 'EAST'})
            if item.__class__ == Module:
                setPortLabel(nodeELK, nodeName, itemWeightAdjusted, 0.5*itemWeightAdjusted)
            ports.append(nodeELK)
        jsonObj = { 'id': elkID(item),
                    'ports': ports,
                    'children': [ toELK(child) for child in item.children if child.__class__ != Wire ],
                    'edges': [ toELK(child) for child in item.children if child.__class__ == Wire ],
                    'properties': { 'portConstraints': 'FIXED_SIDE' } }  # info on layout options: https://www.eclipse.org/elk/reference/options.html
        setName(jsonObj, item.name, itemWeightAdjusted)
        if len(item.children) == 0:
            jsonObj['width'] = 15
            jsonObj['height'] = 15
        if item.__class__ == VectorModule:
            jsonObj['isVectorModule'] = True
        return jsonObj
    if item.__class__ == Wire:
        return { 'id': elkID(item), 'sources': [ elkID(item.src) ], 'targets': [ elkID(item.dst) ] }
    raise Exception(f"Unrecognized class {item.__class__} of item {item}.")

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
    def setMType(self, value):
        self._mtype = value
    def isNode(self):
        return True

def isNode(value):
    '''Returns whether or not value is a Node'''
    return value.__class__ == Node
def isNodeOrMLiteral(value):
    '''Returns whether or not value is a literal or a node.'''
    return isMLiteral(value) or isNode(value)

class Component:
    '''
    Component = Function(children: list[Component], inputs: list[Node], output: Node)
                + Wire(src: Node, dst: Node)
                + Mux(inputs: list[Node], control: Node, output: Node)
                + Module(children: list[Component], inputs: dict[str -> Node], methods: dict[str -> Node])

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
    _num_components_created = 0  #one for each component created, so each component has a unique id
    __slots__ = '_id'
    def __init__(self):
        self._id = Component._num_components_created
        Component._num_components_created += 1
    def getNodeListRecursive(self):
        '''returns a list of all nodes in self in a deterministic order'''
        raise Exception("Not implemented")
    def matchStructure(self, other):
        '''returns true if self and other represent the same hardware, with the same ordering of components but not necessarily matching node identity structure'''
        raise Exception("Not implemented")
    def matchOrdered(self, other):
        '''returns true if self and other represent the same hardware, with the same ordering of components and the same node organization'''
        raise Exception("Not implemented")
    def match(self, other) -> Bool:
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
    def isRegister(self) -> Bool:
        '''Return true if self is a register. This is used when a register's value is used in an expression,
        since most modules' methods can only be accessed by name while a register's output may be accessed
        by referring to the register itself (so we need to determine when a module is actually a register).'''
        return False
    def isComponent(self) -> Bool:
        '''Used by assert statements'''
        return True
    def weight(self):
        ''' Returns an estimate of how large a component is. '''
        if hasattr(self, 'children'):
            return 1 + sum([c.weight() for c in self.children])
        return 0
    def addSourceTokens(self, tokens: 'list[tuple[str, int]]'):
        ''' Given a list of tuples (filename, token), adds the list to the collection of sources of the component. '''
        self._tokensSourcedFrom.append(tokens)
    def getSourceTokens(self) -> 'list[tuple[str, int]]':
        ''' Returns the source tokens of self. '''
        return sum(self._tokensSourcedFrom, [])

class Constant(Component):
    ''' The hardware corresponding to a constant literal value. '''
    __slots__ = '_value', '_output'
    def __init__(self, value: 'MLiteral', output: 'Node' = None):
        self._value = value
        if output == None:
            output = Node()
        self._output = output
    @property
    def value(self) -> 'MLiteral':
        '''The value of the constant'''
        return self.value
    @property
    def output(self) -> 'Node':
        '''The output node'''
        return self._output
    def getNodeListRecursive(self):
        return [self._output]
    def match(self, other):
        if self.__class__ != other.__class__:
            return False
        return self.value == other.value

class Module(Component):
    ''' A minispec module. methods is a dict mapping the name of a method to the node with the method output. '''
    __slots__ = '_name', '_children', '_inputs', '_methods', 'metadata', '_tokensSourcedFrom'
    def __init__(self, name: 'str', children: 'list[Component]', inputs: 'dict[str, Node]', methods: 'dict[str, Node]'):
        Component.__init__(self)
        self.name = name
        self._children = children.copy() #copy the array but not the children themselves
        self._inputs = inputs.copy()
        self._methods = methods.copy()
        self.metadata = None
        self._tokensSourcedFrom: 'list[list[tuple[str, int]]]' = []
    @property
    def name(self):
        '''The name of the module'''
        return self._name
    @name.setter
    def name(self, name: 'str'):
        self._name = name
    @property
    def children(self):
        '''The hardware inside the module'''
        return self._children.copy()
    @children.setter
    def children(self, children: 'list[Component]'):
        raise Exception("Can't directly modify this property")
    def addChild(self, child: 'Component'):
        '''Adds the given hardware to the current module'''
        assert child.isComponent(), "Only components can be children of a module"
        self._children.append(child)
    @property
    def inputs(self):
        '''Returns a copy of the dict of input Nodes to this module'''
        return self._inputs.copy()
    @inputs.setter
    def inputs(self, inputs: 'dict[str, Node]'):
        raise Exception("Can't directly modify this property")
    def addInput(self, inputNode: 'Node', inputName: 'str'):
        '''Add the input with the given name'''
        assert inputName not in self.inputs, f"Can't overwrite existing input {inputName}"
        self._inputs[inputName] = inputNode
    @property
    def methods(self):
        '''Returns a copy of the dict of method output Nodes of this module'''
        return self._methods.copy()
    @methods.setter
    def methods(self, methods: 'dict[str, Node]'):
        raise Exception("Can't directly modify this property")
    def addMethod(self, methodNode: 'Node', methodName: 'str'):
        '''Add the method output node. Used when a method has no arguments.'''
        assert methodName not in self.methods, f"Can't overwrite existing input {methodName}"
        self._methods[methodName] = methodNode
    def __repr__(self):
        return "Module(" + self.name + ", " + self.children.__repr__() + ", " + self.inputs.__repr__() + ", " + self.methods.__repr__() + ")"
    def getNodeListRecursive(self):
        nodes = []
        inputNameList = list(self._inputs)
        inputNameList.sort()
        for inputName in inputNameList:
            nodes.append(self._inputs[inputName])
        methodNameList = list(self._methods)
        methodNameList.sort()
        for methodName in methodNameList:
            nodes.append(self._methods[methodName])
        for child in self._children:
            nodes = nodes + child.getNodeListRecursive()
        return nodes
    def matchStructure(self, other):
        '''returns true if self and other represent the same hardware, with the same ordering of components but not necessarily matching node identity structure'''
        if self.__class__ != other.__class__:
            return False
        if self.name != other.name:
            return False
        if len(self._inputs) != len(other._inputs):
            return False
        if len(self._methods) != len(other._methods):
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
                #see if the nodes set up so far are the same graph
                #checking this now improves matching speed when there are lots of wires, since issues with
                #wire ordering can only be detected by looking at nodes--without partial node checks, we
                #would have to try every permutation of the wires.
                selfNodesSoFar = []
                for k in range(i+1):
                    selfNodesSoFar += self._children[k].getNodeListRecursive()
                otherNodesSoFar = []
                for k in range(i+1):
                    otherNodesSoFar += other._children[k].getNodeListRecursive()
                failed = False
                for ii in range(len(selfNodesSoFar)):
                    for jj in range(ii):
                        if selfNodesSoFar[ii] is selfNodesSoFar[jj] and otherNodesSoFar[ii] is not otherNodesSoFar[jj]:
                            failed = True
                        if selfNodesSoFar[ii] is not selfNodesSoFar[jj] and otherNodesSoFar[ii] is otherNodesSoFar[jj]:
                            failed = True
                        if failed:
                            break
                    if failed:
                        break
                if not failed:
                    #recursively try to match the rest
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
        if set(self._inputs) != set(other._inputs):
            return False
        if set(self._methods) != set(other._methods):
            return False
        return self.matchStep(other, 0)
    def prune(self):
        pass
        #TODO

class Register(Module):
    '''A module corresponding to a register'''
    def __init__(self, name: 'str'):
        super().__init__(name, [], {'_input':Node('input')}, {'_value':Node('value')})
        self.name = name
    def isRegister(self):
        return True
    @property
    def input(self):
        '''The input node to the register'''
        return self._inputs['_input']
    @input.setter
    def input(self, value: Node()):
        raise Exception("Can't directly modify this property")
    @property
    def value(self):
        '''The node with the value of the register'''
        return self._methods['_value']
    @value.setter
    def value(self, value: Node()):
        raise Exception("Can't directly modify this property")
   


class VectorModule(Module):
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

class Function(Component):
    ''' children is a list of components.
    tokensSourcedFrom is an array of arrays of tuples (filename, token) where filename is the name of a source file
    and token is a token index (int) in that source file such that clicking on that token in the given source file should jump
    to this function.
    inputNames is either None or a list[str] of length equal to len(_inputs). The ith entry of inputNames is
    the name of the argument to the function which corresponds to the ith node of _inputs. '''
    __slots__ = '_name', '_children', '_inputs', '_output', '_tokensSourcedFrom', 'inputNames'
    def __init__(self, name: 'str', children: 'list[Component]'=None, inputs: 'list[Node]'=None, output: 'Node'=None):
        Component.__init__(self)
        self.name = name
        if children == None:
            children = []
        self._children = children.copy() #copy the array but not the children themselves
        if inputs == None:
            inputs = []
        assert inputs.__class__ == list, f"Function input list must be list['Node'], not {inputs} which is {inputs.__class__}"
        for input in inputs:
            assert input.isNode(), f"Function input node must be a Node, not {input} which is {input.__class__}"
        self._inputs = inputs
        if output == None:
            output = Node('_' + self.name + '_output')
        assert output.isNode(), f"Function output node must be a Node, not {output} which is {output.__class__}"
        self._output = output
        self._tokensSourcedFrom: 'list[list[tuple[str, int]]]' = []
        self.inputNames = None
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
        assert child.isComponent(), "Only components can be children of a function"
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
                #see if the nodes set up so far are the same graph
                #checking this now improves matching speed when there are lots of wires, since issues with
                #wire ordering can only be detected by looking at nodes--without partial node checks, we
                #would have to try every permutation of the wires.
                selfNodesSoFar = []
                for k in range(i+1):
                    selfNodesSoFar += self._children[k].getNodeListRecursive()
                otherNodesSoFar = []
                for k in range(i+1):
                    otherNodesSoFar += other._children[k].getNodeListRecursive()
                failed = False
                for ii in range(len(selfNodesSoFar)):
                    for jj in range(ii):
                        if selfNodesSoFar[ii] is selfNodesSoFar[jj] and otherNodesSoFar[ii] is not otherNodesSoFar[jj]:
                            failed = True
                        if selfNodesSoFar[ii] is not selfNodesSoFar[jj] and otherNodesSoFar[ii] is otherNodesSoFar[jj]:
                            failed = True
                        if failed:
                            break
                    if failed:
                        break
                if not failed:
                    #recursively try to match the rest
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
    __slots__ = '_inputs', '_control', '_output', '_tokensSourcedFrom', '_inputNames'
    def __init__(self, inputs: 'list[Node]', control: 'Node'=None, output: 'Node'=None):
        Component.__init__(self)
        self._inputs = inputs
        if control == None:
            control = Node('_mux_control')
        self._control = control
        if output == None:
            output = Node('_mux_output')
        self._output = output
        self._inputNames = None
        self._tokensSourcedFrom: 'list[list[tuple[str, int]]]' = []
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
    @property
    def inputNames(self):
        return self._inputNames
    @inputNames.setter
    def inputNames(self, inputNames: 'str'):
        assert(len(inputNames) == len(self._inputs)), f"Wrong number of mux input labels--expected {len(self._inputs)}, got {len(inputNames)}"
        self._inputNames = inputNames
    def __repr__(self):
        return "Mux(" + self.inputs.__repr__() + ", " + self.control.__repr__() + ", " + self.output.__repr__() + ")"
    def __str__(self):
        return "Mux"
    def getNodeListRecursive(self):
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
        return self.matchOrdered(other)
    def prune(self):
        pass #no children
    def inputNodes(self):
        nodes = set(self.inputs)
        nodes.add(self.control)
        return nodes
    def outputNodes(self):
        return {self.output}

class Demux(Component):
    ''' Used for variable assignments to a vector of submodules.
    Has an input value, a control value, and a list of outputs.
    Each output node is a valid signal. TODO redesign. '''
    pass

#not currently used for anything--consider removing.
class Splitter(Component):
    ''' For assignments {a, b, c} = some_bitstring '''
    __slots__ = '_input', '_outputs'
    def __init__(self, input: 'Node', outputs: 'list[Node]'):
        Component.__init__(self)
        self._input = input
        self._outputs = outputs
    @property
    def name(self):
        '''The name of the function, eg 'f' or 'combine#(1,1)' or '*'.'''
        return self._name
    @name.setter
    def name(self, name: 'str'):
        self._name = name
    @property
    def input(self):
        ''' The input Node '''
        return self._input
    @input.setter
    def inputs(self, input: 'Node'):
        raise Exception("Can't directly modify this property")
    @property
    def outputs(self):
        '''Return a copy of the list of output Nodes'''
        return self._outputs.copy()
    @outputs.setter
    def outputs(self, outputs: 'list[Node]'):
        raise Exception("Can't directly modify this property")
    def __repr__(self):
        return "Splitter(" + self.input.__repr__() + ", " + self.outputs.__repr__() + ")"
    def __str__(self):
        return "Splitter"
    def getNodeListRecursive(self):
        return [self._input] + self._outputs.copy()
    def matchStructure(self, other):
        if self.__class__ != other.__class__:
            return False
        if len(self.outputs) != len(other.outputs):
            return False
        return True
    def matchOrdered(self, other):
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
        if self.__class__ != other.__class__:
            return False
        if len(self.outputs) != len(other.outputs):
            return False
        return self.matchOrdered(other)
    def prune(self):
        pass #no children
    def inputNodes(self):
        return {self.input}
    def outputNodes(self):
        return set(self.outputs)


class Wire(Component):
    ''' src and dst are Nodes.'''
    __slots__ = "_src", "_dst"
    def __init__(self, src: 'Node', dst: 'Node'):
        Component.__init__(self)
        assert isNode(src), f"Must be a node, not {src} which is {src.__class__}"
        assert isNode(dst), f"Must be a node, not {dst} which is {dst.__class__}"
        #assert src is not dst, "wire must have distinct ends"  #TODO uncomment this line
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

