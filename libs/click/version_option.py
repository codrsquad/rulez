"""Ick rule: CLI entry points should use @click.version_option."""
import re
import sys
from pathlib import Path

import libcst as cst

_TARGET_FILENAMES = frozenset({'cli.py', 'cmdline.py', 'main.py', '__main__.py'})
_SKIP_DIRS = frozenset({
    '.git', '.venv', 'venv', 'env', '__pycache__', '.tox', 'node_modules', 'dist', 'build',
})
_VERSION_RE = re.compile(r'^__version__\s*=', re.MULTILINE)


def _decorator_func_name(decorator: cst.Decorator) -> str:
    """Return the callable part as a dotted string, e.g. 'click.group', 'version_option'."""
    node = decorator.decorator
    if isinstance(node, cst.Call):
        node = node.func
    parts = []
    while isinstance(node, cst.Attribute):
        parts.append(node.attr.value)
        node = node.value
    if isinstance(node, cst.Name):
        parts.append(node.value)
    return '.'.join(reversed(parts))


class _Transformer(cst.CSTTransformer):
    """Analyze click imports/usage and add @version_option() where missing."""

    def __init__(self, version_info_available: bool) -> None:
        self._version_info_available = version_info_available
        # Collected during traversal
        self._click_alias: str | None = None   # module alias ('click', 'myalias', …)
        self._imported_names: set[str] = set()  # names from `from click import …`
        self._has_any_click_import = False
        self._has_entry_point = False
        self._has_version_option = False
        # State during transformation
        self._done = False
        self._added_decorator = False

    # ── Import analysis ────────────────────────────────────────────────────────

    def visit_Import(self, node: cst.Import) -> bool | None:
        if isinstance(node.names, cst.ImportStar):
            return None
        for alias in node.names:
            if not (isinstance(alias.name, cst.Name) and alias.name.value == 'click'):
                continue
            self._has_any_click_import = True
            if alias.asname is not None and isinstance(alias.asname, cst.AsName):
                name_node = alias.asname.name
                if isinstance(name_node, cst.Name):
                    self._click_alias = name_node.value
            else:
                self._click_alias = 'click'
        return None

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool | None:
        mod = node.module
        root = mod
        while isinstance(root, cst.Attribute):
            root = root.value
        if not (isinstance(root, cst.Name) and root.value == 'click'):
            return None
        self._has_any_click_import = True
        if not isinstance(node.names, cst.ImportStar):
            for alias in node.names:
                if isinstance(alias.name, cst.Name):
                    self._imported_names.add(alias.name.value)
        return None

    # ── Entry-point detection ──────────────────────────────────────────────────

    def _is_click_entry_point(self, name: str) -> bool:
        parts = name.split('.')
        last = parts[-1]
        if last not in ('command', 'group'):
            return False
        # Qualified: @click.command() / @myalias.command()
        if len(parts) == 2 and self._click_alias and parts[0] == self._click_alias:
            return True
        # Unqualified via from-import: @command() / @group()
        if len(parts) == 1 and last in self._imported_names:
            return True
        return False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool | None:
        for dec in node.decorators:
            name = _decorator_func_name(dec)
            if self._is_click_entry_point(name):
                self._has_entry_point = True
            if 'version_option' in name:
                self._has_version_option = True
        return None

    # ── Transformation ─────────────────────────────────────────────────────────

    def _should_fix(self) -> bool:
        return (
            self._has_any_click_import
            and self._has_entry_point
            and not self._has_version_option
            and self._version_info_available
        )

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if self._done or not self._should_fix():
            return updated_node
        decs = updated_node.decorators
        cmd_idx = next(
            (i for i, d in enumerate(decs)
             if self._is_click_entry_point(_decorator_func_name(d))),
            None,
        )
        if cmd_idx is None:
            return updated_node

        if self._click_alias:
            expr = f"{self._click_alias}.version_option()"
        else:
            expr = "version_option()"

        cmd_dec = decs[cmd_idx]
        new_dec = cst.Decorator(
            decorator=cst.parse_expression(expr),
            leading_lines=(),
            whitespace_after_at=cst.SimpleWhitespace(""),
            trailing_whitespace=cmd_dec.trailing_whitespace,
        )
        new_decs = list(decs[:cmd_idx + 1]) + [new_dec] + list(decs[cmd_idx + 1:])
        self._done = True
        self._added_decorator = True
        return updated_node.with_changes(decorators=new_decs)

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        # Only add a new from-import when there's no module alias and we added a decorator.
        if not self._added_decorator or self._click_alias is not None:
            return updated_node
        # Insert `from click import version_option` after the last import statement.
        last_import_idx = -1
        for i, stmt in enumerate(updated_node.body):
            if isinstance(stmt, cst.SimpleStatementLine):
                if any(isinstance(s, (cst.Import, cst.ImportFrom)) for s in stmt.body):
                    last_import_idx = i
        new_import = cst.parse_statement("from click import version_option\n")
        insert_idx = last_import_idx + 1
        new_body = (
            list(updated_node.body[:insert_idx])
            + [new_import]
            + list(updated_node.body[insert_idx:])
        )
        return updated_node.with_changes(body=tuple(new_body))


def _find_toplevel_package(cli_path: Path) -> Path | None:
    """Find the topmost package directory for cli_path (relative to CWD)."""
    parts = cli_path.parent.parts
    for i in range(len(parts)):
        candidate = Path(*parts[:i + 1])
        if (candidate / '__init__.py').exists():
            return candidate
    return None


def _version_info_available(cli_path: Path) -> bool:
    """Return True if __version__ or version.py is available in the toplevel package."""
    pkg = _find_toplevel_package(cli_path)
    if pkg is None:
        return False
    init = pkg / '__init__.py'
    if init.exists() and _VERSION_RE.search(init.read_text(encoding='utf-8')):
        return True
    if (pkg / 'version.py').exists():
        return True
    return False


def main() -> None:
    root = Path('.')
    for path in root.rglob('*.py'):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.name not in _TARGET_FILENAMES:
            continue

        src = path.read_bytes()
        try:
            module = cst.parse_module(src)
        except cst.ParserSyntaxError:
            continue

        transformer = _Transformer(_version_info_available(path))
        new_module = module.visit(transformer)
        if new_module.bytes != src:
            path.write_bytes(new_module.bytes)

    sys.exit(0)


if __name__ == '__main__':
    main()
