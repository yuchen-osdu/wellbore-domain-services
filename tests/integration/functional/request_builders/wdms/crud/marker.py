from request_runner import RequestRunner, Request


def build_request_delete_marker() -> RequestRunner:
    rq_proto = Request(
        name='Delete marker',
        method='DELETE',
        url='{{base_url}}/ddms/v2/markers/{{marker_record_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_versions_of_marker() -> RequestRunner:
    rq_proto = Request(
        name='Get versions of marker',
        method='GET',
        url='{{base_url}}/ddms/v2/markers/{{marker_record_id}}/versions',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_marker() -> RequestRunner:
    rq_proto = Request(
        name='Get marker',
        method='GET',
        url='{{base_url}}/ddms/v2/markers/{{marker_record_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_marker_specific_version() -> RequestRunner:
    rq_proto = Request(
        name='Get marker specific version',
        method='GET',
        url='{{base_url}}/ddms/v2/markers/{{marker_record_id}}/versions/{{marker_record_version}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_create_marker() -> RequestRunner:
    rq_proto = Request(
        name='Create marker',
        method='POST',
        url='{{base_url}}/ddms/v2/markers',
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
      "name": "wdms_e2e_marker",
      "md": { "unitKey": "Unknown", "value": 0 }
  },
  "kind": "{{markerKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)

