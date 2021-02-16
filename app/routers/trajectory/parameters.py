from fastapi import Query
from app.bulk_persistence import JSONOrient


acceptable_values = [o.value for o in JSONOrient if o.value is not "values"]

def trajectory_json_orient_parameter(orient: str = Query(
    JSONOrient.split.value,
    description='define format when using JSON data is used. Value can be ' + ', '.join(acceptable_values),
    regex="|".join(acceptable_values)
)
) -> str:
    return orient
