import pytest


@pytest.mark.parametrize('src,expected', [
    pytest.param('import sys\nx = sys.argv[1]', 'single', id='FIXME1'),
    pytest.param('import sys\nx = sys.argv[1:]', 'multiple', id='FIXME2'),
    ('simple', 'unknown'),
])
def test_classify(src, expected):
    pass
