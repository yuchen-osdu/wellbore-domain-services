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

