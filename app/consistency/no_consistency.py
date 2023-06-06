from typing import Optional
import pandas as pd
from odes_storage.models import Record
from app.bulk_persistence import DataConsistencyChecks, BulkInfoForConsistency


class NoConsistencyChecks(DataConsistencyChecks):
    @classmethod
    def get_reference_curve(cls, record: Record) -> Optional[str]:
        return None

    @classmethod
    def check_bulk_consistency(cls, record: Record, bulk_info: BulkInfoForConsistency):
        pass

    @classmethod
    async def check_bulk_consistency_on_commit_session(cls, record: Record, new_bulk_id):
        return

    @classmethod
    def check_bulk_consistency_on_post_bulk(cls, record: Record, df: pd.DataFrame):
        return
