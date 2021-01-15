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
