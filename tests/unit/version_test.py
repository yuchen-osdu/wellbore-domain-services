from app import __version__, __build_number__, __app_name__
import re


# to ensure info are ok
def test_version_info():
    assert __version__ is not None
    assert type(__version__) == str

    #NOSONAR
    regex = re.compile('^(\\d+)(.\\d+)*$')
    assert regex.match(__version__)

    assert type(__build_number__) == str
    assert __build_number__ is not None

    assert type(__app_name__) == str
    assert __app_name__ is not None
