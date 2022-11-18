
def test_base_app_initialized_via_about(
    base_app_initialized_with_testclient,
):
    """Test base_app via wdms_app routes"""

    app, base_client = base_app_initialized_with_testclient

    res = base_client.get("/api/os-wellbore-ddms/about")
    assert res.status_code == 200
