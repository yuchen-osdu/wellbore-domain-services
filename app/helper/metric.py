from prometheus_fastapi_instrumentator import Instrumentator
from app.conf import Config

def init_metric(wdms_app, logger):
    """
    Initialize Prometheus metrics instrumentation for the FastAPI app.

    This function adds Prometheus monitoring middleware to the FastAPI application
    if the configured cloud provider is Azure ('az').

    Args:
        wdms_app: The wdms application instance to instrument.
        logger: Logger instance.
    """
    if Config.cloud_provider.value == 'az':
        logger.info("Initializing Prometheus metrics instrumentation for Azure cloud provider.")
        Instrumentator().instrument(wdms_app).expose(wdms_app)
