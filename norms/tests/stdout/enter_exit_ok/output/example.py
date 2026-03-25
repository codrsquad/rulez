import sys


class RedirectStdout:
    def __enter__(self):
        self._old = sys.stdout
        sys.stdout = self._stream
        return self

    def __exit__(self, *args):
        sys.stdout = self._old
