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

from ...request_runner import RequestRunner, Request
from typing import Dict


def build_create_session(record_id, prefix, *, meta: Dict[str, str] = None) -> RequestRunner:
    rq_proto = Request(
        name="Create session",
        method="POST",
        url="{{base_url}}/" + f"{prefix}/{record_id}/sessions",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
            "Content-Type": "application/json"
        },
        payload=
        {
          "fromVersion": 0,
          "timeToLive": 1440,
          "mode": "overwrite"
        },
    )

    if meta is not None:
        rq_proto.payload['meta'] = meta

    return RequestRunner(rq_proto)


def build_create_session_empty_payload(record_id, prefix, payload: dict) -> RequestRunner:
    rq_proto = Request(
        name="Create session",
        method="POST",
        url="{{base_url}}/" + f"{prefix}/{record_id}/sessions",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
            "Content-Type": "application/json"
        },
        payload=payload,
    )

    return RequestRunner(rq_proto)


def build_get_session(record_id, prefix, session_id) -> RequestRunner:
    rq_proto = Request(
        name="Get session",
        method="GET",
        url="{{base_url}}/" + f"{prefix}/{record_id}/sessions/{session_id}",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        }
    )

    return RequestRunner(rq_proto)


def build_list_session(record_id, prefix) -> RequestRunner:
    rq_proto = Request(
        name="List session",
        method="GET",
        url="{{base_url}}/" + f"{prefix}/{record_id}/sessions",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        }
    )

    return RequestRunner(rq_proto)


# TODO: temporary
def build_delete_session(record_id, prefix, session_id) -> RequestRunner:
    rq_proto = Request(
        name="Delete session",
        method="DELETE",
        url="{{base_url}}/" + f"{prefix}/{record_id}/sessions/{session_id}",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        }
    )

    return RequestRunner(rq_proto)
