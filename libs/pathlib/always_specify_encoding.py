"""Ick rule: .read_text() and .write_text() must specify encoding explicitly."""
import sys
from pathlib import Path

import libcst as cst
from fixit import Invalid, LintRule, Valid
from fixit.api import fixit_bytes, generate_config
from fixit.ftypes import Options, QualifiedRule

# read_text(encoding, errors)  -- first positional is encoding
# write_text(data, encoding, errors) -- first positional is data, second is encoding
_ENCODING_POSITIONAL_INDEX = {'read_text': 0, 'write_text': 1}


def _needs_encoding(node: cst.Call) -> bool:
    func = node.func
    if not isinstance(func, cst.Attribute):
        return False
    method = func.attr.value
    if method not in _ENCODING_POSITIONAL_INDEX:
        return False
    if any(a.keyword is not None and a.keyword.value == 'encoding' for a in node.args):
        return False
    positional_count = sum(1 for a in node.args if a.keyword is None)
    return positional_count <= _ENCODING_POSITIONAL_INDEX[method]


def _add_encoding(node: cst.Call) -> cst.Call:
    new_args = list(node.args)
    if new_args:
        new_args[-1] = new_args[-1].with_changes(
            comma=cst.Comma(whitespace_after=cst.SimpleWhitespace(' '))
        )
    new_args.append(cst.Arg(
        keyword=cst.Name('encoding'),
        value=cst.SimpleString("'utf-8'"),
        equal=cst.AssignEqual(
            whitespace_before=cst.SimpleWhitespace(''),
            whitespace_after=cst.SimpleWhitespace(''),
        ),
    ))
    return node.with_changes(args=new_args)


class AlwaysSpecifyEncodingRule(LintRule):
    MESSAGE = "specify encoding= explicitly; default is platform-dependent"

    VALID = [
        Valid("p.read_text(encoding='utf-8')"),
        Valid("p.read_text('utf-8')"),
        Valid("p.write_text('hello', encoding='utf-8')"),
        Valid("p.write_text('hello', 'utf-8')"),
    ]
    INVALID = [
        Invalid(
            "p.read_text()",
            expected_replacement="p.read_text(encoding='utf-8')",
        ),
        Invalid(
            "p.read_text(errors='replace')",
            expected_replacement="p.read_text(errors='replace', encoding='utf-8')",
        ),
        Invalid(
            "p.write_text('hello')",
            expected_replacement="p.write_text('hello', encoding='utf-8')",
        ),
        Invalid(
            "p.write_text('hello', errors='replace')",
            expected_replacement="p.write_text('hello', errors='replace', encoding='utf-8')",
        ),
    ]

    def visit_Call(self, node: cst.Call) -> None:
        if _needs_encoding(node):
            self.report(node, replacement=_add_encoding(node))


def main() -> None:
    options = Options(rules=[QualifiedRule('libs.pathlib.always_specify_encoding', 'AlwaysSpecifyEncodingRule')])
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
