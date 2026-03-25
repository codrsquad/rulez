from fixit.testing import add_lint_rule_tests_to_module
from python.norms.dunder_main import DunderMainRule

add_lint_rule_tests_to_module(globals(), [DunderMainRule])
