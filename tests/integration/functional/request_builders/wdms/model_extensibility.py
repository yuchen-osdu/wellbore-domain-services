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


def build_request_get_record_check_for_extra_fields() -> RequestRunner:
    rq_proto = Request(
        name='get_record_check_for_extra_fields',
        method='GET',
        url='{{base_url}}/ddms/v2/{{base_url_entity}}/{{record_id}}',
        headers={
            'Content-Type': 'application/json',
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_clean_up_delete_log() -> RequestRunner:
    rq_proto = Request(
        name='clean_up_delete_log',
        method='DELETE',
        url='{{base_url}}/ddms/v2/logs/{{record_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_create_log_with_extra_fields() -> RequestRunner:
    rq_proto = Request(
        name='create_log_with_extra_fields',
        method='POST',
        url='{{base_url}}/ddms/v2/logs',
        headers={
            'Content-Type': 'application/json',
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
[
{
  "acl": {{record_acl}}, "legal": {{record_legal}},
  "data": {
      "name": "wdms_e2e_well",
      "xxx_extra_at_data": "value_at_data"
  },
  "kind": "{{logKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)


def build_request_create_data_extra_fields() -> RequestRunner:
    rq_proto = Request(
        name='build_request_create_data_extra_fields',
        method='POST',
        url='{{base_url}}/ddms/v2/{{base_url_entity}}',
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
  "data": {{data}},
  "kind": "{{entity_kind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)