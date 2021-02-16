from fastapi import Query
from app.bulk_persistence import JSONOrient

def json_orient_parameter(orient: str = Query(
        JSONOrient.split.value,
        description='define format when using JSON data is used. Value can be ' + ', '.join([o.value for o in JSONOrient]),
        regex="|".join([o.value for o in JSONOrient])
    )
) -> str:
    return orient
