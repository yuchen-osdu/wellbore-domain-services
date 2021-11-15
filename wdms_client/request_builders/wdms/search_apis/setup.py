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


def build_request_seach_tests_setup_end() -> RequestRunner:
    rq_proto = Request(
        name='seach_tests_setup_end',
        method='GET',
        url='{{base_url}}/ddms/v2/about',
        headers={
            'accept': 'application/json',
        },
    )
    return RequestRunner(rq_proto)


def build_request_seach_tests_setup_create_logsets() -> RequestRunner:
    rq_proto = Request(
        name='seach_tests_setup_create_logsets',
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
    "name": "wdms_e2e_search_record_v{{search_record_version}}",
    "azimuthReference": "TN", 
    "channelMnemonics": [
      "DCAL", 
      "DPOR", 
      "GR", 
      "NPOR", 
      "RHOB", 
      "DT"
    ], 
    "channelNames": [
      "Differential Caliper", 
      "Density Porosity", 
      "Gamma Ray", 
      "Enhanced Thermal Neutron Porosity in Selected Lithology", 
      "CDL Bulk Density", 
      "Delta-T (also called Slowness or Interval Transit Time)"
    ], 
    "classification": "Quad-Combo", 
    "dateCreated": "2013-03-22T11:16:03Z", 
    "dateModified": "2013-03-22T11:16:03Z", 
    "elevationReference": {
      "elevationFromMsl": {
        "unitKey": "ft", 
        "value": 2680.5
      }, 
      "name": "KB"
    }, 
    "externalIds": [
      "Petrel:tenant1/ProjectLouisiana/3764913/a9b46fc4-1840-450a-ac01-d15bdaa086ba:9190e417-8d42-4994-9e6a-9a327b4f47b1"
    ], 
    "operation": "Harmonization", 
    "properties": [
      {
        "description": "Run 1 date  {DD/MM/YYYY}", 
        "name": "RUN_DATE-RUN1", 
        "unitKey": "", 
        "value": "22/09/1998"
      }, 
      {
        "description": "Run 1 depth interval", 
        "name": "RUN_DEPTH-TOP-RUN1", 
        "unitKey": "ft", 
        "value": 0
      }, 
      {
        "description": "Run 1 depth interval", 
        "name": "RUN_DEPTH-BASE-RUN1", 
        "unitKey": "ft", 
        "value": 1500
      }, 
      {
        "description": "Run 2 date  {DD/MM/YYYY}", 
        "name": "RUN_DATE-RUN2", 
        "unitKey": "", 
        "value": "23/10/1998"
      }, 
      {
        "description": "Run 2 depth interval", 
        "name": "RUN_DEPTH-TOP-RUN2", 
        "unitKey": "ft", 
        "value": 1500
      }, 
      {
        "description": "Run 2 depth interval", 
        "name": "RUN_DEPTH-BASE-RUN2", 
        "unitKey": "ft", 
        "value": 2513
      }, 
      {
        "associations": [
          "ENSEMBLE_TOOLELEMENT", 
          "EDTC-B_8612", 
          "EDTC-B_8612"
        ], 
        "description": "from Toolstring_Parameter", 
        "name": "EDTC-B_8612", 
        "value": 8612
      }, 
      {
        "description": "zone range", 
        "format": "{AF}", 
        "name": "ERRBND_Zone[1]", 
        "values": [
          -999.25, 
          43474.6413266435
        ]
      }
    ], 
    "reference": {
      "dataType": "number", 
      "dimension": 1, 
      "family": "Measured Depth", 
      "familyType": "Depth", 
      "format": "float32", 
      "mnemonic": "MD", 
      "name": "Measured Depth", 
      "unitKey": "ft"
    }, 
    "referenceType": "Measured Depth", 
    "relationships": {
      "well": {
        "name": "Newton 2-31"
      }, 
      "wellbore": {
        "confidence": 1.0, 
        "id": "{{setup_search_wellbore_id}}", 
        "name": "wddms-e2e-search-test-0000"
      }
    }, 
    "start": {
      "unitKey": "ft", 
      "value": 1234.56
    }, 
    "step": {
      "unitKey": "ft", 
      "value": 0.1
    }, 
    "stop": {
      "unitKey": "ft", 
      "value": 13856.25
    }
  }, 
  "meta": [
    {
      "kind": "Unit", 
      "name": "ft", 
      "persistableReference": "{\"scaleOffset\":{\"scale\":0.3048,\"offset\":0.0},\"symbol\":\"ft\",\"baseMeasurement\":{\"ancestry\":\"Length\",\"type\":\"UM\"},\"type\":\"USO\"}", 
      "propertyNames": [
        "stop.value", 
        "elevationReference.elevationFromMsl.value", 
        "start.value", 
        "step.value", 
        "reference.unitKey"
      ], 
      "propertyValues": [
        "ft"
      ]
    }, 
    {
      "kind": "DateTime", 
      "name": "datetime", 
      "persistableReference": "{\"format\":\"yyyy-MM-ddTHH:mm:ssZ\",\"timeZone\":\"UTC\",\"type\":\"DTM\"}", 
      "propertyNames": [
        "dateModified", 
        "dateCreated"
      ]
    }
  ]
}
]
"""
    )
    return RequestRunner(rq_proto)


def build_request_search_tests_setup_create_osdu_welllogs() -> RequestRunner:
    rq_proto = Request(
        name='seach_tests_setup_create_osdu_welllog',
        method='POST',
        url='{{base_url}}/ddms/v3/welllogs',
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
  "kind": "{{osduWellLogKind}}",
  "data": {
    "WellboreID": "{{setup_search_osdu_wellbore_id}}:",  
    "Name": "wdms_e2e_search_record_v{{search_record_version}}",
    "VerticalMeasurement": {
      "EffectiveDateTime": "2020-02-13T09:13:15.55Z",
      "VerticalMeasurement": 12345.6,
      "TerminationDateTime": "2020-02-13T09:13:15.55Z",
      "VerticalMeasurementTypeID": "namespace:reference-data--VerticalMeasurementType:Plug%20Back%20depth:",
      "VerticalMeasurementPathID": "namespace:reference-data--VerticalMeasurementPath:SomeUniqueVerticalMeasurementPathID:",
      "VerticalMeasurementSourceID": "namespace:reference-data--VerticalMeasurementSource:SomeUniqueVerticalMeasurementSourceID:",
      "WellboreTVDTrajectoryID": "namespace:work-product-component--WellboreTrajectory:WellboreTrajectory-123456:",
      "VerticalMeasurementUnitOfMeasureID": "namespace:reference-data--UnitOfMeasure:m:",
      "VerticalCRSID": "namespace:reference-data--CoordinateReferenceSystem:SomeUniqueCoordinateReferenceSystemID:",
      "VerticalReferenceID": "Example VerticalReferenceID",
      "VerticalMeasurementDescription": "Example VerticalMeasurementDescription"
      },
    "Curves": [{
        "CurveID": "Example CurveID",
        "DateStamp": "2020-02-13T09:13:15.55Z",
        "CurveVersion": "Example CurveVersion",
        "CurveQuality": "Example CurveQuality",
        "InterpreterName": "Example InterpreterName",
        "IsProcessed": true,
        "NullValue": true,
        "DepthCoding": "REGULAR",
        "Interpolate": true,
        "TopDepth": 12345.6,
        "BaseDepth": 12345.6,
        "DepthUnit": "namespace:reference-data--UnitOfMeasure:m:",
        "CurveUnit": "namespace:reference-data--UnitOfMeasure:m:",
        "Mnemonic": "Example Mnemonic",
        "LogCurveTypeID": "namespace:reference-data--LogCurveType:SomeUniqueLogCurveTypeID:",
        "LogCurveBusinessValueID": "namespace:reference-data--LogCurveBusinessValue:SomeUniqueLogCurveBusinessValueID:",
        "LogCurveMainFamilyID": "namespace:reference-data--LogCurveMainFamily:SomeUniqueLogCurveMainFamilyID:",
        "LogCurveFamilyID": "namespace:reference-data--LogCurveFamily:SomeUniqueLogCurveFamilyID:"
  }]
  }, 
  "meta": [
    {
      "kind": "Unit", 
      "name": "ft", 
      "persistableReference": "{\"scaleOffset\":{\"scale\":0.3048,\"offset\":0.0},\"symbol\":\"ft\",\"baseMeasurement\":{\"ancestry\":\"Length\",\"type\":\"UM\"},\"type\":\"USO\"}", 
      "propertyNames": [
        "stop.value", 
        "elevationReference.elevationFromMsl.value", 
        "start.value", 
        "step.value", 
        "reference.unitKey"
      ], 
      "propertyValues": [
        "ft"
      ]
    }, 
    {
      "kind": "DateTime", 
      "name": "datetime", 
      "persistableReference": "{\"format\":\"yyyy-MM-ddTHH:mm:ssZ\",\"timeZone\":\"UTC\",\"type\":\"DTM\"}", 
      "propertyNames": [
        "dateModified", 
        "dateCreated"
      ]
    }
  ]
}
]
"""
    )
    return RequestRunner(rq_proto)


