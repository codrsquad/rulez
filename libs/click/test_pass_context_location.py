from fixit.testing import add_lint_rule_tests_to_module
from python.click.pass_context_location import PassContextLocationRule

add_lint_rule_tests_to_module(globals(), [PassContextLocationRule])
