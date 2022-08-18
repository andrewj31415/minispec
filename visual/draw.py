
''' Component = Module<Array<Component>> + Function<Array<Component>> + Wire '''

''' The ends of wires will be connected to instances of Node. Modules and Functions will
use Node instances to represent inputs and outputs. The Node objects do not appear in the
final JavaScript since they are not needed after computing the final positions of components. 

All of these objects are mutable for placement.

A constant is a function with no arguments.
'''

class Component:
    pass

class Node:
    '''
    name is just for convenience.
    (x, y) are the coordinates of the node.
    '''
    def __init__(self, name=None):
        self.name = name
    def __str__(self):
        if self.name != None:
            return self.name
        return "n"
    def placeAt(self, x, y):
        self.x = x
        self.y = y
        return self
    def translate(self, dx, dy):
        self.x += dx
        self.y += dy
    def copy(self):
        node = Node(self.name)
        node.x = self.x
        node.y = self.y
        return node

class Module(Component):
    '''
    children is a list of components.
    inputs is a list of names of inputs to the module.
    outputs is a list of names of methods of the module.
    '''
    def __init__(self, name: 'str', type: 'str', children: 'list[Component]', inputs: 'list[Node]', outputs: 'list[Node]'):
        self.name = name
        self.type = type
        self.children = children
        self.inputs = inputs
        self.outputs = outputs
        self.timing = "0 ps"
    def __str__(self):
        return "Module " + self.name + " with children " + " | ".join(str(x) for x in self.children)
    def translate(self, dx, dy):
        self.x += dx
        self.y += dy
        for child in self.children:
            child.translate(dx, dy)
        for node in self.inputs:
            node.translate(dx, dy)
        for node in self.outputs:
            node.translate(dx, dy)
    def autoPlace(self):
        '''automatically place nodes'''
        for i in range(len(self.inputs)):
            self.inputs[i].x = self.x
            self.inputs[i].y = self.height*(i+1)/(len(self.inputs)+1)
        for i in range(len(self.outputs)):
            self.outputs[i].x = self.x + self.width
            self.outputs[i].y = self.height*(i+1)/(len(self.outputs)+1)
    def toJavaScript(self):
        d = { 'name': "`" + self.name + "`", 'type': "`" + self.type + "`", 'variant': "'Module'", 'source': self.source,
                'typeSource': self.typeSource, 'x': self.x, 'y': self.y, 'width': self.width, 'height': self.height,
                'timing': "`" + self.timing + "`",
                'children': '[' + ", ".join([child.toJavaScript() for child in self.children]) + ']' }
        return '{' + ", ".join( key+": "+str(d[key]) for key in d) + '}'

class Function(Component):
    ''' children is a list of components. '''
    def __init__(self, name: 'str', children: 'list[Component]', inputs: 'list[Node]'):
        self.name = name
        self.children = children
        self.inputs = inputs
        self.output = Node('_' + name + '_output')
        self.timing = "0 ps"
    def __str__(self):
        if (len(self.children) == 0):
            return "Function " + self.name
        return "Function " + self.name + " with children " + " | ".join(str(x) for x in self.children)
    def translate(self, dx, dy):
        self.x += dx
        self.y += dy
        for child in self.children:
            child.translate(dx, dy)
        for node in self.inputs:
            node.translate(dx, dy)
        self.output.translate(dx, dy)
    def autoPlace(self):
        '''automatically place nodes'''
        for i in range(len(self.inputs)):
            self.inputs[i].x = self.x
            self.inputs[i].y = self.height*(i+1)/(len(self.inputs)+1)
        self.output.x = self.x + self.width
        self.output.y = self.y + self.height/2
    def toJavaScript(self):
        d = { 'name': "`" + self.name + "`", 'variant': "'Function'", 'source': self.source, 'timing': "`" + self.timing + "`",
                'typeSource': self.typeSource, 'x': self.x, 'y': self.y, 'width': self.width, 'height': self.height,
                'children': '[' + ", ".join([child.toJavaScript() for child in self.children]) + ']' }
        return '{' + ", ".join( key+": "+str(d[key]) for key in d) + '}'

class Register(Module):
    def __init__(self, name: 'str', type: 'str'):
        Module.__init__(self, name, type, [], [Node('_' + name + '_input')], [Node('_' + name + '_output')])
        self.input = self.inputs[0]
        self.output = self.outputs[0]

