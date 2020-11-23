from fastapi import APIRouter

# Routes require for the liveliness ('/healthz') and readiness ('/healthz') probes for kubernetes
# The root route ('/') is needs for the liveliness of the Google loadbalancer
# which doesn't take into account the ones defined in the yaml deployment file


router = APIRouter()


@router.get("/healthz", include_in_schema=False)
async def health():
    return {'status': 'healthy'}


@router.get("/readiness", include_in_schema=False)
async def readiness():
    return {'status': 'healthy'}


@router.get("/", include_in_schema=False)
async def ingress_gce_health():
    return {'status': 'healthy'}
