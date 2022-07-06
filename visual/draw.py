
''' Component = Module<Array<Component>> + Function<Array<Component>> + Wire '''

''' The ends of wires will be connected to instances of Node. Modules and Functions will
use Node instances to represent inputs and outputs. The Node objects do not appear in the
final JavaScript since they are not needed after computing the final positions of components. 

All of these objects are mutable for placement.

A constant is a function with no arguments.
'''

from click import pass_obj


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
    def translate(self, dx, dy):
        self.x += dx
        self.y += dy

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
                'children': '[' + ", ".join([child.toJavaScript() for child in self.children]) + ']' }
        return '{' + ", ".join( key+": "+str(d[key]) for key in d) + '}'

class Function(Component):
    ''' children is a list of components. '''
    def __init__(self, name: 'str', children: 'list[Component]', inputs: 'list[Node]'):
        self.name = name
        self.children = children
        self.inputs = inputs
        self.output = Node('_' + name + '_output')
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
        d = { 'name': "`" + self.name + "`", 'variant': "'Function'", 'source': self.source,
                'typeSource': self.typeSource, 'x': self.x, 'y': self.y, 'width': self.width, 'height': self.height,
                'children': '[' + ", ".join([child.toJavaScript() for child in self.children]) + ']' }
        return '{' + ", ".join( key+": "+str(d[key]) for key in d) + '}'

class Register(Component):
    def __init__(self, name: 'str', type: 'str'):
        self.name = name
        self.type = type
        self.input = Node('_' + name + '_input')
        self.output = Node('_' + name + '_output')
    def __str__(self):
        return "Register " + self.name
    def translate(self, dx, dy):
        self.x += dx
        self.y += dy
        self.input.translate(dx, dy)
        self.output.translate(dx, dy)
    def autoPlace(self):
        '''automatically place nodes'''
        self.input.x = self.x
        self.input.y = self.y + self.height/2
        self.output.x = self.x + self.width
        self.output.y = self.y + self.height/2
    def toJavaScript(self):
        d = { 'name': "`" + self.name + "`", 'type': "`" + self.type + "`", 'variant': "'Register'", 'source': self.source,
                'typeSource': self.typeSource, 'x': self.x, 'y': self.y, 'width': self.width, 'height': self.height }
        return '{' + ", ".join( key+": "+str(d[key]) for key in d) + '}'

class Mux(Component):
    def __init__(self, name: 'str', inputs: 'list[Node]'):
        self.name = name
        self.inputs = inputs
        self.output = Node('_' + name + '_output')
        self.control = Node('_' + name + '_control')
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
        d = { 'variant': "'Mux'", 'source': self.source,
                'x': self.x, 'y': self.y, 'width': self.width, 'height': self.height, 'shortHeight': self.shortHeight }
        return '{' + ", ".join( key+": "+str(d[key]) for key in d) + '}'

class Wire(Component):
    ''' src and dst are Nodes.
    The wire starts horizontal from src, goes up at x1, across at height, down at x2, and ends at dst.
    src is at (startx, starty) and dst is at (endx, endy). '''
    def __init__(self, src, dst):
        self.src = src
        self.dst = dst
    def __str__(self):
        return "wire from " + str(self.src) + " to " + str(self.dst)
    def translate(self, dx, dy):
        #wires are not responsible for moving their endpoints--the modules/functions do that.
        self.x1 += dx
        self.height += dy
        self.x2 += dx
    def placeAt(self, x1, height, x2):
        self.x1 = x1
        self.height = height
        self.x2 = x2
    def autoPlace(self):
        self.x1 = self.src.x + (self.dst.x - self.src.x)/2
        self.height = (self.src.y + self.dst.y)/2
        self.x2 = self.src.x + (self.dst.x - self.src.x)/2
    def toJavaScript(self):
        print(self.src)
        print(self.dst)
        d = { 'variant': "'Wire'", 'source': [], 'startx': self.src.x, 'starty': self.src.y,
                'x1': self.x1, 'height': self.height, 'x2': self.x2, 'endx': self.dst.x, 'endy': self.dst.y}
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

uReg = Register("count", "Bit#(2)")
uReg.x, uReg.y, uReg.width, uReg.height = 0, 0, ulRegWidth, ulRegHeight
uReg.autoPlace()

u = Module('upper', 'TwoBitCounter', [uMux, uAdder, uConst1, uReg], [Node("enable")], [Node("getCount")])
u.children.extend([ Wire(u.inputs[0], uMux.control), Wire(uMux.output, uReg.input),
                    Wire(uReg.output, u.outputs[0]), Wire(uReg.output, uAdder.inputs[0]),
                    Wire(uConst1.output, uAdder.inputs[1]), Wire(uReg.output, uMux.inputs[0]),
                    Wire(uAdder.output, uMux.inputs[1]) ]) #add wires to u

u.x, u.y, u.width, u.height = 0, 0, ulWidth, ulHeight
u.autoPlace()

uAdder.translate(*ulAdderC)
uConst1.translate(*ulConst1C)
uMux.translate(*ulMuxC)
uReg.translate(*ulRegC)

u.children[4].placeAt(ulMuxC[0]/8, 7*ulHeight/8, ulMuxC[0] + ulMuxWidth/2)
u.children[5].autoPlace()
u.children[6].autoPlace()
u.children[7].placeAt(ulRegC[0] + ulRegWidth + 5, ulHeight/6, ulAdderC[0] - 10)
u.children[8].autoPlace()
u.children[9].placeAt(ulRegC[0] + ulRegWidth + 5, ulHeight/6, ulMuxC[0] - 10)
u.children[10].autoPlace()

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

