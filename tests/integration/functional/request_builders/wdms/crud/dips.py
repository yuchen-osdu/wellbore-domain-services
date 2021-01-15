from request_runner import RequestRunner, Request


def build_request_get_dipset() -> RequestRunner:
    rq_proto = Request(
        name='Get dipset',
        method='GET',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}',
        headers={
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_query_dips() -> RequestRunner:
    rq_proto = Request(
        name='Query dips',
        method='GET',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}/dips/query?minReference=3500&maxReference=8000&classification=breakout',
        headers={
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_delete_dip() -> RequestRunner:
    rq_proto = Request(
        name='Delete dip',
        method='DELETE',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}/dips/0',
        headers={
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_create_dips() -> RequestRunner:
    rq_proto = Request(
        name='Create dips',
        method='POST',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}/dips',
        headers={
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
[
    {
        "reference": {"unitKey":"meter", "value":2000.0},
        "azimuth":  {"unitKey":"dega", "value":34},
        "inclination":  {"unitKey":"dega", "value":27}
    },
    {
        "reference": {"unitKey":"meter", "value":1000.0},
        "azimuth":  {"unitKey":"dega", "value":0.123456789121212121212},
        "inclination":  {"unitKey":"dega", "value":12},
        "quality":  {"unitKey":"unitless", "value":1},
        "xCoordinate":  {"unitKey":"m", "value":1},
        "yCoordinate":  {"unitKey":"m", "value":2},
        "zCoordinate":  {"unitKey":"m", "value":3},
        "classification": "fracture"
    },
    {
        "reference": {"unitKey":"meter", "value":4000.0},
        "azimuth":  {"unitKey":"dega", "value":4},
        "inclination":  {"unitKey":"dega", "value":2},
        "classification": "breakout"
    } ,
    {
        "reference": {"unitKey":"meter", "value":3000.0},
        "azimuth":  {"unitKey":"dega", "value":3},
        "inclination":  {"unitKey":"dega", "value":1},
        "classification": "fracture"
    }   
]

"""
    )
    return RequestRunner(rq_proto)


def build_request_create__dipset() -> RequestRunner:
    rq_proto = Request(
        name='Create  dipset',
        method='POST',
        url='{{base_url}}/ddms/v2/dipsets',
        headers={
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
[
{
    "acl": {{record_acl}}, "legal": {{record_legal}},
    "data": { "name": "wdms_e2e_dipset_Keon" },
    "kind": "{{dipsetKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)


def build_request_insert_dips() -> RequestRunner:
    rq_proto = Request(
        name='Insert dips',
        method='POST',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}/dips/insert',
        headers={
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
[

    {
        "reference": {"unitKey":"meter", "value":1500.0},
        "azimuth":  {"unitKey":"dega", "value":77},
        "inclination":  {"unitKey":"dega", "value":81}
    },
    {
        "reference": {"unitKey":"meter", "value":888.0},
        "azimuth":  {"unitKey":"dega", "value":666.66},
        "inclination":  {"unitKey":"dega", "value":99.99}
    }
    
]

"""
    )
    return RequestRunner(rq_proto)


def build_request_get_dip_from_index() -> RequestRunner:
    rq_proto = Request(
        name='Get dip from index',
        method='GET',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}/dips/1',
        headers={
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_delete_dipset() -> RequestRunner:
    rq_proto = Request(
        name='Delete dipset',
        method='DELETE',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}',
        headers={
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)


def build_request_patch_dip() -> RequestRunner:
    rq_proto = Request(
        name='Patch dip',
        method='PATCH',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}/dips/0?=',
        headers={
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""

{
    "reference": {"unitKey":"meter", "value":1000.0},
    "azimuth":  {"unitKey":"dega", "value":8},
    "inclination":  {"unitKey":"dega", "value":12},
    "classification": "fracture",
    "quality" :  {"unitKey":"unitless", "value":0},
    "xCoordinate" :  {"unitKey":"meter", "value":12},
    "yCoordinate" :  {"unitKey":"meter", "value":12},
    "zCoordinate" :  {"unitKey":"meter", "value":12}

}

"""
    )
    return RequestRunner(rq_proto)


def build_request_get_dips() -> RequestRunner:
    rq_proto = Request(
        name='Get dips',
        method='GET',
        url='{{base_url}}/ddms/v2/dipsets/{{dipsetId}}/dips',
        headers={
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
    )
    return RequestRunner(rq_proto)

