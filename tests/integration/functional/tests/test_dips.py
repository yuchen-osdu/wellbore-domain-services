# Copyright 2021 Schlumberger
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
from .fixtures import with_wdms_env
from ..request_builders.wdms.crud.dips import *
from jsonschema import validate

from ..request_builders.wdms.crud.log import build_request_get_log

new_parameters_env = {'authorityKind': 'slb',
                      'prefix_data_entity_name': 'wdms_e2e_osdu' }

#it will only be run once
@pytest.fixture(scope='module')
def get_env_variables_with_authority_in_kind(with_wdms_env):
    env_with_authority_in_kind = with_wdms_env.copy()
    for name, value in new_parameters_env.items():
        env_with_authority_in_kind.set(name, value)
    return env_with_authority_in_kind

@pytest.fixture(params=['data_partition', 'authority_slb'])
def get_env(with_wdms_env, get_env_variables_with_authority_in_kind, request):
    return with_wdms_env if request.param == "data_partition" else get_env_variables_with_authority_in_kind


@pytest.mark.tag('basic', 'crud', 'smoke', 'dip', 'bulk')
@pytest.mark.dependency(name="test_create_dipset")
def test_create_dipset(get_env):
    result = build_request_create__dipset().call(get_env)
    result.assert_ok()
    resobj = result.get_response_obj()
    assert resobj.recordCount == 1
    assert len(resobj.recordIds) == 1
    get_env.set('dipsetId', resobj.recordIds[0])
    print(get_env)

@pytest.mark.tag('basic', 'crud', 'smoke', 'dip', 'bulk')
@pytest.mark.dependency(name="test_get_dipset", depends=["test_create_dipset"])
def test_get_dipset(get_env):
    result = build_request_get_dipset().call(get_env)
    result.assert_ok()
    resobj = result.get_response_obj()

    dip_schema = {
        "type": "object",
        "properties": {
            "acl": {
                "type": "object",
                "properties": {
                    "viewers": {"type": "array"},
                    "owners": {"type": "array"}
                }
            },
            "data": {
                "type": "object",
                "properties": {

                }

            },
            "id": {"type": "string"},
            "kind": {"type": "string"},
            "legal": {
                "type": "object",
                "properties": {
                    "legaltags": {"type": "array"},
                    "otherRelevantDataCountries": {"type": "array"}
                }
            },
        },
        "required": ["acl", "data", "id", "kind", "legal"]
    }

    validate(resobj, schema=dip_schema)

    assert resobj.data.name == f'{get_env.get("prefix_data_entity_name")}_dipset_Keon'
    assert resobj.kind == get_env['dipsetKind']


expected_dips = [
    {
        "reference": {
            "unitKey": "meter",
            "value": 1000.0
        },
        "azimuth": {
            "unitKey": "dega",
            "value": 0.12345678912121212
        },
        "inclination": {
            "unitKey": "dega",
            "value": 12.0
        },
        "quality": {
            "unitKey": "unitless",
            "value": 1.0
        },
        "xCoordinate": {
            "unitKey": "meter",
            "value": 1.0
        },
        "yCoordinate": {
            "unitKey": "meter",
            "value": 2.0
        },
        "zCoordinate": {
            "unitKey": "meter",
            "value": 3.0
        },
        "classification": "fracture"
    },
    {
        "reference": {
            "unitKey": "meter",
            "value": 2000.0
        },
        "azimuth": {
            "unitKey": "dega",
            "value": 34.0
        },
        "inclination": {
            "unitKey": "dega",
            "value": 27.0
        }
    },
    {
        "reference": {
            "unitKey": "meter",
            "value": 3000.0
        },
        "azimuth": {
            "unitKey": "dega",
            "value": 0
        },
        "inclination": {
            "unitKey": "dega",
            "value": 1.0
        },
        "classification": "fracture"
    },
    {
        "reference": {
            "unitKey": "meter",
            "value": 4000.0
        },
        "azimuth": {
            "unitKey": "dega",
            "value": 4.0
        },
        "inclination": {
            "unitKey": "dega",
            "value": 2.0
        },
        "classification": "breakout"
    }
]


@pytest.mark.tag('basic', 'crud', 'smoke', 'dip', 'bulk')
@pytest.mark.dependency(name="test_create_dips", depends=["test_create_dipset"])
def test_create_dips(get_env):
    result = build_request_create_dips().call(get_env)
    result.assert_ok()

    assert result.response.json() == expected_dips

