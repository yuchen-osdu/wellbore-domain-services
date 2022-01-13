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

from typing import List
from fastapi import APIRouter, Depends
from odes_search.models import Point, CursorQueryResponse
from app.utils import Context
from app.helper.traces import TracingRoute
from .search_v3 import (
    SearchQuery,
    SearchQueryRequest,
    query_request,
    query_type,
    added_relationships_query,
    query_request_with_specific_attribute,
    OSDU_WELLBORE_KIND,
    OSDU_WELLLOG_KIND,
    OSDU_WELLBOREMARKERSET_KIND,
    WELLBORE_RELATIONSHIP,
    REQUIRED_ROLES_READ,
    DEFAULT_QUERYREQUEST
)

router = APIRouter(route_class=TracingRoute)
query_type = 'fastquery'


def get_ctx() -> Context:
    return Context.current()


@router.post('/fastquery/wellbores', summary="Query with cursor",
             description=f"""Get all Wellbores IDs object.  <p>The wellbore kind is
        {OSDU_WELLBORE_KIND} returns all records IDs IDs directly based on existing schemas</p>{REQUIRED_ROLES_READ}""",
             response_model=CursorQueryResponse)
async def fastquery_wellbores(body: SearchQueryRequest = DEFAULT_QUERYREQUEST, ctx: Context = Depends(get_ctx)):
    return await query_request(query_type, OSDU_WELLBORE_KIND, ctx,  body)

@router.post('/fastquery/wellbores/{wellbore_id}/welllogs',
             summary='Query with cursor, search WellLogs IDs by wellbore ID',
             description=f"""Get all WellLogs IDs objects using its relationship Wellbore ID.  <p>All WellLogs linked to this
            specific ID will be returned</p>
            <p>The LogSet kind is {OSDU_WELLLOG_KIND} returns all records IDs directly based on existing schemas</p>{REQUIRED_ROLES_READ}""",
             response_model=CursorQueryResponse)
async def fastquery_welllogs_bywellbore(wellbore_id: str, body: SearchQueryRequest = DEFAULT_QUERYREQUEST,
                                        ctx: Context = Depends(get_ctx)):
    body.query = added_relationships_query(wellbore_id, WELLBORE_RELATIONSHIP, body.query)
    return await query_request(query_type, OSDU_WELLLOG_KIND, ctx, body)


@router.post('/fastquery/wellbore/{wellbore_attribute}/welllogs',
             summary='Query with cursor, search WellLogs IDs by wellbore attribute',
             description=f"""Get all WellLogs IDs objects using a specific attribute of Wellbores.  <p>All WellLogs linked to Wellbores
            with this specific attribute will be returned</p>
            <p>The LogSet kind is {OSDU_WELLLOG_KIND} returns all records IDs directly based on existing schemas</p>{REQUIRED_ROLES_READ}""",
             response_model=CursorQueryResponse)
async def fastquery_welllogs_bywellboreattribute(wellbore_attribute: str, body: SearchQuery = SearchQuery(query=None),
                ctx: Context = Depends(get_ctx)):
    return await query_request_with_specific_attribute(query_type, wellbore_attribute, OSDU_WELLBORE_KIND,
                                                              OSDU_WELLLOG_KIND, WELLBORE_RELATIONSHIP, ctx,
                                                              body.query)


@router.post('/fastquery/wellbores/{wellbore_id}/wellboremarkersets',
             summary='Query with cursor, search wellbore markersets IDs by wellbore ID',
             description=f"""Get all Wellbore Markersets IDs objects using its relationship Wellbore ID.  <p>All Markers linked to this
            specific ID will be returned</p>
            <p>The Marker kind is {OSDU_WELLBOREMARKERSET_KIND} returns all records IDs directly based on existing schemas</p>{REQUIRED_ROLES_READ}""",
             response_model=CursorQueryResponse)
async def fastquery_markers_bywellbore(wellbore_id: str, body: SearchQueryRequest = DEFAULT_QUERYREQUEST,
                ctx: Context = Depends(get_ctx)):
    body.query = added_relationships_query(wellbore_id, WELLBORE_RELATIONSHIP, body.query)
    return await query_request(query_type, OSDU_WELLBOREMARKERSET_KIND, ctx, body)
