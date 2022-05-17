from enum import Enum
from typing import Dict

from pydantic import BaseModel, Field
from datetime import datetime


class BulkStatisticsStatus(str, Enum):
    """ Status available for computation of bulk data statistics"""
    Error = 'error'
    Started = 'started'
    Running = 'running'
    Complete = 'complete'


class StatisticsComputationMeta(BaseModel):
    """ Meta data of computation for bulk data statistics """
    computation_start_date: datetime = Field(title="Statistics computation start datetime in ISO format",
                                             alias="computationStartDate")
    record_id: str = Field(alias="recordId")
    record_version: str = Field(alias="recordVersion")
    computation_status: BulkStatisticsStatus = Field(alias="computationStatus")


class InternalStatisticsComputationMeta(BaseModel):
    meta: StatisticsComputationMeta
    computation_attempt: int = Field(alias="computationAttempt")
    last_computation_date: datetime = Field(title="Datetime of last computation run. Internal usage",
                                            alias="lastComputationDate")


class CurveStatistics(BaseModel):
    mean: str = Field(title="Mean value")
    std: str = Field(title="Standard deviation value")
    min: str = Field(title="Maximum value")
    p_10: str = Field(alias="10%", title="10th percentiles")
    p_50: str = Field(alias="50%", title="50th percentiles")
    p_90: str = Field(alias="90%", title="50th percentiles")
    max: str = Field(title="Minimum value")
    total_count: str = Field(title="Number of values in the curve")
    non_absent_values_count: str = Field(title="Number of valid values in the curve")


class BulkDataStatisticsResponse(StatisticsComputationMeta):
    """ Response for bulk data statistics and its meta-data """

    data: Dict[str, CurveStatistics] = Field(title="Curves statistics' values",
                                             example="{'MyCurveName': {'count': '499579.0',"
                                                     "'mean': '450.1040135794339',"
                                                     "'std': '317.570786686891',"
                                                     "'min': '-99.0', "
                                                     "'10%': '11.0', "
                                                     "'50%': '451.0',"
                                                     "'90%': '891.0',"
                                                     "'max': '999.0',"
                                                     "'total_count': 1000000}}")

    class Config:
        schema_extra = {
            "example": {
                'creation_utc_date': '2022-04-27 11:46:58.708615',
                'record_id': 'my-record-id',
                'record_version': '123456789',
                'computation_status': 'complete',
                'data': {'ARR[0]': {'count': '499579.0',
                                    'mean': '450.1040135794339',
                                    'std': '317.570786686891',
                                    'min': '-99.0',
                                    '10%': '11.0',
                                    '50%': '451.0',
                                    '90%': '891.0',
                                    'max': '999.0',
                                    'total_count': 1000000},
                         'ARR[1]': {'count': '1000000.0',
                                    'mean': '449.82156',
                                    'std': '317.4500948207909',
                                    'min': '-100.0',
                                    '10%': '10.0',
                                    '50%': '450.0',
                                    '90%': '890.0',
                                    'max': '999.0',
                                    'total_count': 1000000},
                         'ARR[2]': {'count': '1000000.0',
                                    'mean': '449.189524',
                                    'std': '317.43579447840636',
                                    'min': '-100.0',
                                    '10%': '10.0',
                                    '50%': '449.0',
                                    '90%': '889.0',
                                    'max': '999.0',
                                    'total_count': 1000000},
                         'ARR[3]': {'count': '499811.0',
                                    'mean': '449.513766203625',
                                    'std': '317.39295021204254',
                                    'min': '-99.0',
                                    '10%': '9.0',
                                    '50%': '449.0',
                                    '90%': '889.0',
                                    'max': '999.0',
                                    'total_count': 1000000}}
            }
        }
