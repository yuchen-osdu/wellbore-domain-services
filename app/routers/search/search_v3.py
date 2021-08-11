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
from odes_search.models import (
    QueryRequest,
    CursorQueryResponse,
    CursorQueryRequest,
    BaseModel,
    Field,
    Optional,
)
from app.clients.search_service_client import get_search_service
from ..common_parameters import REQUIRED_ROLES_READ
from app.utils import Context
import app.routers.search.search_wrapper as search_wrapper
from .search import (
    query_type,
    SearchQuery,
    get_ctx,
    query_type_returned_fields,
    basic_query_request,
    basic_query_request_with_cursor)

router = APIRouter()

# osdu kind
OSDU_WELLBORE_KIND = '*:wks:master-data--Wellbore:*'
OSDU_WELLLOG_KIND = '*:wks:work-product-component--WellLog:*'
OSDU_WELLBOREMARKERSET_KIND = '*:wks:work-product-component--WellboreMarkerSet:*'
WELLBORE_RELATIONSHIP = "WellboreID"


def create_relationships_id_str(data_type: str, id: str):
    return f'data.{data_type}:\"{id}\"'


def added_query(generated_query: str, user_query: str = None):
    if user_query:
        query = f'{generated_query} AND ({user_query})'
    else:
        query = generated_query
    return query


def update_query_with_names_based_search(names: str = None, user_query: str = None) -> str:
    generated_query = f"data.FacilityName:{names}"
    return added_query(generated_query, user_query)


def escape_forbidden_characters_for_search(input_str: str) -> str:
    # ? and * are allowed for wildcard search
    reserved_char_list = ['+', '-', '=', '>', '<', '!', '(', ')', '{', '}', '[', ']', '^', '"', '~',
                          ':', '\\', '/']

    def escape_char(input_char: str, reserved_char_list: [str]) -> str:
        return input_char if input_char not in reserved_char_list else f"\\{input_char}"

    result_str = ''.join([escape_char(char, reserved_char_list) for char in input_str])
    return result_str


def added_relationships_query(id: str, data_type: str, query: str = None):
    relationships_id = create_relationships_id_str(data_type, id)
    return added_query(relationships_id, query)


async def query_request_with_specific_attribute(query_type: str, attribute: str, attribute_kind: str, kind: str,
                                                data_type: str,
                                                ctx: Context, query: str = None):
    query_request = QueryRequest(kind=attribute_kind,
                                 query=attribute,
                                 returnedFields=['id'])

    client = await get_search_service(ctx)
    query_result = await search_wrapper.SearchWrapper.query_cursorless(
        search_service=client,
        data_partition_id=ctx.partition_id,
        query_request=query_request)

    response = CursorQueryResponse.parse_obj(query_result.dict())

    if not response.results:
        return query_result

    relationships_ids = [create_relationships_id_str(data_type, r["id"]) for r in response.results]
    id_list = ' OR '.join(relationships_ids)  # [a, b, c] => 'a OR b OR c'

    query = added_query(id_list, query)

    returned_fields = query_type_returned_fields(query_type)
    query_request = QueryRequest(kind=kind,
                                 query=query,
                                 returnedFields=[returned_fields])
    return await search_wrapper.SearchWrapper.query_cursorless(
        search_service=client,
        data_partition_id=ctx.partition_id,
        query_request=query_request)


class SearchQueryRequest(BaseModel):
    # Used by as input, w/o kind, etc...
    limit: "Optional[int]" = Field(None, alias="limit")
    query: "Optional[str]" = Field(None, alias="query")
    cursor: "Optional[str]" = Field(None, alias="cursor")
    offset: "Optional[int]" = Field(None, alias="offset")


SearchQueryRequest.update_forward_refs()
DEFAULT_SEARCHQUERYREQUEST = SearchQueryRequest(limit=None, query=None, cursor=None, offset=None)


