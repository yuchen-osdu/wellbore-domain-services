from request_runner import RequestRunner, Request


def build_request_recursive_del_setup_end() -> RequestRunner:
    rq_proto = Request(
        name='recursive_del_setup_end',
        method='DELETE',
        url='{{base_url}}/ddms/v2/logsets/{{recursive_del_ref_record_id}}',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_recursive_del_setup_create_well() -> RequestRunner:
    rq_proto = Request(
        name='recursive_del_setup_create_well',
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
  "data": {"name": "wdms_e2e_recursive_del_well"},
  "kind": "{{wellKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)


def build_request_recursive_del_setup_check_state_start() -> RequestRunner:
    rq_proto = Request(
        name='recursive_del_setup_check_state_start',
        method='POST',
        url='{{base_url}}/ddms/query',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
{
    "kind": "{{logSetKind}}",
    "query": "data.name:\"wdms_e2e_recursive_del_refs\"",
    "returnedFields": ["id", "data.channelNames"]
}

"""
    )
    return RequestRunner(rq_proto)


def build_request_recursive_del_setup_create_logs() -> RequestRunner:
    rq_proto = Request(
        name='recursive_del_setup_create_logs',
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
      "name": "wdms_e2e_recursive_del_log",
      "relationships": {
            "well": {"id":"{{recursive_del_well_id}}"},
            "logset": {"id":"{{recursive_del_logset_id}}"}
        }
    },
  "kind": "{{logKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)


def build_request_recursive_del_setup_create_logset() -> RequestRunner:
    rq_proto = Request(
        name='recursive_del_setup_create_logset',
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
  "data": {
      "name": "wdms_e2e_recursive_del_logset",
      "relationships": {
            "well": {"id":"{{recursive_del_well_id}}"},
            "wellbore": {"id":"{{recursive_del_wellbore_id}}"}
        }
    },
  "kind": "{{logSetKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)


def build_request_recursive_del_setup_create_wellbore() -> RequestRunner:
    rq_proto = Request(
        name='recursive_del_setup_create_wellbore',
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
  "data": {
      "name": "wdms_e2e_recursive_del_wellbore",
      "relationships": { "well": {"id":"{{recursive_del_well_id}}"} }
    },
  "kind": "{{wellboreKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)


def build_request_recursive_del_setup_create_record_refs() -> RequestRunner:
    rq_proto = Request(
        name='recursive_del_setup_create_record_refs',
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
  "kind": "{{logSetKind}}",
  "data": {
      "name": "wdms_e2e_recursive_del_refs",
      "description": "this is not an actual logset, but a record used in wdms integration tests to ref some other records. Purpose is for testing only.",
      "channelNames": [
            "{{recursive_del_well_id}}",
            "{{recursive_del_wellbore_id}}",
            "{{recursive_del_logset_id}}",
            "{{recursive_del_log_id}}"
      ]
  }
}
]
"""
    )
    return RequestRunner(rq_proto)

