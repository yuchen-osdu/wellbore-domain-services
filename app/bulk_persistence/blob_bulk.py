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

from dataclasses import dataclass
from typing import Any


@dataclass
class BlobBulk:
    """
    represents a bulk bloblified, which means serialized in some way. data is expected to be an io.IOBase
    """

    id: str
    """ identifier """
    data: Any = None
    """ data as file-like object """
    content_type: str | None = None
    metadata: dict | None = None
