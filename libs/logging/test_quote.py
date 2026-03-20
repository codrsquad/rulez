from fixit.testing import add_lint_rule_tests_to_module
from python.logs.quote import QuoteRule

add_lint_rule_tests_to_module(globals(), [QuoteRule])
