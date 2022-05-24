from starlette.requests import Request


def set_statistics_computation_enabled(request: Request):
    """
    Set as enabled the computation of statistics for routers calling it as Depends().
    Router's endpoints can use it as "Depends(statistics_computation_enabled)" to retrieve value of attribute
    """
    request.state.enable_stats_computation = True


def is_statistics_computation_enabled(request: Request):
    """ To be used in bulk router's endpoints to get if statistics computation is required """
    return getattr(request.state, 'enable_stats_computation', False)