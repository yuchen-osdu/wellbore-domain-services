def test_base_app_initialized_via_about(
    base_app_initialized_with_testclient,
):
    """Test base_app via wdms_app routes"""

    base_client = base_app_initialized_with_testclient

    assert base_client.get("/api/os-wellbore-ddms/about").status_code == 200
