"""Ick rule: flag line-continuation backslashes inside textwrap.dedent strings."""
import re
import sys
from pathlib import Path

import libcst as cst
from libcst.metadata import PositionProvider, QualifiedNameProvider


_LINE_CONT_RE = re.compile(r'(\\+)\n')


def _has_line_continuation(raw_value: str) -> bool:
    """Return True if the raw string source has a line-continuation backslash after the first line.

    The pattern ``\"\"\"\\`` (continuation right after the opening triple-quote) is
    explicitly allowed; it's only continuations on subsequent lines that break dedent.
    """
    prefix_len = len(raw_value) - len(raw_value.lstrip("rRbBfFuU"))
    content_start = prefix_len + 3  # skip prefix + opening triple-quote

    for m in _LINE_CONT_RE.finditer(raw_value):
        if len(m.group(1)) % 2 == 0:
            continue
        if m.start() == content_start:
            continue  # """\  at the very start is fine
        return True
    return False


class LineContinuationChecker(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (QualifiedNameProvider, PositionProvider)

    def __init__(self) -> None:
        self.issues: list[int] = []

    def visit_Call(self, node: cst.Call) -> None:
        names = self.get_metadata(QualifiedNameProvider, node.func, set())
        if not any(qn.name == "textwrap.dedent" for qn in names):
            return
        if not node.args:
            return
        arg = node.args[0]
        if arg.keyword is not None:
            return
        str_node = arg.value
        if not isinstance(str_node, cst.SimpleString):
            return
        value = str_node.value
        prefix = value[:len(value) - len(value.lstrip("rRbBfFuU"))]
        prefix_lower = prefix.lower()
        if "r" in prefix_lower:
            return  # raw strings: backslash is literal, not a line continuation
        if "b" in prefix_lower:
            return  # bytes strings: textwrap.dedent doesn't accept bytes
        stripped = value[len(prefix):]
        if not (stripped.startswith('"""') or stripped.startswith("'''")):
            return
        if _has_line_continuation(value):
            pos = self.get_metadata(PositionProvider, node)
            self.issues.append(pos.start.line)


def main() -> None:
    exit_status = 0
    for path_str in sys.argv[1:]:
        path = Path(path_str)
        src = path.read_bytes()
        try:
            module = cst.parse_module(src)
        except cst.ParserSyntaxError:
            continue

        checker = LineContinuationChecker()
        wrapper = cst.metadata.MetadataWrapper(module)
        wrapper.visit(checker)

        for lineno in checker.issues:
            print(f"{path_str}:{lineno}: line-continuation backslash in textwrap.dedent string")
            exit_status = 99

    sys.exit(exit_status)


if __name__ == "__main__":
    main()
