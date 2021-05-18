# Copyright 2021 Schlumberger
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import math
from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query, status

import app.routers.dipset.persistence as persistence
from ..common_parameters import REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from app.routers.dipset.dip_model import Dip
from app.utils import Context, get_ctx

# TODO reference: setup reference type  family, unit ...
# TODO setup dipset channels (family, family_type, unit, format of dip attributs)
# TODO logger : should log information when retrieving/creating dipset, log, ...
# TODO dispet should have a wellbore (data.relationships.wellbore)

router = APIRouter()


@router.post(
    "/dipsets/{dipsetid}/dips",
    summary="Define the dips of the dipset",
    response_model=List[Dip],
    response_model_exclude_none=True,
    description="""Replace previous dips by provided dips. Sort dips by reference and azimuth. {}"""
    .format(REQUIRED_ROLES_WRITE),
    operation_id="post_dips",
)
async def post_dips(
    dips: List[Dip], dipsetid: str = Path(..., description="The ID of the dipset"), ctx: Context = Depends(get_ctx)
) -> List[Dip]:
    df = persistence.dips_to_df(dips)
    await persistence.write_dipset_data(ctx, dataframe=df, ds=dipsetid)
    return persistence.df_to_dips(df)


@router.post(
    "/dipsets/{dipsetid}/dips/insert",
    summary="insert dip in  a dipset",
    response_model=List[Dip],
    response_model_exclude_none=True,
    description="""Insert dips in dipset. 
    Existing dips are not replaced. 
    Several dip can have same reference. 
    Operation will sort by reference all dips in dipset (may modify dip indexes). {}""".format(REQUIRED_ROLES_WRITE),
    operation_id="insert_dips",
)
async def insert_dips(
        dips: List[Dip], dipsetid: str, ctx: Context = Depends(get_ctx)) -> List[Dip]:
    my_dipset, df = await persistence.read_dipset_data(ctx, ds=dipsetid)
    df = df.append(persistence.dips_to_df(dips))
    await persistence.write_dipset_data(ctx, dataframe=df, ds=my_dipset)
    return persistence.df_to_dips(df)


@router.get(
    "/dipsets/{dipsetid}/dips",
    summary="Get dips",
    response_model=Optional[List[Dip]],
    response_model_exclude_none=True,
    description="""Return dips from dipset from the given index until the given number of dips specifed in query parameters. 
    If not specified returns all dips from dipset. {}""".format(REQUIRED_ROLES_READ),
    operation_id="get_dips",
    responses={status.HTTP_404_NOT_FOUND: {"description": "DipSet not found"}},
)
async def get_dips(
    dipsetid: str,
    index: Optional[int] = Query(None, ge=0),
    limit: Optional[int] = Query(None, ge=0),
    ctx: Context = Depends(get_ctx),
) -> List[Dip]:

    _, df = await persistence.read_dipset_data(ctx, ds=dipsetid)

    start = 0
    if index is not None:
        start = index

    end = None
    if limit is not None:
        end = start + limit
    df = df.iloc[slice(start, end)]

    return persistence.df_to_dips(df)


@router.get(
    "/dipsets/{dipsetid}/dips/query",
    summary="Query dip from dipset",
    response_model=List[Dip],
    response_model_exclude_none=True,
    description="""Search dip within reference interval and specific classification. {}""".format(REQUIRED_ROLES_READ),
    operation_id="query_dip",
)
async def query_dip(
    dipsetid: str,
    min_ref: Optional[float] = Query(
        None, description="Min reference for the dips to search in the dipset", alias="minReference"
    ),
    max_ref: Optional[float] = Query(
        None, title="Max reference for the dips to search in the dipset", alias="maxReference"
    ),
    classification: Optional[str] = Query(None, title="Classification for the dip to search in the dipset"),
    ctx: Context = Depends(get_ctx),
) -> List[Dip]:
    _, df = await persistence.read_dipset_data(ctx, ds=dipsetid)

    if classification is not None:
        df = df[df["classification"] == classification]
    if min_ref is not None and not math.isnan(min_ref):
        df = df[df["reference"] >= min_ref]
    if max_ref is not None and not math.isnan(max_ref):
        df = df[df["reference"] <= max_ref]

    return persistence.df_to_dips(df)


@router.get(
    "/dipsets/{dipsetid}/dips/{index}",
    summary="Get a dip at index",
    response_model=Dip,
    response_model_exclude_none=True,
    description=""""Return dip from dipset at the given index. {}""".format(REQUIRED_ROLES_READ),
    operation_id="get_dip_by_index",
    responses={status.HTTP_404_NOT_FOUND: {"description": "DipSet or index not found"}},
)
async def get_dip_by_index(dipsetid: str, index: int, ctx: Context = Depends(get_ctx)) -> Dip:
    _, df = await persistence.read_dipset_data(ctx, ds=dipsetid)
    return persistence.series_to_dip(df.iloc[index])


@router.patch(
    "/dipsets/{dipsetid}/dips/{index}",
    summary="Update dip",
    response_model=List[Dip],
    response_model_exclude_none=True,
    description=""""Update dip at index     
    Operation will sort by reference all dips in dipset (may modify dip indexes).""",
    operation_id="patch_dip",
    responses={status.HTTP_404_NOT_FOUND: {"description": "DipSet not found"}},
)
async def patch_dip(dip: Dip, dipsetid: str, index: int, ctx: Context = Depends(get_ctx)) -> List[Dip]:
    # TODO input validation 0 <= index < size
    my_dipset, df = await persistence.read_dipset_data(ctx, ds=dipsetid)
    # Update the data
    df.iloc[index] = persistence.dip_to_series(dip)

    await persistence.write_dipset_data(ctx, dataframe=df, ds=my_dipset)
    return persistence.df_to_dips(df)


@router.delete(
    "/dipsets/{dipsetid}/dips/{index}",
    summary="Delete a dip",
    response_model=List[Dip],
    response_model_exclude_none=True,
    description="Removes the dip at index. {}".format(REQUIRED_ROLES_WRITE),
    operation_id="delete_dip_by_index",
    responses={status.HTTP_404_NOT_FOUND: {"description": "DipSet or index not found"}},
)
async def delete_dip_by_index(dipsetid: str, index: int, ctx: Context = Depends(get_ctx)) -> List[Dip]:
    # TODO input validation 0 <= index < size
    my_dipset, df = await persistence.read_dipset_data(ctx, ds=dipsetid)
    df.drop(index=index, inplace=True)
    await persistence.write_dipset_data(ctx, dataframe=df, ds=my_dipset)
    return persistence.df_to_dips(df)
