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
from datetime import timedelta

import logging
import os

from unittest import mock

import app.conf as conf
import pytest
from app.conf import ConfigurationContainer
from app.context import Context

from fastapi import Header
from hypothesis import settings, Verbosity, HealthCheck, Phase

from .data import (
    well_v3_file_contents, well_v3_110_file_contents, well_v3_120_file_contents,
    wellbore_v3_file_contents, wellbore_v3_110_file_contents, wellbore_v3_111_file_contents,
    wellbore_v3_120_file_contents, wellbore_v3_130_file_contents,
    marker_v3_file_contents, marker_v3_120_file_contents, marker_v3_121_file_contents,
    wellboreintervalset_v3_100_file_contents, trajectory_v3_file_contents, welllog_v3_110_file_contents,
    welllog_v3_120_file_contents, domain, data_partition,
    legal_tags, well_v3_record_list, well_v3_110_record_list, well_v3_120_record_list,
    wellbore_v3_record_list, wellbore_v3_110_record_list, wellbore_v3_111_record_list,
    wellbore_v3_120_record_list, wellbore_v3_130_record_list,
    marker_v3_record_list, marker_v3_120_record_list, marker_v3_121_record_list, wellboreintervalset_v3_100_record_list,
    trajectory_v3_record_list, welllog110_v3_record_list, welllog120_v3_record_list, well_wks_record, well_wks_mini_record,
    wellbore_wks_record, wellbore_wks_mini_record
)

from .fixtures import (
    local_dev_config,
    local_bulk_persistence_config,
    app_initialized_with_testclient,
    app_configurable_with_testclient,
    mock_storage_client_holding_data,
    mock_schema_client_holding_data
)

from .fixtures_pkg import (
    dask_custom_config,
    testing_app_local_chunking_no_consistency,
    testing_app_local_chunking_with_consistency
)


@pytest.fixture(autouse=False)
def top_fixture(monkeypatch):
    """
    # WARNING: global app.conf.Config corruption
    Hooks mechanism from PyTest.
    This fixture will be called after `pytest_configure` and can use fixture such as monkeypatch
    """

    provider_name = 'local'
    monkeypatch.setenv(name=ConfigurationContainer.cloud_provider.key, value=provider_name)

    environment_dict = os.environ.copy()
    conf.Config = ConfigurationContainer.with_load_all(
        environment_dict=environment_dict,
        contextual_loader=None
    )


@pytest.fixture
def nope_logger_fixture():
    with mock.patch('app.helper.logger._LOGGER', spec_set=logging.Logger, new_callable=mock.NonCallableMock) as Logger:
        yield Logger


def pytest_configure(config):
    """
    Pytest Hook, called before loading fixtures and test cases.
    """
    # Env vars used by client lib configuration.
    # Required to be set before fixtures as all tests are currently loading dependencies at import time.
    os.environ.setdefault('KEYVAULT_URL', 'non-empty-name')
    os.environ.setdefault('SERVICE_HOST_PARTITION', 'https://test-endpoint/api/partition')

    # defining settings profile for local dev runs or CI runs
    # they can be loaded via `$pytest --hypothesis-profile debug`
    # Ref: https://hypothesis.readthedocs.io/en/latest/settings.html?highlight=profile#settings-profiles

    # A long deadline per example to generate various examples
    settings.register_profile("debug", deadline=timedelta(milliseconds=1000), print_blob=True,
                              suppress_health_check=[HealthCheck.too_slow], verbosity=Verbosity.normal)

    # Only test with explicit examples, or replay failing examples.
    # Does NOT generate new examples. Do it locally with "debug" profile.
    settings.register_profile("ci", deadline=None, derandomize=True,
                              phases=[Phase.explicit, Phase.reuse, Phase.target, Phase.shrink],
                              print_blob=True, report_multiple_bugs=False, verbosity=Verbosity.verbose)
    if 'CI' in os.environ:
        # default to ci profile if environment looks like it.
        settings.load_profile(os.getenv(u"HYPOTHESIS_PROFILE", "ci"))
    else:
        settings.load_profile(os.getenv(u"HYPOTHESIS_PROFILE", "debug"))


def pytest_unconfigure(config):
    """
    Pytest Hook, called after running all test cases.
    """
    del os.environ['KEYVAULT_URL']
    del os.environ['SERVICE_HOST_PARTITION']


@pytest.fixture(scope="session")
def anyio_backend():
    return 'asyncio'
