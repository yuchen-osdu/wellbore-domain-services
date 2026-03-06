from fastapi import Query, Request, HTTPException, status
from pandas import DataFrame

from app.bulk_persistence import MimeType, MimeTypes
from app.bulk_persistence import JSONOrient


def json_orient_parameter(
        orient: JSONOrient = Query(JSONOrient.split, description='format for JSON only.')
) -> JSONOrient:
    return orient


WRITE_BULK_SUPPORTED_MIME_TYPES = [MimeTypes.JSON, MimeTypes.PARQUET]
READ_BULK_SUPPORTED_MIME_TYPES = [MimeTypes.PARQUET, MimeTypes.JSON]  # by priority order


def write_bulk_content_type(request: Request) -> MimeType:
    content_type = request.headers.get('Content-Type', None)
    try:
        return next(m for m in WRITE_BULK_SUPPORTED_MIME_TYPES if m.match(content_type))
    except:
        raise HTTPException(status_code=400, detail=f'Content-Type invalid: "{content_type}"')


def read_bulk_accept_type(request: Request) -> MimeType:
    accept_value = request.headers.get('Accept', None)
    if not accept_value or '*/*' in accept_value:
        return READ_BULK_SUPPORTED_MIME_TYPES[0]  # parquet by default
    for t in READ_BULK_SUPPORTED_MIME_TYPES:
        if any((v in accept_value for v in (t.type, *t.alternative_types))):
            return t
    raise HTTPException(status_code=400, detail=f'No supported type found in "{accept_value}"')


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


BODY_DESCRIPTION = """
Contains the data corresponding to the dataframe. The header "Content-Type" must be set accordingly to the format sent:
<br/>&nbsp;**Parquet** format(*application/x-parquet*): see [Apache parquet website](https://parquet.apache.org/).
<br/>&nbsp;**JSON** format (*application/json*): see [Pandas.Dataframe JSON format orient "split"](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_json.html).
"""
BODY_DESCRIPTION += f'.\n Examples in JSON for data with {_dataframe_sample.shape[0]} rows and {_dataframe_sample.shape[1]} columns: '
BODY_DESCRIPTION += f'\n<br/>`{_dataframe_sample.to_json(None, orient="split")}`<br/>&nbsp;'