def build_request_seach_tests_setup_create_record_refs() -> RequestRunner:
    rq_proto = Request(
        name='seach_tests_setup_create_record_refs',
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
      "name": "wdms_e2e_search_refs_v{{search_record_version}}",
      "description": "this is not an actual logset, but a record used in wdms integration tests to ref some other records. Purpose is for testing only.",
      "channelNames": [
            "{{setup_search_wellbore_id}}",
            "{{setup_search_logset_id}}"
      ]
  }
}
]

"""
    )
    return RequestRunner(rq_proto)


def build_request_seach_tests_setup_create_logs() -> RequestRunner:
    rq_proto = Request(
        name='seach_tests_setup_create_logs',
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
  "kind": "{{logKind}}",
  "data": {
    "azimuthReference": "TN", 
    "dateCreated": "2013-03-22T11:16:03Z", 
    "dateModified": "2013-03-22T11:16:03Z", 
	"basin": "Feda Graben (Central Graben)", 
    "elevationReference": {
      "elevationFromMsl": {
        "unitKey": "ft", 
        "value": 2680.5
      }, 
      "name": "KB"
    }, 
    "externalIds": [
      "Petrel:tenant1/ProjectLouisiana/3764913/a9b46fc4-1840-450a-ac01-d15bdaa086ba:438c35f3-fb59-4581-bb21-93b591d7cd1f"
    ], 
    "history": [
      {
        "date": "2019-02-01T11:16:03Z", 
        "description": "Created by Quanti_ Borehole computation; \nFamilies: True Vertical Depth; \nVariables: TVD, \nZonation: ZONATION_ALL; Unit: ft; \nMudType: Water; BSALinput: 0; Unit: ppk; BFHIinput: -9999; Unit: unitless; BPressCompute: Compute from mud weight and TVD; AirGap: 2; Unit: m; MudWeight: 1.1; Unit: g/m3; BTempCompute: Compute from depth tie point and gradient; BTEMPinput: 75; Unit: degC; BTEMPreferenceTVD: 2438.4; Unit: m; BTEMPgradient: 2; Unit: degC/100m; RmCompute: Compute from zoned variables; RMinput: 0.1; Unit: ohm.m; RMtemperature: 20; Unit: degC; RMFinput: 0.08; Unit: ohm.m; RMFtemperature: 20; Unit: degC; RMCinput: 0.16; Unit: ohm.m; RMCtemperature: 20; Unit: degC; RWinput: 0.1; Unit: ohm.m; RWtemperature: 100; Unit: degC; FormationSalinity: -9999; Unit: ppk;", 
        "user": "Ddahan"
      }
    ], 
    "log": {
      "dataType": "number", 
      "dimension": 1, 
      "family": "Density Porosity", 
      "familyType": "Porosity", 
      "format": "float32", 
      "logstoreId": 2156256839304115, 
      "mnemonic": "DPOR", 
      "name": "Density Porosity", 
      "properties": [
        {
          "description": "Linear depth offset of the channel sensor relative to some reference point, typically the toolstring zero", 
          "name": "MEASURE_POINT_OFFSET", 
          "unitKey": "m", 
          "value": 0.264922
        }
      ], 
      "unitKey": "%"
    }, 
    "name": "DPOR", 
    "reference": {
      "dataType": "number", 
      "dimension": 1, 
      "family": "Measured Depth", 
      "familyType": "Depth", 
      "format": "float32", 
      "mnemonic": "MD", 
      "name": "Measured Depth", 
      "unitKey": "ft"
    }, 
    "referenceType": "Measured Depth", 
    "relationships": {
      "logSet": {
        "id": "{{setup_search_logset_id}}"
      }, 
      "well": {
        "name": "wddms-e2e-search-test-0000"
      }, 
      "wellbore": {
        "confidence": 1.0, 
        "id": "{{setup_search_wellbore_id}}", 
        "name": "wddms-e2e-search-test-0000"
      }
    }, 
    "start": {
      "unitKey": "ft", 
      "value": 1234.56
    }, 
    "step": {
      "unitKey": "ft", 
      "value": 0.1
    }, 
    "stop": {
      "unitKey": "ft", 
      "value": 13856.25
    }
  },
  "meta": [
    {
      "kind": "Unit", 
      "name": "ft", 
      "persistableReference": "{\"scaleOffset\":{\"scale\":0.3048,\"offset\":0.0},\"symbol\":\"ft\",\"baseMeasurement\":{\"ancestry\":\"Length\",\"type\":\"UM\"},\"type\":\"USO\"}", 
      "propertyNames": [
        "reference.unitKey", 
        "stop.value", 
        "elevationReference.elevationFromMsl.value", 
        "start.value", 
        "step.value"
      ], 
      "propertyValues": [
        "ft"
      ]
    }, 
    {
      "kind": "Unit", 
      "name": "%", 
      "persistableReference": "{\"scaleOffset\":{\"scale\":0.01,\"offset\":0.0},\"symbol\":\"%\",\"baseMeasurement\":{\"ancestry\":\"Dimensionless\",\"type\":\"UM\"},\"type\":\"USO\"}", 
      "propertyNames": [
        "log.unitKey"
      ], 
      "propertyValues": [
        "%"
      ]
    }, 
    {
      "kind": "Unit", 
      "name": "m", 
      "persistableReference": "{\"scaleOffset\":{\"scale\":1.0,\"offset\":0.0},\"symbol\":\"m\",\"baseMeasurement\":{\"ancestry\":\"Length\",\"type\":\"UM\"},\"type\":\"USO\"}", 
      "propertyNames": [
        "log.properties.namedProperty.value"
      ]
    }
  ]
}
]
"""
    )
    return RequestRunner(rq_proto)


