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

import asyncio
import logging
import os

from unittest import mock

import app.conf as conf
import pytest
from app.conf import ConfigurationContainer
from app.context import Context

from fastapi import Header
from hypothesis import settings, Verbosity, HealthCheck

from .data import (
    well_v2_file_contents, well_v3_file_contents, wellbore_v2_file_contents, wellbore_v3_file_contents,
    domain, data_partition, legal_tags,
    well_v2_record_list, well_v3_record_list, wellbore_v2_record_list, wellbore_v3_record_list,
    well_wks_record, well_wks_mini_record, wellbore_wks_record, wellbore_wks_mini_record
)

from .fixtures import (
    local_dev_config,
    base_app_initialized_with_testclient,
    app_initialized_with_testclient,
    app_configurable_with_testclient,
    mock_storage_client_holding_data
)

from .fixtures_pkg import (
    dask_client
)


@pytest.fixture(autouse=False)
def top_fixture(monkeypatch):
    """
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
    settings.register_profile("default", deadline=None, verbosity=Verbosity.normal)
    settings.register_profile("debug", suppress_health_check=[HealthCheck.too_slow], verbosity=Verbosity.verbose)
    settings.load_profile(os.getenv(u"HYPOTHESIS_PROFILE", "default"))


def pytest_unconfigure(config):
    """
    Pytest Hook, called after running all test cases.
    """
    del os.environ['KEYVAULT_URL']
    del os.environ['SERVICE_HOST_PARTITION']


# all tests with pytest-asyncio will share the same loop
# Ref: https://github.com/pytest-dev/pytest-asyncio#event_loop
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    # teardown
    loop.close()


@pytest.fixture
def init_fixtures(monkeypatch, tmp_path):
    monkeypatch.setenv(name="USE_LOCALFS_BLOB_STORAGE_WITH_PATH", value=str(tmp_path))
    conf.Config = conf.ConfigurationContainer.with_load_all()
    yield


async def do_nothing():
    # empty method
    pass


async def set_default_partition(data_partition_id: str = Header("opendes")):
    Context.set_current_with_value(partition_id=data_partition_id)
