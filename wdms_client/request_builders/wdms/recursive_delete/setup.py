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


def build_request_recursive_del_setup_check_state_start() -> RequestRunner:
    rq_proto = Request(
        name='recursive_del_setup_check_state_start',
        method='POST',
        url='{{base_url}}/ddms/query',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
{
    "kind": "{{logSetKind}}",
    "query": "data.name:\"wdms_e2e_recursive_del_refs\"",
    "returnedFields": ["id", "data.channelNames"]
}

"""
    )
    return RequestRunner(rq_proto)


def build_request_recursive_del_setup_create_logs() -> RequestRunner:
    rq_proto = Request(
        name='recursive_del_setup_create_logs',
        method='POST',
        url='{{base_url}}/ddms/v2/logs',
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
  "data": {
      "name": "wdms_e2e_recursive_del_log",
      "relationships": {
            "well": {"id":"{{recursive_del_well_id}}"},
            "logset": {"id":"{{recursive_del_logset_id}}"}
        }
    },
  "kind": "{{logKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)
