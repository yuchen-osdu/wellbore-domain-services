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

import re
import shutil
import sys

FILE_TO_UPDATE = 'app/__init__.py'
VERSION_FIELD_NAME = '__version__'
BUILD_NUMBER_FIELD_NAME = '__build_number__'

FIELDS_TO_CAPTURE = [VERSION_FIELD_NAME, BUILD_NUMBER_FIELD_NAME]

# capture KEY = basic string
regexp_key_value_capture = re.compile(
    "^[\\s]*(" + '|'.join(FIELDS_TO_CAPTURE) + ")[\\s]*=[\\s]*[('\\\")](.+)[('\\\")].*"
)
regexp_key_capture = re.compile(
    "^[\\s]*(" + '|'.join(FIELDS_TO_CAPTURE) + ")[\\s]*=.*"
)


def set_version(file_name: str, *, build_number: str, patch_number: str):
    initial_value = {k: None for k in FIELDS_TO_CAPTURE}
    lines = ['# updated by script -------------------\n', '\n']

    # capture
    with open(file_name) as f:
        for line in f:
            lines.append(line)
            m = regexp_key_value_capture.match(line)
            if m is not None and len(m.groups()) == 2:
                key, value = m.group(1, 2)
                initial_value[key] = value

    # backup
    shutil.copyfile(file_name, file_name + '.bck')

    new_values = {
        VERSION_FIELD_NAME: '"' + initial_value[VERSION_FIELD_NAME] + f'.{patch_number or "0000"}' + '"',
        BUILD_NUMBER_FIELD_NAME: f'"{build_number or "unknown"}"',
    }

    with open(file_name, 'w') as f:
        for line in lines:
            m = regexp_key_capture.match(line)
            if m is not None:
                key = m.group(1)
                if key in new_values:
                    f.write('# was: ' + line)
                    line = f'{key} = {new_values[key]}\n\n'
            f.write(line)  # other line kept untouched


if __name__ == "__main__":
    kwargs = {arg.split('=')[0]: arg.split('=')[1] for arg in sys.argv[1:]}
    assert 'build_number' in kwargs and 'patch_number' in kwargs, 'build_number and patch_number must be defined'
    set_version(FILE_TO_UPDATE, build_number=kwargs['build_number'], patch_number=kwargs['patch_number'])
