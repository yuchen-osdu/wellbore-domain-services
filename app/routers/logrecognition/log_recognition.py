from fastapi import APIRouter, Depends, HTTPException
from app.utils import Context
from app.utils import get_ctx
import starlette.status as status
from pydantic import BaseModel
from typing import Optional
from far import family_processor as family_processor
import far.family_processor.model as farmodel
router = APIRouter()


class LogrecognitionService:
    #NOSONAR
    class __OnlyOne:
        def __init__(self):
            self.family_processor = family_processor.make_family_processor()

    instance = None

    def __init__(self):
        if not LogrecognitionService.instance:
            LogrecognitionService.instance = LogrecognitionService.__OnlyOne()

    def get_family_processor(self):
        return LogrecognitionService.instance.family_processor


async def get_logrecognition_service(ctx: Context = Depends(get_ctx)) -> LogrecognitionService:
    return LogrecognitionService()


class GuessRequest(BaseModel):
    label: str  # Channel name, as defined in LAS or DLIS
    log_unit: Optional[str] = None  # Channel unit, as defined in LAS or DLIS
    description: Optional[str] = None  # Channel description, as defined in LAS or DLIS
    class Config:
        schema_extra = {
            "example": {
                "label": "GR",
                "log_unit": "gApi",
                "description": "",
            }
        }



class GuessResponse(BaseModel):
    family: Optional[str] = None  # Guessed family
    family_type: Optional[str] = None  # Family type corresponding to guessed family
    log_unit: Optional[str] = None  # Guessed log unit
    base_unit: Optional[str] = None  # Unit to convert log


@router.post('/recognize', response_model=GuessResponse,
            summary="Recognize unit and family",
            description="""Find the more probable family and unit""",
            operation_id="recognize")
async def post_recognize(body: GuessRequest,
                    log_recognition_service: LogrecognitionService = Depends(get_logrecognition_service),
                    ctx: Context = Depends(get_ctx)) -> GuessResponse:
    processor = log_recognition_service.get_family_processor()
    result = processor.guess(log_info=farmodel.GuessRequest(**body.dict()))
    if result.error is not None:
        raise HTTPException(status_code=400, detail=result.error)
    response: GuessResponse = GuessResponse(family=result.family, family_type=result.family_type,
                                            log_unit=result.log_unit, base_unit=result.base_unit)
    return response