class Mux(Component):
    def __init__(self, name: 'str', inputs: 'list[Node]'):
        self.name = name
        self.inputs = inputs
        self.output = Node('_' + name + '_output')
        self.control = Node('_' + name + '_control')
        self.timing = "0 ps"
    def __str__(self):
        return "mux " + self.name
    def translate(self, dx, dy):
        self.x += dx
        self.y += dy
        for node in self.inputs:
            node.translate(dx, dy)
        self.output.translate(dx, dy)
        self.control.translate(dx, dy)
    def autoPlace(self):
        '''automatically place nodes'''
        for i in range(len(self.inputs)):
            self.inputs[i].x = self.x
            self.inputs[i].y = self.height*(i+1)/(len(self.inputs)+1)
        self.output.x = self.x + self.width
        self.output.y = self.y + self.height/2
        self.control.x = self.x + self.width/2
        self.control.y = self.height - (self.height - self.shortHeight)/4
    def toJavaScript(self):
        d = { 'variant': "'Mux'", 'source': self.source, 'timing': "`" + self.timing + "`",
                'x': self.x, 'y': self.y, 'width': self.width, 'height': self.height, 'shortHeight': self.shortHeight }
        return '{' + ", ".join( key+": "+str(d[key]) for key in d) + '}'


'''
Should we have wires containing wire components?

A wire needs to keep track of a tree-like data structure which also has endpoints kept outside the structure.

Wire nodes are copied and unique.
'''

'''
JavaScript wire:
element with x1,y1, x2,y2 and children which are other wires coming after/out.
hovering over an element activates all children and parents.
'''

class Wire(Component):
    ''' src and dst are Nodes. children is a list of Wires. '''
    def __init__(self, src, dst, type="unknown", children=None):
        self.src = src.copy()
        self.dst = dst.copy()
        self.children = children if children != None else []
        self.type = type
        self.source = []
        self.typeSource = []
    def __str__(self):
        return "wire from " + str(self.src) + " to " + str(self.dst)
    def append(self, x, y):
        ''' src -> dst becomes src -> dst -> (x,y).
        returns the wire dst -> (x,y). '''
        node = Node().placeAt(x, y)
        wire = Wire(self.dst, node, self.type)
        self.children.append(wire)
        return wire
    def autoPlace(self):
        midx = (self.src.x + self.dst.x)/2
        midNode1 = Node().placeAt(midx, self.src.y)
        midNode2 = Node().placeAt(midx, self.dst.y)
        self.children = [Wire(midNode1, midNode2, self.type, [Wire(midNode2, self.dst, self.type)])]
        self.dst = midNode1
        return self
    def setSource(self, source):
        assert len(self.children) < 2, "Can only add source to a single wire"
        if len(self.children) == 1:
            self.children[0].setSource(source)
        else:
            self.source = source
        return self
    def translate(self, dx, dy):
        self.src.translate(dx, dy)
        self.dst.translate(dx, dy)
        for child in self.children:
            child.translate(dx, dy)
    def toJavaScript(self):
        d = { 'variant': "'Wire'", 'source': self.source, 'typeSource': self.typeSource, 'type': "`" + self.type + "`",
                'startx': self.src.x, 'starty': self.src.y, 'endx': self.dst.x, 'endy': self.dst.y,
                'children': '[' + ", ".join([child.toJavaScript() for child in self.children]) + ']'}
        return '{' + ", ".join( key+": "+str(d[key]) for key in d) + '}'


ulWidth, ulHeight = 100, 60
ulMuxWidth, ulMuxHeight = 3, 10 #Height of the longer side
ulMuxShortHeight = ulMuxHeight*5/8 #Height of the shorter side
ulAdderWidth, ulAdderHeight = 10, 10
ulConst1Width, ulConst1Height = 10, 5
ulRegWidth, ulRegHeight = 10, 20

#upper left corner Coords
ulMuxC = [3*ulWidth/5 - ulMuxWidth/2, ulHeight/2 - ulMuxHeight/2]
ulRegC = [4*ulWidth/5 - ulRegWidth/2, ulHeight/2 - ulRegHeight/2]
ulConst1C = [ulWidth/5 - ulConst1Width/2, 3*ulHeight/4 - ulConst1Height/2]
ulAdderC = [2*ulWidth/5 - ulAdderWidth/2, 5*ulHeight/8 - ulAdderHeight/2]

uMux = Mux("uMux", [Node("m1"), Node("m2")])
uMux.x, uMux.y, uMux.width, uMux.height, uMux.shortHeight = 0, 0, ulMuxWidth, ulMuxHeight, ulMuxShortHeight
uMux.autoPlace()

uAdder = Function("+", [], [Node("a1"), Node("a2")])
uAdder.x, uAdder.y, uAdder.width, uAdder.height = 0, 0, ulAdderWidth, ulAdderHeight
uAdder.autoPlace()

