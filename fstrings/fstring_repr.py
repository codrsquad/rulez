"""Ick rule: replace {repr(...)} in f-strings with {...!r}."""
import sys
from pathlib import Path

import libcst as cst
from fixit import LintRule, Invalid, Valid


class FstringReprRule(LintRule):
    MESSAGE = "Use {x!r} instead of {repr(x)} in f-strings"

    VALID = [
        Valid("f'{x!r}'"),
        Valid("f'{x}'"),
        Valid("f'{repr}'"),
        Valid("f'{repr(x, y)}'"),
    ]
    INVALID = [
        Invalid(
            "f'{repr(x)}'",
            expected_replacement="f'{x!r}'",
        ),
        Invalid(
            "f'value is {repr(obj)} here'",
            expected_replacement="f'value is {obj!r} here'",
        ),
        Invalid(
            "f'{repr(x):10}'",
            expected_replacement="f'{x!r:10}'",
        ),
    ]

    def visit_FormattedStringExpression(self, node: cst.FormattedStringExpression) -> None:
        expr = node.expression
        if not (
            isinstance(expr, cst.Call)
            and isinstance(expr.func, cst.Name)
            and expr.func.value == 'repr'
            and len(expr.args) == 1
            and not isinstance(expr.args[0].value, cst.StarredElement)
            and expr.args[0].keyword is None
            and expr.args[0].star == ''
        ):
            return
        if node.conversion is not None:
            return
        inner = expr.args[0].value
        new_node = node.with_changes(expression=inner, conversion='r')
        self.report(node, replacement=new_node)


def main():
    from fixit.api import fixit_bytes, generate_config
    from fixit.ftypes import Options, QualifiedRule

    options = Options(rules=[QualifiedRule('fstrings.fstring_repr', 'FstringReprRule')])
    for path_str in sys.argv[1:]:
        path = Path(path_str)
        src = path.read_bytes()
        config = generate_config(path, options=options)
        gen = fixit_bytes(path, src, config=config, autofix=True)
        try:
            while True:
                next(gen)
        except StopIteration as e:
            if e.value is not None:
                path.write_bytes(e.value)
    sys.exit(0)


if __name__ == '__main__':
    main()
