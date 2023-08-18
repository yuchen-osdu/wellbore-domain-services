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

from wdms_client.request_builders.wdms.about import build_request_about
from wdms_client.request_builders.wdms.status import build_request_status
from wdms_client.request_builders.wdms.version import build_request_version
from .fixtures import with_wdms_env
import pytest


@pytest.mark.tag('basic', 'smoke', 'about')
def test_about(with_wdms_env):
    result = build_request_about().call(with_wdms_env)
    result.assert_ok()

    resobj = result.get_response_obj()
    fields = ["service", "version", "buildNumber", "cloudEnvironment"]
    for f in fields:
        assert f in resobj, f"missing {f} in body"
        assert isinstance(resobj[f], str), f"{f} should be a string"

    assert resobj.cloudEnvironment == with_wdms_env['cloud_provider']


@pytest.mark.tag('basic', 'smoke')
def test_version(with_wdms_env):
    result = build_request_version().call(with_wdms_env)
    result.assert_ok()
    assert result.get_response_obj()
    details = result.get_response_obj()["details"]
    print(details)
    assert details["read_bulk_backend"]
    assert details["write_bulk_backend"]


@pytest.mark.tag('basic', 'smoke')
def test_status(with_wdms_env):
    result = build_request_status().call(with_wdms_env)
    result.assert_ok()
    assert result.get_response_obj()
