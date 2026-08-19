from typing import Optional, NamedTuple


class BulkStorageVersion(NamedTuple):
    """ This is the version of the bulk storage engine """

    version: str
    """ unique version identifier """

    uri_prefix: Optional[str]
    """ associated uri prefix """


BulkStorageVersion_V0 = BulkStorageVersion(version='0', uri_prefix=None)
""" first bulk management implementation with direct management to blob storage with a single blob """

BulkStorageVersion_V1 = BulkStorageVersion(version='1', uri_prefix="wdms-1")
""" version 1, using Dask to handle bulk manipulation and storage """

BulkStorageVersion_Invalid = BulkStorageVersion(version='', uri_prefix=None)
""" represent an invalid/undefined storage version """
