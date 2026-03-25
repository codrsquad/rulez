"""Ick rule: sys.stdout must only be reassigned via a context manager."""
import sys
from pathlib import Path

import libcst as cst
import libcst.metadata as meta


def _is_sys_stdout(node: cst.BaseExpression) -> bool:
    return (
        isinstance(node, cst.Attribute)
        and isinstance(node.value, cst.Name)
        and node.value.value == 'sys'
        and node.attr.value == 'stdout'
    )


def _is_cm_func(node: cst.FunctionDef) -> bool:
    if node.name.value in ('__enter__', '__exit__'):
        return True
    for dec in node.decorators:
        d = dec.decorator
        if isinstance(d, cst.Name) and d.value == 'contextmanager':
            return True
        if (
            isinstance(d, cst.Attribute)
            and isinstance(d.value, cst.Name)
            and d.value.value == 'contextlib'
            and d.attr.value == 'contextmanager'
        ):
            return True
    return False


class _Visitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (meta.PositionProvider,)

    def __init__(self) -> None:
        self._cm_stack: list[bool] = []
        self.violations: list[int] = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        self._cm_stack.append(_is_cm_func(node))

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:
        self._cm_stack.pop()

    def _check(self, node: cst.CSTNode, target: cst.BaseExpression) -> None:
        if not _is_sys_stdout(target):
            return
        if any(self._cm_stack):
            return
        pos = self.get_metadata(meta.PositionProvider, node)
        self.violations.append(pos.start.line)

    def visit_Assign(self, node: cst.Assign) -> None:
        for t in node.targets:
            self._check(node, t.target)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if node.value is not None:
            self._check(node, node.target)


def check_file(path: Path) -> list[int]:
    src = path.read_bytes()
    try:
        tree = cst.parse_module(src)
    except cst.ParserSyntaxError:
        return []
    wrapper = meta.MetadataWrapper(tree)
    visitor = _Visitor()
    wrapper.visit(visitor)
    return visitor.violations


def main() -> None:
    found_any = False
    for path_str in sys.argv[1:]:
        path = Path(path_str)
        for line_no in check_file(path):
            print(f'{path}:{line_no}: assign to sys.stdout directly; use a context manager')
            found_any = True
    sys.exit(99 if found_any else 0)


if __name__ == '__main__':
    main()
