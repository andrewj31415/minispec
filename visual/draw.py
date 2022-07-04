
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
    def toJavaScript(self):
        d = { 'name': "`" + self.name + "`", 'type': "`" + self.type + "`", 'variant': "'Module'", 'source': [],
                'typeSource': [], 'x': self.x, 'y': self.y, 'width': self.width, 'height': self.height,
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
    def toJavaScript(self):
        d = { 'name': "`" + self.name + "`", 'variant': "'Function'", 'source': '[]',
                'typeSource': '[]', 'x': self.x, 'y': self.y, 'width': self.width, 'height': self.height,
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
    def toJavaScript(self):
        d = { 'name': "`" + self.name + "`", 'type': "`" + self.type + "`", 'variant': "'Register'", 'source': [],
                'typeSource': [], 'x': self.x, 'y': self.y, 'width': self.width, 'height': self.height }
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
    def toJavaScript(self):
        d = { 'variant': "'Mux'", 'source': [],
                'x': self.x, 'y': self.y, 'width': self.width, 'height': self.height }
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
    def toJavaScript(self):
        print(self.src)
        print(self.dst)
        d = { 'variant': "'Wire'", 'source': [], 'startx': self.src.x, 'starty': self.src.y,
                'x1': self.x1, 'height': self.height, 'x2': self.x2, 'endx': self.dst.x, 'endy': self.dst.y}
        return '{' + ", ".join( key+": "+str(d[key]) for key in d) + '}'

uMux = Mux("uMux", [Node("m1"), Node("m2")])
uMux.x, uMux.y, uMux.width, uMux.height = 0, 0, 10, 10
uMux.inputs[0].placeAt(0, 3)
uMux.inputs[1].placeAt(0, 7)
uMux.output.placeAt(10, 5)
uMux.control.placeAt(5, 10)

uAdder = Function("+", [], [Node("a1"), Node("a2")])
uAdder.x, uAdder.y, uAdder.width, uAdder.height = 0, 0, 10, 10
uAdder.inputs[0].placeAt(0, 3)
uAdder.inputs[1].placeAt(0, 6)
uAdder.output.placeAt(10, 5)

uConst1 = Function("1'b1", [], [])
uConst1.x, uConst1.y, uConst1.width, uConst1.height = 0, 0, 10, 10
uConst1.output.placeAt(10, 5)

uReg = Register("count", "Bit#(2)")
uReg.x, uReg.y, uReg.width, uReg.height = 0, 0, 10, 10
uReg.input.placeAt(0, 5)
uReg.output.placeAt(10, 5)

u = Module('upper', 'TwoBitCounter', [uMux, uAdder, uConst1, uReg], [Node("enable")], [Node("getCount")])
u.children.extend([ Wire(u.inputs[0], uMux.control), Wire(uMux.output, uReg.input),
                    Wire(uReg.output, u.outputs[0]), Wire(uReg.output, uAdder.inputs[0]),
                    Wire(uConst1.output, uAdder.inputs[1]), Wire(uReg.output, uMux.inputs[0]),
                    Wire(uAdder.output, uMux.inputs[1]) ]) #add wires to u

u.x, u.y, u.width, u.height = 0, 0, 100, 100
u.inputs[0].placeAt(0, 50)
u.outputs[0].placeAt(100, 50)

uAdder.translate(20, 30)
uConst1.translate(20, 70)
uMux.translate(40, 40)
uReg.translate(60, 40)

u.children[4].placeAt(20, 50, 30)
u.children[5].placeAt(45, 40, 55)
u.children[6].placeAt(80, 40, 90)
u.children[7].placeAt(80, 10, 10)
u.children[8].placeAt(5, 70, 15)
u.children[9].placeAt(0, 0, 0)
u.children[10].placeAt(0, 0, 0)







print(u)
print(u.toJavaScript())

'''lMux = Mux("uMux", [Node("m1"), Node("m2")])
lAdder = Function("+", [], [Node("a1"), Node("a2")])
lConst1 = Function("1b'1", [], [])
lReg = Register("count")

l = Module('TwoBitCounter', [lMux, lAdder, lConst1, lReg], [Node("enable")], [Node("getCount")])
l.children.extend([ Wire(l.inputs[0], lMux.control), Wire(lMux.output, lReg.input),
                    Wire(lReg.output, l.outputs[0]), Wire(lReg.output, lAdder.inputs[0]),
                    Wire(lConst1.output, lAdder.inputs[1]), Wire(lReg.output, lMux.inputs[0]),
                    Wire(lAdder.output, lMux.inputs[1]) ]) #add wires to l

m = Module('FourBitCounter', [u, l])'''


import pathlib

templateFile = pathlib.Path(__file__).with_name('template.html')

template = templateFile.read_text()

template = u.toJavaScript().join(template.split("/* Python elements go here */"))

output = pathlib.Path(__file__).with_name('sample.html')
output.open("w").write(template)