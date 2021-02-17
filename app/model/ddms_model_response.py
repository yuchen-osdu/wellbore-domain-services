from __future__ import annotations
from typing import List, Optional
from pydantic import Field

from app.model.model_curated import DDMSBaseModel


class AboutResponseUser(DDMSBaseModel):
    tenant: Optional[str] = None
    email: Optional[str] = None


class V1DmsInfo(DDMSBaseModel):
    kinds: Optional[List[str]] = None


class V1AboutResponse(DDMSBaseModel):
    user: Optional[AboutResponseUser] = None
    dmsInfo: Optional[V1DmsInfo] = None


class FastSearchResponse(DDMSBaseModel):
    results: Optional[List[str]] = None

#unused after revert on bug 602935
class WriteDataResponse(DDMSBaseModel):
    rowCount: Optional[int] = Field(..., description="Row count")
    columnCount: Optional[int] = Field(..., description="Column count")

