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

from ....request_runner import RequestRunner, Request


def build_request_search_markersets_by_wellbore_id() -> RequestRunner:
    rq_proto = Request(
        name='search markersets by wellbore id',
        method='POST',
        url='{{base_url}}/ddms/v3/{{search_query_type}}/wellbores/{{setup_search_osdu_wellbore_id}}/wellboremarkersets',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_osdu_wellbores_by_geo_polygon() -> RequestRunner:
    rq_proto = Request(
        name='search wellbores by geo polygon',
        method='POST',
        url='{{base_url}}/ddms/v3/{{search_query_type}}/wellbores/bygeopolygon',
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
                        "latitude": -20,
                        "longitude": 71
                    },
                    {
                        "latitude": -22,
                        "longitude": 71
                    },
                    {
                        "latitude": -22,
                        "longitude": 73
                    }
,
                    {
                        "latitude": -20,
                        "longitude": 71
                    }                    
              ],
               "query": {
                         "query": ""
                        }
           }
                """
    )
    return RequestRunner(rq_proto)


def build_request_search_welllogs_by_wellbores_attribute() -> RequestRunner:
    rq_proto = Request(
        name='search logset by wellbores attribute',
        method='POST',
        url='{{base_url}}/ddms/v3/{{search_query_type}}/wellbore/data.DefaultVerticalMeasurementID:"KB"/welllogs',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_osdu_wellbores_by_bounding_box() -> RequestRunner:
    rq_proto = Request(
        name='search wellbores by bounding box',
        method='POST',
        url='{{base_url}}/ddms/v3/{{search_query_type}}/wellbores/byboundingbox?latitude_top_left=-20&longitude_top_left=71&latitude_bottom_right=-22&longitude_bottom_right=73',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_osdu_wellbores_by_distance() -> RequestRunner:
    rq_proto = Request(
        name='search wellbores by distance',
        method='POST',
        url='{{base_url}}/ddms/v3/{{search_query_type}}/wellbores/bydistance?latitude=-21.5399&longitude=72.4635&distance=100',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_welllogs_by_wellbore_id() -> RequestRunner:
    rq_proto = Request(
        name='search logset by wellbore id',
        method='POST',
        url='{{base_url}}/ddms/v3/{{search_query_type}}/wellbores/{{setup_search_osdu_wellbore_id}}/welllogs',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_wellbore_by_name() -> RequestRunner:
    rq_proto = Request(
        name='search wellbore by name',
        method='POST',
        url='{{base_url}}/alpha/ddms/v3/{{search_query_type}}/wellbores?names=wdms_e2e_search_refs_v%2A',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{}'
    )
    return RequestRunner(rq_proto)


def build_request_search_trajectory_by_wellbore_id() -> RequestRunner:
    rq_proto = Request(
        name='search wellbore by name',
        method='POST',
        url='{{base_url}}/alpha/ddms/v3/{{search_query_type}}/wellbores/{{setup_search_osdu_wellbore_id}}/wellboretrajectories',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{}'
    )
    return RequestRunner(rq_proto)


def build_request_search_welllog_by_name() -> RequestRunner:
    rq_proto = Request(
        name='search wellbore by name',
        method='POST',
        url='{{base_url}}/alpha/ddms/v3/{{search_query_type}}/welllogs?names=wdms_e2e_search_record_%2A',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{}'
    )
    return RequestRunner(rq_proto)


def build_request_search_welllog_by_curve_mnemonics() -> RequestRunner:
    rq_proto = Request(
        name='search wellbore by name',
        method='POST',
        url='{{base_url}}/alpha/ddms/v3/{{search_query_type}}/welllogs?mnemonics=Example%20Mnemonic',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{}'
    )
    return RequestRunner(rq_proto)



def build_request_search_welllog_by_name_and_wellbore() -> RequestRunner:
    rq_proto = Request(
        name='search wellbore by name',
        method='POST',
        url='{{base_url}}/alpha/ddms/v3/{{search_query_type}}/welllogs?names=wdms_e2e_search_record_%2A'
            '&wellbore_id={{setup_search_osdu_wellbore_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{}'
    )
    return RequestRunner(rq_proto)
