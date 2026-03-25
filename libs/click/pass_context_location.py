"""Ick rule: @click.pass_context must be the last (innermost) decorator."""
import sys
from pathlib import Path

import libcst as cst
from fixit import Invalid, LintRule, Valid


def _is_pass_context(decorator: cst.Decorator) -> bool:
    dec = decorator.decorator
    if isinstance(dec, cst.Attribute):
        return (
            isinstance(dec.value, cst.Name)
            and dec.value.value == 'click'
            and dec.attr.value == 'pass_context'
        )
    if isinstance(dec, cst.Name):
        return dec.value == 'pass_context'
    return False


class PassContextLocationRule(LintRule):
    MESSAGE = "@click.pass_context must be the last decorator"

    VALID = [
        Valid(
            """
            @click.command()
            @click.option('--name')
            @click.pass_context
            def cmd(ctx, name): pass
            """
        ),
        Valid(
            """
            @click.command()
            @click.pass_context
            def cmd(ctx): pass
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            @click.command()
            @click.pass_context
            @click.option('--name')
            def cmd(ctx, name): pass
            """,
            expected_replacement="""
            @click.command()
            @click.option('--name')
            @click.pass_context
            def cmd(ctx, name): pass
            """,
        ),
    ]

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        decs = node.decorators
        if len(decs) < 2:
            return
        pc_indices = [i for i, d in enumerate(decs) if _is_pass_context(d)]
        if not pc_indices:
            return
        pc_idx = pc_indices[0]
        if pc_idx == len(decs) - 1:
            return
        pc_dec = decs[pc_idx]
        new_decs = list(decs[:pc_idx]) + list(decs[pc_idx + 1:]) + [pc_dec]
        self.report(node, replacement=node.with_changes(decorators=new_decs))


def main():
    from fixit.api import fixit_bytes, generate_config
    from fixit.ftypes import Options, QualifiedRule

    options = Options(rules=[QualifiedRule('libs.click.pass_context_location', 'PassContextLocationRule')])
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
