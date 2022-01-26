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

from app import __version__, __build_number__, __app_name__
import re
from sys import version_info


# to ensure info are ok
def test_version_info():
    assert __version__ is not None
    assert type(__version__) == str

    #NOSONAR
    regex = re.compile('^(\\d+)(.\\d+)*$')
    assert regex.match(__version__)

    assert type(__build_number__) == str
    assert __build_number__ is not None

    assert type(__app_name__) == str
    assert __app_name__ is not None


def test_python_version():
    assert version_info.major == 3 and version_info.minor >= 8, 'Python version required >=3.8'
