from enum import Enum
from typing import Union


class JSONOrient(Enum):
    # not allow 'table' because very verbose then comes with significant overhead
    split = "split"
    index = "index"
    columns = "columns"
    records = "records"
    values = "values"

    @classmethod
    def get(cls, orient: Union[str, "JSONOrient"]) -> "JSONOrient":
        return JSONOrient[orient] if isinstance(orient, str) else orient