def build_request_seach_tests_setup_create_wellbore() -> RequestRunner:
    rq_proto = Request(
        name='seach_tests_setup_create_wellbore',
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
  "data": {
    "name": "wdms_e2e_search_record_v{{search_record_version}}",
    "basinContext": {
      "basinCode": "C5031", 
      "basinName": "Williston Basin", 
      "subBasinCode": "C50310104", 
      "subBasinName": "Three Forks Formation and Jefferson Group"
    }, 
    "block": "Block 11/8", 
    "country": "United States of America", 
    "county": "Stark", 
    "dateCreated": "2013-03-22T11:16:03Z", 
    "dateLicenseIssued": "2012-10-21T18:00:00Z", 
    "dateModified": "2013-03-22T11:16:03Z", 
    "datePluggedAbandoned": "2019-02-21T18:00:00Z", 
    "dateSpudded": "2014-02-21T19:00:00Z", 
    "directionWell": "producer", 
    "district": "Fryburg", 
    "elevationReference": {
      "elevationFromMsl": {
        "unitKey": "ft", 
        "value": 2650.5
      }, 
      "name": "GL"
    }, 
    "field": "Bell", 
    "fluidWell": "oil-gas", 
    "groundElevation": {
      "unitKey": "ft", 
      "value": 2645.6
    }, 
    "locationWGS84": {
      "features": [
        {
          "geometry": {
            "coordinates": [
              -103.2380248, 
              46.8925081, 
              2650.5
            ], 
            "type": "Point"
          }, 
          "properties": {
            "name": "Newton 2-31"
          }, 
          "type": "Feature"
        }
      ], 
      "type": "FeatureCollection"
    },
    "operator": "Don E. Beckert", 
    "operatorDivision": "Division ND", 
    "plssLocation": {
      "range": "99W", 
      "section": 31, 
      "township": "140N"
    }, 
    "propertyDictionary": {
      "API Number": "33003000080000", 
      "Activity Code": "E", 
      "Basin": "WILLISTON BASIN", 
      "Basin Code": "713200", 
      "Class Initial Code": "WF", 
      "Class Initial Name": "NEW FIELD WILDCAT", 
      "Country Name": "UNITED STATES", 
      "County Name": "BARNES", 
      "Current Operator City": "BILLINGS", 
      "Current Operator Name": "NYVATEX MONTANA", 
      "Date First Report": "11-12-1982", 
      "Date Last Activity": "06-03-2016", 
      "Depth Total Projected": "1800", 
      "Elevation Reference Datum": "GR", 
      "Elevation Reference Value": "1407", 
      "Field Name": "WILDCAT", 
      "Final Status": "ABANDON LOCATION", 
      "Formation Projected Name": "PRECAMBRIAN", 
      "Ground Elevation": "1407", 
      "Hole Direction": "VERTICAL", 
      "Lease Acres": "40", 
      "Lease Name": "TRIEBOLD", 
      "Operator City": "BILLINGS", 
      "Operator Name": "NYVATEX MONTANA", 
      "Permit Date": "11-10-1982", 
      "Permit Filer Long": ";PRESIDENT;;;;;;;", 
      "Permit Number": "9896", 
      "Permit Status": "APPROVED", 
      "Source": "PI", 
      "State Name": "NORTH DAKOTA", 
      "Status Final Code": "A", 
      "Sub Basin": "EASTERN SHELF (WILLISTON BASIN)", 
      "Sub Basin Code": "100000004313", 
      "Surface LL Source": "IH", 
      "Surface Latitude": "+47.1981919", 
      "Surface Longitude": " -97.8621697", 
      "UWI": "33003000080000", 
      "Unit of Measure": "ACRE", 
      "Well Num": "34-14"
    }, 
    "region": "North America", 
    "relationships": {
      "well": {
        "name": "Newton 2-31"
        } 
    },
    "state": "North Dakota", 
    "uwi": "33-089-00300-00", 
    "wellHeadElevation": {
      "unitKey": "ft", 
      "value": 2650.5
    }, 
    "wellHeadGeographic": {
      "crsKey": "geographic", 
      "elevationFromMsl": {
        "unitKey": "ft", 
        "value": 2650.5
      }, 
      "latitude": 46.89249512931594, 
      "longitude": -103.23756979739804
    }, 
    "wellHeadProjected": {
      "crsKey": "projected", 
      "elevationFromMsl": {
        "unitKey": "ft", 
        "value": 2650.5
      }, 
      "x": 1315694.366039069, 
      "y": 458966.7531300551
    }, 
    "wellHeadWgs84": {
      "latitude": 46.8925081, 
      "longitude": -103.2380248
    }, 
    "wellLocationType": "Onshore", 
    "wellNumberGovernment": "42-501-20130-P", 
    "wellNumberLicense": "42-501-20130-P", 
    "wellNumberOperator": "12399-001", 
    "wellPurpose": "development -- producer", 
    "wellStatus": "active -- producing", 
    "wellType": "reentry"
  }, 
  "kind": "{{wellboreKind}}",
  "acl": {{record_acl}}, "legal": {{record_legal}}
}
]
"""
    )
    return RequestRunner(rq_proto)


def build_request_search_tests_setup_create_osdu_wellbore() -> RequestRunner:
    rq_proto = Request(
        name='seach_tests_setup_create_osdu_wellbore',
        method='POST',
        url='{{base_url}}/ddms/v3/wellbores',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        payload=r"""
