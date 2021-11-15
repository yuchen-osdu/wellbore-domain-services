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
from app.bulk_persistence import BulkId, NoBulkException, UnknownChannelsException, InvalidBulkException
from app.model.model_curated import trajectory as Trajectory

from app.bulk_persistence import get_dataframe, create_and_store_dataframe

from app.utils import Context

TrajectoryId = str


class Persistence:
    """Gets the bulk data for the trajectory

    Args:
    record (Trajectory): trajectory record to get the bulkd data
    channels (list[str]): Filters the channel to be returned, if none return all channels

    Returns:
    pandas.Dataframe: containing bulkd data for the specified record

    Raises:
    NoBulkException: record doesn't have any bulk.
    InvalidBulkException: value of data.bulkURI in record is invalid.
    """
    @classmethod
    async def read_bulk(
        cls, ctx: Context, record: Trajectory, channels=None
    ) -> pd.DataFrame:

        if record.data is None or not hasattr(record.data,'bulkURI') or record.data.bulkURI is None:  # todo what about empty string
            raise NoBulkException

        try:
            bulkid, _prefix = BulkId.bulk_urn_decode(record.data.bulkURI)
            # TODO use prefix to know how to read the bulk
            df = await get_dataframe(ctx, bulkid)
        except Exception as ex:
            raise InvalidBulkException(ex) from ex

        if not channels:
            return df

        try:
            return df[channels]
        except KeyError as key_error:  # unknown channels
            raise UnknownChannelsException(key_error)


    @classmethod
    async def write_bulk(cls, ctx, dataframe: pd.DataFrame) -> str:
        bulk_id = await create_and_store_dataframe(ctx, dataframe)
        return BulkId.bulk_urn_encode(bulk_id)
