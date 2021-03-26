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
from app.routers.conf import REQUIRED_ROLES_READ
from app.utils import Context
import app.routers.search.search_wrapper as search_wrapper
from pydantic import BaseModel, Field

router = APIRouter()

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


def query_spatial_filter_builder(spacial_filter_type: str, latitude1: str = None, longitude1: float = None,
                                 latitude2: str = None, longitude2: float = None, distance: int = None,
                                 points: List[Point] = None):
    if spacial_filter_type == "bydistance":
        point = Point(latitude=latitude1, longitude=longitude1)
        by_distance = ByDistance(distance=distance, point=point)
        spatial_filter = SpatialFilter(field=crs_format, byDistance=by_distance)
    if spacial_filter_type == "byboundingbox":
        point_top_left = Point(latitude=latitude1, longitude=longitude1)
        point_bottom_right = Point(latitude=latitude2, longitude=longitude2)
        by_bounding_box = ByBoundingBox(topLeft=point_top_left, bottomRight=point_bottom_right)
        spatial_filter = SpatialFilter(field=crs_format, byBoundingBox=by_bounding_box)
    if spacial_filter_type == "bygeopolygon":
        by_geo_polygon = ByGeoPolygon(points=points)
        spatial_filter = SpatialFilter(field=crs_format, byGeoPolygon=by_geo_polygon)
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


@router.post('/query', summary='Query', description="{}".format(REQUIRED_ROLES_READ), response_model=QueryResponse)
async def query(query_request: QueryRequest,
                ctx: Context = Depends(get_ctx)) -> QueryResponse:
    client = await get_search_service(ctx)
    return await client.query(data_partition_id=ctx.partition_id,
                              query_request=query_request)


@router.post('/query_with_cursor', summary='Query with cursor', description="{}".format(REQUIRED_ROLES_READ), response_model=CursorQueryResponse)
async def query_with_cursor(query_request: QueryRequest,
                            ctx: Context = Depends(get_ctx)):
    client = await get_search_service(ctx)
    return await search_wrapper.SearchWrapper.query_cursorless(
        search_service=client,
        data_partition_id=ctx.partition_id,
        query_request=query_request)


