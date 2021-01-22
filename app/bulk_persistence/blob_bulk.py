from dataclasses import dataclass
from typing import Any


@dataclass
class BlobBulk:
    """
    represents a bulk bloblified, which means serialized in some way. data is expected to be an io.IOBase
    """

    id: str
    """ identifier """
    data: Any = None
    """ data as file-like object """
    content_type: str = None
    metadata: dict = None
