from request_runner import RequestRunner, Request


def build_request_about() -> RequestRunner:
    rq_proto = Request(
        name='about',
        method='GET',
        url='{{base_url}}/ddms/v2/about',
        headers={
            'accept': 'application/json',
            'Connection': '{{header_connection}}',
        },
    )
    return RequestRunner(rq_proto)