@pytest.mark.tag('basic', 'crud', 'smoke', 'dip', 'bulk')
@pytest.mark.dependency(name="test_create_dips", depends=["test_create_dipset"])
def test_get_dipset_virification_authority_kind(get_env):
    result_dipset = build_request_get_dipset().call(get_env)
    result_dipset.assert_ok()
    resobj_dipset = result_dipset.get_response_obj()
    log_list = [log_name for log_name in resobj_dipset.data.relationships if "Log" in log_name]
    authorityKind = get_env.get("authorityKind")
    for log in log_list:
        log_id = resobj_dipset.data.relationships[log].id
        get_env.set('log_record_id', log_id)
        result_log = build_request_get_log().call(get_env)
        resobj_log = result_log.get_response_obj()

        assert resobj_log.kind.split(':')[0] == authorityKind


@pytest.mark.tag('basic', 'crud', 'smoke', 'dip', 'bulk')
@pytest.mark.dependency(name="test_get_dips", depends=["test_create_dips"])
def test_get_dips(get_env):
    result = build_request_get_dips().call(get_env)
    result.assert_ok()

    assert result.response.json() == expected_dips


@pytest.mark.tag('basic', 'crud', 'smoke', 'dip', 'bulk')
@pytest.mark.dependency(name="test_get_dip_from_index", depends=["test_create_dips"])
def test_get_dip_from_index(get_env):
    result = build_request_get_dip_from_index().call(get_env)
    result.assert_ok()
    expected = {
        "reference": {
            "unitKey": "meter",
            "value": 2000.0
        },
        "azimuth": {
            "unitKey": "dega",
            "value": 34.0
        },
        "inclination": {
            "unitKey": "dega",
            "value": 27.0
        }
    }
    assert result.response.json() == expected


@pytest.mark.tag('basic', 'crud', 'smoke', 'dip', 'bulk')
@pytest.mark.dependency(name="test_insert_dips", depends=["test_get_dips", "test_get_dip_from_index"])
def test_insert_dips(get_env):
    result = build_request_insert_dips().call(get_env)
    result.assert_ok()
    assert result.response.json() == [
        {
            "reference": {
                "unitKey": "meter",
                "value": 888.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 666.66
            },
            "inclination": {
                "unitKey": "dega",
                "value": 99.99
            }
        },
        {
            "reference": {
                "unitKey": "meter",
                "value": 1000.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 0.12345678912121212
            },
            "inclination": {
                "unitKey": "dega",
                "value": 12.0
            },
            "quality": {
                "unitKey": "unitless",
                "value": 1.0
            },
            "xCoordinate": {
                "unitKey": "meter",
                "value": 1.0
            },
            "yCoordinate": {
                "unitKey": "meter",
                "value": 2.0
            },
            "zCoordinate": {
                "unitKey": "meter",
                "value": 3.0
            },
            "classification": "fracture"
        },
        {
            "reference": {
                "unitKey": "meter",
                "value": 1500.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 77.0
            },
            "inclination": {
                "unitKey": "dega",
                "value": 81.0
            }
        },
        {
            "reference": {
                "unitKey": "meter",
                "value": 2000.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 34.0
            },
            "inclination": {
                "unitKey": "dega",
                "value": 27.0
            }
        },
        {
            "reference": {
                "unitKey": "meter",
                "value": 3000.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 10
            },
            "inclination": {
                "unitKey": "dega",
                "value": 1.0
            },
            "classification": "fracture"
        },
        {
            "reference": {
                "unitKey": "meter",
                "value": 4000.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 4.0
            },
            "inclination": {
                "unitKey": "dega",
                "value": 2.0
            },
            "classification": "breakout"
        }
    ]


