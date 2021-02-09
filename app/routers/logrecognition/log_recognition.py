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

import far.family_processor.model as farmodel
from fastapi import APIRouter, Depends, HTTPException
from starlette import status
from typing import Optional, List
from pydantic import BaseModel, Field
import odes_storage.models as model

import app.routers.logrecognition.family_processor_manager as fp_manager
from app.clients.storage_service_client import get_storage_record_service
from app.conf import Config
from app.utils import Context
from app.utils import get_ctx

router = APIRouter()


class CatalogItem(BaseModel):
    unit: str
    family: Optional[str] = ""
    rule: str


class MainFanilyCatalogItem(BaseModel):
    MainFamily: str
    Family: str
    Unit: str


class Catalog(BaseModel):
    family_catalog: List[CatalogItem]
    main_family_catalog: Optional[List[MainFanilyCatalogItem]] = None


class CatalogRecord(BaseModel):
    acl: "model.StorageAcl" = Field(..., alias="acl")
    legal: "model.Legal" = Field(..., alias="legal")
    data: "Catalog" = Field(..., alias="data")

    class Config:
        schema_extra = {
            "example": {
                "acl": {
                    "viewers": [
                        "abc@slb.com, cde@slb.com"
                    ],
                    "owners": [
                        "abc@slb.com, cde@slb.com"
                    ]
                },
                "legal": {
                    "legaltags": [
                        "opendes-public-usa-dataset-1"
                    ],
                    "otherRelevantDataCountries": [
                        "US"
                    ]
                },
                "data": {
                    "family_catalog": [
                        {
                            "unit": "ohm.m",
                            "family": "Medium Resistivity",
                            "rule": "MEDR"
                        }
                    ],
                    "main_family_catalog": [
                        {
                            "MainFamily": "Resistivity",
                            "Family": "Medium Resistivity",
                            "Unit": "OHMM"
                        }
                    ]
                }
            }
        }


family_processor_manager = fp_manager.FamilyProcessorManager(Config.custom_catalog_timeout.value)


class GuessRequest(BaseModel):
    label: str  # Channel name, as defined in LAS or DLIS
    log_unit: Optional[str] = None  # Channel unit, as defined in LAS or DLIS
    description: Optional[str] = None  # Channel description, as defined in LAS or DLIS

    class Config:
        schema_extra = {
            "example": {
                "label": "GRD",
                "log_unit": "GAPI",
                "description": "LDTD Gamma Ray",
            }
        }


class GuessResponse(BaseModel):
    family: Optional[str] = None  # Guessed family
    family_type: Optional[List[str]] = None  # Family type corresponding to guessed family
    log_unit: Optional[str] = None  # Guessed log unit
    base_unit: Optional[str] = None  # Unit to convert log


@router.post('/family', response_model=GuessResponse,
             summary="Recognize family and unit",
             description="Find the most probable family and unit using family assignment rule based catalogs. "
                         "User defined catalog will have the priority.",
             operation_id="family")
async def post_recognize_custom(body: GuessRequest,
                                ctx: Context = Depends(get_ctx)) -> GuessResponse:
    processor = await family_processor_manager.get_processor(ctx, ctx.partition_id)
    result = processor.guess(log_info=farmodel.GuessRequest(**body.dict()))
    if result.error is not None:
        # Try with the default catalog
        default_processor = family_processor_manager.get_default_processor()
        result = default_processor.guess(log_info=farmodel.GuessRequest(**body.dict()))
        if result.error is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error)

    # family_processor_manager can return a 'str' or a 'List[str]', ensure in any case a List[str] is returned
    if isinstance(result.family_type, str):
        result.family_type = [result.family_type]

    response: GuessResponse = GuessResponse(family=result.family,
                                            family_type=result.family_type,
                                            log_unit=result.log_unit,
                                            base_unit=result.base_unit)
    return response


@router.put('/upload-catalog',
            response_model=model.CreateUpdateRecordsResponse,
            summary="Upload user-defined catalog with family assignment rules",
            description="""Upload user-defined catalog with family assignment rules for specific partition ID. 
            If there is an existing catalog, it will be replaced. It takes maximum of 5 mins to replace the existing catalog. 
            Hence, any call to retrieve the family should be made after 5 mins of uploading the catalog""",
            operation_id="upload-catalog")
async def upload_catalog(body: CatalogRecord,
                         ctx: Context = Depends(get_ctx)) -> model.CreateUpdateRecordsResponse:
    storage_client = await get_storage_record_service(ctx)
    # force the id
    record = model.Record(**body.dict(by_alias=True),
                          id=f"{ctx.partition_id}{fp_manager.FIXED_RECORD_ID}",
                          kind=f"{ctx.partition_id}:wdms:familycatalog:1.0.0"
                          )
    response = await storage_client.create_or_update_records(ctx.partition_id, record=[record])
    return response