uConst1 = Function("1'b1", [], [])
uConst1.x, uConst1.y, uConst1.width, uConst1.height = 0, 0, ulConst1Width, ulConst1Height
uConst1.autoPlace()

uReg = Register("count", "Bit#(4)")
uReg.x, uReg.y, uReg.width, uReg.height = 0, 0, ulRegWidth, ulRegHeight
uReg.autoPlace()

u = Module('upper', 'FourBitCounter', [uMux, uAdder, uConst1, uReg], [Node("enable")], [Node("getCount")])

u.x, u.y, u.width, u.height = 0, 0, ulWidth, ulHeight
u.autoPlace()

uAdder.translate(*ulAdderC)
uConst1.translate(*ulConst1C)
uMux.translate(*ulMuxC)
uReg.translate(*ulRegC)

uAdder.timing = "45.36 ps"
uMux.timing = "40.48 ps"
uReg.timing = "23.86 ps"
u.timing = "64.64 ps"

uwire1 = Wire(u.inputs[0], Node().placeAt(ulMuxC[0]/8, u.inputs[0].y), "Bool")
uwire1.append(ulMuxC[0]/8, 7*ulHeight/8).append(ulMuxC[0] + ulMuxWidth/2, 7*ulHeight/8).append(ulMuxC[0] + ulMuxWidth/2, uMux.control.y).append(uMux.control.x, uMux.control.y).setSource([['fourbitcounter', 143, 149]])

uwire2 = Wire(uReg.output, Node().placeAt(ulRegC[0] + ulRegWidth + 5, uReg.output.y), "Bit#(4)")
uwire2.append(u.outputs[0].x, u.outputs[0].y).setSource([['fourbitcounter', 81, 86]])
uwire3 = uwire2.append(ulRegC[0] + ulRegWidth + 5, ulHeight/6).append(ulMuxC[0] - 10, ulHeight/6)
uwire3.append(ulMuxC[0] - 10, uMux.inputs[0].y).append(uMux.inputs[0].x, uMux.inputs[0].y).setSource([['fourbitcounter', 131, 182]])
uwire3.append(ulAdderC[0] - 10, ulHeight/6).append(ulAdderC[0] - 10, uAdder.inputs[0].y).append(uAdder.inputs[0].x, uAdder.inputs[0].y).setSource([['fourbitcounter', 172, 177]])

u.children.extend([ uwire1,
                    Wire(uMux.output, uReg.input, "Bit#(4)").autoPlace().setSource([['fourbitcounter', 131, 182]]),
                    uwire2,
                    Wire(uConst1.output, uAdder.inputs[1], "Bit#(1)").autoPlace().setSource([['fourbitcounter', 180, 181]]),
                    Wire(uAdder.output, uMux.inputs[1], "Bit#(4)").autoPlace().setSource([['fourbitcounter', 172, 181]]) ]) #add wires to u

# organize l
lMux = Mux("lMux", [Node("m1"), Node("m2")])
lMux.x, lMux.y, lMux.width, lMux.height, lMux.shortHeight = 0, 0, ulMuxWidth, ulMuxHeight, ulMuxShortHeight
lMux.inputs[0].placeAt(0, ulMuxHeight/3)
lMux.inputs[1].placeAt(0, 2*ulMuxHeight/3)
lMux.output.placeAt(ulMuxWidth, ulMuxHeight/2)
lMux.control.placeAt(ulMuxWidth/2, ulMuxHeight - (ulMuxHeight-ulMuxShortHeight)/4)

lAdder = Function("+", [], [Node("a1"), Node("a2")])
lAdder.x, lAdder.y, lAdder.width, lAdder.height = 0, 0, ulAdderWidth, ulAdderHeight
lAdder.inputs[0].placeAt(0, ulAdderHeight/3)
lAdder.inputs[1].placeAt(0, 2*ulAdderHeight/3)
lAdder.output.placeAt(ulAdderWidth, ulAdderHeight/2)

lConst1 = Function("1'b1", [], [])
lConst1.x, lConst1.y, lConst1.width, lConst1.height = 0, 0, ulConst1Width, ulConst1Height
lConst1.output.placeAt(ulConst1Width, ulConst1Height/2)

lReg = Register("count", "Bit#(4)")
lReg.x, lReg.y, lReg.width, lReg.height = 0, 0, ulRegWidth, ulRegHeight
lReg.input.placeAt(0, ulRegHeight/2)
lReg.output.placeAt(ulRegWidth, ulRegHeight/2)