lReg = Register("count", "Bit#(2)")
lReg.x, lReg.y, lReg.width, lReg.height = 0, 0, ulRegWidth, ulRegHeight
lReg.input.placeAt(0, ulRegHeight/2)
lReg.output.placeAt(ulRegWidth, ulRegHeight/2)

l = Module('lower', 'TwoBitCounter', [lMux, lAdder, lConst1, lReg], [Node("enable")], [Node("getCount")])
l.children.extend([ Wire(l.inputs[0], lMux.control), Wire(lMux.output, lReg.input),
                    Wire(lReg.output, l.outputs[0]), Wire(lReg.output, lAdder.inputs[0]),
                    Wire(lConst1.output, lAdder.inputs[1]), Wire(lReg.output, lMux.inputs[0]),
                    Wire(lAdder.output, lMux.inputs[1]) ]) #add wires to l

l.x, l.y, l.width, l.height = 0, 0, ulWidth, ulHeight
l.inputs[0].placeAt(0, ulHeight/2)
l.outputs[0].placeAt(ulWidth, ulHeight/2)

lAdder.translate(*ulAdderC)
lConst1.translate(*ulConst1C)
lMux.translate(*ulMuxC)
lReg.translate(*ulRegC)

l.children[4].placeAt(ulMuxC[0]/8, 7*ulHeight/8, ulMuxC[0] + ulMuxWidth/2)
l.children[5].autoPlace()
l.children[6].autoPlace()
l.children[7].placeAt(ulRegC[0] + ulRegWidth + 5, ulHeight/6, ulAdderC[0] - 10)
l.children[8].autoPlace()
l.children[9].placeAt(ulRegC[0] + ulRegWidth + 5, ulHeight/6, ulMuxC[0] - 10)
l.children[10].autoPlace()

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

mConst3 = Function("2b'3", [], [])
mConst3.x, mConst3.y, mConst3.width, mConst3.height = 0, 0, mConst3Width, mConst3Height
mConst3.autoPlace()

m = Module('stuff', 'FourBitCounter', [u, l, mConcat, mAnd, mEq, mConst3], [Node("enable")], [Node("getCount")])
m.children.extend([ Wire(m.inputs[0], l.inputs[0]), Wire(m.inputs[0], mAnd.inputs[0]),
                    Wire(mConst3.output, mEq.inputs[0]), Wire(l.outputs[0], mEq.inputs[1]),
                    Wire(mEq.output, mAnd.inputs[1]), Wire(mAnd.output, u.inputs[0]),
                    Wire(u.outputs[0], mConcat.inputs[0]), Wire(l.outputs[0], mConcat.inputs[1]),
                    Wire(mConcat.output, m.outputs[0]) ])

m.x, m.y, m.width, m.height = 0, 0, mWidth, mHeight
m.autoPlace()

u.translate(*uC)
l.translate(*lC)
mConcat.translate(*mConcatC)
mAnd.translate(*mAndC)
mEq.translate(*mEqC)
mConst3.translate(*mConst3C)

m.children[6].autoPlace()
m.children[7].placeAt(mWidth/20, mHeight/8, mWidth/6)
m.children[8].autoPlace()
m.children[9].placeAt(3*mWidth/4, mHeight/2, mWidth/8)
m.children[10].autoPlace()
m.children[11].autoPlace()
m.children[12].autoPlace()
m.children[13].autoPlace()
m.children[14].autoPlace()

m.source = []
m.typeSource = [['fourbitcounter', 22, 338]]
u.source = [['fourbitcounter', 74, 94]]
u.typeSource = [['twobitcounter', 0, 203]]
l.source = [['fourbitcounter', 49, 69]]
l.typeSource = [['twobitcounter', 0, 203]]

mConcat.source = [['fourbitcounter', 139, 171]]
mConcat.typeSource = [] #built-in, no type source
mAnd.source = [['fourbitcounter', 291, 293]]
mAnd.typeSource = []
mEq.source = [['fourbitcounter', 310, 312]]
mEq.typeSource = []
mConst3.source = [['fourbitcounter', 313, 314]]
mConst3.typeSource = []

uAdder.source = [['twobitcounter', 177, 178]]
uAdder.typeSource = []
uConst1.source = [['twobitcounter', 179, 180]]
uConst1.typeSource = []
uMux.source = [['twobitcounter', 138, 149], ['twobitcounter', 162, 181]] #muxes do not have typeSource
uReg.source = [['twobitcounter', 26, 49]]
uReg.typeSource = []

lAdder.source = [['twobitcounter', 177, 178]]
lAdder.typeSource = []
lConst1.source = [['twobitcounter', 179, 180]]
lConst1.typeSource = []
lMux.source = [['twobitcounter', 138, 149], ['twobitcounter', 162, 181]]
lReg.source = [['twobitcounter', 26, 49]]
lReg.typeSource = []

print(m)
print(m.toJavaScript())

# Graph drawing algorithms:
# https://en.wikipedia.org/wiki/Layered_graph_drawing

import pathlib

templateFile = pathlib.Path(__file__).with_name('template.html')

template = templateFile.read_text()

template = m.toJavaScript().join(template.split("/* Python elements go here */"))

output = pathlib.Path(__file__).with_name('sample.html')
output.open("w").write(template)