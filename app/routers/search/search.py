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
from odes_search.models import (
    QueryRequest,
    QueryResponse,
    CursorQueryResponse,
    SpatialFilter,
    Point,
    ByDistance,
    ByBoundingBox,
    ByGeoPolygon,
    CursorQueryRequest)
from app.clients.search_service_client import get_search_service
from ..common_parameters import REQUIRED_ROLES_READ
from app.context import Context
import app.routers.search.search_wrapper as search_wrapper
from app.helper.traces import TracingRoute
from pydantic import BaseModel, Field

router = APIRouter(route_class=TracingRoute)

wellbore_kind = '*:wks:wellbore:*'
log_kind = '*:wks:log:*'
logSet_kind = '*:wks:logSet:*'
marker_kind = '*:wks:marker:*'
crs_format = 'data.wellHeadWgs84'
query_type = 'query'
LIMIT = 1000


class SearchQuery(BaseModel):
    query: str = Field(None, alias="query")


def get_ctx() -> Context:
    return Context.current()


def query_type_returned_fields(query_type: str):
    returned_fields = 'id' if query_type == 'fastquery' else '*'
    return returned_fields


async def query_request_with_spatial_filter(query_type: str, spatial_filter: SpatialFilter, ctx: Context,
                                            query: str = None):
    returned_fields = query_type_returned_fields(query_type)
    query_request = QueryRequest(kind=wellbore_kind,
                                 query=query,
                                 returnedFields=[returned_fields],
                                 spatialFilter=spatial_filter)
    return await search_wrapper.SearchWrapper.query_cursorless(
        search_service=await get_search_service(ctx),
        data_partition_id=ctx.partition_id,
        query_request=query_request)


def query_spatial_filter_builder(spacial_filter_type: str, latitude1: float = None, longitude1: float = None,
                                 latitude2: float = None, longitude2: float = None, distance: int = None,
                                 points: List[Point] = None, geo_field: str = crs_format):
    if spacial_filter_type == "bydistance":
        point = Point(latitude=latitude1, longitude=longitude1)
        by_distance = ByDistance(distance=distance, point=point)
        spatial_filter = SpatialFilter(field=geo_field, byDistance=by_distance)
    if spacial_filter_type == "byboundingbox":
        point_top_left = Point(latitude=latitude1, longitude=longitude1)
        point_bottom_right = Point(latitude=latitude2, longitude=longitude2)
        by_bounding_box = ByBoundingBox(topLeft=point_top_left, bottomRight=point_bottom_right)
        spatial_filter = SpatialFilter(field=geo_field, byBoundingBox=by_bounding_box)
    if spacial_filter_type == "bygeopolygon":
        by_geo_polygon = ByGeoPolygon(points=points)
        spatial_filter = SpatialFilter(field=geo_field, byGeoPolygon=by_geo_polygon)
    return spatial_filter


def create_relationships_id_str(data_type, id):
    return f'data.relationships.{data_type}.id:\"{id}\"'


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
    id_list = ' OR '.join(relationships_ids) # [a, b, c] => 'a OR b OR c'

    if query:
        query = f'({id_list}) AND ({query})'
    else:
        query = f'{id_list}'

    returned_fields = query_type_returned_fields(query_type)
    query_request = QueryRequest(kind=kind,
                                 query=query,
                                 returnedFields=[returned_fields])
    return await search_wrapper.SearchWrapper.query_cursorless(
        search_service=client,
        data_partition_id=ctx.partition_id,
        query_request=query_request)


async def basic_query_request(query_type: str, kind: str, ctx: Context, query: str = None):
    returned_fields = query_type_returned_fields(query_type)
    query_request = QueryRequest(kind=kind,
                                 query=query,
                                 returnedFields=[returned_fields])
    client = await get_search_service(ctx)
    return await search_wrapper.SearchWrapper.query_cursorless(
        search_service=client,
        data_partition_id=ctx.partition_id,
        query_request=query_request)

async def basic_query_request_with_cursor(query_type: str, kind: str, ctx: Context, query: str = None):
    returned_fields = query_type_returned_fields(query_type)
    if not query:
        query = None
    query_request = CursorQueryRequest(kind=kind,
                                       limit=LIMIT,
                                       query=query,
                                       returnedFields=[returned_fields])
    client = await get_search_service(ctx)
    return await client.query_with_cursor(
        data_partition_id=ctx.partition_id,
        cursor_query_request=query_request)


def added_query(id: str, data_type: str, query: str = None):
    relationships_id = create_relationships_id_str(data_type, id)
    if query:
        query = f'{relationships_id} AND ({query})'
    else:
        query = relationships_id
    return query


