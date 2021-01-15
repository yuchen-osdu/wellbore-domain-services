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
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
[
{

  "acl": {{record_acl}}, "legal": {{record_legal}},
  "data": {"name": "wdms_e2e_wellbore"},
  "kind": "{{wellboreKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)

