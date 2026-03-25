import pytest


@pytest.mark.parametrize('src,expected', [
    ('import sys\nx = sys.argv[1]', 'single'),
    ('import sys\nx = sys.argv[1:]', 'multiple'),
    ('simple', 'unknown'),
])
def test_classify(src, expected):
    pass
