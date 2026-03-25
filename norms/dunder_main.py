"""Ick rule: replace unconditional module-level main() calls with if __name__ == '__main__': block."""
import sys
from pathlib import Path

import libcst as cst
from fixit import Invalid, LintRule, Valid


def _is_main_call(stmt: cst.BaseStatement) -> bool:
    if not isinstance(stmt, cst.SimpleStatementLine):
        return False
    if len(stmt.body) != 1:
        return False
    body_item = stmt.body[0]
    if not isinstance(body_item, cst.Expr):
        return False
    call = body_item.value
    return (
        isinstance(call, cst.Call)
        and isinstance(call.func, cst.Name)
        and call.func.value == 'main'
    )


def _make_if_main(stmt: cst.SimpleStatementLine) -> cst.If:
    inner = stmt.with_changes(leading_lines=[])
    return cst.If(
        test=cst.Comparison(
            left=cst.Name("__name__"),
            comparisons=[
                cst.ComparisonTarget(
                    operator=cst.Equal(
                        whitespace_before=cst.SimpleWhitespace(" "),
                        whitespace_after=cst.SimpleWhitespace(" "),
                    ),
                    comparator=cst.SimpleString('"__main__"'),
                ),
            ],
        ),
        body=cst.IndentedBlock(body=[inner]),
        leading_lines=stmt.leading_lines,
    )


class DunderMainRule(LintRule):
    MESSAGE = "Unconditional main() call should be guarded with `if __name__ == '__main__':`"

    VALID = [
        Valid(
            """
            def main():
                pass

            if __name__ == "__main__":
                main()
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            def main():
                pass

            main()
            """,
            expected_replacement="""
            def main():
                pass

            if __name__ == "__main__":
                main()
            """,
        ),
        Invalid(
            """
            def main(args):
                pass

            main(sys.argv[1:])
            """,
            expected_replacement="""
            def main(args):
                pass

            if __name__ == "__main__":
                main(sys.argv[1:])
            """,
        ),
    ]

    def visit_Module(self, node: cst.Module) -> None:
        for stmt in node.body:
            if _is_main_call(stmt):
                self.report(stmt, replacement=_make_if_main(stmt))


def main() -> None:
    from fixit.api import fixit_bytes, generate_config
    from fixit.ftypes import Options, QualifiedRule

    options = Options(rules=[QualifiedRule('norms.dunder_main', 'DunderMainRule')])
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