[
{
 "data": {
  "FacilityTypeID": "slb-osdu-dev-des-prod-testing:reference-data--FacilityType:Wellbore:",
  "CurrentOperatorID": "slb-osdu-dev-des-prod-testing:master-data--Organisation:KOTUKU%20CONSOLIDATED%20OIL%20CO:",
  "FacilityName": "wdms_e2e_search_refs_v{{search_record_version}}",
  "FacilityNameAliases": [
   {
    "AliasName": "08042021110609",
    "AliasNameTypeID": "slb-osdu-dev-des-prod-testing:reference-data--AliasNameType:UniqueIdentifier:"
   },
   {
    "AliasName": "SLB",
    "AliasNameTypeID": "slb-osdu-dev-des-prod-testing:reference-data--AliasNameType:RegulatoryIdentifier:"
   },
   {
    "AliasName": "operator5",
    "AliasNameTypeID": "slb-osdu-dev-des-prod-testing:reference-data--AliasNameType:IndustryName:"
   }
  ],
  "FacilityEvents": [
   {
    "FacilityEventTypeID": "slb-osdu-dev-des-prod-testing:reference-data--FacilityEventType:Spud:",
    "EffectiveDateTime": "1909-01-01T00:00:00"
   }
  ],
  "GeoContexts": [
   {
    "GeoPoliticalEntityID": "slb-osdu-dev-des-prod-testing:master-data--GeoPoliticalEntity:Germany:",
    "GeoTypeID": "slb-osdu-dev-des-prod-testing:reference-data--GeoPoliticalEntityType:Country:"
   },
   {
    "GeoPoliticalEntityID": "slb-osdu-dev-des-prod-testing:master-data--GeoPoliticalEntity::"
   },
   {
    "GeoPoliticalEntityID": "slb-osdu-dev-des-prod-testing:master-data--GeoPoliticalEntity:New%20South%20Wales:",
    "GeoTypeID": "slb-osdu-dev-des-prod-testing:reference-data--GeoPoliticalEntityType:State:"
   }
  ],
  "SpatialLocation": {
   "AsIngestedCoordinates": {
    "type": "AnyCrsFeatureCollection",
    "CoordinateReferenceSystemID": "slb-osdu-dev-des-prod-testing:reference-data--CoordinateReferenceSystem:GCS_WGS_1984:",
    "persistableReferenceCrs": "{\"wkt\":\"GEOGCS[\"GCS_WGS_1984\",DATUM[\"D_WGS_1984\",SPHEROID[\"WGS_1984\",6378137.0,298.257223563]],PRIMEM[\"Greenwich\",0.0],UNIT[\"Degree\",0.0174532925199433],AUTHORITY[\"EPSG\",4326]]\",\"ver\":\"PE_10_3_1\",\"name\":\"GCS_WGS_1984\",\"authCode\":{\"auth\":\"EPSG\",\"code\":\"4326\"},\"type\":\"LBC\"}",
    "persistableReferenceVerticalCrs": "{\"wkt\":\"GEOGCS[\"GCS_WGS_1984\",DATUM[\"D_WGS_1984\",SPHEROID[\"WGS_1984\",6378137.0,298.257223563]],PRIMEM[\"Greenwich\",0.0],UNIT[\"Degree\",0.0174532925199433],AUTHORITY[\"EPSG\",4326]]\",\"ver\":\"PE_10_3_1\",\"name\":\"GCS_WGS_1984\",\"authCode\":{\"auth\":\"EPSG\",\"code\":\"4326\"},\"type\":\"LBC\"}",
    "persistableReferenceUnitZ": "m",
    "features": [
     {
      "type": "AnyCrsFeature",
      "geometry": {
       "type": "AnyCrsPoint",
       "coordinates": [
        -21.5399,
        215.21
       ]
      }
     }
    ]
   },
   "Wgs84Coordinates": {
    "type": "FeatureCollection",
    "features": [
     {
      "type": "Feature",
      "geometry": {
       "type": "Point",
       "coordinates": [
        72.4635,
        -21.5399
       ]
      }
     }
    ]
   },
   "SpatialGeometryTypeID": "slb-osdu-dev-des-prod-testing:reference-data--SpatialGeometryType:Point:"
  },
  "VerticalMeasurements": [
   {
    "VerticalMeasurement": 264.21,
    "VerticalMeasurementTypeID": "slb-osdu-dev-des-prod-testing:reference-data--VerticalMeasurementType:KB:",
    "VerticalMeasurementPathID": "slb-osdu-dev-des-prod-testing:reference-data--VerticalMeasurementPath:ELEV:",
    "VerticalMeasurementUnitOfMeasureID": "slb-osdu-dev-des-prod-testing:reference-data--UnitOfMeasure:m:",
    "VerticalMeasurementID": "KB"
   },
   {
    "VerticalMeasurement": 34.0,
    "VerticalMeasurementPathID": "slb-osdu-dev-des-prod-testing:reference-data--VerticalMeasurementPath:MD:",
    "VerticalMeasurementUnitOfMeasureID": "slb-osdu-dev-des-prod-testing:reference-data--UnitOfMeasure:m:",
    "VerticalMeasurementID": "Total Depth MD"
   },
   {
    "VerticalMeasurement": 77.25,
    "VerticalMeasurementPathID": "slb-osdu-dev-des-prod-testing:reference-data--VerticalMeasurementPath:MD:",
    "VerticalMeasurementUnitOfMeasureID": "slb-osdu-dev-des-prod-testing:reference-data--UnitOfMeasure:m:",
    "VerticalMeasurementID": "Total Depth Driller MD"
   },
   {
    "VerticalMeasurement": 67.25,
    "VerticalMeasurementPathID": "slb-osdu-dev-des-prod-testing:reference-data--VerticalMeasurementPath:MD:",
    "VerticalMeasurementUnitOfMeasureID": "slb-osdu-dev-des-prod-testing:reference-data--UnitOfMeasure:m:",
    "VerticalMeasurementID": "Total Depth Planned MD"
   },
   {
    "VerticalMeasurement": 78.24,
    "VerticalMeasurementPathID": "slb-osdu-dev-des-prod-testing:reference-data--VerticalMeasurementPath:MD:",
    "VerticalMeasurementUnitOfMeasureID": "slb-osdu-dev-des-prod-testing:reference-data--UnitOfMeasure:m:",
    "VerticalMeasurementID": "Total Depth Sub Sea Planned MD"
   },
   {
    "VerticalMeasurement": 87.25,
    "VerticalMeasurementPathID": "slb-osdu-dev-des-prod-testing:reference-data--VerticalMeasurementPath:MD:",
    "VerticalMeasurementUnitOfMeasureID": "slb-osdu-dev-des-prod-testing:reference-data--UnitOfMeasure:m:",
    "VerticalMeasurementID": "Total Depth Projected MD"
   },
   {
    "VerticalMeasurement": 73.25,
    "VerticalMeasurementPathID": "slb-osdu-dev-des-prod-testing:reference-data--VerticalMeasurementPath:TVD:",
    "VerticalMeasurementUnitOfMeasureID": "slb-osdu-dev-des-prod-testing:reference-data--UnitOfMeasure:m:",
    "VerticalMeasurementID": "Total Depth TVD"
   },
   {
    "VerticalMeasurement": 45.89,
    "VerticalMeasurementPathID": "slb-osdu-dev-des-prod-testing:reference-data--VerticalMeasurementPath:TVD:",
    "VerticalMeasurementUnitOfMeasureID": "slb-osdu-dev-des-prod-testing:reference-data--UnitOfMeasure:m:",
    "VerticalMeasurementID": "Total Depth Driller TVD"
   },
   {
    "VerticalMeasurement": 57.93,
    "VerticalMeasurementPathID": "slb-osdu-dev-des-prod-testing:reference-data--VerticalMeasurementPath:TVD:",
    "VerticalMeasurementUnitOfMeasureID": "slb-osdu-dev-des-prod-testing:reference-data--UnitOfMeasure:m:",
    "VerticalMeasurementID": "Total Depth Planned TVD"
   },
   {
    "VerticalMeasurement": 64.21,
    "VerticalMeasurementPathID": "slb-osdu-dev-des-prod-testing:reference-data--VerticalMeasurementPath:TVD:",
    "VerticalMeasurementUnitOfMeasureID": "slb-osdu-dev-des-prod-testing:reference-data--UnitOfMeasure:m:",
    "VerticalMeasurementID": "Total Depth Sub Sea Planned TVD"
   },
   {
    "VerticalMeasurement": 264.21,
    "VerticalMeasurementPathID": "slb-osdu-dev-des-prod-testing:reference-data--VerticalMeasurementPath:ELEV:",
    "VerticalMeasurementUnitOfMeasureID": "slb-osdu-dev-des-prod-testing:reference-data--UnitOfMeasure:m:",
    "VerticalMeasurementID": "Well Head Elevation"
   },
   {
    "VerticalMeasurement": 58.25,
    "VerticalMeasurementPathID": "slb-osdu-dev-des-prod-testing:reference-data--VerticalMeasurementPath:MD:",
    "VerticalMeasurementUnitOfMeasureID": "slb-osdu-dev-des-prod-testing:reference-data--UnitOfMeasure:m:",
    "VerticalMeasurementID": "Kick-off Depth MD"
   },
   {
    "VerticalMeasurement": 47.25,
    "VerticalMeasurementPathID": "slb-osdu-dev-des-prod-testing:reference-data--VerticalMeasurementPath:TVD:",
    "VerticalMeasurementUnitOfMeasureID": "slb-osdu-dev-des-prod-testing:reference-data--UnitOfMeasure:m:",
    "VerticalMeasurementID": "Kick-off Depth TVD"
   }
  ],
  "DefaultVerticalMeasurementID": "KB",
  "ExtensionProperties": {
   }
  },
 "meta": [
  {
   "kind": "CRS",
   "name": "GCS_WGS_1984",
   "persistableReference": "{\"wkt\":\"GEOGCS[\"GCS_WGS_1984\",DATUM[\"D_WGS_1984\",SPHEROID[\"WGS_1984\",6378137.0,298.257223563]],PRIMEM[\"Greenwich\",0.0],UNIT[\"Degree\",0.0174532925199433],AUTHORITY[\"EPSG\",4326]]\",\"ver\":\"PE_10_3_1\",\"name\":\"GCS_WGS_1984\",\"authCode\":{\"auth\":\"EPSG\",\"code\":\"4326\"},\"type\":\"LBC\"}",
   "propertyNames": [
    "wellHeadWgs84.longitude",
    "wellHeadWgs84.latitude",
    "wellHeadGeographic.longitude",
    "wellHeadGeographic.latitude"
   ]
  },
  {
   "kind": "DateTime",
   "name": "datetime",
   "persistableReference": "{\"type\": \"DTM\", \"format\": \"yyyy-MM-dd\", \"timeZone\": \"UTC\"}",
   "propertyNames": [
    "spudDate"
   ]
  },
  {
   "kind": "Unit",
   "name": "m",
   "persistableReference": "{\"scaleOffset\":{\"scale\":1.0,\"offset\":0.0},\"symbol\":\"m\",\"baseMeasurement\":{\"ancestry\":\"L\",\"type\":\"UM\"},\"type\":\"USO\"}",
   "propertyNames": [
    "elevationReference.elevationFromMsl.value",
    "wellHeadElevation.value",
    "wellHeadGeographic.elevationFromMsl.value",
    "totalDepthMd.value"
   ]
  }
 ],
 "version": 1623075680181059,
 "kind": "{{osduWellboreKind}}",
 "acl": {{record_acl}}, 
 "legal": {{record_legal}} 
}
]
"""
    )
    return RequestRunner(rq_proto)


def build_request_seach_tests_setup_create_markers() -> RequestRunner:
    rq_proto = Request(
        name='seach_tests_setup_create_markers',
        method='POST',
        url='{{base_url}}/ddms/v2/markers',
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
    "name": "wdms_e2e_search_record_v{{search_record_version}}",
    "md": {"unitKey": "Unknown", "value": 0},
     "relationships": {
      "wellbore": {
        "confidence": 1.0, 
        "id": "{{setup_search_wellbore_id}}", 
        "name": "wdms_e2e_search_record_v{{search_record_version}}"
      }
    }
  },
  "kind": "{{markerKind}}"
}
]
"""
    )
    return RequestRunner(rq_proto)


