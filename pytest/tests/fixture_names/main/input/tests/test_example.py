import pytest
from pytest import fixture
import pytest as pt
from pytest import fixture as fx


# Bad: leading underscore with @pytest.fixture (attribute form)
@pytest.fixture
def _plain_fixture():
    pass


# Bad: called with no args
@pytest.fixture()
def _called_fixture():
    pass


# Bad: called with autouse=True
@pytest.fixture(autouse=True)
def _autouse_fixture():
    pass


# Bad: from-import form
@fixture
def _direct_fixture():
    pass


# Bad: aliased module import
@pt.fixture
def _aliased_module_fixture():
    pass


# Bad: aliased direct import
@fx
def _aliased_direct_fixture():
    pass


# Bad: async fixture
@pytest.fixture
async def _async_fixture():
    pass


# Good: no underscore
@pytest.fixture
def plain_fixture():
    pass


# Good: underscore but no fixture decorator
def _helper():
    pass
