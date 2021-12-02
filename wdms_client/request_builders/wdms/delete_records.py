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


from wdms_client.request_runner import RequestRunner, Request


def build_request_delete_osdu_records() -> RequestRunner:
    rq_proto = Request(
        name="Delete Records",
        method="POST",
        url="{{base_url}}/ddms/v3/records/delete",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
        payload=r""" {{record_ids}} """,
    )
    return RequestRunner(rq_proto)
