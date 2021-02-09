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


def build_request_get_well() -> RequestRunner:
    rq_proto = Request(
        name='Get well',
        method='GET',
        url='{{base_url}}/ddms/v2/wells/{{well_record_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_delete_well() -> RequestRunner:
    rq_proto = Request(
        name='Delete well',
        method='DELETE',
        url='{{base_url}}/ddms/v2/wells/{{well_record_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_well_specific_version() -> RequestRunner:
    rq_proto = Request(
        name='Get well specific version',
        method='GET',
        url='{{base_url}}/ddms/v2/wells/{{well_record_id}}/versions/{{well_record_version}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_versions_of_well() -> RequestRunner:
    rq_proto = Request(
        name='Get versions of well',
        method='GET',
        url='{{base_url}}/ddms/v2/wells/{{well_record_id}}/versions',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_create_well() -> RequestRunner:
    rq_proto = Request(
        name='Create well',
        method='POST',
        url='{{base_url}}/ddms/v2/wells',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
[
{
  "acl": {{record_acl}}, "legal": {{record_legal}},
  "data": {"name": "wdms_e2e_well"},
  "kind": "{{wellKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)

