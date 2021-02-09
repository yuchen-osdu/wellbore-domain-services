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


@pytest.mark.tag('basic', 'crud', 'smoke', 'dip', 'bulk')
@pytest.mark.dependency()
def test_create_dipset(with_wdms_env):
    result = build_request_create__dipset().call(with_wdms_env)
    result.assert_ok()
    resobj = result.get_response_obj()
    assert resobj.recordCount == 1
    assert len(resobj.recordIds) == 1
    with_wdms_env.set('dipsetId', resobj.recordIds[0])


@pytest.mark.tag('basic', 'crud', 'smoke', 'dip', 'bulk')
@pytest.mark.dependency(depends=["test_create_dipset"])
def test_get_dipset(with_wdms_env):
    result = build_request_get_dipset().call(with_wdms_env)
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

    assert resobj.data.name == "wdms_e2e_dipset_Keon"
    assert resobj.kind == with_wdms_env['dipsetKind']


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
            "value": 3.0
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
@pytest.mark.dependency(depends=["test_create_dipset"])
def test_create_dips(with_wdms_env):
    result = build_request_create_dips().call(with_wdms_env)
    result.assert_ok()

    assert result.response.json() == expected_dips


@pytest.mark.tag('basic', 'crud', 'smoke', 'dip', 'bulk')
@pytest.mark.dependency(depends=["test_create_dips"])
def test_get_dips(with_wdms_env):
    result = build_request_get_dips().call(with_wdms_env)
    result.assert_ok()

    assert result.response.json() == expected_dips


@pytest.mark.tag('basic', 'crud', 'smoke', 'dip', 'bulk')
@pytest.mark.dependency(depends=["test_create_dips"])
def test_get_dip_from_index(with_wdms_env):
    result = build_request_get_dip_from_index().call(with_wdms_env)
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
@pytest.mark.dependency(depends=["test_get_dips", "test_get_dip_from_index"])
def test_insert_dips(with_wdms_env):
    result = build_request_insert_dips().call(with_wdms_env)
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
                "value": 3.0
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
@pytest.mark.dependency(depends=["test_insert_dips"])
def test_patch_dip(with_wdms_env):
    result = build_request_patch_dip().call(with_wdms_env)
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
                "value": 3.0
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
@pytest.mark.dependency(depends=["test_patch_dip"])
def test_delete_dip(with_wdms_env):
    result = build_request_delete_dip().call(with_wdms_env)
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
                "value": 3.0
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
@pytest.mark.dependency(depends=["test_delete_dip"])
def test_query_dips(with_wdms_env):
    result = build_request_query_dips().call(with_wdms_env)
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


# @pytest.mark.dependency(depends=["test_query_dips"])
@pytest.mark.tag('basic', 'crud', 'smoke', 'dip', 'bulk')
def test_delete_dipset(with_wdms_env):
    if with_wdms_env.get('dipsetId', None):
        result = build_request_delete_dipset().call(with_wdms_env)
        result.assert_status_code(204)
