from request_runner import RequestRunner, Request


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


def build_request_get_log_bulk_data() -> RequestRunner:
    rq_proto = Request(
        name='Get log bulk data',
        method='GET',
        url='{{base_url}}/ddms/v2/logs/{{log_record_id}}/data?orient=split',
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
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
[
{
  "acl": {{record_acl}}, "legal": {{record_legal}},
  "data": {"name": "wdms_e2e_log"},
  "kind": "{{logKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)


def build_request_add_log_bulk_data() -> RequestRunner:
    rq_proto = Request(
        name='Add log bulk data',
        method='POST',
        url='{{base_url}}/ddms/v2/logs/{{log_record_id}}/data?orient=split',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload={
            "columns": [
                "Ref",
                "col_1",
                "col_2"
            ],
            "index": [0, 1, 2],
            "data": [
                [1, 10, 11],
                [1.5, 20, 21],
                [2, 30, 31]
            ]
        }
    )
    return RequestRunner(rq_proto)
