import pytest
from app.routers.bulk.bulk_routes import router
from app.routers.ddms_v2 import log_ddms_v2
from app.routers.ddms_v3 import wellbore_trajectory_ddms_v3, welllog_ddms_v3
from app.wdms_app import wdms_app, ALPHA_APIS_PREFIX, DDMS_V2_PATH, DDMS_V3_PATH

from ..test_utils import gen_all_routes_request

base_paths = [
    DDMS_V3_PATH + welllog_ddms_v3.WELL_LOGS_API_BASE_PATH,
    DDMS_V3_PATH + wellbore_trajectory_ddms_v3.WELLBORE_TRAJECTORIES_API_BASE_PATH,
    ALPHA_APIS_PREFIX + DDMS_V2_PATH + log_ddms_v2.LOGS_API_BASE_PATH
]
bulk_routes_path = [(route.path, route.methods) for route in router.routes]


@pytest.fixture()
def dependencies_check_app(app_configurable_with_testclient):

    from app.routers.bulk.utils import set_legacy_input_dataframe_check, set_v3_input_dataframe_check

    app, client = app_configurable_with_testclient(fake_data_partition_id=True,
                                                   disable_bulk_consistency=True)

    # app dependency_overrides will be restored by the fixture after the test.
    # we can modify them here for our needs

    async def expected_legacy_check_func():
        raise ArithmeticError("I'm raising for legacy injection")

    async def expected_v3_check_func():
        raise RuntimeError("I'm raising for v3 injection")

    app.dependency_overrides[set_legacy_input_dataframe_check] = expected_legacy_check_func
    app.dependency_overrides[set_v3_input_dataframe_check] = expected_v3_check_func

    return client


def _is_trajectories_v3_route(route_url: str):
    """ Return true if given route_url is OSDU Trajectory v3 api """
    return route_url.startswith(DDMS_V3_PATH + wellbore_trajectory_ddms_v3.WELLBORE_TRAJECTORIES_API_BASE_PATH)


def _is_welllogs_v3_route(route_url: str):
    """ Return true if given route_url is OSDU WellLog v3 api """
    return route_url.startswith(DDMS_V3_PATH + welllog_ddms_v3.WELL_LOGS_API_BASE_PATH)


@pytest.mark.parametrize("route_url,method", list(gen_all_routes_request(wdms_app)))
def test_ensure_bulk_apis_dependencies_injection(dependencies_check_app, route_url, method):
    client = dependencies_check_app

    bulk_paths = bulk_routes_path
    all_bulk_paths = {prefix + router_path: methods for prefix in base_paths for router_path, methods in bulk_paths}

    if route_url in all_bulk_paths.keys() and method in all_bulk_paths[route_url]:
        if _is_welllogs_v3_route(route_url) or _is_trajectories_v3_route(route_url):
            with pytest.raises(RuntimeError):
                client.request(method, route_url)
        elif ALPHA_APIS_PREFIX + DDMS_V2_PATH + log_ddms_v2.LOGS_API_BASE_PATH in route_url:
            with pytest.raises(ArithmeticError):
                client.request(method, route_url)
        else:
            pytest.fail(f"bulk API with unknown prefix: '{route_url}'")
