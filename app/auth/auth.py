from cachetools import TTLCache
from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from starlette.authentication import AuthCredentials
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED
from app.model.user import User
from app.utils import Context, async_with_cache
from app.helper import logger
import jwt

# manually using basic global cache for now as decorator doesn't work with coroutine
_user_info_cache = TTLCache(maxsize=512, ttl=60, getsizeof=lambda x: 1)


# Make the name very explicit for now
class OpenDESBearerToken(HTTPBearer):
    pass


security = OpenDESBearerToken()


async def require_opendes_authorized_user(request: Request,
                                          credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    ctx = Context.current()

    user = await _get_user_from_token(ctx, token)
    request.scope['auth'] = AuthCredentials(['authenticated'])
    request.scope['user'] = user

    Context.set_current_with_value(auth=token, user=user)


async def _get_user_from_token(ctx: Context, token: str) -> User:
    global _user_info_cache
    cache_key: str = token
    return await async_with_cache(_user_info_cache, cache_key, get_user_from_token_not_cached, ctx, token)


async def get_user_from_token_not_cached(ctx: Context, token: str) -> User:
    # TODO REAL entitlement call is needed here, for now basic decode without verify
    try:
        token_payload = jwt.decode(token, verify=False)
        email = token_payload['email']
    except (KeyError, PyJWTError):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail='invalid token',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    groups = []
    return User(email=email, authenticated=True, groups=groups)
