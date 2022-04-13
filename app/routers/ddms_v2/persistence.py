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

import pandas as pd

from odes_storage.models import Record

from app.bulk_persistence import create_and_store_dataframe, get_dataframe, trace_dataframe_attributes
from app.context import Context
from app.model.log_bulk import LogBulkHelper

from app.helper.traces import with_trace
from app.helper.logger import get_logger


class Persistence:
    @classmethod
    @with_trace("read_bulk")
    async def read_bulk(
        cls,
        ctx: Context,
        record: Record,
        bulk_id_path: str,
    ) -> pd.DataFrame:
        bulk_uri = LogBulkHelper.get_bulk_uri(record, bulk_id_path)
        # TODO use prefix to know how to read the bulk
        if not bulk_uri.is_valid():
            return pd.DataFrame()

        result_df = await get_dataframe(ctx, bulk_uri.bulk_id)
        trace_dataframe_attributes(result_df)
        return result_df

    @classmethod
    @with_trace("write_bulk")
    async def write_bulk(cls, ctx: Context, dataframe) -> str:
        trace_dataframe_attributes(dataframe)
        try:
            return await create_and_store_dataframe(ctx, dataframe)
        except Exception:
            get_logger().exception("write_bulk")
            raise