class SimpleCursorQueryRequest(BaseModel):
    # Used by as input, w/o kind, etc...
    limit: "Optional[int]" = Field(None, alias="limit")
    query: "Optional[str]" = Field(None, alias="query")
    cursor: "Optional[str]" = Field(None, alias="cursor")


SimpleCursorQueryRequest.update_forward_refs()
DEFAULT_CURSORQUERYREQUEST = SimpleCursorQueryRequest(limit=None, query=None, cursor=None)


class SimpleOffsetQueryRequest(BaseModel):
    limit: "Optional[int]" = Field(None, alias="limit")
    query: "Optional[str]" = Field(None, alias="query")
    offset: "Optional[int]" = Field(None, alias="offset")


SimpleOffsetQueryRequest.update_forward_refs()
DEFAULT_QUERYREQUEST = SimpleOffsetQueryRequest(limit=None, query=None, offset=None)


async def query_request_with_cursor(query_type: str, kind: str, ctx: Context, query: SimpleCursorQueryRequest = None):
    returned_fields = query_type_returned_fields(query_type)
    query_request = CursorQueryRequest(kind=kind,
                                       limit=query.limit or 1000,
                                       query=query.query,
                                       returnedFields=[returned_fields],
                                       cursor=query.cursor)
    client = await get_search_service(ctx)
    return await client.query_with_cursor(
        data_partition_id=ctx.partition_id,
        cursor_query_request=query_request)


async def query_request_with_offset(query_type: str, kind: str, ctx: Context, query: SimpleOffsetQueryRequest = None):
    returned_fields = query_type_returned_fields(query_type)

    query_request = QueryRequest(kind=kind,
                                 limit=query.limit or 1000,
                                 query=query.query,
                                 returnedFields=[returned_fields],
                                 offset=query.offset)
    client = await get_search_service(ctx)
    return await client.query(
        data_partition_id=ctx.partition_id,
        query_request=query_request)


async def query_request(query_type: str, kind: str, ctx: Context, query: SearchQueryRequest = None):
    # use offset if not not none else use cursor
    query_as_dict = query.dict(exclude_none=True, exclude_unset=True)
    if query.offset is not None:
        cursor_query = SimpleOffsetQueryRequest(**query_as_dict)
        return await query_request_with_offset(query_type, kind, ctx, cursor_query)

    cursor_query = SimpleCursorQueryRequest(**query_as_dict)
    return await query_request_with_cursor(query_type, kind, ctx, cursor_query)


@router.post('/query/wellbores/byname', summary='Query with cursor or offset, get wellbores',
             description=f"""Get Wellbores object by name.  <p>The wellbore kind is {OSDU_WELLBORE_KIND}
        returns all records directly based on existing schemas. The query is done on data.FacilityName field</p>{REQUIRED_ROLES_READ}""",
             response_model=CursorQueryResponse)
async def query_wellbores_by_name(names: str, body: SearchQueryRequest = DEFAULT_QUERYREQUEST,
                                  ctx: Context = Depends(get_ctx)):
    names = escape_forbidden_characters_for_search(names)
    body.query = update_query_with_names_based_search(names=names, user_query=body.query)
    return await query_request(query_type, OSDU_WELLBORE_KIND, ctx, body)


# @router.post('/querywithcursor/wellbores/byname', summary='Query with cursor, get wellbores',
#              description=f"""Get Wellbores object by name.  <p>The wellbore kind is {OSDU_WELLBORE_KIND}
#         returns all records directly based on existing schemas. The query is done on data.FacilityName field</p>{REQUIRED_ROLES_READ}""",
#              response_model=CursorQueryResponse)
# async def query_cursor_wellbores_by_name(names: str, body: SimpleCursorQueryRequest = DEFAULT_CURSORQUERYREQUEST, ctx: Context = Depends(get_ctx)):
#     names = escape_forbidden_characters_for_search(names)
#     body.query = update_query_with_names_based_search(names=names, user_query=body.query)
#     return await query_request_with_cursor(query_type, OSDU_WELLBORE_KIND, ctx, body)
#
#
# @router.post('/querywithoffset/wellbores/byname', summary='Query with offset, get wellbores',
#              description=f"""Get Wellbores object by name.  <p>The wellbore kind is {OSDU_WELLBORE_KIND}
#         returns all records directly based on existing schemas. The query is done on data.FacilityName field</p>{REQUIRED_ROLES_READ}""",
#              response_model=CcsQueryResponse)
# async def query_offset_wellbores_by_name(names: str, body: SimpleOffsetQueryRequest = DEFAULT_QUERYREQUEST, ctx: Context = Depends(get_ctx)):
#     names = escape_forbidden_characters_for_search(names)
#     body.query = update_query_with_names_based_search(names=names, user_query=body.query)
#     return await query_request_with_offset(query_type, OSDU_WELLBORE_KIND, ctx, body)


