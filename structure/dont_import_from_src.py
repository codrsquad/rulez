import ast
import sys
import re

from pathlib import Path

SRC_PREFIX = re.compile(r'^src(\..*)?$')

def main(filenames: list[str]) -> int:
    exit_code = 0
    for f in filenames:
        mod = ast.parse(Path(f).read_bytes())
        for stmt in mod.body:
            if isinstance(stmt, ast.Import):
                for name in stmt.names:
                    if SRC_PREFIX.fullmatch(name.name):
                        print(f"{f}:{name.lineno}:{name.col_offset} imports from `src`")
                        exit_code = 99
            elif isinstance(stmt, ast.ImportFrom):
                if stmt.module is None:
                    for name in stmt.names:
                        if SRC_PREFIX.fullmatch(name.name):
                            print(f"{f}:{name.lineno}:{name.col_offset} imports from `src`")
                            exit_code = 99
                elif SRC_PREFIX.fullmatch(stmt.module):
                    print(f"{f}:{stmt.lineno}:{stmt.col_offset} imports from `src`")
                    exit_code = 99
    return exit_code

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

