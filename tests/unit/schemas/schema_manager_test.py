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
from unittest.mock import create_autospec, patch, AsyncMock

import odes_schema
import pytest

from app.clients import SchemaServiceClient
from app.injector.app_injector import WithLifeTime
from app.schemas import SchemaMode, SchemaManager, schema_library
from tests.unit.test_utils import ctx_fixture


def test_schema_mode_values():
    enum_map = SchemaMode._value2member_map_
    assert enum_map[0].name == 'ORIGINAL'
    assert enum_map[1].name == 'OPTIMISED'
    assert enum_map[2].name == 'EXTRA_FORBID'
    assert enum_map[3].name == 'EXTRA_FORBID_OPTIMISED'


def test_create_versions_of_schema():
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


schema_service_client_mock = create_autospec(SchemaServiceClient, spec_set=True, instance=True)


def injection_coro_builder(*, return_value):
    # because of our app_injector design
    async def injection_coro(
            *args, **kwargs
    ):
        return return_value

    return injection_coro


@pytest.fixture
def ctx_fixture_with_search_client(ctx_fixture):
    ctx_fixture.app_injector.register(SchemaServiceClient,
                                      injection_coro_builder(return_value=schema_service_client_mock),
                                      WithLifeTime.Singleton())
    yield ctx_fixture
    ctx_fixture.app_injector.register(SchemaServiceClient, AsyncMock())


@pytest.mark.anyio
async def test_load_unknown_schema_success(ctx_fixture_with_search_client):
    kind = "osdu:fs:fs:1.0.0"
    returned_schema = {"x-osdu-schema-source": "osdu:fs:fs:1.0.0"}
    with patch.object(schema_service_client_mock, 'get_schema', return_value=returned_schema):
        res = await SchemaManager._load_unknown_schema(kind=kind, ctx=ctx_fixture_with_search_client)
        assert res == returned_schema


@pytest.mark.anyio
async def test_load_unknown_schema_404(ctx_fixture_with_search_client):
    kind = "osdu:fs:fs:1.0.0"
    side_effect = odes_schema.UnexpectedResponse(status_code=404, reason_phrase="Not Found", content=None, headers=None)
    with patch.object(schema_service_client_mock, 'get_schema', side_effect=side_effect):
        with pytest.raises(odes_schema.UnexpectedResponse) as e:
            res = await SchemaManager._load_unknown_schema(kind=kind, ctx=ctx_fixture_with_search_client)
        assert e.value.status_code == 404


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


@pytest.mark.anyio
async def test_get_schema_in_cache(ctx_fixture_with_search_client):
    kind = "osdu:wks:master-data--Wellbore:1.3.0"
    res = await SchemaManager.get_schema(kind=kind, ctx=ctx_fixture_with_search_client, mode=SchemaMode.EXTRA_FORBID)
    assert res["x-osdu-schema-source"] == kind


@pytest.mark.anyio
async def test_get_schema_from_service_success(ctx_fixture_with_search_client):
    kind = "osdu:fs:fs:1.0.0"
    returned_schema = {"x-osdu-schema-source": "osdu:fs:fs:1.0.0"}
    with patch.object(schema_service_client_mock, 'get_schema', return_value=returned_schema):
        res = await SchemaManager.get_schema(kind=kind, ctx=ctx_fixture_with_search_client,
                                             mode=SchemaMode.EXTRA_FORBID)
        assert res["x-osdu-schema-source"] == kind


@pytest.mark.anyio
async def test_get_schema_from_service_404(ctx_fixture_with_search_client):
    kind = "osdu:fs:fs:1.0.0"
    side_effect = odes_schema.UnexpectedResponse(status_code=404, reason_phrase="Not Found", content=None, headers=None)
    with patch.object(schema_service_client_mock, 'get_schema', side_effect=side_effect):
        with pytest.raises(odes_schema.UnexpectedResponse) as e:
            res = await SchemaManager.get_schema(kind=kind, ctx=ctx_fixture_with_search_client,
                                                 mode=SchemaMode.EXTRA_FORBID)
        assert e.value.status_code == 404


@pytest.mark.anyio
async def test_validate_entities(ctx_fixture_with_search_client, wellbore_v3_130_record_list):
    pass


@pytest.mark.anyio
@pytest.mark.parametrize(("mode"), [
    SchemaMode.ORIGINAL,
    SchemaMode.OPTIMISED,
    SchemaMode.EXTRA_FORBID,
    SchemaMode.EXTRA_FORBID_OPTIMISED,
])
@pytest.mark.parametrize(("record_list_f"), [
    "well_v3_record_list",
    "well_v3_110_record_list",
    "well_v3_120_record_list",
    "wellbore_v3_record_list",
    "wellbore_v3_110_record_list",
    "wellbore_v3_111_record_list",
    "wellbore_v3_120_record_list",
    "wellbore_v3_130_record_list",
    "marker_v3_record_list",
    "marker_v3_120_record_list",
    "marker_v3_121_record_list",
    "wellboreintervalset_v3_100_record_list",
    "trajectory_v3_record_list",
    "welllog110_v3_record_list",
    "welllog120_v3_record_list",

])
async def test_validate_records_success(ctx_fixture_with_search_client, mode, record_list_f, request):
    # we expect no Exception
    record_list = request.getfixturevalue(record_list_f)
    await schema_library.validate_records(record_list, ctx_fixture_with_search_client, mode)
