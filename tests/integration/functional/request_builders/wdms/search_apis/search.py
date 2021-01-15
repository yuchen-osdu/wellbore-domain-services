from request_runner import RequestRunner, Request


def build_request_search_logs_by_logset_id() -> RequestRunner:
    rq_proto = Request(
        name='search logs by logset id',
        method='POST',
        url='{{base_url}}/ddms/query/logset/{{search_logset_id}}/logs',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_markers_by_wellbore_id() -> RequestRunner:
    rq_proto = Request(
        name='search markers by wellbore id',
        method='POST',
        url='{{base_url}}/ddms/query/wellbore/{{search_wellbore_id}}/markers',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_wellbores_by_geo_polygon() -> RequestRunner:
    rq_proto = Request(
        name='search wellbores by geo polygon',
        method='POST',
        url='{{base_url}}/ddms/query/wellbores/bygeopolygon',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
        {
            "points": [
                   {
                        "latitude": 46,
                        "longitude": -101
                    },
                    {
                        "latitude": 49,
                        "longitude": -102
                    },
                    {
                        "latitude": 45,
                        "longitude": -105
                    }
              ],
               "query": {
                         "query": ""
                        }
           }
                """
    )
    return RequestRunner(rq_proto)


def build_request_search_logs_by_wellbore_id() -> RequestRunner:
    rq_proto = Request(
        name='search logs by wellbore id',
        method='POST',
        url='{{base_url}}/ddms/query/wellbore/{{search_wellbore_id}}/logs',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_logset_by_wellbores_attribute() -> RequestRunner:
    rq_proto = Request(
        name='search logset by wellbores attribute',
        method='POST',
        url='{{base_url}}/ddms/query/wellbores/data.state:"North Dakota"/logsets',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_logs_by_wellbores_attribute() -> RequestRunner:
    rq_proto = Request(
        name='search logs by wellbores attribute',
        method='POST',
        url='{{base_url}}/ddms/query/wellbores/data.state:"North Dakota"/logs',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_wellbores_by_bounding_box() -> RequestRunner:
    rq_proto = Request(
        name='search wellbores by bounding box',
        method='POST',
        url='{{base_url}}/ddms/query/wellbores/byboundingbox?latitude_top_left=48&longitude_top_left=-104&latitude_bottom_right=45&longitude_bottom_right=-101',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_wellbores_by_distance() -> RequestRunner:
    rq_proto = Request(
        name='search wellbores by distance',
        method='POST',
        url='{{base_url}}/ddms/query/wellbores/bydistance?latitude=46.8&longitude=-103.2&distance=15000',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_logs_by_logsets_attribute() -> RequestRunner:
    rq_proto = Request(
        name='search logs by logsets attribute',
        method='POST',
        url='{{base_url}}/ddms/query/logsets/data.classification:"Quad-Combo"/logs',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)


def build_request_search_logset_by_wellbore_id() -> RequestRunner:
    rq_proto = Request(
        name='search logset by wellbore id',
        method='POST',
        url='{{base_url}}/ddms/query/wellbore/{{search_wellbore_id}}/logsets',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload='{ "query": "" }'
    )
    return RequestRunner(rq_proto)

