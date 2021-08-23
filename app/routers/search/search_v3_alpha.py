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

from fastapi import APIRouter, Depends
from odes_search.models import CursorQueryResponse
from app.utils import Context
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
    query_type)
from ..common_parameters import REQUIRED_ROLES_READ

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
             summary='Query with cursor, search WellLogs by name and optionally by wellbore ID',
             description=f"""Get all WellLogs objects using its name and optionally relationship Wellbore ID.  
            <p>The WellLogs kind is {OSDU_WELLLOG_KIND} returns all records directly based on existing schemas. The query is done on data.Name field</p>{REQUIRED_ROLES_READ}""",
             response_model=CursorQueryResponse)
async def query_welllogs_by_name(names: str = None, wellbore_id: str = None, body: SearchQueryRequest = DEFAULT_QUERYREQUEST,
                                   ctx: Context = Depends(get_ctx)):
    if wellbore_id is not None:
        body.query = added_relationships_query(wellbore_id, WELLBORE_RELATIONSHIP, body.query)
    names = escape_forbidden_characters_for_search(names)
    body.query = update_query_with_names_based_search(names=names, user_query=body.query, name_field="data.Name")
    return await query_request(query_type, OSDU_WELLLOG_KIND, ctx, body)
