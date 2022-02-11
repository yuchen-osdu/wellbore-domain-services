from abc import ABC, abstractmethod

import pandas as pd


class ConsistencyException(RuntimeError):
    pass


class DataConsistencyChecks(ABC):
    @classmethod
    async def check_bulk_consistency_on_commit_session(cls, record: "Record", new_bulk_id):
        pass

    @classmethod
    def check_bulk_consistency_on_post_bulk(cls, record: "Record", df: pd.DataFrame):
        pass


class NoConsistencyChecks(DataConsistencyChecks):
    @classmethod
    async def check_bulk_consistency_on_commit_session(cls, record: "Record", new_bulk_id):
        return

    @classmethod
    def check_bulk_consistency_on_post_bulk(cls, record: "Record", df: pd.DataFrame):
        return
