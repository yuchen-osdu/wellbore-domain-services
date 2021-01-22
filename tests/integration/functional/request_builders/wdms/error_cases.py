from request_runner import RequestRunner, Request


def build_request_create_log_with_invalid_data_should_422() -> RequestRunner:
    rq_proto = Request(
        name='create_log_with_invalid_data_should_422',
        method='POST',
        url='{{base_url}}/ddms/v2/logs',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
[{"data":{"name":"incomplete_data"}}]
"""
    )
    return RequestRunner(rq_proto)