def build_request_search_tests_setup_create_osdu_markersets() -> RequestRunner:
    rq_proto = Request(
        name='seach_tests_setup_create_osdu_markersets',
        method='POST',
        url='{{base_url}}/ddms/v3/wellboremarkersets',
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
  "kind": "{{osduWellboreMarkerSetKind}}",
  "data": {
    "Name": "wdms_e2e_search_record_v{{search_record_version}}",
    "WellboreID": "{{setup_search_osdu_wellbore_id}}:",
      "Markers": [
        {
          "MarkerName": "Example MarkerName",
          "MarkerMeasuredDepth": 12345.6,
          "MarkerDate": "2020-02-13T09:13:15.55Z",
          "MarkerObservationNumber": 12345.6,
          "MarkerInterpreter": "Example MarkerInterpreter",
          "MarkerTypeID": "namespace:reference-data--MarkerType:BioStratigraphy:",
          "FeatureTypeID": "namespace:reference-data--FeatureType:Base:",
          "FeatureName": "Example FeatureName",
          "PositiveVerticalDelta": 12345.6,
          "NegativeVerticalDelta": 12345.6,
          "SurfaceDipAngle": 12345.6,
          "SurfaceDipAzimuth": 12345.6,
          "Missing": "Example Missing",
          "GeologicalAge": "Example GeologicalAge"
        }
      ]    
    }
}
]
"""
    )
    return RequestRunner(rq_proto)


def build_request_search_tests_setup_create_osdu_trajectories() -> RequestRunner:
    rq_proto = Request(
        name='seach_tests_setup_create_osdu_trajectories',
        method='POST',
        url='{{base_url}}/ddms/v3/wellboretrajectories',
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
  "kind": "{{osduWellboreTrajectoryKind}}",
  "data": {
    "Name": "wdms_e2e_search_record_v{{search_record_version}}",
    "WellboreID": "{{setup_search_osdu_wellbore_id}}:",
    "TopDepthMeasuredDepth": 12345.6,
    "BaseDepthMeasuredDepth": 123.6,
    "AzimuthReferenceType": "namespace:reference-data--AzimuthReferenceType:TrueNorth:",
    "CalculationMethodType": "namespace:reference-data--CalculationMethodType:MinimumCurvature:",
    "ProjectedCRSID": "namespace:reference-data--CoordinateReferenceSystem:ProjectedCRS.EPSG.32615:",
    "ActiveIndicator": true,
    "VerticalMeasurement": {
      "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
      "VerticalMeasurement": 12345.6,
      "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00",
      "VerticalMeasurementTypeID": "namespace:reference-data--VerticalMeasurementType:PBD:",
      "VerticalMeasurementPathID": "namespace:reference-data--VerticalMeasurementPath:MD:",
      "VerticalMeasurementSourceID": "namespace:reference-data--VerticalMeasurementSource:DRL:",
      "WellboreTVDTrajectoryID": "namespace:work-product-component--WellboreTrajectory:WellboreTrajectory-456:",
      "VerticalMeasurementUnitOfMeasureID": "namespace:reference-data--UnitOfMeasure:m:",
      "VerticalCRSID": "namespace:reference-data--CoordinateReferenceSystem:BoundCRS::OSDU::23031018:",
      "VerticalReferenceID": "Example VerticalReferenceID",
      "VerticalMeasurementDescription": "Example VerticalMeasurementDescription"
    },
    "SurveyType": "Example Directional Survey Type"
    }
}
]
"""
    )
    return RequestRunner(rq_proto)



def build_request_seach_tests_setup_start() -> RequestRunner:
    rq_proto = Request(
        name='seach_tests_setup_start',
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
    "query": "data.name:\"wdms_e2e_search_refs_v{{search_record_version}}\"",
    "returnedFields": ["id", "data.channelNames"]
}

"""
    )
    return RequestRunner(rq_proto)


def build_request_osdu_seach_tests_setup_start() -> RequestRunner:
    rq_proto = Request(
        name='seach_tests_setup_start',
        method='POST',
        url='{{base_url}}/ddms/query',
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
        },
        # "kind": "{{osduWellboreKind}}",
        #         "query": "data.FacilityName:\"wdms_e2e_search_refs_v{{search_record_version}}\"",

    payload=r"""
{
    "kind": "{{osduWellboreTrajectoryKind}}",
    "query": "data.Name:\"wdms_e2e_search_record_v{{search_record_version}}\" AND _exists_:data.WellboreID",
    "returnedFields": ["id", "data.WellboreID"]
}

"""
    )
    return RequestRunner(rq_proto)

