from fastapi import Query, Request, HTTPException
from pandas import DataFrame

from app.bulk_persistence.mime_types import MimeType, MimeTypes
from app.bulk_persistence import JSONOrient


def json_orient_parameter(
        orient: JSONOrient = Query(JSONOrient.split, description='format for JSON only.')
) -> JSONOrient:
    return orient


WRITE_BULK_SUPPORTED_MIME_TYPES = [MimeTypes.JSON, MimeTypes.PARQUET]


def write_bulk_content_type(request: Request) -> MimeType:
    content_type = request.headers.get('Content-Type', None)
    try:
        return next(m for m in WRITE_BULK_SUPPORTED_MIME_TYPES if m.match(content_type))
    except:
        raise HTTPException(status_code=400, detail=f'Content-Type invalid: "{content_type}"')


_dataframe_sample = DataFrame(
    [
        [0, 1111.1, 2222.1],
        [0.5, 1111.2, 2222.2],
        [1, 1111.3, 2222.3],
        [1.5, 1111.4, 2222.4],
        [2, 1111.5, 2222.5],
    ],
    columns=["Ref", "col_1", "col_2"],
    index=[0, 1, 2, 3, 4]
)


body_description = """
Contains the data corresponding to the dataframe. The header "Content-Type" must be set accordingly to the format sent:
<br/>&nbsp;**Parquet** format(*application/x-parquet*): see [Apache parquet website](https://parquet.apache.org/).
<br/>&nbsp;**JSON** format (*application/json*): see [Pandas.Dataframe JSON format](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_json.html).
 In that case 'orient' parameter must be provided 
"""
body_description += '.\n Examples in JSON for data with {} rows and {} columns with different _orient_: '.format(
                _dataframe_sample.shape[0],
                _dataframe_sample.shape[1])
body_description += ''.join([f'\n* {o}:  <br/>`{_dataframe_sample.to_json(None, orient=o)}`<br/>&nbsp;'
                     for o in JSONOrient])


REQUEST_DATA_BODY_SCHEMA = {
    'description': body_description,
    # put examples here because of bug in swagger UI to properly render multiple examples
    'required': True,
    'content': {
        'application/json': {
            'schema': {
                # swagger UI bug, so single example here
                'example': _dataframe_sample.to_json(None, orient=JSONOrient.split, indent=2)
            }
        },
        'application/x-parquet': {
            'schema': {'type': 'string', 'format': 'binary'}
        }
    }
}

REQUIRED_ROLES_READ = """
<p>Required roles: 'users.datalake.viewers' or 'users.datalake.editors' or 'users.datalake.admins'.
"In addition, users must be a member of data groups to access the data.</p>
"""

REQUIRED_ROLES_WRITE = "<p>Required roles: 'users.datalake.editors' or 'users.datalake.admins'.</p>"
