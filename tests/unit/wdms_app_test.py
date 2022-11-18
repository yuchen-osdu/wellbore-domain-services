import pytest


@pytest.mark.anyio
async def test_wdms_app_initialized_via_about(
    app_initialized_with_testclient,
):
    """Test wdms_app configuration"""

    _, client = app_initialized_with_testclient

    assert (await client.get("/about")).status_code == 200



async def test_wdms_app_configure_via_version(
    app_configurable_with_testclient,
):
    """Test wdms_app configuration"""

    _, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True
    )

    assert (await client.get("/version")).status_code == 200
