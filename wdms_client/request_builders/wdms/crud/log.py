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


def build_request_delete_log() -> RequestRunner:
    rq_proto = Request(
        name='Delete log',
        method='DELETE',
        url='{{base_url}}/ddms/v2/logs/{{log_record_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_versions_of_log() -> RequestRunner:
    rq_proto = Request(
        name='Get versions of log',
        method='GET',
        url='{{base_url}}/ddms/v2/logs/{{log_record_id}}/versions',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_log() -> RequestRunner:
    rq_proto = Request(
        name='Get log',
        method='GET',
        url='{{base_url}}/ddms/v2/logs/{{log_record_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_log_specific_version() -> RequestRunner:
    rq_proto = Request(
        name='Get log specific version',
        method='GET',
        url='{{base_url}}/ddms/v2/logs/{{log_record_id}}/versions/{{log_record_version}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_create_log() -> RequestRunner:
    rq_proto = Request(
        name='Create log',
        method='POST',
        url='{{base_url}}/ddms/v2/logs',
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
  "data": {"name": "{{prefix_data_entity_name}}_log"},
  "kind": "{{logKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)