@router.post('/query/wellbores', summary='Query with cursor, get wellbores',
             description=f"""Get all Wellbores object.  <p>The wellbore kind is {OSDU_WELLBORE_KIND}
        returns all records directly based on existing schemas</p>{REQUIRED_ROLES_READ}""",
             response_model=CursorQueryResponse)
async def query_wellbores(body: SearchQuery = None, ctx: Context = Depends(get_ctx)):
    return await basic_query_request_with_cursor(query_type, OSDU_WELLBORE_KIND, ctx, body.query)


@router.post('/query/wellbores/{wellboreId}/welllogs', summary='Query with cursor, search WellLogs by wellbore ID',
             description=f"""Get all WellLogs object using its relationship Wellbore ID.  <p>All WellLogs linked to this
            specific ID will be returned</p>
            <p>The WellLogs kind is {OSDU_WELLLOG_KIND} returns all records directly based on existing schemas</p>{REQUIRED_ROLES_READ}""",
             response_model=CursorQueryResponse)
async def query_welllogs_bywellbore(wellboreId: str, body: SearchQuery = None,
                                    ctx: Context = Depends(get_ctx)):
    query = added_relationships_query(wellboreId, WELLBORE_RELATIONSHIP, body.query)
    return await basic_query_request(query_type, OSDU_WELLLOG_KIND, ctx, query)


@router.post('/query/wellbore/{wellboreAttribute}/welllogs',
             summary='Query with cursor, search WellLogs by wellbore attribute',
             description=f"""Get all WellLogs object using a specific attribute of Wellbores.  <p>All WellLogs linked to Wellbores
            with this specific attribute will be returned</p>
            <p>The WellLogs kind is {OSDU_WELLLOG_KIND} returns all records directly based on existing schemas</p>{REQUIRED_ROLES_READ}""",
             response_model=CursorQueryResponse)
async def query_welllogs_bywellboreattribute(wellboreAttribute: str, body: SearchQuery = None,
                                             ctx: Context = Depends(get_ctx)):
    return await query_request_with_specific_attribute(query_type, wellboreAttribute, OSDU_WELLBORE_KIND,
                                                       OSDU_WELLLOG_KIND,
                                                       WELLBORE_RELATIONSHIP, ctx,
                                                       body.query)


@router.post('/query/wellbores/{wellboreId}/wellboremarkersets',
             summary='Query with cursor, search wellbore markersets by wellbore ID',
             description=f"""Get all Wellbore Markersets objects using its relationship Wellbore ID.  <p>All Markers linked to this
            specific ID will be returned</p>
            <p>The Wellbore Markerset kind is {OSDU_WELLBOREMARKERSET_KIND} returns all records directly based on existing schemas</p>{REQUIRED_ROLES_READ}""",
             response_model=CursorQueryResponse)
async def query_markers_bywellbore(wellboreId: str, body: SearchQuery = None,
                                   ctx: Context = Depends(get_ctx)):
    query = added_relationships_query(wellboreId, WELLBORE_RELATIONSHIP, body.query)
    return await basic_query_request(query_type, OSDU_WELLBOREMARKERSET_KIND, ctx, query)
