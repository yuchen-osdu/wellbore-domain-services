from enum import Enum
from pydantic import BaseModel
from typing import List
from datetime import datetime


class BulkStatisticsStatus(str, Enum):
    """ Status available for computation of bulk data statistics"""
    Error = 'error'
    Started = 'started'
    Running = 'running'
    Complete = 'complete'


# class BulkDataStatisticsSplit(BaseModel):
#     columns: List[str]
#     index: List[str]
#     data: List[List[float]]


class BulkDataStatisticsMeta(BaseModel):
    """ Meta data of computation for bulk data statistics """
    creation_utc_date: datetime
    record_id: str
    record_version: str
    computation_status: BulkStatisticsStatus


class BulkDataStatisticsResponse(BulkDataStatisticsMeta):
    """ Status available for computation of bulk data statistics"""

    # leave undefined model for now
    # todo: choose
    data: dict
