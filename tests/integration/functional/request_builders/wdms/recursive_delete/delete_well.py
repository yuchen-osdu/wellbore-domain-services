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


def build_request_check_logset_is_deleted() -> RequestRunner:
    rq_proto = Request(
        name='check logset is deleted',
        method='GET',
        url='{{base_url}}/ddms/v2/logsets/{{recursive_del_logset_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_recursive_delete_well() -> RequestRunner:
    rq_proto = Request(
        name='recursive delete well',
        method='DELETE',
        url='{{base_url}}/ddms/v2/wells/{{recursive_del_well_id}}?recursive=true',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_check_log_is_deleted() -> RequestRunner:
    rq_proto = Request(
        name='check log is deleted',
        method='GET',
        url='{{base_url}}/ddms/v2/logs/{{recursive_del_log_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_check_wellbore_is_deleted() -> RequestRunner:
    rq_proto = Request(
        name='check wellbore is deleted',
        method='GET',
        url='{{base_url}}/ddms/v2/wellbores/{{recursive_del_wellbore_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)

