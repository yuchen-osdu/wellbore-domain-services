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

from request_runner import RequestRunner, Request


def build_request_search_logs_by_logset_id() -> RequestRunner:
    rq_proto = Request(
        name='search logs by logset id',
        method='POST',
        url='{{base_url}}/ddms/{{search_query_type}}/logset/{{search_logset_id}}/logs',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_markers_by_wellbore_id() -> RequestRunner:
    rq_proto = Request(
        name='search markers by wellbore id',
        method='POST',
        url='{{base_url}}/ddms/{{search_query_type}}/wellbore/{{search_wellbore_id}}/markers',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_wellbores_by_geo_polygon() -> RequestRunner:
    rq_proto = Request(
        name='search wellbores by geo polygon',
        method='POST',
        url='{{base_url}}/ddms/{{search_query_type}}/wellbores/bygeopolygon',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
        {
            "points": [
                   {
                        "latitude": 46,
                        "longitude": -101
                    },
                    {
                        "latitude": 49,
                        "longitude": -102
                    },
                    {
                        "latitude": 45,
                        "longitude": -105
                    }
              ],
               "query": {
                         "query": ""
                        }
           }
                """
    )
    return RequestRunner(rq_proto)


def build_request_search_logs_by_wellbore_id() -> RequestRunner:
    rq_proto = Request(
        name='search logs by wellbore id',
        method='POST',
        url='{{base_url}}/ddms/{{search_query_type}}/wellbore/{{search_wellbore_id}}/logs',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_logset_by_wellbores_attribute() -> RequestRunner:
    rq_proto = Request(
        name='search logset by wellbores attribute',
        method='POST',
        url='{{base_url}}/ddms/{{search_query_type}}/wellbores/data.state:"North Dakota"/logsets',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_logs_by_wellbores_attribute() -> RequestRunner:
    rq_proto = Request(
        name='search logs by wellbores attribute',
        method='POST',
        url='{{base_url}}/ddms/{{search_query_type}}/wellbores/data.state:"North Dakota"/logs',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_wellbores_by_bounding_box() -> RequestRunner:
    rq_proto = Request(
        name='search wellbores by bounding box',
        method='POST',
        url='{{base_url}}/ddms/{{search_query_type}}/wellbores/byboundingbox?latitude_top_left=48&longitude_top_left=-104&latitude_bottom_right=45&longitude_bottom_right=-101',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_wellbores_by_distance() -> RequestRunner:
    rq_proto = Request(
        name='search wellbores by distance',
        method='POST',
        url='{{base_url}}/ddms/{{search_query_type}}/wellbores/bydistance?latitude=46.8&longitude=-103.2&distance=15000',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_logs_by_logsets_attribute() -> RequestRunner:
    rq_proto = Request(
        name='search logs by logsets attribute',
        method='POST',
        url='{{base_url}}/ddms/{{search_query_type}}/logsets/data.classification:"Quad-Combo"/logs',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_logset_by_wellbore_id() -> RequestRunner:
    rq_proto = Request(
        name='search logset by wellbore id',
        method='POST',
        url='{{base_url}}/ddms/{{search_query_type}}/wellbore/{{search_wellbore_id}}/logsets',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_wellbores() -> RequestRunner:
    rq_proto = Request(
        name='search wellbores',
        method='POST',
        url='{{base_url}}/ddms/{{search_query_type}}/wellbores',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_logs() -> RequestRunner:
    rq_proto = Request(
        name='search logs',
        method='POST',
        url='{{base_url}}/ddms/{{search_query_type}}/logs',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)