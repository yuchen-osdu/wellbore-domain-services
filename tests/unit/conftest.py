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

from app.conf import ConfigurationContainer
import app.conf as conf
import os
import pytest


@pytest.fixture(autouse=True)
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


def pytest_configure(config):
    """
        Pytest Hook, called before loading fixtures and test cases.
    """
    # Env vars used by client lib configuration.
    # Required to be set before fixtures as all tests are currently loading dependencies at import time.
    os.environ.setdefault('KEYVAULT_URL', 'non-empty-name')
    os.environ.setdefault('SERVICE_HOST_PARTITION', 'https://test-endpoint/api/partition')


def pytest_unconfigure(config):
    """
        Pytest Hook, called after running all test cases.
    """
    del os.environ['KEYVAULT_URL']
    del os.environ['SERVICE_HOST_PARTITION']

