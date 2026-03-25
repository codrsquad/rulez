"""Ick rule: replace quoted %s format specs in logging calls with %r."""
import re
import sys
from pathlib import Path

import libcst as cst
from fixit import Invalid, LintRule, Valid
from fixit.api import fixit_bytes, generate_config
from fixit.ftypes import Options, QualifiedRule

LOG_METHODS = frozenset({
    'debug', 'info', 'warning', 'warn', 'error', 'critical', 'exception', 'log',
})

_QUOTED_S = re.compile(r"""'%s'|"%s\"""")


def _fix_string(node: cst.SimpleString) -> cst.SimpleString | None:
    new_value = _QUOTED_S.sub('%r', node.value)
    if new_value == node.value:
        return None
    return node.with_changes(value=new_value)


def _fix_fmt(
    node: cst.SimpleString | cst.FormattedString | cst.ConcatenatedString,
) -> cst.SimpleString | cst.FormattedString | cst.ConcatenatedString | None:
    """Return a fixed node if any quoted %s was found, else None."""
    if isinstance(node, cst.SimpleString):
        return _fix_string(node)
    if isinstance(node, cst.ConcatenatedString):
        new_left = _fix_fmt(node.left)
        new_right = _fix_fmt(node.right)
        if new_left is None and new_right is None:
            return None
        return node.with_changes(
            left=new_left if new_left is not None else node.left,
            right=new_right if new_right is not None else node.right,
        )
    return None


class QuoteRule(LintRule):
    MESSAGE = "Use %r instead of '%s' or \"%s\" in logging format strings"

    VALID = [
        Valid('logger.info("value is %r", x)'),
        Valid('logger.info("value is %s", x)'),
        Valid('print("value is \'%s\'", x)'),
    ]
    INVALID = [
        Invalid(
            """logger.info("value is '%s'", x)""",
            expected_replacement="""logger.info("value is %r", x)""",
        ),
        Invalid(
            """logger.debug('value is "%s"', x)""",
            expected_replacement="""logger.debug('value is %r', x)""",
        ),
        Invalid(
            """logger.info("value is " "'%s'" " end", x)""",
            expected_replacement="""logger.info("value is " "%r" " end", x)""",
        ),
    ]

    def visit_Call(self, node: cst.Call) -> None:
        func = node.func
        if not isinstance(func, cst.Attribute):
            return
        if func.attr.value not in LOG_METHODS:
            return
        if not node.args:
            return

        fmt_arg = node.args[0]
        new_fmt = _fix_fmt(fmt_arg.value)
        if new_fmt is None:
            return

        new_args = (fmt_arg.with_changes(value=new_fmt), *node.args[1:])
        self.report(node, replacement=node.with_changes(args=new_args))


def main() -> None:
    options = Options(rules=[QualifiedRule('libs.logging.quote', 'QuoteRule')])
    for path_str in sys.argv[1:]:
        path = Path(path_str)
        src = path.read_bytes()
        gen = fixit_bytes(path, src, config=generate_config(path, options=options), autofix=True)
        try:
            while True:
                next(gen)
        except StopIteration as e:
            if e.value is not None:
                path.write_bytes(e.value)
    sys.exit(0)


if __name__ == '__main__':
    main()