REQUEST_DATA_BODY_SCHEMA = {
    'description': BODY_DESCRIPTION,
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
Required roles: 'users.datalake.viewers' or 'users.datalake.editors' or 'users.datalake.admins'.
In addition, users must be a member of data groups to access the data.
"""

REQUIRED_ROLES_WRITE = """
Required roles: 'users.datalake.editors' or 'users.datalake.admins'.
"""

BULK_READ_NOTE = """
**Important**: In order to minimize reading time.

1. Partial reading
    - Select only needed columns
    
Note: using curves filtering has a cost, use it only if it reduces significantly the amount of retrieved bulk data.

2. Full reading
    - Try to read all the curves, if those errors are returned go to next steps:
        - HTTP 400 "Too many columns requested"
        - HTTP 400 "Too many values requested"
        - HTTP 413 "the resource requested exceeds the limit" (When WBDDMS worker are enabled)
    - Get curve names and number of rows per curve by using describe parameter
       - Each request should fetch as many as columns it is possible until upper limits are reached (> 10 millions values or > 3000 columns)
"""

BULK_WRITE_NOTE = """
**Important**: In order to minimize writing time, it's necessary to:  
- Double check whether bulk data is big enough to be sent with chunking APIs: meaning > 10 millions values or > 3000 columns
    - If no, use instead POST /ddms/v3/welllogs/MY_RECORD_ID/data API
- Ensure all curve's values are in the same chunk to be sent
- Each chunk should contain as many as columns it is possible until upper limits are reached (> 10 millions values or > 3000 columns)
"""

BULK_URI_RULES = """
BulkURI consistency:
- ExtensionProperties.wdms.bulkURI is managed by WBDDMS and must not be set when creating a new record.
- When updating an existing record, bulkURI must match the previous version exactly.
Requests that violate these rules are rejected with HTTP 400.
"""


response_401 = {status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"}}
response_403 = {status.HTTP_403_FORBIDDEN: {"description": "Forbidden"}}
response_404 = {status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
response_500 = {status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}}

# Session commit - body - examples
sessions_body_examples = {
    "commit": {
        "summary": "Commit session data",
        "value": {
            "state": "commit",
        },
    },
    "abandon": {
        "summary": "Abandon session data",
        "value": {
            "state": "abandon",
        },
    },
}


successful_get_bulk_data_responses_examples = {
    "description": "Successful Response",
    "content": {
        MimeTypes.JSON.type: {
            "examples": {
                "json-data-split-example": {
                    "summary": "/data - JSON format 'split' orient ",
                    "value": {
                        "columns": ["MD", "GR", "NEU", "DEN"],
                        "index": [0, 1, 2, 3, 4],
                        "data": [
                            [1000, 9.7731657028, 42, 443], [1001, 9.7741136551, 50, 551],
                            [1002, 9.7746782303, 60, 661],
                            [1003, 9.7746782303, 70, 771], [1004, 9.7741136551, 80, 881]
                        ]
                    }
                },
                "json-data-columns-example": {
                    "summary": "/data - JSON format 'columns' orient ",
                    "value": {
                        "MD": {"1000": 1000, "1001": 1001, "1002": 1002, "1003": 1003, "1004": 1004},
                        "GR": {"1000": 9.7731657028, "1001": 9.7741136551, "1002": 9.7746782303,
                               "1003": 9.7746782303, "1004": 9.7741136551},
                        "NEU": {"1000": 42, "1001": 50, "1002": 60, "1003": 70, "1004": 80},
                        "DEN": {"1000": 443, "1001": 551, "1002": 661, "1003": 771, "1004": 881}}
                },
                "data-describe": {
                    "summary": "/data describe True",
                    "value": {
                        "columns": ["MD", "GR", "NEU", "DEN"],
                        "numberOfRows": 5
                    }
                },

            }
        },
        MimeTypes.PARQUET.type: {
            "examples": {
                "parquet-example": {
                    "summary": "/data - Parquet format (binary)",
                    "value": r"b'PAR1\x15\x04\x15P\x15@L\x15\n\x15\x00\x12\x00\x00(\x08\xe8\x03\x00\x05\x01\x00\xe9\r\x08\x00\xea\r\x08<\xeb\x03\x00\x00\x00\x00\x00\x00\xec\x03\x00\x00\x00\x00\x00\x00\x15\x00\x15\x16\x15\x1a,\x15\n\x15\x10\x15\x06\x15\x06\x1c\x18\x08\xec\x03\x00\x00\x00\x00\x00\x00\x18\x08\xe8\x03\x00\x00\x00\x00\x00\x00\x16\x00(\x08\xec\x03\x00\x00\x00\x00\x00\x00\x18\x08\xe8\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0b(\x02\x00\x00\x00\n\x01\x03\x03\x88F\x00&\xf8\x01\x1c\x15\x04\x195\x10\x00\x06\x19\x18\x02MD\x15\x02\x16\n\x16\xfc\x01\x16\xf0\x01&d&\x08\x1c\x18\x08\xec\x03\x00\x00\x00\x00\x00\x00\x18\x08\xe8\x03\x00\x00\x00\x00\x00\x00\x16\x00(\x08\xec\x03\x00\x00\x00\x00\x00\x00\x18\x08\xe8\x03\x00\x00\x00\x00\x00\x00\x00\x19,\x15\x04\x15\x00\x15\x02\x00\x15\x00\x15\x10\x15\x02\x00\x00\x00\x15\x04\x150\x154L\x15\x06\x15\x00\x12\x00\x00\x18\\h\xd4\xff_\xdc\x8b#@C\x15\x00\xa0X\x8c#@\x91\x1f\x00\xa0\xa2\x8c#@\x15\x00\x15\x14\x15\x18,\x15\n\x15\x10\x15\x06\x15\x06\x1c\x18\x08\x91\x1f\x00\xa0\xa2\x8c#@\x18\x08h\xd4\xff_\xdc\x8b#@\x16\x00(\x08\x91\x1f\x00\xa0\xa2\x8c#@\x18\x08h\xd4\xff_\xdc\x8b#@\x00\x00\x00\n$\x02\x00\x00\x00\n\x01\x02\x03\xa4\x01&\x92\x05\x1c\x15\n\x195\x10\x00\x06\x19\x18\x02GR\x15\x02\x16\n\x16\xda\x01\x16\xe2\x01&\x80\x04&\xb0\x03\x1c\x18\x08\x91\x1f\x00\xa0\xa2\x8c#@\x18\x08h\xd4\xff_\xdc\x8b#@\x16\x00(\x08\x91\x1f\x00\xa0\xa2\x8c#@\x18\x08h\xd4\xff_\xdc\x8b#@\x00\x19,\x15\x04\x15\x00\x15\x02\x00\x15\x00\x15\x10\x15\x02\x00\x00\x00\x15\x04\x15P\x15@L\x15\n\x15\x00\x12\x00\x00(\x04*\x00\t\x01\x002\t\x07\x04\x00<\r\x08<F\x00\x00\x00\x00\x00\x00\x00P\x00\x00\x00\x00\x00\x00\x00\x15\x00\x15\x16\x15\x1a,\x15\n\x15\x10\x15\x06\x15\x06\x1c\x18\x08P\x00\x00\x00\x00\x00\x00\x00\x18\x08*\x00\x00\x00\x00\x00\x00\x00\x16\x00(\x08P\x00\x00\x00\x00\x00\x00\x00\x18\x08*\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0b(\x02\x00\x00\x00\n\x01\x03\x03\x88F\x00&\xbe\x08\x1c\x15\x04\x195\x10\x00\x06\x19\x18\x03NEU\x15\x02\x16\n\x16\xfc\x01\x16\xf0\x01&\xaa\x07&\xce\x06\x1c\x18\x08P\x00\x00\x00\x00\x00\x00\x00\x18\x08*\x00\x00\x00\x00\x00\x00\x00\x16\x00(\x08P\x00\x00\x00\x00\x00\x00\x00\x18\x08*\x00\x00\x00\x00\x00\x00\x00\x00\x19,\x15\x04\x15\x00\x15\x02\x00\x15\x00\x15\x10\x15\x02\x00\x00\x00\x15\x04\x15P\x15DL\x15\n\x15\x00\x12\x00\x00(\x08\xbb\x01\x00\x05\x01\x04'\x02\x05\x07\x04\x00\x95\r\x08<\x03\x03\x00\x00\x00\x00\x00\x00q\x03\x00\x00\x00\x00\x00\x00\x15\x00\x15\x16\x15\x1a,\x15\n\x15\x10\x15\x06\x15\x06\x1c\x18\x08q\x03\x00\x00\x00\x00\x00\x00\x18\x08\xbb\x01\x00\x00\x00\x00\x00\x00\x16\x00(\x08q\x03\x00\x00\x00\x00\x00\x00\x18\x08\xbb\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0b(\x02\x00\x00\x00\n\x01\x03\x03\x88F\x00&\xf0\x0b\x1c\x15\x04\x195\x10\x00\x06\x19\x18\x03DEN\x15\x02\x16\n\x16\xfc\x01\x16\xf4\x01&\xdc\n&\xfc\t\x1c\x18\x08q\x03\x00\x00\x00\x00\x00\x00\x18\x08\xbb\x01\x00\x00\x00\x00\x00\x00\x16\x00(\x08q\x03\x00\x00\x00\x00\x00\x00\x18\x08\xbb\x01\x00\x00\x00\x00\x00\x00\x00\x19,\x15\x04\x15\x00\x15\x02\x00\x15\x00\x15\x10\x15\x02\x00\x00\x00\x15\x04\x19\\5\x00\x18\x06schema\x15\x08\x00\x15\x04%\x02\x18\x02MD\x00\x15\n%\x02\x18\x02GR\x00\x15\x04%\x02\x18\x03NEU\x00\x15\x04%\x02\x18\x03DEN\x00\x16\n\x19\x1c\x19L&\xf8\x01\x1c\x15\x04\x195\x10\x00\x06\x19\x18\x02MD\x15\x02\x16\n\x16\xfc\x01\x16\xf0\x01&d&\x08\x1c\x18\x08\xec\x03\x00\x00\x00\x00\x00\x00\x18\x08\xe8\x03\x00\x00\x00\x00\x00\x00\x16\x00(\x08\xec\x03\x00\x00\x00\x00\x00\x00\x18\x08\xe8\x03\x00\x00\x00\x00\x00\x00\x00\x19,\x15\x04\x15\x00\x15\x02\x00\x15\x00\x15\x10\x15\x02\x00\x00\x00&\x92\x05\x1c\x15\n\x195\x10\x00\x06\x19\x18\x02GR\x15\x02\x16\n\x16\xda\x01\x16\xe2\x01&\x80\x04&\xb0\x03\x1c\x18\x08\x91\x1f\x00\xa0\xa2\x8c#@\x18\x08h\xd4\xff_\xdc\x8b#@\x16\x00(\x08\x91\x1f\x00\xa0\xa2\x8c#@\x18\x08h\xd4\xff_\xdc\x8b#@\x00\x19,\x15\x04\x15\x00\x15\x02\x00\x15\x00\x15\x10\x15\x02\x00\x00\x00&\xbe\x08\x1c\x15\x04\x195\x10\x00\x06\x19\x18\x03NEU\x15\x02\x16\n\x16\xfc\x01\x16\xf0\x01&\xaa\x07&\xce\x06\x1c\x18\x08P\x00\x00\x00\x00\x00\x00\x00\x18\x08*\x00\x00\x00\x00\x00\x00\x00\x16\x00(\x08P\x00\x00\x00\x00\x00\x00\x00\x18\x08*\x00\x00\x00\x00\x00\x00\x00\x00\x19,\x15\x04\x15\x00\x15\x02\x00\x15\x00\x15\x10\x15\x02\x00\x00\x00&\xf0\x0b\x1c\x15\x04\x195\x10\x00\x06\x19\x18\x03DEN\x15\x02\x16\n\x16\xfc\x01\x16\xf4\x01&\xdc\n&\xfc\t\x1c\x18\x08q\x03\x00\x00\x00\x00\x00\x00\x18\x08\xbb\x01\x00\x00\x00\x00\x00\x00\x16\x00(\x08q\x03\x00\x00\x00\x00\x00\x00\x18\x08\xbb\x01\x00\x00\x00\x00\x00\x00\x00\x19,\x15\x04\x15\x00\x15\x02\x00\x15\x00\x15\x10\x15\x02\x00\x00\x00\x16\xce\x07\x16\n&\x08\x16\xb6\x07\x14\x00\x00\x19\x1c\x18\x0cARROW:schema\x18\xf8\x02/////xABAAAQAAAAAAAKAAwABgAFAAgACgAAAAABBAAMAAAACAAIAAAABAAIAAAABAAAAAQAAACoAAAAZAAAADQAAAAEAAAAeP///wAAAQIQAAAAFAAAAAQAAAAAAAAAAwAAAERFTgBo////AAAAAUAAAACk////AAABAhAAAAAUAAAABAAAAAAAAAADAAAATkVVAJT///8AAAABQAAAAND///8AAAEDEAAAABwAAAAEAAAAAAAAAAIAAABHUgAAAAAGAAgABgAGAAAAAAACABAAFAAIAAYABwAMAAAAEAAQAAAAAAABAhAAAAAcAAAABAAAAAAAAAACAAAATUQAAAgADAAIAAcACAAAAAAAAAFAAAAAAAAAAA==\x00\x18 parquet-cpp-arrow version 10.0.0\x19L\x1c\x00\x00\x1c\x00\x00\x1c\x00\x00\x1c\x00\x00\x00\x7f\x03\x00\x00PAR1'"
                }
            }
        },
    }}


create_sessions_examples = {
    "update": {
        "summary": "Start update session",
        "value": {
            "mode": "update"
        }
    },
    "overwrite": {
        "summary": "Start overwrite session",
        "value": {
            "mode": "overwrite"
        }
    },
    "full": {
        "summary": "Start update session at specific record version",
        "value": {
            "fromVersion": 123456789,
            "mode": "update",
        }
    },
    "set session meta": {
        "summary": "Start update session and session meta attributes",
        "value": {
            "mode": "update",
            "meta": {
                "extendedLoadCompleted": True
            }
        }
    },
}