@pytest.mark.tag('basic', 'crud', 'smoke', 'dip', 'bulk')
@pytest.mark.dependency(name="test_patch_dip", depends=["test_insert_dips"])
def test_patch_dip(get_env):
    result = build_request_patch_dip().call(get_env)
    result.assert_ok()

    assert result.response.json() == [
        {
            "reference": {
                "unitKey": "meter",
                "value": 1000.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 0.12345678912121212
            },
            "inclination": {
                "unitKey": "dega",
                "value": 12.0
            },
            "quality": {
                "unitKey": "unitless",
                "value": 1.0
            },
            "xCoordinate": {
                "unitKey": "meter",
                "value": 1.0
            },
            "yCoordinate": {
                "unitKey": "meter",
                "value": 2.0
            },
            "zCoordinate": {
                "unitKey": "meter",
                "value": 3.0
            },
            "classification": "fracture"
        },
        {
            "reference": {
                "unitKey": "meter",
                "value": 1000.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 8.0
            },
            "inclination": {
                "unitKey": "dega",
                "value": 12.0
            },
            "xCoordinate": {
                "unitKey": "meter",
                "value": 12.0
            },
            "yCoordinate": {
                "unitKey": "meter",
                "value": 12.0
            },
            "zCoordinate": {
                "unitKey": "meter",
                "value": 12.0
            },
            "classification": "fracture"
        },
        {
            "reference": {
                "unitKey": "meter",
                "value": 1500.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 77.0
            },
            "inclination": {
                "unitKey": "dega",
                "value": 81.0
            }
        },
        {
            "reference": {
                "unitKey": "meter",
                "value": 2000.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 34.0
            },
            "inclination": {
                "unitKey": "dega",
                "value": 27.0
            }
        },
        {
            "reference": {
                "unitKey": "meter",
                "value": 3000.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 0
            },
            "inclination": {
                "unitKey": "dega",
                "value": 1.0
            },
            "classification": "fracture"
        },
        {
            "reference": {
                "unitKey": "meter",
                "value": 4000.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 4.0
            },
            "inclination": {
                "unitKey": "dega",
                "value": 2.0
            },
            "classification": "breakout"
        }
    ]


@pytest.mark.tag('basic', 'crud', 'smoke', 'dip', 'bulk')
@pytest.mark.dependency(name="test_delete_dip", depends=["test_patch_dip"])
def test_delete_dip(get_env):
    result = build_request_delete_dip().call(get_env)
    result.assert_ok()

    assert result.get_response_obj() == [
        {
            "reference": {
                "unitKey": "meter",
                "value": 1000.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 8.0
            },
            "inclination": {
                "unitKey": "dega",
                "value": 12.0
            },
            "xCoordinate": {
                "unitKey": "meter",
                "value": 12.0
            },
            "yCoordinate": {
                "unitKey": "meter",
                "value": 12.0
            },
            "zCoordinate": {
                "unitKey": "meter",
                "value": 12.0
            },
            "classification": "fracture"
        },
        {
            "reference": {
                "unitKey": "meter",
                "value": 1500.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 77.0
            },
            "inclination": {
                "unitKey": "dega",
                "value": 81.0
            }
        },
        {
            "reference": {
                "unitKey": "meter",
                "value": 2000.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 34.0
            },
            "inclination": {
                "unitKey": "dega",
                "value": 27.0
            }
        },
        {
            "reference": {
                "unitKey": "meter",
                "value": 3000.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 0
            },
            "inclination": {
                "unitKey": "dega",
                "value": 1.0
            },
            "classification": "fracture"
        },
        {
            "reference": {
                "unitKey": "meter",
                "value": 4000.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 4.0
            },
            "inclination": {
                "unitKey": "dega",
                "value": 2.0
            },
            "classification": "breakout"
        }
    ]


@pytest.mark.tag('basic', 'crud', 'smoke', 'dip', 'bulk')
@pytest.mark.dependency(name="test_query_dips", depends=["test_delete_dip"])
def test_query_dips(get_env):
    result = build_request_query_dips().call(get_env)
    result.assert_ok()

    assert result.get_response_obj() == [
        {
            "reference": {
                "unitKey": "meter",
                "value": 4000.0
            },
            "azimuth": {
                "unitKey": "dega",
                "value": 4.0
            },
            "inclination": {
                "unitKey": "dega",
                "value": 2.0
            },
            "classification": "breakout"
        }
    ]


@pytest.mark.tag('basic', 'crud', 'smoke', 'dip', 'bulk')
@pytest.mark.dependency(name="test_delete_dipset")
def test_delete_dipset(get_env):
    if get_env.get('dipsetId', None):
        result = build_request_delete_dipset().call(get_env)
        result.assert_status_code(204)


@pytest.mark.tag('basic', 'crud', 'smoke', 'dip')
@pytest.mark.dependency(name="test_dip_error_code")
def test_dip_error_code(get_env):
    env = get_env
    env.set('dipsetId', 'opendes:doc:00000000000000000000000000000000000')
    build_request_get_dips().call(get_env, assert_status=404).get_response_obj()