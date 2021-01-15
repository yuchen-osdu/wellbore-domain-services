from request_runner import RequestRunner, Request


def build_request_version() -> RequestRunner:
    rq_proto = Request(
        name='version',
        method='GET',
        url='{{base_url}}/ddms/v2/version',
        headers={
            'accept': 'application/json',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)

