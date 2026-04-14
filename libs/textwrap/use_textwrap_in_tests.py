"""Ick rule: wrap left-margin multiline strings in test files with textwrap.dedent."""
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


def _has_prefix(value: str) -> bool:
    return value[0].lower() in "rbufe"


def _split_content(value: str, quote: str) -> tuple[str, str, str]:
    """Return (prefix, content, quote) where content is between the triple quotes."""
    prefix_len = len(value) - len(value.lstrip("rRbBfFuU"))
    prefix = value[:prefix_len]
    content = value[prefix_len + len(quote): -len(quote)]
    return prefix, content, quote


def _content_lines_at_margin(content: str) -> bool:
    """Return True if any non-empty content line has 0 leading spaces."""
    lines = content.split("\n")
    start = 1 if lines[0] in ("", "\\") else 0
    for line in lines[start:-1]:
        if line and not line[0].isspace():
            return True
    return False


def _is_textwrap_dedent(node: cst.Call) -> bool:
    func = node.func
    return (
        isinstance(func, cst.Attribute)
        and isinstance(func.value, cst.Name)
        and func.value.value == "textwrap"
        and isinstance(func.attr, cst.Name)
        and func.attr.value == "dedent"
    )


def _leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _reindent_content(content: str, correct_indent: str, stmt_indent: str) -> str:
    """Re-indent string content. Returns new content between triple quotes."""
    lines = content.split("\n")
    has_leading_newline = lines[0] == ""

    if has_leading_newline:
        new_lines = [""]
        for line in lines[1:-1]:
            if line.strip():
                new_lines.append(correct_indent + line.lstrip())
            else:
                new_lines.append("")
        new_lines.append(stmt_indent)
        return "\n".join(new_lines)
    else:
        # Content starts immediately after """, insert \\\n
        new_lines = []
        start_idx = 1 if lines[0] == "\\" else 0
        for line in lines[start_idx:-1]:
            if line.strip():
                new_lines.append(correct_indent + line.lstrip())
            else:
                new_lines.append("")
        return "\\\n" + "\n".join(new_lines) + "\n" + stmt_indent


class UseTextwrapTransformer(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, module: cst.Module, src_lines: list[str]) -> None:
        self._module = module
        self._src_lines = src_lines
        self.needs_import = False
        self._has_textwrap_import = False
        self._docstring_ids: set[int] = set()
        self._in_dedent_depth = 0

    def _collect_docstring(self, body: tuple) -> None:
        if not body:
            return
        first = body[0]
        if isinstance(first, cst.SimpleStatementLine) and len(first.body) == 1:
            stmt = first.body[0]
            if isinstance(stmt, cst.Expr) and isinstance(stmt.value, cst.SimpleString):
                self._docstring_ids.add(id(stmt.value))

    def visit_Module(self, node: cst.Module) -> Optional[bool]:
        self._collect_docstring(node.body)
        return True

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        self._collect_docstring(node.body.body)
        return True

    def visit_ClassDef(self, node: cst.ClassDef) -> Optional[bool]:
        self._collect_docstring(node.body.body)
        return True

    def visit_Call(self, node: cst.Call) -> Optional[bool]:
        if _is_textwrap_dedent(node):
            self._in_dedent_depth += 1
        return True

    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        if _is_textwrap_dedent(original_node):
            self._in_dedent_depth -= 1
        return updated_node

    def visit_Import(self, node: cst.Import) -> Optional[bool]:
        names = node.names
        if isinstance(names, cst.ImportStar):
            return True
        for alias in names:
            name = alias.name
            if isinstance(name, cst.Name) and name.value == "textwrap":
                self._has_textwrap_import = True
        return True

    def leave_SimpleString(
        self, original_node: cst.SimpleString, updated_node: cst.SimpleString
    ) -> cst.BaseExpression:
        if id(original_node) in self._docstring_ids:
            return updated_node
        if self._in_dedent_depth > 0:
            return updated_node
        value = updated_node.value
        quote = _triple_quote(value)
        if quote is None:
            return updated_node
        if _has_prefix(value):
            return updated_node

        prefix, content, _ = _split_content(value, quote)
        if "\n" not in content:
            return updated_node
        if not _content_lines_at_margin(content):
            return updated_node

        pos = self.get_metadata(PositionProvider, original_node)
        src_line = self._src_lines[pos.start.line - 1]
        stmt_indent = " " * _leading_spaces(src_line)
        if not stmt_indent:
            return updated_node

        correct_indent = stmt_indent

        new_content = _reindent_content(content, correct_indent, stmt_indent)
        new_value = prefix + quote + new_content + quote
        new_string = updated_node.with_changes(value=new_value)
        self.needs_import = True
        return cst.Call(
            func=cst.Attribute(
                value=cst.Name("textwrap"),
                attr=cst.Name("dedent"),
            ),
            args=[cst.Arg(value=new_string)],
        )

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        if not self.needs_import or self._has_textwrap_import:
            return updated_node
        import_stmt = cst.parse_statement("import textwrap\n")
        body = list(updated_node.body)
        # Find insertion point: after last existing import
        insert_at = 0
        for i, stmt in enumerate(body):
            if isinstance(stmt, cst.SimpleStatementLine):
                if any(isinstance(s, (cst.Import, cst.ImportFrom)) for s in stmt.body):
                    insert_at = i + 1
        body.insert(insert_at, import_stmt)
        # Ensure 2 blank lines before the next non-import statement
        next_idx = insert_at + 1
        if next_idx < len(body):
            next_stmt = body[next_idx]
            if hasattr(next_stmt, "leading_lines"):
                if len(next_stmt.leading_lines) < 2:
                    body[next_idx] = next_stmt.with_changes(
                        leading_lines=[cst.EmptyLine(), cst.EmptyLine()]
                    )
        return updated_node.with_changes(body=body)


def main() -> None:
    for path_str in sys.argv[1:]:
        path = Path(path_str)
        src = path.read_bytes()
        module = cst.parse_module(src)
        src_lines = src.decode(module.encoding).splitlines()
        wrapper = cst.metadata.MetadataWrapper(module)
        transformer = UseTextwrapTransformer(module, src_lines)
        new_module = wrapper.visit(transformer)
        if new_module.bytes != src:
            path.write_bytes(new_module.bytes)
    sys.exit(0)


if __name__ == "__main__":
    main()
