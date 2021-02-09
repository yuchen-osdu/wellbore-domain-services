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

import sys
import pathlib
import pytest
import logging
import warnings


logger = logging.getLogger()

# disable pywin32 deprecation warning, imported by azure lib and artifacts-keyring
warnings.filterwarnings("ignore", "the imp module is deprecated")

integration_test_base_path = str(pathlib.Path(__file__).parent.absolute())
sys.path.append(integration_test_base_path)  # set the current directory into the python path

# put after sys.path update
from .variables import Variables, CmdLineSpecialVar
from .tests.fixtures import WDMS_Variables

FILTER_IN_TAGS = set()
FILTER_OUT_TAGS = set()


def pytest_addoption(parser):
    parser.addoption('--filter-tag', default='',
                     help='exclude or not test based on tag(s). Separate multiple tag by "|" .'
                          'Prefix tag by "!" to filter out test with the given tag. Tags are case insensitive')

    parser.addoption('--environment', default='',
                     help='Specify a environment as a JSON file (postman format)')

    parser.addoption('--timeout-request', type=int, default=0,
                     help='Specify a timeout for requests (milliseconds), 0 means no timeout')

    parser.addoption('--log-request-level', type=int, default=1,
                     help='add info in the log for every request call: 0 nothing, 1 url & status_code, 2 full')

    parser.addoption('--insecure', action='store_true',
                     help='Disables SSL validations')

    parser.addoption(
        '--retry-on-error', default='',
        help='retry up to 4 times on the specific error code (>=500). Separate multiple code by "|"')

    parser.addoption(
        '--header', action='append',
        help='header to set for any request (can be overridden at test level), format header_name: header_value')

    parser.addoption(
        '--param', action='append',
        help='set a parameter value (it overrides environ file ones but can be overridden at test level), format param_name: param_value')


def set_environment_from_config(pytest_config, variables: Variables):
    local_env = Variables.load_env(integration_test_base_path + '/local_environment.json', ignore_empty=True)
    variables.update_env(local_env)

    env_file = pytest_config.getoption('environment', default=None)
    if env_file:
        loaded_env = Variables.load_env(env_file)
        variables.update_env(loaded_env)

    # timeout
    timeout_request = pytest_config.getoption('timeout_request', default=0)
    if timeout_request:
        CmdLineSpecialVar.set_timeout_request(variables, int(timeout_request))

    # log request level
    log_request_level = pytest_config.getoption('log_request_level', default=1)
    if log_request_level:
        CmdLineSpecialVar.set_log_request_level(variables, int(log_request_level))

    # disable ssl validation
    disable_ssl_validation = pytest_config.getoption('insecure', default=False)
    CmdLineSpecialVar.set_disable_ssl_validation(variables, disable_ssl_validation)
    if disable_ssl_validation:
        # only trigger this warning once, not on each call
        warnings.filterwarnings("ignore", "Unverified HTTPS request is being made")

    retry_on_error = pytest_config.getoption('retry_on_error', default=None)
    if retry_on_error:
        CmdLineSpecialVar.set_retry_on_error(variables, [int(e) for e in retry_on_error.split('|')])

    # custom header
    headers = pytest_config.getoption('header', default=None) or []
    header_dict = {}
    for header in headers:
        if not isinstance(header, str):
            continue
        idx = header.find(':')
        if idx > 1:
            header_dict[header[: idx].strip()] = header[idx + 1:-1].strip()
    if header_dict:
        CmdLineSpecialVar.set_headers(variables, header_dict)

    # custom param
    params = pytest_config.getoption('param', default=None) or []

    if params:
        for param in params:
            if not isinstance(param, str):
                continue
            idx = param.find(':')
            if idx > 1:
                variables.set(param[: idx].strip(), param[idx + 1:-1].strip())


def pytest_configure(config):
    set_environment_from_config(config, WDMS_Variables)

    config.addinivalue_line("markers", "tag: add tags to a test to extend filtering capability")

    if CmdLineSpecialVar.get_disable_ssl_validation(WDMS_Variables):
        # filter warning when disabling ssl validation in order to not be spammed by warning and still spot real onces
        # it would be better to use action=once to have the error only a single time but it not works properly,
        # so just ignore this warning
        config.addinivalue_line("filterwarnings", "ignore::urllib3.exceptions.InsecureRequestWarning")

    # filter tags
    tag_sequence = config.getoption('filter_tag', default=None)
    for tag in tag_sequence.split('|'):
        if len(tag) < 2:
            continue
        if tag[0] == '!':
            FILTER_OUT_TAGS.add(tag[1:].lower())
        else:
            FILTER_IN_TAGS.add(tag.lower())


def pytest_runtest_setup(item):
    if FILTER_IN_TAGS or FILTER_OUT_TAGS:
        item_tags = set()
        for mark in item.iter_markers(name="tag"):
            for arg in mark.args:
                if isinstance(arg, list):
                    item_tags.update({t.lower() for t in arg})
                else:
                    item_tags.add(arg.lower())
        if FILTER_IN_TAGS:
            if not FILTER_IN_TAGS.intersection(item_tags):
                pytest.skip('unmatched tags: ' + '|'.join(FILTER_IN_TAGS))

        if FILTER_OUT_TAGS:
            if FILTER_OUT_TAGS.intersection(item_tags):
                pytest.skip('matched tags: ' + '|'.join(FILTER_OUT_TAGS))
