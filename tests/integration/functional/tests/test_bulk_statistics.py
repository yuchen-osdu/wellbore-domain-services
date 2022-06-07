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

from time import sleep
import pytest
import pandas as pd

from wdms_client.request_runner import RequestRunner, make_basic_wdms_request_proto
from ..generate_dataframe import generate_df
from .fixtures import with_wdms_env


def make_welllog(df: pd.DataFrame):
    """ df: 1 column = 1 curve, first column = reference curve """
    r = {
        "acl": {"owners": ["{{acl_owner}}"], "viewers": ["{{acl_viewer}}"]},
        "legal": {
            "legaltags": ["{{legal_tag}}"], "otherRelevantDataCountries": ["US", "FR"]
        },
        "kind": "{{osduWellLogKind}}",
        "data": {
            "Source": "wdms_e2e_bulk_statistic",
            "Curves": [
                {
                    "CurveID": c,
                    "NumberOfColumns": 1
                } for c in df.columns
            ],
            "ReferenceCurveID": df.columns[0]
        },
        "meta": []
    }
    return r


@pytest.fixture(scope="module")
def well_log_with_data(with_wdms_env):
    """ return welllog record and dataframe of the bulk"""

    df = generate_df(["MD", "C1", "C2"], range(20))

    welllog = make_welllog(df)

    # create well log record
    welllog_id = RequestRunner(
        make_basic_wdms_request_proto('POST', '/ddms/v3/welllogs', payload=[welllog])
    ).call(with_wdms_env, assert_status=200).get_response_obj().recordIds[0]

    # push bulk data
    welllog_id_version = RequestRunner(
        make_basic_wdms_request_proto('POST', f'/ddms/v3/welllogs/{welllog_id}/data', payload=df)
    ).call(with_wdms_env, assert_status=200).get_response_obj().recordIdVersions[0]

    welllog['id'] = welllog_id
    welllog['version'] = welllog_id_version.split(':')[-1]

    yield welllog, df

    # clean up now
    RequestRunner(
        make_basic_wdms_request_proto('DELETE', f'/ddms/v3/welllogs/{welllog_id}?purge=true')
    ).call(with_wdms_env).assert_ok()


@pytest.mark.tag('bulk', 'v3', 'statistic')
def test_get_bulk_statistic_basic_workflow(with_wdms_env, well_log_with_data):
    # GIVEN well log with just pushed bulk data
    welllog, df = well_log_with_data
    welllog_id = welllog['id']
    welllog_version = welllog['version']

    # compute expected stats
    total_count = len(df.index)
    describe_result = df.describe(percentiles=[.10, .5, .90]).to_dict()
    expected_stats = dict()
    for curve, stat_dict in describe_result.items():
        expected_stats[curve] = {'totalCount': str(total_count)}
        for k, v in stat_dict.items():
            expected_stats[curve]['nonAbsentValuesCount' if k == 'count' else k] = str(v)

    # WHEN call to trigger to statistic computation
    # THEN should returns 409 as computation already triggered
    response = RequestRunner(
        make_basic_wdms_request_proto('POST',
                                      f'/ddms/v3/welllogs/{welllog_id}/versions/{welllog_version}/data/statistics')
    ).call(with_wdms_env, assert_status=409)

    # WHEN call to get statistic, doing several attempt as computation is asynchronous
    sleep_attempts = [5, 30]  # means as many attempt with a sleep before each
    for i_sleep_attempt in sleep_attempts:
        sleep(i_sleep_attempt)
        response = RequestRunner(
            make_basic_wdms_request_proto('GET', f'/ddms/v3/welllogs/{welllog_id}/data/statistics')
        ).call(with_wdms_env)
        if response.ok:
            break

    # THEN response successful & statistic match the expected once
    response.assert_ok()
    assert response.get_response_obj().data == expected_stats
