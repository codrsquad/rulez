import textwrap


def test_foo():
    result = some_func(
        other_func(
            textwrap.dedent("""
hello
world
""")
        )
    )
