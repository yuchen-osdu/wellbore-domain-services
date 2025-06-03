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
from unittest.mock import AsyncMock, create_autospec

import pytest

from app.clients import SchemaServiceClient
from app.injector.app_injector import WithLifeTime
from app.schemas import schema_library
from tests.unit.test_utils import ctx_fixture

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


@pytest.mark.parametrize(("termination_date", "pydantic_failure_expected"), [
    ("1991-04-26", False),  # ISO
    ("08/23/2019", True),  # OSDU
    ("08-23-2019", True),  # OSDU
    ("08.23.2019", True),  # OSDU
    ("08 23 2019", True),  # OSDU
    ("Aug/23/19", True),  # OSDU
    ("August/23/19", True),  # OSDU
    ("August 23, 2019", True),  # OSDU
    ("23-Aug-2019", True),  # OSDU
    ("23/08/2019", True),  # OSDU
    ("2019/8/23", True),  # OSDU
    ("2019-08-23", False),  # OSDU
    ("Fri, Aug 23 2019", True),  # OSDU
    ("Friday, Aug 23 2019", True),  # OSDU
    ("anything else", True),  # because format is not checked by JSon schema
])
@pytest.mark.anyio
async def test_date_format(ctx_fixture_with_search_client, termination_date, pydantic_failure_expected):
    """
    JSon schema only allow ISO date format
    OSDU consortium allows more date format
    Supported formats for DAT:

    Format	Example
    MM/dd/yyyy	08/23/2019
    MM-dd-yy	08-23-2019
    MM.dd.yy	08.23.2019
    MM dd yy	08 23 2019
    MMM/dd/yy	Aug/23/19
    MMMM/dd/yy	August/23/19
    MMMM d, yyyy	August 23, 2019
    dd-MMM-yyyy	23-Aug-2019
    dd/MM/yyyy	23/08/2019
    yyyy/M/d	2019/8/23
    yyyy-MM-d	2019-08-23
    E, MMM dd yyyy	Fri, Aug 23 2019
    EEEE, MMM dd yyyy	Friday, Aug 23 2019
    :return:
    """
    # Create entity
    wellbore_entity = {
        "kind": "osdu:wks:master-data--Wellbore:1.3.0",
        "acl": {
            "owners": [
                "E.&Du.tDJUBlW8xeG.wbGTHaBvD61.mq.Db.2.pNPeTECDUv2@LZfnotxwemE.IGia5Xuljh.4.Nm"
            ],
            "viewers": [
                "d&N6guMxO.9AHCk4z6nU.752mXt.0nwNXQo.U-QjrP3Z._v+wKu.5R.gFWZ8tt.vBVUxQ5yB.HJ82RHsh-+O.6tCBBRpT@SKw5MF.N1nzeauiY.rCtQ1Ux.FNGZ.edt23jsW.FhB6NmQjF.bEZn36M.Tz.NOf8-.Mv1b.nMA"
            ]
        },
        "legal": {
            "legaltags": [
                "adipisicing enim incididunt deserunt pariatur"
            ],
            "otherRelevantDataCountries": [
                "FV"
            ],
            "status": "uncompliant"
        },
        "data": {
            "HistoricalInterests": [{
                "TerminationDateTime": termination_date
            }]
        },
    }

    # Check if it is ok with JSon Schema without format check
    await schema_library._validate_entities([wellbore_entity], ctx_fixture_with_search_client)


@pytest.mark.parametrize(("effective_datetime", "pydantic_failure_expected"), [
    ("1991-04-26T20:11:44.517Z", False),  # ISO
    ("08/23/2019 12:08:01", True),  # OSDU
    ("08/23/2019 12:08:01.001", True),  # OSDU
    ("08/23/2019 12.08.01", True),  # OSDU
    ("2019-08-23T12:08:01Z", False),  # OSDU
    ("Friday, Aug 23, 2019 12:08:01 PM", True),  # OSDU
    ("anything else", True),  # because format is not checked by JSon schema
])
@pytest.mark.anyio
async def test_date_time_format(ctx_fixture_with_search_client, effective_datetime, pydantic_failure_expected):
    """
    JSon schema only allow ISO date format
    OSDU consortium allows more date format

    Supported formats for DTM:
    Format	Example
    MM/dd/yyyy HH:mm:ss	08/23/2019 12:08:01
    MM/dd/yyyy HH:mm:ss.SSS	08/23/2019 12:08:01.001
    MM/dd/yyyy H.mm.ss	08/23/2019 12.08.01
    yyyy-MM-ddTHH:mm:ssZ	2019-08-23T12:08:01Z
    EEEE, MMM dd, yyyy HH:mm:ss a	Friday, Aug 23, 2019 12:08:01 PM
    :return:
    """
    # Create entity
    wellbore_entity = {
        "kind": "osdu:wks:master-data--Wellbore:1.3.0",
        "acl": {
            "owners": [
                "E.&Du.tDJUBlW8xeG.wbGTHaBvD61.mq.Db.2.pNPeTECDUv2@LZfnotxwemE.IGia5Xuljh.4.Nm"
            ],
            "viewers": [
                "d&N6guMxO.9AHCk4z6nU.752mXt.0nwNXQo.U-QjrP3Z._v+wKu.5R.gFWZ8tt.vBVUxQ5yB.HJ82RHsh-+O.6tCBBRpT@SKw5MF.N1nzeauiY.rCtQ1Ux.FNGZ.edt23jsW.FhB6NmQjF.bEZn36M.Tz.NOf8-.Mv1b.nMA"
            ]
        },
        "legal": {
            "legaltags": [
                "adipisicing enim incididunt deserunt pariatur"
            ],
            "otherRelevantDataCountries": [
                "FV"
            ],
            "status": "uncompliant"
        },
        "data": {
            "FacilityNameAliases": [{
                "EffectiveDateTime": effective_datetime
            }]
        }
    }

    # Check if it is ok with JSon Schema without format check
    await schema_library._validate_entities([wellbore_entity], ctx_fixture_with_search_client)
