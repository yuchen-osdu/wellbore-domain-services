from enum import Enum
from pydantic import BaseModel
from typing import List
from datetime import datetime


class BulkStatisticsStatus(str, Enum):
    Error = 'error'
    Started = 'started'
    Running = 'running'
    Complete = 'complete'


class BulkDataStatistics(BaseModel):
    columns: List[str]
    index: List[str]
    data: List[List[float]]


class BulkDataStatisticsMeta(BaseModel):
    creation_utc_date: datetime
    record_id: str
    record_version: str
    computation_status: BulkStatisticsStatus


class BulkDataStatisticsResponse(BulkDataStatisticsMeta):
    data: dict
