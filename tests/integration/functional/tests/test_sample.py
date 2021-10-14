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

"""
 This file contains test sample showing how use RequestRunner
"""
import pytest
from wdms_client.request_runner import Request, RequestRunner
from wdms_client.variables import Variables


def sample_of_test():
    # define some variables
    environment = Variables.from_dict({
        "echo_url": "https://postman-echo.com/post",
        "param1": "value1",
        "param2": "{{param1}} - value2",  # use a nested variable,
        "int_value": 42,
        "param_dict": {"param1": "{{param1}}", "int_value": "{{int_value}}"}  # use a nested in dict
    })

    # basic get set
    assert environment['echo_url'] == "https://postman-echo.com/post"
    assert environment['param2'] == 'value1 - value2'
    assert environment['int_value'] == 42
    assert environment.get('not_exist', 'default_value') == 'default_value'
    environment['not_exist'] = 'now exists'
    assert environment.get('not_exist', 'default_value') == 'now exists'

    # substitution in dict
    assert environment['param_dict']['param1'] == 'value1'
    assert environment['param_dict']['int_value'] == '42'  # substituted but converted to str

    # declare a request
    request_prototype = Request(method='POST',
                                url='{{echo_url}}?param1={{param1}}',
                                headers={
                                    'accept': 'application/json',
                                    'Content-Type': 'application/json',
                                    'x-param1': '{{param1}}',
                                    'x-param2': '{{param2}}',
                                    'x-custom-param': '{{custom_param}}'
                                },
                                payload={
                                    'param1': '{{param1}}',
                                    'param_mix': 'param1={{param1}} & int_value={{int_value}}',
                                })

    runner = RequestRunner(request_prototype)

    # run the call and assert 200
    result = runner.call(
        env=environment,   # [optional] environment to use
        headers={'x-additional-header': 'ok'},  # [optional] additional headers
        assert_status=200,  # [optional] assert on a specific status code
        custom_param='custom_param_value',  # add a parameter
        param2='param2_override'  # add parameter, here override param2 value from environment
    )

    # some other way to assert on status code
    result.assert_status_code(200)
    result.assert_ok()
    result.response.raise_for_status()
    assert result.ok
    assert result.response.status_code == 200

    # check the input request
    assert result.request.url == 'https://postman-echo.com/post?param1=value1'
    assert result.request.headers['x-param2'] == 'param2_override'
    assert result.request.headers['x-custom-param'] == 'custom_param_value'
    request_body_obj = result.request.get_body_obj()
    assert request_body_obj['param1'] == 'value1'
    assert request_body_obj.param1 == 'value1'  # as attribute thanks to Munch lib

    # check the response (response is a Requests.response)
    response = result.response
    print(response.headers)

    response_obj = result.get_response_obj()
    assert response_obj.args.param1 == 'value1'  # postman echo par every request query param in response.args
    assert response_obj.headers.accept == 'application/json'
    assert response_obj.headers['x-param2'] == 'param2_override'

    # other info
    print('call took', result.elapsed, 'seconds')
    result.assert_status_code(200)  # assert on a specific status code




