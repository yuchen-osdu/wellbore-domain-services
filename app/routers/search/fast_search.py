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
from app.routers.conf import REQUIRED_ROLES_READ
from app.utils import Context
import app.routers.search.search as search

router = APIRouter()
wellbore_kind = '*:wks:wellbore:*'
log_kind = '*:wks:log:*'
logSet_kind = '*:wks:logSet:*'
marker_kind = '*:wks:marker:*'
crs_format = 'data.wellHeadWgs84'
query_type = 'fastquery'


def get_ctx() -> Context:
    return Context.current()


@router.post('/fastquery/wellbores', summary="Query with cursor",
             description="""Get all Wellbores IDs object.  <p>The wellbore kind is
        *:wks:wellbore:* returns all records IDs IDs directly based on existing schemas</p>{}""".format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def fastquery_wellbores(body: search.SearchQuery = None, ctx: Context = Depends(get_ctx)):
    return await search.basic_query_request(query_type, wellbore_kind, ctx,  body.query)


@router.post('/fastquery/wellbores/bydistance', summary=f'Query with cursor, CRS format: {crs_format}',
             description="""Get all Wellbores IDs IDs objects in a specific area. <p>The specific area will be define by a circle
            based on its center coordinates (lat, lon) and radius (meters) </p>
            <p>The wellbore kind is *:wks:wellbore:* returns all records IDs IDs directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def fastquery_wellbores_bydistance(latitude: float, longitude: float, distance: int, body: search.SearchQuery = None,
                ctx: Context = Depends(get_ctx)):
    spatial_filter = search.query_spatial_filter_builder("bydistance", latitude1=latitude, longitude1=longitude,
                                                         distance=distance)
    return await search.query_request_with_spatial_filter(query_type, spatial_filter, ctx, body.query)


@router.post('/fastquery/wellbores/byboundingbox', summary=f'Query with cursor, CRS format: {crs_format}',
             description="""Get all Wellbores IDs objects in a specific area. <p>The specific area will be define by a square
            based on its top left coordinates (lat, lon) and its bottom right coordinates (log, lat) </p>
            <p>The wellbore kind is *:wks:wellbore:* returns all records IDs directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def fastquery_wellbores_byboundingbox(latitude_top_left: float, longitude_top_left: float,
                latitude_bottom_right: float, longitude_bottom_right: float,
                body: search.SearchQuery = None, ctx: Context = Depends(get_ctx)):
    spatial_filter = search.query_spatial_filter_builder("byboundingbox", latitude1=latitude_top_left,
                                                         longitude1=longitude_top_left,
                                                         latitude2=latitude_bottom_right,
                                                         longitude2=longitude_bottom_right)
    return await search.query_request_with_spatial_filter(query_type, spatial_filter, ctx, body.query)


@router.post('/fastquery/wellbores/bygeopolygon', summary=f'Query with cursor, CRS format: {crs_format}',
             description="""Get all Wellbores IDs objects in a specific area.  <p>The specific area will be define by a 
            polygon based on each of its coordinates (lat, lon) with a minimum of three</p>
            <p>The wellbore kind is *:wks:wellbore:* returns all records IDs directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def fastquery_wellbores_bygeopolygon(points: List[Point], query: search.SearchQuery = None,
                ctx: Context = Depends(get_ctx)):
    spatial_filter = search.query_spatial_filter_builder("bygeopolygon", points=points)
    return await search.query_request_with_spatial_filter(query_type, spatial_filter, ctx, query.query)


@router.post('/fastquery/wellbore/{wellbore_id}/logsets',
             summary='Query with cursor, search logSets IDs by wellbore ID',
             description="""Get all LogSets IDs objects using its relationship Wellbore ID.  <p>All LogSets linked to this
            specific ID will be returned</p>
            <p>The LogSet kind is *:wks:logSet:* returns all records IDs directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def fastquery_logsets_bywellbore(wellbore_id: str, body: search.SearchQuery = None,
                ctx: Context = Depends(get_ctx)):
    query = search.added_query(wellbore_id, "wellbore", body.query)
    return await search.basic_query_request(query_type, logSet_kind, ctx, query)


@router.post('/fastquery/wellbores/{wellbore_attribute}/logsets',
             summary='Query with cursor, search logSets IDs by wellbore attribute',
             description="""Get all LogSets IDs objects using a specific attribute of Wellbores.  <p>All LogSets linked to Wellbores
            with this specific attribute will be returned</p>
            <p>The LogSet kind is *:wks:logSet:* returns all records IDs directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def fastquery_logsets_bywellboreattribute(wellbore_attribute: str, body: search.SearchQuery = None,
                ctx: Context = Depends(get_ctx)):
    return await search.query_request_with_specific_attribute(query_type, wellbore_attribute, wellbore_kind,
                                                              logSet_kind, "wellbore", ctx,
                                                              body.query)


@router.post('/fastquery/logs', summary='Query with cursor, gets logs',
             description="""Get all Logs object.  <p>The Logs kind is
        *:wks:log:* returns all records IDs directly based on existing schemas</p>{}""".format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def fastquery_logs(body: search.SearchQuery = None, ctx: Context = Depends(get_ctx)):
    return await search.basic_query_request(query_type, log_kind, ctx, body.query)


@router.post('/fastquery/wellbore/{wellbore_id}/logs', summary='Query with cursor, search logs IDs by wellbore ID',
             description="""Get all Logs IDs objects using its relationship Wellbore ID.  <p>All Logs linked to this
            specific ID will be returned</p>
            <p>The Log kind is *:wks:log:* returns all records IDs directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def fastquery_logs_bywellbore(wellbore_id: str, body: search.SearchQuery = None,
                ctx: Context = Depends(get_ctx)):
    query = search.added_query(wellbore_id, "wellbore", body.query)
    return await search.basic_query_request(query_type, log_kind, ctx, query)


@router.post('/fastquery/wellbores/{wellbore_attribute}/logs',
             summary='Query with cursor, search logs IDs by wellbore attribute',
             description="""Get all Logs IDs objects using a specific attribute of Wellbores.  <p>All Logs linked to Wellbores
            with this specific attribute will be returned</p>
            <p>The Log kind is *:wks:log:* returns all records IDs directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def fastquery_logs_bywellboreattribute(wellbore_attribute: str, body: search.SearchQuery = None,
                ctx: Context = Depends(get_ctx)):
    return await search.query_request_with_specific_attribute(query_type, wellbore_attribute, wellbore_kind, log_kind,
                                                              "wellbore", ctx,
                                                              body.query)


@router.post('/fastquery/logset/{logset_id}/logs', summary='Query with cursor, search logs IDs by logSet ID',
             description="""Get all Logs IDs objects using its relationship Logset ID.  <p>All Logs linked to this
            specific ID will be returned</p>
            <p>The Log kind is *:wks:log:* returns all records IDs directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def fastquery_logs_bylogset(logset_id: str, body: search.SearchQuery = None,
                ctx: Context = Depends(get_ctx)):
    query = search.added_query(logset_id, "logSet", body.query)
    return await search.basic_query_request(query_type, log_kind, ctx, query)


@router.post('/fastquery/logsets/{logset_attribute}/logs',
             summary='Query with cursor, search logs IDs by logSet attribute',
             description="""Get all Logs IDs objects using a specific attribute of LogSets.  <p>All Logs linked to LogSets
            with this specific attribute will be returned</p>
            <p>The Log kind is *:wks:log:* returns all records IDs directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def fastquery_logs_bylogsetattribute(logset_attribute: str, body: search.SearchQuery = None,
                ctx: Context = Depends(get_ctx)):
    return await search.query_request_with_specific_attribute(query_type, logset_attribute, logSet_kind, log_kind,
                                                              "logSet", ctx,
                                                              body.query)


@router.post('/fastquery/wellbore/{wellbore_id}/markers',
             summary='Query with cursor, search markers IDs by wellbore ID',
             description="""Get all Markers IDs objects using its relationship Wellbore ID.  <p>All Markers linked to this
            specific ID will be returned</p>
            <p>The Marker kind is *:wks:marker:* returns all records IDs directly based on existing schemas</p>{}"""
             .format(REQUIRED_ROLES_READ),
             response_model=CursorQueryResponse)
async def fastquery_markers_bywellbore(wellbore_id: str, body: search.SearchQuery = None,
                ctx: Context = Depends(get_ctx)):
    query = search.added_query(wellbore_id, "wellbore", body.query)
    return await search.basic_query_request(query_type, marker_kind, ctx, query)
