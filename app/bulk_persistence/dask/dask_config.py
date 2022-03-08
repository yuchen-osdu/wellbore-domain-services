import dask

from ..wdms_temp_dir import get_wdms_temp_dir

dask.config.set({'temporary_directory': get_wdms_temp_dir()})
