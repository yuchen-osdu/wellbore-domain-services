from request_runner import RequestRunner, Request


def build_request_get_versions_of_trajectory() -> RequestRunner:
    rq_proto = Request(
        name='Get versions of trajectory',
        method='GET',
        url='{{base_url}}/ddms/v2/trajectories/{{trajectory_record_id}}/versions',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_trajectory() -> RequestRunner:
    rq_proto = Request(
        name='Get trajectory',
        method='GET',
        url='{{base_url}}/ddms/v2/trajectories/{{trajectory_record_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_trajectory_specific_version() -> RequestRunner:
    rq_proto = Request(
        name='Get trajectory specific version',
        method='GET',
        url='{{base_url}}/ddms/v2/trajectories/{{trajectory_record_id}}/versions/{{trajectory_record_version}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_delete_trajectory() -> RequestRunner:
    rq_proto = Request(
        name='Delete trajectory',
        method='DELETE',
        url='{{base_url}}/ddms/v2/trajectories/{{trajectory_record_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_create_trajectory() -> RequestRunner:
    rq_proto = Request(
        name='Create trajectory',
        method='POST',
        url='{{base_url}}/ddms/v2/trajectories',
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
  "data": {"name": "wdms_e2e_trajectory"},
  "kind": "{{trajectoryKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)

