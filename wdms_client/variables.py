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

from typing import Optional
from contextlib import contextmanager
import json


class Variables:
    """
        Manage variables and nested substitution. Quite similar to a dict:
        vars['var1'] = 'value1'

        nested variable must are inside double embraces '{{'  '}}':
        vars['var2'] = 'the value of var1 = {{var1}}'

        then
        assert vars['my_var2'] == 'the value of var1 = value1'

        limitation, in case of nested variable, is only resolve in dict or string + the value is always
        converted to string

    """
    def __init__(self):
        self._variables = {}

    def __iter__(self):
        for v in self._variables.values():
            yield v

    @classmethod
    def load_env(cls, file_path, ignore_empty=False):
        with open(file_path) as file:
            return cls.from_pm_env_obj(json.load(file), ignore_empty)

    @classmethod
    def from_dict(cls, variables_dict):
        inst = cls()
        for k, v in variables_dict.items():
            if len(k) > 0:  # avoiding empty string issues
                inst.set(k, v)
        return inst

    def update(self, **kwargs):
        self._variables.update(kwargs)

    def update_env(self, other: 'Variables'):
        self._variables.update(other._variables)

    @classmethod
    def from_pm_env_obj(cls, data, ignore_empty=False):
        inst = cls()
        values = data['values']
        for var_data in values:
            if var_data.get('enabled', True):
                value = var_data['value']
                if value or not ignore_empty:
                    inst._variables[var_data['key']] = var_data['value']
        return inst

    def resolve(self, d):

        if isinstance(d, dict):
            return {k: self.resolve(v) for k, v in d.items()}

        if isinstance(d, list):
            return [self.resolve(e) for e in d]

        if isinstance(d, str):
            return self._resolve_value(d)

        return d

    def _resolve_value(self, value: Optional[str]) -> Optional[str]:
        if not value or not isinstance(value, str):
            return value

        idx = value.find('{{', 0)
        while idx >= 0:
            idx_end = value.find('}}', idx)
            if idx_end > idx + 2:
                nested_var = value[idx+2: idx_end]
                if nested_var in self:
                    nested_value = self.get(nested_var)
                    if isinstance(nested_value, dict):
                        nested_value = json.dumps(nested_value, indent=0)
                    value = value.replace('{{' + str(nested_var) + '}}', str(nested_value))
                    idx = 0

            idx = value.find('{{', idx + 2)
        return value

    def get(self, key: str, default=None) -> Optional:
        if key not in self._variables:
            return self.resolve(default)
        return self.resolve(self._variables[key])

    def __getitem__(self, key: str):
        return self.resolve(self._variables[key])

    def __contains__(self, item):
        return self._variables.__contains__(item)

    def set(self, key: str, value):
        self._variables[key] = value

    def __setitem__(self, key: str, value):
        self._variables[key] = value

    def print(self):
        for k, v in self._variables.items():
            print(f'{k}={v}')

    def enumerate(self):
        for k in self._variables.keys():
            yield k, self.get(k)

    def copy(self):
        new_inst = Variables()
        new_inst._variables = self._variables.copy()
        return new_inst

    @contextmanager
    def scoped_update(self, **kwargs):
        origin_variables = self._variables.copy()
        self.update(**kwargs)
        yield self
        self._variables = origin_variables

    def __str__(self):
        return self._variables.__str__()

    def __repr__(self):
        return self._variables.__repr__()


class CmdLineSpecialVar:
    """
    These are internal variables used to setup parameters for the run
    """

    timeout_request_key = '___param_timeout_request'
    """ timeout in seconds for the server to issue a response  """

    headers_key = '___param_headers'
    """ custom to put for each request make (can be overridden add test level) """

    log_request_level_key = '___param_log_request'
    """ 0 nothing, 1: one line summary, 2: complete request/response headers and payload """

    disable_ssl_validation_key = '___param_disable_ssl_validation'
    """ boolean, to disable or not the ssl validation """

    retry_on_error_key = '___param_retry_on_error'
    """ list of error code on to enable retry strategy (limited to 4 attempts) """

    @staticmethod
    def set_timeout_request(variables: Variables, value: int):
        variables.set(CmdLineSpecialVar.timeout_request_key, value)

    @staticmethod
    def get_timeout_request(variables: Variables):
        return variables.get(CmdLineSpecialVar.timeout_request_key, default=0)

    @staticmethod
    def set_retry_on_error(variables: Variables, list_of_status_code):
        variables.set(CmdLineSpecialVar.retry_on_error_key, [int(s) for s in list_of_status_code])

    @staticmethod
    def get_retry_on_error(variables: Variables):
        return variables.get(CmdLineSpecialVar.retry_on_error_key, default=[])

    @staticmethod
    def set_disable_ssl_validation(variables: Variables, value: bool):
        variables.set(CmdLineSpecialVar.disable_ssl_validation_key, value)

    @staticmethod
    def get_disable_ssl_validation(variables: Variables):
        return variables.get(CmdLineSpecialVar.disable_ssl_validation_key, default=False)

    @staticmethod
    def set_log_request_level(variables: Variables, value: int):
        variables.set(CmdLineSpecialVar.log_request_level_key, value)

    @staticmethod
    def get_log_request_level(variables: Variables):
        return variables.get(CmdLineSpecialVar.log_request_level_key, default=1)

    @staticmethod
    def set_headers(variables: Variables, value: dict):
        variables.set(CmdLineSpecialVar.headers_key, value)

    @staticmethod
    def get_headers(variables: Variables):
        return variables.get(CmdLineSpecialVar.headers_key, default={})