l = Module('lower', 'FourBitCounter', [lMux, lAdder, lConst1, lReg], [Node("enable")], [Node("getCount")])

l.x, l.y, l.width, l.height = 0, 0, ulWidth, ulHeight
l.inputs[0].placeAt(0, ulHeight/2)
l.outputs[0].placeAt(ulWidth, ulHeight/2)

lAdder.translate(*ulAdderC)
lConst1.translate(*ulConst1C)
lMux.translate(*ulMuxC)
lReg.translate(*ulRegC)

lAdder.timing = "45.36 ps"
lMux.timing = "40.48 ps"
lReg.timing = "23.86 ps"
l.timing = "64.64 ps"

lwire1 = Wire(l.inputs[0], Node().placeAt(ulMuxC[0]/8, l.inputs[0].y), "Bool")
lwire1.append(ulMuxC[0]/8, 7*ulHeight/8).append(ulMuxC[0] + ulMuxWidth/2, 7*ulHeight/8).append(ulMuxC[0] + ulMuxWidth/2, lMux.control.y).append(lMux.control.x, lMux.control.y).setSource([['fourbitcounter', 143, 149]])

lwire2 = Wire(lReg.output, Node().placeAt(ulRegC[0] + ulRegWidth + 5, lReg.output.y), "Bit#(4)")
lwire2.append(l.outputs[0].x, l.outputs[0].y).setSource([['fourbitcounter', 81, 86]])
lwire3 = lwire2.append(ulRegC[0] + ulRegWidth + 5, ulHeight/6).append(ulMuxC[0] - 10, ulHeight/6)
lwire3.append(ulMuxC[0] - 10, lMux.inputs[0].y).append(lMux.inputs[0].x, lMux.inputs[0].y).setSource([['fourbitcounter', 131, 182]])
lwire3.append(ulAdderC[0] - 10, ulHeight/6).append(ulAdderC[0] - 10, lAdder.inputs[0].y).append(lAdder.inputs[0].x, lAdder.inputs[0].y).setSource([['fourbitcounter', 172, 177]])

l.children.extend([ lwire1,
                    Wire(lMux.output, lReg.input, "Bit#(4)").autoPlace().setSource([['fourbitcounter', 131, 182]]),
                    lwire2,
                    Wire(lConst1.output, lAdder.inputs[1], "Bit#(1)").autoPlace().setSource([['fourbitcounter', 180, 181]]),
                    Wire(lAdder.output, lMux.inputs[1], "Bit#(4)").autoPlace().setSource([['fourbitcounter', 172, 181]]) ]) #add wires to l

mWidth, mHeight = 230, 180
mConcatWidth, mConcatHeight = 10, 10
mAndWidth, mAndHeight = 10, 10
mEqWidth, mEqHeight = 10, 10
mConst3Width, mConst3Height = 10, 5

uC = [5*mWidth/8 - ulWidth/2, mHeight/4 - ulHeight/2]
lC = [3*mWidth/8 - ulWidth/2, 3*mHeight/4 - ulHeight/2]
mConcatC = [15*mWidth/16 - mConcatWidth/2, mHeight/2 - mConcatHeight/2]
mAndC = [3*mWidth/10 - mAndWidth/2, 40]
mEqC = [2*mWidth/10 - mEqWidth/2, 50]
mConst3C = [mWidth/10 - mConst3Width/2, 45]

mConcat = Function("{}", [], [Node("a1"), Node("a2")])
mConcat.x, mConcat.y, mConcat.width, mConcat.height = 0, 0, mConcatWidth, mConcatHeight
mConcat.autoPlace()

mAnd = Function("&&", [], [Node("a1"), Node("a2")])
mAnd.x, mAnd.y, mAnd.width, mAnd.height = 0, 0, mAndWidth, mAndHeight
mAnd.autoPlace()

mEq = Function("==", [], [Node("a1"), Node("a2")])
mEq.x, mEq.y, mEq.width, mEq.height = 0, 0, mEqWidth, mEqHeight
mEq.autoPlace()

mConst3 = Function("4b'15", [], [])
mConst3.x, mConst3.y, mConst3.width, mConst3.height = 0, 0, mConst3Width, mConst3Height
mConst3.autoPlace()

m = Module('TopLevelModule', 'EightBitCounter', [u, l, mConcat, mAnd, mEq, mConst3], [Node("enable")], [Node("getCount")])

m.x, m.y, m.width, m.height = 0, 0, mWidth, mHeight
m.autoPlace()

u.translate(*uC)
l.translate(*lC)
mConcat.translate(*mConcatC)
mAnd.translate(*mAndC)
mEq.translate(*mEqC)
mConst3.translate(*mConst3C)

