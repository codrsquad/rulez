import sys
import contextlib


@contextlib.contextmanager
def redirect():
    old = sys.stdout
    sys.stdout = open('log.txt', 'w')
    try:
        yield
    finally:
        sys.stdout = old
