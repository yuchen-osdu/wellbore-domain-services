from request_runner import RequestRunner, Request


def build_request_status() -> RequestRunner:
    rq_proto = Request(
        name='status',
        method='GET',
        url='{{base_url}}/ddms/v2/status',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)