m.timing = "88.66 ps"
mAnd.timing = "19.74 ps"
mEq.timing = "36.18 ps"

mwire1 = Wire(m.inputs[0], Node().placeAt(mWidth/20, m.inputs[0].y), "Bool")
mwire1.append(l.inputs[0].x/2, m.inputs[0].y).append(l.inputs[0].x/2, l.inputs[0].y).append(l.inputs[0].x, l.inputs[0].y).setSource([['eightbitcounter', 258, 264]])
mwire1.append(mWidth/20, mHeight/8).append(mWidth/6, mHeight/8).append(mWidth/6, mAnd.inputs[0].y).append(mAnd.inputs[0].x, mAnd.inputs[0].y).setSource([['eightbitcounter', 289, 295]])

mwire2 = Wire(l.outputs[0], Node().placeAt(3*mWidth/4, l.outputs[0].y), "Bit#(4)")
mwire3 = mwire2.append(3*mWidth/4, mConcat.inputs[1].y)
mwire3.append(mConcat.inputs[1].x, mConcat.inputs[1].y).setSource([['eightbitcounter', 161, 175]])
mwire3.append(3*mWidth/4, mHeight/2).append(mWidth/8, mHeight/2).append(mWidth/8, mEq.inputs[1].y).append(mEq.inputs[1].x, mEq.inputs[1].y).setSource([['eightbitcounter', 300, 314]])

m.children.extend([ mwire1,
                    Wire(mConst3.output, mEq.inputs[0], "Bit#(4)").autoPlace().setSource([['eightbitcounter', 318, 320]]),
                    mwire2,
                    Wire(mEq.output, mAnd.inputs[1], "Bool").autoPlace().setSource([['eightbitcounter', 299, 321]]),
                    Wire(mAnd.output, u.inputs[0], "Bool").autoPlace().setSource([['eightbitcounter', 289, 321]]),
                    Wire(u.outputs[0], mConcat.inputs[0], "Bit#(4)").autoPlace().setSource([['eightbitcounter', 145, 159]]),
                    Wire(mConcat.output, m.outputs[0], "Bit#(8)").autoPlace().setSource([['eightbitcounter', 144, 176]]) ])

m.source = []
m.typeSource = [['eightbitcounter', 24, 344]]

u.source = [['eightbitcounter', 78, 99]]
u.typeSource = [['fourbitcounter', 0, 204]]

l.source = [['eightbitcounter', 52, 73]]
l.typeSource = [['fourbitcounter', 0, 204]]

mConcat.source = [['eightbitcounter', 144, 176]]
mConcat.typeSource = [] #built-in, no type source
mAnd.source = [['eightbitcounter', 296, 298]]
mAnd.typeSource = []
mEq.source = [['eightbitcounter', 315, 317]]
mEq.typeSource = []
mConst3.source = [['eightbitcounter', 318, 320]]
mConst3.typeSource = []

uAdder.source = [['fourbitcounter', 178, 179]]
uAdder.typeSource = []
uConst1.source = [['fourbitcounter', 180, 181]]
uConst1.typeSource = []
uMux.source = [['fourbitcounter', 139, 150], ['fourbitcounter', 163, 182]] #muxes do not have typeSource
uReg.source = [['fourbitcounter', 27, 50]]
uReg.typeSource = []

lAdder.source = [['fourbitcounter', 178, 179]]
lAdder.typeSource = []
lConst1.source = [['fourbitcounter', 180, 181]]
lConst1.typeSource = []
lMux.source = [['fourbitcounter', 139, 150], ['fourbitcounter', 163, 182]]
lReg.source = [['fourbitcounter', 27, 50]]
lReg.typeSource = []

topLevlLength = 30

m.translate(topLevlLength, 0)

topLevelInput = Wire(Node().placeAt(0, m.inputs[0].y), m.inputs[0], "Bool").setSource([])
topLevelOutput = Wire(m.outputs[0], Node().placeAt(m.outputs[0].x+topLevlLength, m.outputs[0].y), "Bit#(8)").setSource([])


#print(m)
#print(m.toJavaScript())


# Graph drawing algorithms:
# https://en.wikipedia.org/wiki/Layered_graph_drawing

import pathlib

templateFile = pathlib.Path(__file__).with_name('template.html')

template = templateFile.read_text()

template = ",".join([m.toJavaScript(), topLevelInput.toJavaScript(), topLevelOutput.toJavaScript()]).join(template.split("/* Python elements go here */"))

output = pathlib.Path(__file__).with_name('sample.html')
output.open("w").write(template)