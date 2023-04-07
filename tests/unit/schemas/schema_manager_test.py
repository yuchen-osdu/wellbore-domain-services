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
import json
from os import path

import pytest

from app.schemas import SchemaMode, SchemaManager


def test_schema_mode_values():
    enum_map = SchemaMode._value2member_map_
    assert enum_map[1].name == 'ORIGINAL'
    assert enum_map[2].name == 'OPTIMISED'
    assert enum_map[3].name == 'EXTRA_FORBID'
    assert enum_map[4].name == 'EXTRA_FORBID_OPTIMISED'


def test__create_versions_of_schema():
    # Load one schemas - Wellbore 1.3.0 for instance
    json_file = "osdu..wks..master-data--Wellbore..1.3.0.json"
    json_file_ref_org = "osdu..wks..master-data--Wellbore..1.3.0_ref.json"
    json_file_ref_extra_f = "osdu..wks..master-data--Wellbore..1.3.0._ref_extra_f.json"
    with open(path.join(path.dirname(path.realpath(__file__)), "resources", json_file)) as json_file_stream:
        json_schema_content = json.load(json_file_stream)

        org, _, extra_f, _ = SchemaManager._create_versions_of_schema(json_schema_content)
        with open(path.join(path.dirname(path.realpath(__file__)), "resources", json_file_ref_org)) as ref_org_fp:
            ref_org = json.load(ref_org_fp)
            assert org == ref_org
        with open(path.join(path.dirname(path.realpath(__file__)), "resources",
                            json_file_ref_extra_f)) as json_file_ref_extra_f_fp:
            ref_extra_f = json.load(json_file_ref_extra_f_fp)
            assert extra_f == ref_extra_f


def test_load_known_schemas():
    SchemaManager.load_known_schemas()
    assert "osdu:wks:master-data--Wellbore:1.3.0" in SchemaManager.schema_library
    assert "osdu:wks:master-data--Wellbore:1.3.0" in SchemaManager.optimised_schema_library
    assert "osdu:wks:master-data--Wellbore:1.3.0" in SchemaManager.schema_forbid_extra_library
    assert "osdu:wks:master-data--Wellbore:1.3.0" in SchemaManager.optimised_schema_forbid_extra_library


def test_load_unknown_schema():
    # TODO Use a mock for schema client
    pass


@pytest.mark.parametrize(("mode"), [SchemaMode.OPTIMISED, SchemaMode.ORIGINAL, SchemaMode.EXTRA_FORBID,
                                    SchemaMode.EXTRA_FORBID_OPTIMISED])
def test_get_known_schema(mode):
    schema = "osdu:wks:master-data--Wellbore:1.3.0"
    res = SchemaManager._get_known_schema(schema, mode)
    assert res is not None


def test_get_known_schema_unknown_mode():
    schema = "osdu:wks:master-data--Wellbore:1.3.0"
    res = SchemaManager._get_known_schema(schema, 42)
    assert res is None


def test_get_known_schema_unknown_schema():
    schema = "osdu:wks:master-data--unknown:1.3.0"
    res = SchemaManager._get_known_schema(schema, SchemaMode.ORIGINAL)
    assert res is None


def test_get_schema():
    # TODO test with mock on schema service
    pass


def test_validate_records():
    # TODO test with mock on schema service
    pass


def test_validate_entities():
    # TODO test with mock on schema service
    pass
