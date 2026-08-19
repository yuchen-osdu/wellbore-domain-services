import tempfile
from os import path, makedirs


def _setup_temp_dir() -> str:
    tmpdir = tempfile.gettempdir()
    if not tmpdir.endswith('wdmsosdu'):
        tmpdir = path.join(tmpdir, 'wdmsosdu')
        makedirs(tmpdir, exist_ok=True)
        tempfile.tempdir = tmpdir
    return tmpdir


_TEMP_DIR = _setup_temp_dir()


def get_temp_dir():
    return _TEMP_DIR
