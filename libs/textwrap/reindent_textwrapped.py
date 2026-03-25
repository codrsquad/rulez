"""Ick rule: normalize indentation inside textwrap.dedent() strings."""
import sys
from pathlib import Path
from typing import Optional

import libcst as cst
from libcst.metadata import PositionProvider


def _triple_quote(value: str) -> Optional[str]:
    """Return the triple-quote style if the string is triple-quoted, else None."""
    stripped = value.lstrip("rRbBfFuU")
    for q in ('"""', "'''"):
        if stripped.startswith(q):
            return q
    return None


def _is_textwrap_dedent(node: cst.Call) -> bool:
    func = node.func
    return (
        isinstance(func, cst.Attribute)
        and isinstance(func.value, cst.Name)
        and func.value.value == "textwrap"
        and isinstance(func.attr, cst.Name)
        and func.attr.value == "dedent"
    )


def _get_string_arg(node: cst.Call) -> Optional[cst.SimpleString]:
    if len(node.args) != 1:
        return None
    arg = node.args[0]
    if arg.keyword is not None:
        return None
    if not isinstance(arg.value, cst.SimpleString):
        return None
    return arg.value


def _leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _reindent(value: str, quote: str, correct_indent: str, stmt_indent: str) -> Optional[str]:
    """Return new string value with corrected indentation, or None if already correct."""
    prefix_len = len(value) - len(value.lstrip("rRbBfFuU"))
    prefix = value[:prefix_len]
    content = value[prefix_len + len(quote): -len(quote)]

    if "\n" not in content:
        return None

    lines = content.split("\n")
    has_leading_newline = lines[0] == ""
    has_backslash = lines[0] == "\\"

    if has_leading_newline or has_backslash:
        content_lines = lines[1:-1]
    else:
        content_lines = lines[:-1]

    non_empty = [l for l in content_lines if l.strip()]
    if not non_empty:
        return None

    current_min = min(_leading_spaces(l) for l in non_empty)
    correct_len = len(correct_indent)

    if current_min == correct_len:
        return None

    def fix_line(line: str) -> str:
        if not line.strip():
            return ""
        stripped = line[current_min:]
        return correct_indent + stripped

    if has_leading_newline or has_backslash:
        new_lines = [lines[0]]
        for line in lines[1:-1]:
            new_lines.append(fix_line(line))
        new_lines.append(stmt_indent)
    else:
        new_lines = []
        for line in lines[:-1]:
            new_lines.append(fix_line(line))
        new_lines.append(stmt_indent)

    new_content = "\n".join(new_lines)
    return prefix + quote + new_content + quote


class ReindentTextwrappedTransformer(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, module: cst.Module, src_lines: list[str]) -> None:
        self._module = module
        self._src_lines = src_lines

    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        if not _is_textwrap_dedent(updated_node):
            return updated_node
        str_node = _get_string_arg(updated_node)
        if str_node is None:
            return updated_node
        quote = _triple_quote(str_node.value)
        if quote is None:
            return updated_node

        pos = self.get_metadata(PositionProvider, original_node)
        src_line = self._src_lines[pos.start.line - 1]
        stmt_indent = " " * _leading_spaces(src_line)
        correct_indent = stmt_indent + self._module.default_indent

        new_value = _reindent(str_node.value, quote, correct_indent, stmt_indent)
        if new_value is None:
            return updated_node

        new_str = str_node.with_changes(value=new_value)
        new_arg = updated_node.args[0].with_changes(value=new_str)
        return updated_node.with_changes(args=[new_arg])


def main() -> None:
    for path_str in sys.argv[1:]:
        path = Path(path_str)
        src = path.read_bytes()
        module = cst.parse_module(src)
        src_lines = src.decode(module.encoding).splitlines()
        wrapper = cst.metadata.MetadataWrapper(module)
        transformer = ReindentTextwrappedTransformer(module, src_lines)
        new_module = wrapper.visit(transformer)
        if new_module.bytes != src:
            path.write_bytes(new_module.bytes)
    sys.exit(0)


if __name__ == "__main__":
    main()
