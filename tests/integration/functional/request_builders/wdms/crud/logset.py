from request_runner import RequestRunner, Request


def build_request_get_versions_of_logset() -> RequestRunner:
    rq_proto = Request(
        name='Get versions of logset',
        method='GET',
        url='{{base_url}}/ddms/v2/logsets/{{logset_record_id}}/versions',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_logset_specific_version() -> RequestRunner:
    rq_proto = Request(
        name='Get logset specific version',
        method='GET',
        url='{{base_url}}/ddms/v2/logsets/{{logset_record_id}}/versions/{{logset_record_version}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_logset() -> RequestRunner:
    rq_proto = Request(
        name='Get logset',
        method='GET',
        url='{{base_url}}/ddms/v2/logsets/{{logset_record_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_delete_logset() -> RequestRunner:
    rq_proto = Request(
        name='Delete logset',
        method='DELETE',
        url='{{base_url}}/ddms/v2/logsets/{{logset_record_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_create_logset() -> RequestRunner:
    rq_proto = Request(
        name='Create logset',
        method='POST',
        url='{{base_url}}/ddms/v2/logsets',
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
  "data": {"name": "wdms_e2e_logset"},
  "kind": "{{logSetKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)

