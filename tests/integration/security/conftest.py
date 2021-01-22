

def pytest_addoption(parser):
    parser.addoption("--base_url", action="store")
    parser.addoption("--check_cert", action="store", default=True)
    parser.addoption("--token", action="store")


def pytest_generate_tests(metafunc):
    base_url = metafunc.config.getoption("base_url")
    verify_cert = bool(metafunc.config.getoption('check_cert'))
    token = metafunc.config.getoption("token")
    metafunc.parametrize(
        'base_url, check_cert, token',
        [(base_url, verify_cert, token)])
