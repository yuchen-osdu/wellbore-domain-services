from fastapi import APIRouter
from starlette.responses import RedirectResponse

router = APIRouter()


@router.get("/token", include_in_schema=False)
async def get_auth_token():
    return RedirectResponse('https://oauth-gen-python-dot-opendes.appspot.com/provider')
