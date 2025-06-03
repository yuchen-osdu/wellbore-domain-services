from prometheus_fastapi_instrumentator import Instrumentator
from app.conf import Config

def init_metric(wdms_app):
    if Config.cloud_provider.value == 'az':
        Instrumentator().instrument(wdms_app).expose(wdms_app)
