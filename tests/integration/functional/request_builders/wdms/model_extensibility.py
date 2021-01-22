from request_runner import RequestRunner, Request


def build_request_get_log_check_for_extra_fields() -> RequestRunner:
    rq_proto = Request(
        name='get_log_check_for_extra_fields',
        method='GET',
        url='{{base_url}}/ddms/v2/logs/{{record_id}}',
        headers={
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

