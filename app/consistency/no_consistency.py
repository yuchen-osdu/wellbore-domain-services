import pandas as pd
from app.bulk_persistence import DataConsistencyChecks


class NoConsistencyChecks(DataConsistencyChecks):
    @classmethod
    async def check_bulk_consistency_on_commit_session(cls, record: "Record", new_bulk_id):
        return

    @classmethod
    def check_bulk_consistency_on_post_bulk(cls, record: "Record", df: pd.DataFrame):
        return
