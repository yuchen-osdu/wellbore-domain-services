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

from enum import Enum
from typing import Union


class JSONOrient(Enum):
    # not allow 'table' because very verbose then comes with significant overhead
    split = "split"
    index = "index"
    columns = "columns"
    records = "records"
    values = "values"

    @classmethod
    def get(cls, orient: Union[str, "JSONOrient"]) -> "JSONOrient":
        return JSONOrient[orient] if isinstance(orient, str) else orient
