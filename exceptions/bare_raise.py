import ast
import sys


class BareRaiseChecker(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.except_depth = 0
        self.issues = []

    def visit_ExceptHandler(self, node):
        self.except_depth += 1
        self.generic_visit(node)
        self.except_depth -= 1

    def visit_Raise(self, node):
        if node.exc is None and self.except_depth == 0:
            self.issues.append((node.lineno, node.col_offset))
        self.generic_visit(node)


def main(filenames):
    exit_status = 0
    for filename in filenames:
        with open(filename, "rb") as f:
            source = f.read()
        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError:
            continue
        checker = BareRaiseChecker(filename)
        checker.visit(tree)
        for lineno, col in checker.issues:
            print(f"{filename}:{lineno}:{col}: bare 'raise' outside except block")
            exit_status = 99

    sys.exit(exit_status)


if __name__ == "__main__":
    main(sys.argv[1:])
