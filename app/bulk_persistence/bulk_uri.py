from typing import Optional, Tuple
import uuid

from .bulk_storage_version import (
    BulkStorageVersion, BulkStorageVersion_V0, BulkStorageVersion_V1, BulkStorageVersion_Invalid)


class BulkURI:
    """
    Bulk URI, contains the bulk identifier (bulk_id) and Storage engine version which identifies how
    the bulk is stored.

    Usage:
        - ctor from URI string value:
            `bulk_uri = BulkURI.decode(uri_str)`

        - ctor explicit given a bulk_id and a storage version:
            `bulk_uri = BulkURI(bulk_id=bulk_id_value, version=BulkStorageVersion_V1)`

        - ctor explict using class method:
            `bulk_uri  = BulkURI.from_bulk_storage_V1(bulk_id_value)`

        - encode to URI string value:
            `uri_str: str = bulk_uri.encode()`

        - check which storage engine version is:
            `bulk_uri.storage_version == BulkStorageVersion_V0`
            `bulk_uri.is_bulk_storage_V0()`
    """

    def __init__(self, bulk_id: str, version: BulkStorageVersion):
        """
         make an new one or invalid
         Either pass uri alone or bulk_id, version
         :param bulk_id: expected as a valid uuid
         :param version: storage version
         :throw: ValueError
        """
        if not bulk_id or not version or version == BulkStorageVersion_Invalid:
            bulk_id = ''
            version = BulkStorageVersion_Invalid
        else:
            # ensure valid uuid
            uuid.UUID(bulk_id)

        self._bulk_id = bulk_id
        self._storage_version = version

    @classmethod
    def invalid(cls):
        """ make an invalid instance """
        return cls('', BulkStorageVersion_Invalid)

    @classmethod
    def decode(cls, uri: str) -> 'BulkURI':
        """
         construct a BulkURI from an encoded URI
         :throw: ValueError
        """
        if not uri:
            return BulkURI.invalid()
        bulk_id, prefix = cls._decode_uri(uri)
        if not prefix:
            version = BulkStorageVersion_V0
        elif prefix == BulkStorageVersion_V1.uri_prefix:
            version = BulkStorageVersion_V1
        else:
            raise ValueError('Unsupported prefix in bulk URI: ' + prefix)
        return cls(bulk_id=bulk_id, version=version)

    def is_bulk_storage_V0(self) -> bool:
        """ convenient check that returns True is version == BulkStorageVersions.V0 """
        return self._storage_version.version == BulkStorageVersion_V0.version

    @classmethod
    def from_bulk_storage_V0(cls, bulk_id: str) -> 'BulkURI':
        """ construct a BulkURI for storage engine V0 given a bulk id """
        return cls(bulk_id=bulk_id, version=BulkStorageVersion_V0)

    @classmethod
    def from_bulk_storage_V1(cls, bulk_id: str) -> 'BulkURI':
        """ construct a BulkURI for storage engine V1 given a bulk id """
        return cls(bulk_id=bulk_id, version=BulkStorageVersion_V1)

    @property
    def bulk_id(self) -> str:
        return self._bulk_id

    @property
    def storage_version(self) -> BulkStorageVersion:
        return self._storage_version

    def encode(self) -> str:
        """
        encode to uri as string
        If the prefix is not empty returns, uri format = `urn:$prefix:uuid:$bulk_id`
        If the prefix is empty or None, uri format = `urn:uuid:$bulk_id`
        :Throw: ValueError
        """
        if self._storage_version.uri_prefix:
            return f'urn:{self._storage_version.uri_prefix}:uuid:{self._bulk_id}'
        return uuid.UUID(self._bulk_id).urn

    def encode_for_ddms_datasets(self) -> str:
        """
        encode to uri as string
        If the prefix is not empty returns, uri format = `urn://$prefix/uuid:$bulk_id`
        If the prefix is empty or None, uri format = `urn://uuid:$bulk_id`
        :Throw: ValueError
        """
        if self._storage_version.uri_prefix:
            return f'urn://{self._storage_version.uri_prefix}/uuid:{self._bulk_id}'
        return f'urn://uuid:{self._bulk_id}'

    @classmethod
    def _decode_uri(cls, uri: str) -> Tuple[str, Optional[str]]:
        """
        Decode urn into uuid and optional prefix. Returns tuple [uuid, prefix].
          If urn is `urn:$prefix:uuid:$bulk_id`, will return [$bulk_id, $prefix]
          If urn is `urn:uuid:$bulk_id`, will return [$bulk_id, None]
        :throw: ValueError if urn empty or invalid UUID
        """
        if uri is None:
            raise ValueError('attempted to decode empty urn')
        parts = uri.split(":")
        if len(parts) < 4:
            return str(uuid.UUID(uri)), None
        return str(uuid.UUID(f"{parts[0]}:{parts[-2]}:{parts[-1]}")), ":".join(parts[1:-2])

    def is_valid(self) -> bool:
        """ check invalid """
        if self._bulk_id and self._storage_version.version:
            return True
        return False
