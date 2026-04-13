import ast
import sys


class FixtureNameChecker(ast.NodeVisitor):
    def __init__(self, filename, source_lines):
        self.filename = filename
        self.source_lines = source_lines
        self.issues = []
        self.pytest_aliases: set[str] = set()   # names where name.fixture is the decorator
        self.fixture_aliases: set[str] = set()  # names that *are* pytest.fixture

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name == "pytest":
                self.pytest_aliases.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module == "pytest":
            for alias in node.names:
                if alias.name == "fixture":
                    self.fixture_aliases.add(alias.asname or alias.name)
        self.generic_visit(node)

    def _is_fixture_decorator(self, decorator):
        # Unwrap call: @pytest.fixture() or @pytest.fixture(autouse=True)
        if isinstance(decorator, ast.Call):
            decorator = decorator.func
        # @pytest.fixture  or  @pt.fixture
        if (
            isinstance(decorator, ast.Attribute)
            and decorator.attr == "fixture"
            and isinstance(decorator.value, ast.Name)
            and decorator.value.id in self.pytest_aliases
        ):
            return True
        # @fixture  or  @fx
        if isinstance(decorator, ast.Name) and decorator.id in self.fixture_aliases:
            return True
        return False

    def _check_function(self, node):
        if node.name.startswith("_") and any(
            self._is_fixture_decorator(d) for d in node.decorator_list
        ):
            # Find the name's column in the source line — more reliable than +4
            # and handles 'async def' correctly (col_offset points to 'async').
            line = self.source_lines[node.lineno - 1]
            name_col = line.index(node.name, node.col_offset)
            self.issues.append((node.lineno, name_col, node.name))

    def visit_FunctionDef(self, node):
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self._check_function(node)
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
        source_lines = source.decode("utf-8", errors="replace").splitlines()
        checker = FixtureNameChecker(filename, source_lines)
        checker.visit(tree)
        for lineno, col, name in checker.issues:
            print(
                f"{filename}:{lineno}:{col}: no need to make things look private in tests: '{name}'"
            )
            exit_status = 99
    sys.exit(exit_status)


if __name__ == "__main__":
    main(sys.argv[1:])
