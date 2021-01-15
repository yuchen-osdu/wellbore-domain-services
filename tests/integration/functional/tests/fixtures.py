import pytest
from variables import Variables
from ..request_builders.wdms_variables import variables_dict

WDMS_Variables = Variables.from_dict(variables_dict)


@pytest.fixture(scope='session')
def with_wdms_env():
    return WDMS_Variables
