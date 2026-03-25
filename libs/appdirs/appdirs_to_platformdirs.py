"""Ick rule: replace appdirs with platformdirs in imports and dependency files."""
import re
import sys
from pathlib import Path

import libcst as cst
from fixit import Invalid, LintRule, Valid
from fixit.api import fixit_bytes, generate_config
from fixit.ftypes import Options, QualifiedRule

_SKIP_DIRS = frozenset({
    '.git', '.venv', 'venv', 'env', '__pycache__', '.tox', 'node_modules', 'dist', 'build',
})
_DEP_GLOBS = ['requirements*.txt', 'requirements/**/*.txt', 'pyproject.toml', 'setup.cfg']
_APPDIRS_RE = re.compile(r'\bappdirs\b', re.IGNORECASE)


def _has_appdirs_root(node: cst.BaseExpression) -> bool:
    while isinstance(node, cst.Attribute):
        node = node.value
    return isinstance(node, cst.Name) and node.value == 'appdirs'


def _replace_root(node: cst.BaseExpression) -> cst.BaseExpression:
    if isinstance(node, cst.Name):
        return node.with_changes(value='platformdirs')
    if isinstance(node, cst.Attribute):
        return node.with_changes(value=_replace_root(node.value))
    return node


class AppdirsRule(LintRule):
    MESSAGE = "Use platformdirs instead of appdirs"

    VALID = [
        Valid("import platformdirs"),
        Valid("from platformdirs import user_data_dir"),
    ]
    INVALID = [
        Invalid(
            "import appdirs",
            expected_replacement="import platformdirs",
        ),
        Invalid(
            "from appdirs import user_data_dir",
            expected_replacement="from platformdirs import user_data_dir",
        ),
        Invalid(
            "import appdirs as ad",
            expected_replacement="import platformdirs as ad",
        ),
    ]

    def visit_Import(self, node: cst.Import) -> None:
        new_aliases = []
        changed = False
        for alias in node.names:
            if _has_appdirs_root(alias.name):
                new_aliases.append(alias.with_changes(name=_replace_root(alias.name)))
                changed = True
            else:
                new_aliases.append(alias)
        if changed:
            self.report(node, replacement=node.with_changes(names=new_aliases))

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.module is None or not _has_appdirs_root(node.module):
            return
        self.report(node, replacement=node.with_changes(module=_replace_root(node.module)))


def _fix_python_files(root: Path) -> None:
    options = Options(rules=[QualifiedRule('libs.appdirs.appdirs_to_platformdirs', 'AppdirsRule')])
    for path in root.rglob('*.py'):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        src = path.read_bytes()
        config = generate_config(path, options=options)
        gen = fixit_bytes(path, src, config=config, autofix=True)
        try:
            while True:
                next(gen)
        except StopIteration as e:
            if e.value is not None:
                path.write_bytes(e.value)


def _fix_dep_files(root: Path) -> None:
    seen = set()
    for pattern in _DEP_GLOBS:
        for path in root.glob(pattern):
            if path in seen:
                continue
            seen.add(path)
            text = path.read_text()
            new_text = _APPDIRS_RE.sub('platformdirs', text)
            if new_text != text:
                path.write_text(new_text)


def main():
    root = Path('.')
    _fix_python_files(root)
    _fix_dep_files(root)
    sys.exit(0)


if __name__ == '__main__':
    main()
