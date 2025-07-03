import ast
import sys
from pathlib import Path

from static_qualname import Env

METHODS_THAT_MODIFY = {
    "insert",
    "append",
}

def main(filenames: list[str]) -> int:
    qualname_env = Env()
    exit_code = 0
    for f in filenames:
        mod = ast.parse(Path(f).read_bytes())
        for stmt in mod.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                if isinstance(stmt.value.func, ast.Attribute):
                    func = stmt.value.func.attr
                    # TODO static-qualname doesn't have a way to feed this one
                    # file to understand from- or as-imports today.
                    if (func in METHODS_THAT_MODIFY and 
                        qualname_env.real_qualname(ast.unparse(stmt.value.func.value))
                        == "sys.path"
                        ):
                        print(f"{f}:{stmt.lineno}:{stmt.col_offset} uses {func} to modify sys.path")
                        exit_code = 99
    return exit_code

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