@router.post('/query/wellbores', summary='Query with cursor',
             description="""Get all Wellbores object.  <p>The wellbore kind is
        *:wks:wellbore:* returns all records directly based on existing schemas</p>{}""".format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def query_wellbores(body: SearchQuery = None, ctx: Context = Depends(get_ctx)):
    return await basic_query_request_with_cursor(query_type, wellbore_kind, ctx, body.query)


@router.post('/query/wellbores/bydistance', summary=f'Query with cursor, CRS format: {crs_format}',
             description="""Get all Wellbores object in a specific area. <p>The specific area will be define by a circle
            based on its center coordinates (lat, lon) and radius (meters) </p>
            <p>The wellbore kind is *:wks:wellbore:* returns all records directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def query_wellbores_bydistance(latitude: float, longitude: float, distance: int, body: SearchQuery = None,
                                     ctx: Context = Depends(get_ctx)):
    spatial_filter = query_spatial_filter_builder("bydistance", latitude1=latitude, longitude1=longitude,
                                                  distance=distance)
    return await query_request_with_spatial_filter(query_type, spatial_filter, ctx, body.query)


@router.post('/query/wellbores/byboundingbox', summary=f'Query with cursor, CRS format: {crs_format}',
             description="""Get all Wellbores object in a specific area. <p>The specific area will be define by a square
            based on its top left coordinates (lat, lon) and its bottom right coordinates (log, lat) </p>
            <p>The wellbore kind is *:wks:wellbore:* returns all records directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def query_wellbores_byboundingbox(latitude_top_left: float, longitude_top_left: float,
                                        latitude_bottom_right: float, longitude_bottom_right: float,
                                        body: SearchQuery = None, ctx: Context = Depends(get_ctx)):
    spatial_filter = query_spatial_filter_builder("byboundingbox", latitude1=latitude_top_left,
                                                  longitude1=longitude_top_left,
                                                  latitude2=latitude_bottom_right, longitude2=longitude_bottom_right)
    return await query_request_with_spatial_filter(query_type, spatial_filter, ctx, body.query)


@router.post('/query/wellbores/bygeopolygon', summary=f'Query with cursor, CRS format: {crs_format}',
             description="""Get all Wellbores object in a specific area.  <p>The specific area will be define by a 
            polygon based on each of its coordinates (lat, lon) with a minimum of three</p>
            <p>The wellbore kind is *:wks:wellbore:* returns all records directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def query_wellbores_bygeopolygon(points: List[Point], query: SearchQuery = None,
                                       ctx: Context = Depends(get_ctx)):
    spatial_filter = query_spatial_filter_builder("bygeopolygon", points=points)
    return await query_request_with_spatial_filter(query_type, spatial_filter, ctx, query.query)


@router.post('/query/wellbore/{wellboreId}/logsets', summary='Query with cursor, search logSets by wellbore ID',
             description="""Get all LogSets object using its relationship Wellbore ID.  <p>All LogSets linked to this
            specific ID will be returned</p>
            <p>The LogSet kind is *:wks:logSet:* returns all records directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def query_logsets_bywellbore(wellboreId: str, body: SearchQuery = None,
                                   ctx: Context = Depends(get_ctx)):
    query = added_query(wellboreId, "wellbore", body.query)
    return await basic_query_request(query_type, logSet_kind, ctx, query)


@router.post('/query/wellbores/{wellboreAttribute}/logsets',
             summary='Query with cursor, search logSets by wellbore attribute',
             description="""Get all LogSets object using a specific attribute of Wellbores.  <p>All LogSets linked to Wellbores
            with this specific attribute will be returned</p>
            <p>The LogSet kind is *:wks:logSet:* returns all records directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def query_logsets_bywellboreattribute(wellboreAttribute: str, body: SearchQuery = None,
                                            ctx: Context = Depends(get_ctx)):
    return await query_request_with_specific_attribute(query_type, wellboreAttribute, wellbore_kind, logSet_kind,
                                                       "wellbore", ctx,
                                                       body.query)


@router.post('/query/logs', summary='Query with cursor, gets logs',
             description="""Get all Logs object.  <p>The Logs kind is
        *:wks:log:* returns all records directly based on existing schemas</p>{}""".format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def query_logs(body: SearchQuery = None, ctx: Context = Depends(get_ctx)):
    return await basic_query_request_with_cursor(query_type, log_kind, ctx, body.query)


@router.post('/query/wellbore/{wellboreId}/logs', summary='Query with cursor, search logs by wellbore ID',
             description="""Get all Logs object using its relationship Wellbore ID.  <p>All Logs linked to this
            specific ID will be returned</p>
            <p>The Log kind is *:wks:log:* returns all records directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def query_logs_bywellbore(wellboreId: str, body: SearchQuery = None,
                                ctx: Context = Depends(get_ctx)):
    query = added_query(wellboreId, "wellbore", body.query)
    return await basic_query_request(query_type, log_kind, ctx, query)


@router.post('/query/wellbores/{wellboreAttribute}/logs',
             summary='Query with cursor, search logs by wellbore attribute',
             description="""Get all Logs object using a specific attribute of Wellbores.  <p>All Logs linked to Wellbores
            with this specific attribute will be returned</p>
            <p>The Log kind is *:wks:log:* returns all records directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def query_logs_bywellboreattribute(wellboreAttribute: str, body: SearchQuery = None,
                                         ctx: Context = Depends(get_ctx)):
    return await query_request_with_specific_attribute(query_type, wellboreAttribute, wellbore_kind, log_kind,
                                                       "wellbore", ctx,
                                                       body.query)


@router.post('/query/logset/{logsetId}/logs', summary='Query with cursor, search logs by logSet ID',
             description="""Get all Logs object using its relationship Logset ID.  <p>All Logs linked to this
            specific ID will be returned</p>
            <p>The Log kind is *:wks:log:* returns all records directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def query_logs_bylogset(logsetId: str, body: SearchQuery = None,
                              ctx: Context = Depends(get_ctx)):
    query = added_query(logsetId, "logSet", body.query)
    return await basic_query_request(query_type, log_kind, ctx, query)


@router.post('/query/logsets/{logsetAttribute}/logs', summary='Query with cursor, search logs by logSet attribute',
             description="""Get all Logs object using a specific attribute of LogSets.  <p>All Logs linked to LogSets
            with this specific attribute will be returned</p>
            <p>The Log kind is *:wks:log:* returns all records directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def query_logs_bylogsetattribute(logsetAttribute: str, body: SearchQuery = None,
                                       ctx: Context = Depends(get_ctx)):
    return await query_request_with_specific_attribute(query_type, logsetAttribute, logSet_kind, log_kind, "logSet",
                                                       ctx,
                                                       body.query)


@router.post('/query/wellbore/{wellboreId}/markers', summary='Query with cursor, search markers by wellbore ID',
             description="""Get all Markers object using its relationship Wellbore ID.  <p>All Markers linked to this
            specific ID will be returned</p>
            <p>The Marker kind is *:wks:marker:* returns all records directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def query_markers_bywellbore(wellboreId: str, body: SearchQuery = None,
                                   ctx: Context = Depends(get_ctx)):
    query = added_query(wellboreId, "wellbore", body.query)
    return await basic_query_request(query_type, marker_kind, ctx, query)
