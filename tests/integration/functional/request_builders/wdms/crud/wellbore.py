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


def build_request_delete_wellbore() -> RequestRunner:
    rq_proto = Request(
        name='Delete wellbore',
        method='DELETE',
        url='{{base_url}}/ddms/v2/wellbores/{{wellbore_record_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_wellbore_specific_version() -> RequestRunner:
    rq_proto = Request(
        name='Get wellbore specific version',
        method='GET',
        url='{{base_url}}/ddms/v2/wellbores/{{wellbore_record_id}}/versions/{{wellbore_record_version}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_wellbore() -> RequestRunner:
    rq_proto = Request(
        name='Get wellbore',
        method='GET',
        url='{{base_url}}/ddms/v2/wellbores/{{wellbore_record_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_versions_of_wellbore() -> RequestRunner:
    rq_proto = Request(
        name='Get versions of wellbore',
        method='GET',
        url='{{base_url}}/ddms/v2/wellbores/{{wellbore_record_id}}/versions',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_create_wellbore() -> RequestRunner:
    rq_proto = Request(
        name='Create wellbore',
        method='POST',
        url='{{base_url}}/ddms/v2/wellbores',
        headers={
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
[
{

  "acl": {{record_acl}}, "legal": {{record_legal}},
  "data": {"name": "{{prefix_data_entity_name}}_wellbore"},
  "kind": "{{wellboreKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)

