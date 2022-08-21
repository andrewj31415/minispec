

import os, sys  # see https://stackoverflow.com/questions/16780014/import-file-from-parent-directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parsesynth import *


import pathlib
def pull(name):
    '''reads the text of the given file and returns it'''
    textFile = pathlib.Path(__file__).with_name(name + ".ms")
    text = textFile.read_text()
    return text

#import parsesynth

text = pull('function')
output = parseAndSynth(text, 'f')
expected = Function('f', [], []) #TODO
#assert output.match(expected), "Should give matching hardware description"

'''
Parameterization features to test:
  Multiple parameters
  Parameter overriding, partial overriding, no overriding (overriding 0, some, all parameters)
  Functions with same name but different numbers of parameters (0, 1, >1) should not interfere with each other
  Integer parameter arithmetic, including defining functions with parameters not evaluatable until runtime
  After implementing types/modules:
    custom types/modules, with the same categories as above
'''

text = pull('parameterize')
output = parseAndSynth(text, 'e')
print(output.__repr__())
