import dask

from ..temp_dir import get_temp_dir

dask.config.set({'temporary_directory': get_temp_dir()})
