from abc import ABC, abstractmethod
import pandas as pd
from fastapi import status

from .dask.errors import BulkError


class ConsistencyException(BulkError):
    http_status = status.HTTP_400_BAD_REQUEST
    pass


class DataConsistencyChecks(ABC):
    @classmethod
    async def check_bulk_consistency_on_commit_session(cls, record: "Record", new_bulk_id):
        pass

    @classmethod
    def check_bulk_consistency_on_post_bulk(cls, record: "Record", df: pd.DataFrame):
        pass



