import pytest
import anyio


@pytest.fixture(scope="session")
def anyio_backend():
    return 'asyncio'




