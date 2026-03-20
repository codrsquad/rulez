"""Ick rule: add FIXME ids to pytest.mark.parametrize tuples containing multiline strings."""
import ast
import sys
from pathlib import Path

import libcst as cst
from fixit import Invalid, LintRule, Valid


def _is_multiline_string(node: cst.BaseExpression) -> bool:
    if isinstance(node, cst.SimpleString):
        try:
            val = ast.literal_eval(node.value)
            return isinstance(val, (str, bytes)) and b'\n' in (
                val if isinstance(val, bytes) else val.encode()
            )
        except Exception:
            return False
    if isinstance(node, cst.ConcatenatedString):
        return _is_multiline_string(node.left) or _is_multiline_string(node.right)
    return False


def _is_pytest_param(node: cst.BaseExpression) -> bool:
    return (
        isinstance(node, cst.Call)
        and isinstance(node.func, cst.Attribute)
        and node.func.attr.value == 'param'
        and isinstance(node.func.value, cst.Name)
        and node.func.value.value == 'pytest'
    )


def _is_parametrize_call(call: cst.Call) -> bool:
    func = call.func
    return (
        isinstance(func, cst.Attribute)
        and func.attr.value == 'parametrize'
        and isinstance(func.value, cst.Attribute)
        and func.value.attr.value == 'mark'
    )


def _make_pytest_param(tuple_node: cst.Tuple, fixme_id: str) -> cst.Call:
    args = [
        cst.Arg(value=elem.value).with_changes(
            comma=cst.Comma(whitespace_after=cst.SimpleWhitespace(' '))
        )
        for elem in tuple_node.elements
    ]
    id_arg = cst.Arg(
        keyword=cst.Name('id'),
        value=cst.SimpleString(f"'{fixme_id}'"),
        equal=cst.AssignEqual(
            whitespace_before=cst.SimpleWhitespace(''),
            whitespace_after=cst.SimpleWhitespace(''),
        ),
    )
    return cst.Call(
        func=cst.Attribute(value=cst.Name('pytest'), attr=cst.Name('param')),
        args=[*args, id_arg],
    )


def _replace_cases(call: cst.Call) -> cst.Call | None:
    """Return a new Call with qualifying tuples replaced, or None if no changes."""
    if not _is_parametrize_call(call) or len(call.args) < 2:
        return None
    cases = call.args[1].value
    if not isinstance(cases, cst.List):
        return None

    fixme_counter = 0
    new_elements = []
    changed = False
    for element in cases.elements:
        val = element.value
        if (
            isinstance(val, cst.Tuple)
            and not _is_pytest_param(val)
            and any(_is_multiline_string(e.value) for e in val.elements)
        ):
            fixme_counter += 1
            new_elements.append(element.with_changes(value=_make_pytest_param(val, f'FIXME{fixme_counter}')))
            changed = True
        else:
            new_elements.append(element)

    if not changed:
        return None
    new_cases = cases.with_changes(elements=new_elements)
    return call.with_changes(
        args=[call.args[0], call.args[1].with_changes(value=new_cases), *call.args[2:]]
    )


class ParametrizeIdsRule(LintRule):
    MESSAGE = "pytest.mark.parametrize tuple with multiline string should use pytest.param with an id"

    VALID = [
        Valid(
            """
            @pytest.mark.parametrize('x', [
                ('simple',),
            ])
            def test_foo(x): pass
            """
        ),
        Valid(
            """
            @pytest.mark.parametrize('x', [
                pytest.param('hello\\nworld', id='my_id'),
            ])
            def test_foo(x): pass
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            @pytest.mark.parametrize('x,y', [
                ('hello\\nworld', 1),
                ('simple', 2),
                ('bar\\nbaz', 3),
            ])
            def test_foo(x, y): pass
            """,
            expected_replacement="""
            @pytest.mark.parametrize('x,y', [
                pytest.param('hello\\nworld', 1, id='FIXME1'),
                ('simple', 2),
                pytest.param('bar\\nbaz', 3, id='FIXME2'),
            ])
            def test_foo(x, y): pass
            """,
        ),
    ]

    def visit_Call(self, node: cst.Call) -> None:
        new_node = _replace_cases(node)
        if new_node is not None:
            self.report(node, replacement=new_node)


def main():
    from fixit.api import fixit_bytes, generate_config
    from fixit.ftypes import Options, QualifiedRule

    options = Options(rules=[QualifiedRule('pytest.parametrize_ids', 'ParametrizeIdsRule')])
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
