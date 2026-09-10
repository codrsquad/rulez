import src
import src.foo
import src.foo as bar
from src.foo import baz

from . import src
from .src import foo

import foo.src.foo # ok
