from fixit.testing import add_lint_rule_tests_to_module
from python.fstrings.fstring_repr import FstringReprRule

add_lint_rule_tests_to_module(globals(), [FstringReprRule])
