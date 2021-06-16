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

import uuid
from typing import Tuple


class BulkId:
    @staticmethod
    def new_bulk_id() -> str:
        return str(uuid.uuid4())

    @classmethod
    def bulk_urn_encode(cls, bulk_id: str, prefix: str = None) -> str:
        if prefix:
            return f'urn:{prefix}:uuid:{uuid.UUID(bulk_id)}'
        return uuid.UUID(bulk_id).urn


    # Returns a tuple (<uuid> : str, <prefix> : str)
    @classmethod
    def bulk_urn_decode(cls, urn: str) -> Tuple[str, str]:
        parts = urn.split(":")
        if len(parts) < 4:
            return str(uuid.UUID(urn)), None
        return str(uuid.UUID(f"{parts[0]}:{parts[-2]}:{parts[-1]}")), ":".join(parts[1:-2])
