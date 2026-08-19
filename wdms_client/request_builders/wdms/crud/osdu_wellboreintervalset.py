# Copyright 2021 Schlumberger
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ....request_runner import RequestRunner, Request


def build_request_delete_osdu_wellboreintervalset_100() -> RequestRunner:
    rq_proto = Request(
        name="Delete wellboreintervalset",
        method="DELETE",
        url="{{base_url}}/ddms/v3/wellboreintervalsets/{{osdu_wellboreintervalset_100_record_id}}",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_osdu_wellboreintervalset_100_specific_version() -> RequestRunner:
    rq_proto = Request(
        name="Get wellboreintervalset specific version",
        method="GET",
        url="{{base_url}}/ddms/v3/wellboreintervalsets/{{osdu_wellboreintervalset_100_record_id}}/versions/{{osdu_wellboreintervalset_100_record_version}}",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_osdu_wellboreintervalset_100() -> RequestRunner:
    rq_proto = Request(
        name="Get wellboreintervalset",
        method="GET",
        url="{{base_url}}/ddms/v3/wellboreintervalsets/{{osdu_wellboreintervalset_100_record_id}}",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_versions_of_osdu_wellboreintervalset_100() -> RequestRunner:
    rq_proto = Request(
        name="Get versions of wellboreintervalset",
        method="GET",
        url="{{base_url}}/ddms/v3/wellboreintervalsets/{{osdu_wellboreintervalset_100_record_id}}/versions",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
    )
    return RequestRunner(rq_proto)


def build_request_create_osdu_wellboreintervalset_100(b_use_fixed_id=True) -> RequestRunner:
    if b_use_fixed_id:
        id_field = '"id": "{{data_partition}}:work-product-component--WellboreIntervalSet:c7c421a7-f496-5aef-8093-298c32bfdea9",'
    else:
        id_field = ''

    rq_proto = Request(
        name="Create OSDU wellboreintervalset",
        method="POST",
        url="{{base_url}}/ddms/v3/wellboreintervalsets",
        headers={
            "accept": "application/json",
            'Content-Type': 'application/json',
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
        payload='[{' + id_field + r"""
  "acl": {{record_acl}}, "legal": {{record_legal}},
  "kind": "{{osduWellboreIntervalSetKind}}",
  "tags": {
    "NameOfKey": "String value"
  },
  "createTime": "2020-12-16T11:46:20.163Z",
  "createUser": "some-user@some-company-cloud.com",
  "modifyTime": "2020-12-16T11:52:24.477Z",
  "modifyUser": "some-user@some-company-cloud.com",
  "meta": [
    {
      "kind": "Unit",
      "name": "m",
      "persistableReference": "{\"abcd\":{\"a\":0.0,\"b\":1.0,\"c\":1.0,\"d\":0.0},\"symbol\":\"m\",\"baseMeasurement\":{\"ancestry\":\"L\",\"type\":\"UM\"},\"type\":\"UAD\"}",
      "unitOfMeasureID": "namespace:reference-data--UnitOfMeasure:m:",
      "propertyNames": [
        "TopMeasuredDepth",
        "BottomMeasuredDepth"
      ]
    }
  ],
        "data": {
          "Name": "Example Name",
          "SubmitterName": "Example SubmitterName",
          "AuthorIDs": [
            "Example AuthorIDs"
          ],
          "WellboreID": "namespace:master-data--Wellbore:SomeUniqueWellboreID:",
          "VerticalMeasurement": {
                "VerticalMeasurement": 2680.5,
                "VerticalMeasurementPathID": "namespace:reference-data--VerticalMeasurementPath:MD:",
                "VerticalMeasurementUnitOfMeasureID": "namespace:reference-data--UnitOfMeasure:ft:"
            },      
          "StratigraphicColumnID": "namespace:work-product-component--StratigraphicColumn:stratigraphiccolumnid:",
          "StratigraphicColumnRankInterpretationID": "namespace:work-product-component--StratigraphicColumnRankInterpretation:Gudrun-Rank2-:",
          "Intervals": [
            {
              "IntervalID": "ba829e6d-30e0-4375-906c-4e7c62c9f7ec",
              "GeologicUnitInterpretationIDs": [
                "partition-id:work-product-component--StratigraphicUnitInterpretation:Draupne-:"
              ],
              "StartMeasuredDepth": 4049.0,
              "StartSubSeaVerticalDepth": 4030.9,
              "StartIntervalName": "Top-Draupne",
              "StartMarkerSetID": "namespace:work-product-component--WellboreMarkerSet:15-3-7-SingleRank-:",
              "StartMarkerID": "a580a3bb-c2db-4845-bbc1-050b417307c0",
              "StartBoundaryInterpretationID": "namespace:work-product-component--HorizonInterpretation:Top-Draupne-:",
              "StopMeasuredDepth": 4502.0,
              "StopSubSeaVerticalDepth": 4483.8,
              "StopIntervalName": "Top-Heather",
              "StopMarkerSetID": "namespace:work-product-component--WellboreMarkerSet:15-3-7-SingleRank-:",
              "StopMarkerID": "7699229b-36e8-4aed-884f-a1e844e5b9d7",
              "StopBoundaryInterpretationID": "namespace:work-product-component--HorizonInterpretation:Top-Heather-:"
            }
          ],
          "IntervalProperties": {
            "KeyColumns": [
              {
                "ValueType": "number",
                "ValueCount": 1,
                "UnitQuantityID": "namespace:reference-data--UnitQuantity:plane%20angle:",
                "PropertyType": {
                  "PropertyTypeID": "namespace:reference-data--PropertyType:ace68d4c-7400-431d-9a33-0541b8bfc4b4:",
                  "Name": "dip azimuth"
                },
                "RelationshipTargetKind": "osdu:wks:reference-data--UnitOfMeasure:",
                "FacetIDs": [
                  {
                    "FacetTypeID": "namespace:reference-data--FacetType:conditions:",
                    "FacetRoleID": "namespace:reference-data--FacetRole:I:"
                  }
                ]
              }
            ],
            "Columns": [
              {
                "ValueType": "string",
                "ValueCount": 1,
                "UnitQuantityID": "namespace:reference-data--UnitQuantity:plane%20angle:",
                "PropertyType": {
                  "PropertyTypeID": "namespace:reference-data--PropertyType:ace68d4c-7400-431d-9a33-0541b8bfc4b4:",
                  "Name": "dip azimuth"
                },
                "RelationshipTargetKind": "osdu:wks:reference-data--UnitOfMeasure:",
                "FacetIDs": [
                  {
                    "FacetTypeID": "namespace:reference-data--FacetType:conditions:",
                    "FacetRoleID": "namespace:reference-data--FacetRole:I:"
                  }
                ]
              }
            ],
            "ColumnSize": 5,
            "ColumnValues": [
              {
                "BooleanColumn": [
                  true,
                  false,
                  true,
                  true,
                  false
                ],
                "IntegerColumn": [
                  0,
                  1,
                  2,
                  3,
                  4
                ],
                "NumberColumn": [
                  0.1,
                  2.3,
                  4.5,
                  6.7,
                  8.9
                ],
                "StringColumn": [
                  "foo",
                  "bar",
                  "foo again",
                  "bar again",
                  "foo bar"
                ],
                "UndefinedValueRows": [
                  3,
                  4
                ]
              }
            ],
            "ColumnBasedTableType": "namespace:reference-data--ColumnBasedTableType:Facies:"
        },
      "ExtensionProperties": {}
    }
}
]""",
    )
    return RequestRunner(rq_proto)


def get_cleaned_ref_and_res() -> dict:
    ref = {
        "kind": "osdu:wks:work-product-component--WellboreIntervalSet:1.0.0",
        "acl": {
            "owners": [
                "someone@company.com"
            ],
            "viewers": [
                "someone@company.com"
            ]
        },
        "legal": {
            "legaltags": [
                "Example legaltags"
            ],
            "otherRelevantDataCountries": [
                "US"
            ],
            "status": "compliant"
        },
        "tags": {
            "NameOfKey": "String value"
        },
        "createTime": "2020-12-16T11:46:20.163Z",
        "createUser": "some-user@some-company-cloud.com",
        "modifyTime": "2020-12-16T11:52:24.477Z",
        "modifyUser": "some-user@some-company-cloud.com",
        "meta": [
            {
                "kind": "Unit",
                "name": "m",
                "persistableReference": "{\"abcd\":{\"a\":0.0,\"b\":1.0,\"c\":1.0,\"d\":0.0},\"symbol\":\"m\",\"baseMeasurement\":{\"ancestry\":\"L\",\"type\":\"UM\"},\"type\":\"UAD\"}",
                "unitOfMeasureID": "namespace:reference-data--UnitOfMeasure:m:",
                "propertyNames": [
                    "TopMeasuredDepth",
                    "BottomMeasuredDepth"
                ]
            }
        ],
        "data": {
            "Name": "Example Name",
            "SubmitterName": "Example SubmitterName",
            "AuthorIDs": [
                "Example AuthorIDs"
            ],
            "WellboreID": "namespace:master-data--Wellbore:SomeUniqueWellboreID:",
            "VerticalMeasurement": {
                "VerticalMeasurement": 2680.5,
                "VerticalMeasurementPathID": "namespace:reference-data--VerticalMeasurementPath:MD:",
                "VerticalMeasurementUnitOfMeasureID": "namespace:reference-data--UnitOfMeasure:ft:"
            },
            "StratigraphicColumnID": "namespace:work-product-component--StratigraphicColumn:stratigraphiccolumnid:",
            "StratigraphicColumnRankInterpretationID": "namespace:work-product-component--StratigraphicColumnRankInterpretation:Gudrun-Rank2-:",
            "Intervals": [
                {
                    "IntervalID": "ba829e6d-30e0-4375-906c-4e7c62c9f7ec",
                    "GeologicUnitInterpretationIDs": [
                        "partition-id:work-product-component--StratigraphicUnitInterpretation:Draupne-:"
                    ],
                    "StartMeasuredDepth": 4049.0,
                    "StartSubSeaVerticalDepth": 4030.9,
                    "StartIntervalName": "Top-Draupne",
                    "StartMarkerSetID": "namespace:work-product-component--WellboreMarkerSet:15-3-7-SingleRank-:",
                    "StartMarkerID": "a580a3bb-c2db-4845-bbc1-050b417307c0",
                    "StartBoundaryInterpretationID": "namespace:work-product-component--HorizonInterpretation:Top-Draupne-:",
                    "StopMeasuredDepth": 4502.0,
                    "StopSubSeaVerticalDepth": 4483.8,
                    "StopIntervalName": "Top-Heather",
                    "StopMarkerSetID": "namespace:work-product-component--WellboreMarkerSet:15-3-7-SingleRank-:",
                    "StopMarkerID": "7699229b-36e8-4aed-884f-a1e844e5b9d7",
                    "StopBoundaryInterpretationID": "namespace:work-product-component--HorizonInterpretation:Top-Heather-:"
                }
            ],
            "IntervalProperties": {
                "KeyColumns": [
                    {
                        "ValueType": "number",
                        "ValueCount": 1,
                        "UnitQuantityID": "namespace:reference-data--UnitQuantity:plane%20angle:",
                        "PropertyType": {
                            "PropertyTypeID": "namespace:reference-data--PropertyType:ace68d4c-7400-431d-9a33-0541b8bfc4b4:",
                            "Name": "dip azimuth"
                        },
                        "RelationshipTargetKind": "osdu:wks:reference-data--UnitOfMeasure:",
                        "FacetIDs": [
                            {
                                "FacetTypeID": "namespace:reference-data--FacetType:conditions:",
                                "FacetRoleID": "namespace:reference-data--FacetRole:I:"
                            }
                        ]
                    }
                ],
                "Columns": [
                    {
                        "ValueType": "string",
                        "ValueCount": 1,
                        "UnitQuantityID": "namespace:reference-data--UnitQuantity:plane%20angle:",
                        "PropertyType": {
                            "PropertyTypeID": "namespace:reference-data--PropertyType:ace68d4c-7400-431d-9a33-0541b8bfc4b4:",
                            "Name": "dip azimuth"
                        },
                        "RelationshipTargetKind": "osdu:wks:reference-data--UnitOfMeasure:",
                        "FacetIDs": [
                            {
                                "FacetTypeID": "namespace:reference-data--FacetType:conditions:",
                                "FacetRoleID": "namespace:reference-data--FacetRole:I:"
                            }
                        ]
                    }
                ],
                "ColumnSize": 5,
                "ColumnValues": [
                    {
                        "BooleanColumn": [
                            True,
                            False,
                            True,
                            True,
                            False
                        ],
                        "IntegerColumn": [
                            0,
                            1,
                            2,
                            3,
                            4
                        ],
                        "NumberColumn": [
                            0.1,
                            2.3,
                            4.5,
                            6.7,
                            8.9
                        ],
                        "StringColumn": [
                            "foo",
                            "bar",
                            "foo again",
                            "bar again",
                            "foo bar"
                        ],
                        "UndefinedValueRows": [
                            3,
                            4
                        ]
                    }
                ],
                "ColumnBasedTableType": "namespace:reference-data--ColumnBasedTableType:Facies:"
            },
            "ExtensionProperties": {}
        }

    }
    # Remove fields generated by server
    del ref["createTime"]
    del ref["createUser"]
    del ref["modifyUser"]
    del ref["modifyTime"]
    # Add mandatory fields
    ref["kind"] = "opendes:wks:master-data--WellboreIntervalSet:1.0.0"
    ref["acl"] = {
        "owners": ["data.default.owners@opendes.p4d.cloud.slb-ds.com"],
        "viewers": ["data.default.viewers@opendes.p4d.cloud.slb-ds.com"],
    }
    ref["legal"] = {
        "legaltags": ["opendes-public-usa-dataset-1"],
        "otherRelevantDataCountries": ["US"],
        "status": "compliant",
    }
    return ref
