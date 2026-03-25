from fixit.testing import add_lint_rule_tests_to_module
from python.pathlib.always_specify_encoding import AlwaysSpecifyEncodingRule

add_lint_rule_tests_to_module(globals(), [AlwaysSpecifyEncodingRule])
