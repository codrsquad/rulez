import sys

sys.path.insert(0, "/foo")
sys.path.append("/bar")
sys.path.index("/bar")

from sys import path as baz

baz.insert(0, "/foo")
baz.index("/foo")

import sys as frob

frob.path.insert(0, "/foo")
frob.path.index("/foo")
