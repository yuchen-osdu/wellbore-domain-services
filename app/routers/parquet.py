from fastapi import APIRouter, status, HTTPException
from pydantic import BaseModel
from app.utils import Context
from fastapi import Depends
from typing import List

import pandas as pd
import numpy as np
import json
from fastapi.responses import Response

import os
import uuid

router = APIRouter()
prefix = '/p/performance-test-data/regular'

MIME_TYPE_JSON = "application/json"
MIME_TYPE_MSGPACK = "application/x-msgpack"


def get_ctx() -> Context:
    return Context.current()


class WriteLogBody(BaseModel):
    index: List[float]
    value: List[float]
    unit: str


def _get_df_from_id(log_id: str):
    path = f'{prefix}/log={log_id}/'
    if not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail='Log already does not exits with this id')

    df = pd.read_parquet(path + 'log.parquet', columns=['index', 'value'])

    # replace NaN by "Nan" (add ~7ms overhead on 100k log values)
    df['value'] = df['value'].replace(np.nan, str('NaN'))
    return df


def read_parquet_with_panda(log_id: str):
    df = _get_df_from_id(log_id)
    response = {
        "values": df['value'].tolist(),
        "index": df['index'].tolist(),
    }
    return response


def read_parquet_with_panda_io(log_id: str):
    df = _get_df_from_id(log_id)
    return df.to_json()


def read_parquet_with_panda_serialized(log_id: str):
    df = _get_df_from_id(log_id)

    response = ''.join(['{"index": ', df["index"].to_json(orient='values'),
                        ', "values": ', df["value"].to_json(orient='values'),
                        "}"])
    return response


def write_parquet_with_panda(log: WriteLogBody):
    log_id = str(uuid.uuid4())[:8]

    path = f'{prefix}/log={log_id}/'
    if os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail='Log already exits with this id')

    df_data = dict(index=log.index,
                   value=log.value)

    df = pd.DataFrame(data=df_data)
    df['unit'] = log.unit
    df['curve_name'] = f'GR-{log_id}'

    os.makedirs(path)
    df.to_parquet(path + 'log.parquet')
    return log_id


@router.get("/read-10k")
async def read_10k_items():
    log_id = "10k"
    content = read_parquet_with_panda_serialized(log_id)
    return Response(content=content, media_type=MIME_TYPE_JSON)


@router.get("/read-40k")
async def read_40k_items():
    log_id = "40k"
    content = read_parquet_with_panda_serialized(log_id)
    return Response(content=content, media_type=MIME_TYPE_JSON)


@router.get("/read-40k-msgpack")
async def read_40k_items_msgpack():
    try:
        import umsgpack  # loaded only when needed
    except ImportError:
        raise HTTPException(status_code=500, detail="umsgpack not installed")

    log_id = "40k"
    data = read_parquet_with_panda(log_id)
    return Response(content=umsgpack.packb(data), media_type=MIME_TYPE_MSGPACK)


@router.get("/read-40k-df-to-json")
async def read_40k_items_io():
    log_id = "40k"
    content = read_parquet_with_panda_io(log_id)
    return Response(content=content, media_type=MIME_TYPE_JSON)


@router.get("/read-100k-df-to-json")
async def read_100k_items_io():
    log_id = "100k"
    content = read_parquet_with_panda_io(log_id)
    return Response(content=content, media_type=MIME_TYPE_JSON)


@router.get("/read-1million-df-to-json")
async def read_1million_items_io():
    log_id = "1million"
    content = read_parquet_with_panda_io(log_id)
    return Response(content=content, media_type=MIME_TYPE_JSON)


@router.get("/read-100k")
async def read_100k_items():
    log_id = "100k"
    content = read_parquet_with_panda_serialized(log_id)
    return Response(content=content, media_type=MIME_TYPE_JSON)


@router.get("/read-1million")
async def read_1million_items():
    log_id = "1million"
    content = read_parquet_with_panda_serialized(log_id)
    return Response(content=content, media_type=MIME_TYPE_JSON)


@router.get("/read-40k-pyarrow")
async def read_40k_items_pyarrow():
    try:
        import pyarrow as pa

    except ImportError:
        raise HTTPException(status_code=500, detail="pyarrow not installed")

    log_id = "40k"
    df = _get_df_from_id(log_id)

    context = pa.default_serialization_context()
    df_bytestring = context.serialize(df).to_buffer().to_pybytes()
    return Response(content=df_bytestring, media_type=MIME_TYPE_MSGPACK)


@router.get("/read-100k-pyarrow")
async def read_100k_items_pyarrow():
    try:
        import pyarrow as pa

    except ImportError:
        raise HTTPException(status_code=500, detail="pyarrow not installed")

    log_id = "100k"
    df = _get_df_from_id(log_id)

    context = pa.default_serialization_context()
    df_bytestring = context.serialize(df).to_buffer().to_pybytes()
    return Response(content=df_bytestring, media_type=MIME_TYPE_MSGPACK)


@router.get("/read-1million-pyarrow")
async def read_1million_items_pyarrow():
    try:
        import pyarrow as pa

    except ImportError:
        raise HTTPException(status_code=500, detail="pyarrow not installed")

    log_id = "1million"
    df = _get_df_from_id(log_id)

    context = pa.default_serialization_context()
    df_bytestring = context.serialize(df).to_buffer().to_pybytes()
    return Response(content=df_bytestring, media_type=MIME_TYPE_MSGPACK)


@router.get("/read-1million-msgpack")
async def read_1million_items():
    try:
        import umsgpack  # loaded only when needed
    except ImportError:
        raise HTTPException(status_code=500, detail="umsgpack not installed")

    log_id = "1million"
    data = read_parquet_with_panda_serialized(log_id)
    return Response(content=umsgpack.packb(data), media_type="application/x-msgpack")


@router.get("/read-10million")
async def read_10million_items():
    log_id = "10million"
    content = read_parquet_with_panda_serialized(log_id)
    return Response(content=content, media_type=MIME_TYPE_JSON)


@router.get("/read-by-id")
async def read_by_id(log_id: str):
    content = read_parquet_with_panda_serialized(log_id)
    return Response(content=content, media_type=MIME_TYPE_JSON)


@router.put("/write", status_code=201)
async def write_items(log_body: WriteLogBody):
    if len(log_body.index) != len(log_body.value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Mismatch length between index and value arrays')

    return write_parquet_with_panda(log_body)
