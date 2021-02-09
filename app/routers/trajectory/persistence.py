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
import starlette.status as status
from app.bulk_persistence import BulkId
from app.model.model_curated import trajectory as Trajectory

from app.bulk_persistence import get_dataframe, create_and_store_dataframe

from app.utils import Context
from fastapi import HTTPException

TrajectoryId = str


class Persistence:
    @classmethod
    async def read_bulk(
        cls, ctx: Context, record: Trajectory, channels=None
    ) -> pd.DataFrame:

        if record.data is None or not hasattr(record.data, 'bulkURI') or record.data.bulkURI is None: # todo what abou tempty string
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No data")

        df = await get_dataframe(ctx, BulkId.bulk_urn_decode(record.data.bulkURI))

        if not channels:
            return df

        try:
            return df[channels]
        except KeyError as key_error:  # unknown channels
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"{key_error}"
            ) from key_error


    @classmethod
    async def write_bulk(cls, ctx, dataframe: pd.DataFrame) -> str:
        bulk_id = await create_and_store_dataframe(ctx, dataframe)
        return BulkId.bulk_urn_encode(bulk_id)
