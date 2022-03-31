from app.conf import Config
from prometheus_fastapi_instrumentator import Instrumentator

def init_metric(wdms_app):

    if Config.cloud_provider.value == 'az':
         Instrumentator().instrument(wdms_app).expose(wdms_app)