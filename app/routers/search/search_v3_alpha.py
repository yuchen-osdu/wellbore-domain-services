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

from typing import Optional, Dict, List

from fastapi import APIRouter, Depends
from odes_search.models import CursorQueryResponse, QueryRequest
from pydantic import BaseModel, Field

from app.utils import Context
from . import search_wrapper
from .search_v3 import (
    SearchQueryRequest,
    DEFAULT_QUERYREQUEST,
    OSDU_WELLBORE_KIND,
    OSDU_WELLBORETRAJECTORY_KIND,
    OSDU_WELLLOG_KIND,
    escape_forbidden_characters_for_search,
    update_query_with_names_based_search,
    query_request,
    added_relationships_query,
    WELLBORE_RELATIONSHIP,
    get_ctx,
    query_type, update_query_with_nested_names_based_search)
from ..common_parameters import REQUIRED_ROLES_READ
from ...clients.search_service_client import get_search_service
from ...model.osdu_model import Curve110

router = APIRouter()


@router.post('/query/wellbores', summary='Query with cursor or offset, get wellbores',
             description=f"""Get Wellbores object by name.  <p>The wellbore kind is {OSDU_WELLBORE_KIND}
        returns all records directly based on existing schemas. The query is done on data.FacilityName field</p>{REQUIRED_ROLES_READ}""",
             response_model=CursorQueryResponse)
async def query_wellbores_by_name(names: str = None, body: SearchQueryRequest = DEFAULT_QUERYREQUEST,
                                  ctx: Context = Depends(get_ctx)):
    names = escape_forbidden_characters_for_search(names)
    body.query = update_query_with_names_based_search(names=names, user_query=body.query)
    return await query_request(query_type, OSDU_WELLBORE_KIND, ctx, body)


@router.post('/query/wellbores/{wellboreId}/wellboretrajectories',
             summary='Query with cursor, search wellbore trajectories by wellbore ID',
             description=f"""Get all Wellbore Trajectories objects using its relationship Wellbore ID.  <p>All Wellbore Trajectories linked to this
            specific ID will be returned</p>
            <p>The Wellbore Trajectories kind is {OSDU_WELLBORETRAJECTORY_KIND} returns all records directly based on existing schemas</p>{REQUIRED_ROLES_READ}""",
             response_model=CursorQueryResponse)
async def query_trajectories_bywellbore(wellboreId: str, body: SearchQueryRequest = DEFAULT_QUERYREQUEST,
                                   ctx: Context = Depends(get_ctx)):
    body.query = added_relationships_query(wellboreId, WELLBORE_RELATIONSHIP, body.query)
    return await query_request(query_type, OSDU_WELLBORETRAJECTORY_KIND, ctx, body)


@router.post('/query/welllogs',
             summary='Query with cursor, search WellLogs by name and optionally by wellbore ID and curves mnemonics',
             description=f"""Get all WellLogs objects using its name and optionally relationship Wellbore ID. Filtering can be done on curves mnemonics
            <p>The WellLogs kind is {OSDU_WELLLOG_KIND} returns all records directly based on existing schemas. The query is done on data.Name field</p>{REQUIRED_ROLES_READ}""",
             response_model=CursorQueryResponse)
async def query_welllogs_by_name(names: str = None, wellbore_id: str = None, mnemonics: str = None,
                                 body: SearchQueryRequest = DEFAULT_QUERYREQUEST,
                                 ctx: Context = Depends(get_ctx)):
    if wellbore_id is not None:
        body.query = added_relationships_query(wellbore_id, WELLBORE_RELATIONSHIP, body.query)
    names = escape_forbidden_characters_for_search(names)
    mnemonics = escape_forbidden_characters_for_search(mnemonics)
    body.query = update_query_with_names_based_search(names=names, user_query=body.query, name_field="data.Name")
    body.query = update_query_with_nested_names_based_search(array_field='data.Curves', nested_field='Mnemonic',
                                                             names=mnemonics, user_query=body.query)
    return await query_request(query_type, OSDU_WELLLOG_KIND, ctx, body)
    
    
class CurvePer(BaseModel):
    results: "Optional[Dict[str, List[Curve110]]]" = Field(None, alias="results")

class CurvesQueryResponse(BaseModel):
    results: "Optional[Dict[str, List[Curve110]]]" = Field(None, alias="results")


@router.post('/query/wellbores/{wellboreid}/curves',
             summary='Query with cursor',
             description=f"""Get all Curves from all WellLogs using relationship Wellbore ID.<p></p>
            <p>The WellLog  kind is {OSDU_WELLLOG_KIND}</p>{REQUIRED_ROLES_READ}""",
             response_model=CurvesQueryResponse,
             response_model_exclude_unset=True)
async def query_curves_by_wellbore(wellboreid: str, ctx: Context = Depends(get_ctx)):
    query = added_relationships_query(wellboreid, WELLBORE_RELATIONSHIP, None)
    welllogs_query_request = QueryRequest(kind=OSDU_WELLLOG_KIND,
                                 query=query,
                                 returnedFields=['id', 'data.Curves'])

    client = await get_search_service(ctx)
    results = await search_wrapper.SearchWrapper.query_cursorless(
        search_service=client,
        data_partition_id=ctx.partition_id,
        query_request=welllogs_query_request)

    curves_response = CurvesQueryResponse()
    curves_response.results = dict()
    if results.results is not None:
        for item in results.results:
            curves_response.results[item['id']] = item.get('data', {}).get('Curves', [])

    return curves_response
