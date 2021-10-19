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


def build_request_get_dipset() -> RequestRunner:
    rq_proto = Request(
        name='Get dipset',
        method='GET',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}',
        headers={
            'Content-Type': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_query_dips() -> RequestRunner:
    rq_proto = Request(
        name='Query dips',
        method='GET',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}/dips/query?minReference=3500&maxReference=8000&classification=breakout',
        headers={
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_delete_dip() -> RequestRunner:
    rq_proto = Request(
        name='Delete dip',
        method='DELETE',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}/dips/0',
        headers={
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_create_dips() -> RequestRunner:
    rq_proto = Request(
        name='Create dips',
        method='POST',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}/dips',
        headers={
            'Content-Type': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
[
    {
        "reference": {"unitKey":"meter", "value":2000.0},
        "azimuth":  {"unitKey":"dega", "value":34},
        "inclination":  {"unitKey":"dega", "value":27}
    },
    {
        "reference": {"unitKey":"meter", "value":1000.0},
        "azimuth":  {"unitKey":"dega", "value":0.123456789121212121212},
        "inclination":  {"unitKey":"dega", "value":12},
        "quality":  {"unitKey":"unitless", "value":1},
        "xCoordinate":  {"unitKey":"m", "value":1},
        "yCoordinate":  {"unitKey":"m", "value":2},
        "zCoordinate":  {"unitKey":"m", "value":3},
        "classification": "fracture"
    },
    {
        "reference": {"unitKey":"meter", "value":4000.0},
        "azimuth":  {"unitKey":"dega", "value":4},
        "inclination":  {"unitKey":"dega", "value":2},
        "classification": "breakout"
    } ,
    {
        "reference": {"unitKey":"meter", "value":3000.0},
        "azimuth":  {"unitKey":"dega", "value":0},
        "inclination":  {"unitKey":"dega", "value":1},
        "classification": "fracture"
    }   
]

"""
    )
    return RequestRunner(rq_proto)


def build_request_create_dips_simple() -> RequestRunner:
    rq_proto = Request(
        name='Create dips',
        method='POST',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetIdSimple}}/dips',
        headers={
            'Content-Type': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
            [
                {{data_dips_simple}}
            ]
        """
    )
    return RequestRunner(rq_proto)

def build_request_create__dipset() -> RequestRunner:
    rq_proto = Request(
        name='Create  dipset',
        method='POST',
        url='{{base_url}}/ddms/v2/dipsets',
        headers={
            'Content-Type': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
[
{
    "acl": {{record_acl}}, "legal": {{record_legal}},
    "data": { "name": "{{prefix_data_entity_name}}_dipset_Keon" },
    "kind": "{{dipsetKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)


def build_request_insert_dips() -> RequestRunner:
    rq_proto = Request(
        name='Insert dips',
        method='POST',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}/dips/insert',
        headers={
            'Content-Type': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
[

    {
        "reference": {"unitKey":"meter", "value":1500.0},
        "azimuth":  {"unitKey":"dega", "value":77},
        "inclination":  {"unitKey":"dega", "value":81}
    },
    {
        "reference": {"unitKey":"meter", "value":888.0},
        "azimuth":  {"unitKey":"dega", "value":666.66},
        "inclination":  {"unitKey":"dega", "value":99.99}
    }
    
]

"""
    )
    return RequestRunner(rq_proto)


def build_request_get_dip_from_index() -> RequestRunner:
    rq_proto = Request(
        name='Get dip from index',
        method='GET',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}/dips/1',
        headers={
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_delete_dipset() -> RequestRunner:
    rq_proto = Request(
        name='Delete dipset',
        method='DELETE',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}',
        headers={
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_patch_dip() -> RequestRunner:
    rq_proto = Request(
        name='Patch dip',
        method='PATCH',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}/dips/0?=',
        headers={
            'Content-Type':'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""

{
    "reference": {"unitKey":"meter", "value":1000.0},
    "azimuth":  {"unitKey":"dega", "value":8},
    "inclination":  {"unitKey":"dega", "value":12},
    "classification": "fracture",
    "quality" :  {"unitKey":"unitless", "value":0},
    "xCoordinate" :  {"unitKey":"meter", "value":12},
    "yCoordinate" :  {"unitKey":"meter", "value":12},
    "zCoordinate" :  {"unitKey":"meter", "value":12}

}

"""
    )
    return RequestRunner(rq_proto)


def build_request_get_dips() -> RequestRunner:
    rq_proto = Request(
        name='Get dips',
        method='GET',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}/dips',
        headers={
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)

