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

from app.bulk_persistence import create_and_store_dataframe
import pandas as pd
from app.bulk_persistence import get_dataframe

from odes_storage.models import Record
from app.utils import Context

from app.model.log_bulk import LogBulkHelper


class Persistence:
    @classmethod
    async def read_bulk(
        cls,
        ctx: Context,
        record: Record,
        bulk_id_path: str,
    ) -> pd.DataFrame:
        bulk_id = LogBulkHelper.get_bulk_id(record, bulk_id_path)
        if bulk_id is None:
            return pd.DataFrame()

        return await get_dataframe(ctx, bulk_id)

    @classmethod
    async def write_bulk(cls, ctx: Context, dataframe) -> str:
        return await create_and_store_dataframe(ctx, dataframe)
