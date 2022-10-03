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
import json


def build_request_delete_osdu_wellbore() -> RequestRunner:
    rq_proto = Request(
        name="Delete wellbore",
        method="DELETE",
        url="{{base_url}}/ddms/v3/wellbores/{{osdu_wellbore_record_id}}",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_osdu_wellbore_specific_version() -> RequestRunner:
    rq_proto = Request(
        name="Get wellbore specific version",
        method="GET",
        url="{{base_url}}/ddms/v3/wellbores/{{osdu_wellbore_record_id}}/versions/{{osdu_wellbore_record_version}}",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_osdu_wellbore() -> RequestRunner:
    rq_proto = Request(
        name="Get wellbore",
        method="GET",
        url="{{base_url}}/ddms/v3/wellbores/{{osdu_wellbore_record_id}}",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_versions_of_osdu_wellbore() -> RequestRunner:
    rq_proto = Request(
        name="Get versions of wellbore",
        method="GET",
        url="{{base_url}}/ddms/v3/wellbores/{{osdu_wellbore_record_id}}/versions",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
    )
    return RequestRunner(rq_proto)


def build_request_create_osdu_wellbore() -> RequestRunner:
    rq_proto = Request(
        name="Create OSDU wellbore",
        method="POST",
        url="{{base_url}}/ddms/v3/wellbores",
        headers={
            "accept": "application/json",
            'Content-Type': 'application/json',
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
        payload=r"""[{
  "acl": {{record_acl}}, "legal": {{record_legal}},
  "id": "{{data_partition}}:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9",
  "kind": "{{osduWellboreKind}}",
  "tags": {
    "NameOfKey": "String value"
  },
  "createTime": "2020-12-16T11:46:20.163Z",
  "createUser": "some-user@some-company-cloud.com",
  "modifyTime": "2020-12-16T11:52:24.477Z",
  "modifyUser": "some-user@some-company-cloud.com",
  "meta": [],
  "data": {
    "ResourceHomeRegionID": "namespace:reference-data--OSDURegion:SomeUniqueOSDURegionID:",
    "ResourceHostRegionIDs": [
      "namespace:reference-data--OSDURegion:SomeUniqueOSDURegionID:"
    ],
    "ResourceCurationStatus": "namespace:reference-data--ResourceCurationStatus:CREATED:",
    "ResourceLifecycleStatus": "namespace:reference-data--ResourceLifecycleStatus:LOADING:",
    "ResourceSecurityClassification": "namespace:reference-data--ResourceSecurityClassification:RESTRICTED:",
    "Source": "Example Data Source",
    "ExistenceKind": "namespace:reference-data--ExistenceKind:Prototype:",
    "NameAliases": [
      {
        "AliasName": "Example AliasName",
        "AliasNameTypeID": "namespace:reference-data--AliasNameType:Regulatory%20Identifier:",
        "DefinitionOrganisationID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
        "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
        "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00"
      }
    ],
    "GeoContexts": [
      {
        "BasinID": "namespace:master-data--Basin:SomeUniqueBasinID:",
        "GeoTypeID": "namespace:reference-data--BasinType:SomeUniqueBasinTypeID:"
      }
    ],
    "SpatialLocation": {
      "SpatialLocationCoordinatesDate": "2020-02-13T09:13:15.550000+00:00",
      "QuantitativeAccuracyBandID": "namespace:reference-data--QuantitativeAccuracyBand:SomeUniqueQuantitativeAccuracyBandID:",
      "QualitativeSpatialAccuracyTypeID": "namespace:reference-data--QualitativeSpatialAccuracyType:SomeUniqueQualitativeSpatialAccuracyTypeID:",
      "CoordinateQualityCheckPerformedBy": "Example CoordinateQualityCheckPerformedBy",
      "CoordinateQualityCheckDateTime": "2020-02-13T09:13:15.550000+00:00",
      "CoordinateQualityCheckRemarks": [
        "Example CoordinateQualityCheckRemarks"
      ],
      "AsIngestedCoordinates": {
        "type": "AnyCrsFeatureCollection",
        "CoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:BoundCRS.SLB.32021.15851:",
        "VerticalCoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:VerticalCRS.EPSG.5773:",
        "persistableReferenceCrs": "{\"lateBoundCRS\":{\"wkt\":\"PROJCS[\\\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\\\",GEOGCS[\\\"GCS_North_American_1927\\\",DATUM[\\\"D_North_American_1927\\\",SPHEROID[\\\"Clarke_1866\\\",6378206.4,294.9786982]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],PROJECTION[\\\"Lambert_Conformal_Conic\\\"],PARAMETER[\\\"False_Easting\\\",2000000.0],PARAMETER[\\\"False_Northing\\\",0.0],PARAMETER[\\\"Central_Meridian\\\",-100.5],PARAMETER[\\\"Standard_Parallel_1\\\",46.1833333333333],PARAMETER[\\\"Standard_Parallel_2\\\",47.4833333333333],PARAMETER[\\\"Latitude_Of_Origin\\\",45.6666666666667],UNIT[\\\"Foot_US\\\",0.304800609601219],AUTHORITY[\\\"EPSG\\\",32021]]\",\"ver\":\"PE_10_3_1\",\"name\":\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\",\"authCode\":{\"auth\":\"EPSG\",\"code\":\"32021\"},\"type\":\"LBC\"},\"singleCT\":{\"wkt\":\"GEOGTRAN[\\\"NAD_1927_To_WGS_1984_79_CONUS\\\",GEOGCS[\\\"GCS_North_American_1927\\\",DATUM[\\\"D_North_American_1927\\\",SPHEROID[\\\"Clarke_1866\\\",6378206.4,294.9786982]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],GEOGCS[\\\"GCS_WGS_1984\\\",DATUM[\\\"D_WGS_1984\\\",SPHEROID[\\\"WGS_1984\\\",6378137.0,298.257223563]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],METHOD[\\\"NADCON\\\"],PARAMETER[\\\"Dataset_conus\\\",0.0],AUTHORITY[\\\"EPSG\\\",15851]]\",\"ver\":\"PE_10_3_1\",\"name\":\"NAD_1927_To_WGS_1984_79_CONUS\",\"authCode\":{\"auth\":\"EPSG\",\"code\":\"15851\"},\"type\":\"ST\"},\"ver\":\"PE_10_3_1\",\"name\":\"NAD27 * OGP-Usa Conus / North Dakota South [32021,15851]\",\"authCode\":{\"auth\":\"SLB\",\"code\":\"32021079\"},\"type\":\"EBC\"}",
        "persistableReferenceVerticalCrs": "{\"authCode\":{\"auth\":\"EPSG\",\"code\":\"5773\"},\"type\":\"LBC\",\"ver\":\"PE_10_3_1\",\"name\":\"EGM96_Geoid\",\"wkt\":\"VERTCS[\\\"EGM96_Geoid\\\",VDATUM[\\\"EGM96_Geoid\\\"],PARAMETER[\\\"Vertical_Shift\\\",0.0],PARAMETER[\\\"Direction\\\",1.0],UNIT[\\\"Meter\\\",1.0],AUTHORITY[\\\"EPSG\\\",5773]]\"}",
        "persistableReferenceUnitZ": "{\"scaleOffset\":{\"scale\":1.0,\"offset\":0.0},\"symbol\":\"m\",\"baseMeasurement\":{\"ancestry\":\"Length\",\"type\":\"UM\"},\"type\":\"USO\"}",
        "features": [
          {
            "type": "AnyCrsFeature",
            "properties": {},
            "geometry": {
              "type": "AnyCrsPoint",
              "coordinates": [
                12345.6,
                12345.6
              ],
              "bbox": [
                12345.6,
                12345.6,
                12345.6,
                12345.6
              ]
            },
            "bbox": [
              12345.6,
              12345.6,
              12345.6,
              12345.6
            ]
          }
        ],
        "bbox": [
          12345.6,
          12345.6,
          12345.6,
          12345.6
        ]
      },
      "Wgs84Coordinates": {
        "type": "FeatureCollection",
        "features": [
          {
            "type": "Feature",
            "properties": {},
            "geometry": {
              "type": "Point",
              "coordinates": [
                12345.6,
                12345.6
              ],
              "bbox": [
                12345.6,
                12345.6,
                12345.6,
                12345.6
              ]
            },
            "bbox": [
              12345.6,
              12345.6,
              12345.6,
              12345.6
            ]
          }
        ],
        "bbox": [
          12345.6,
          12345.6,
          12345.6,
          12345.6
        ]
      },
      "AppliedOperations": [
        "conversion from ED_1950_UTM_Zone_31N to GCS_European_1950; 1 points converted",
        "transformation GCS_European_1950 to GCS_WGS_1984 using ED_1950_To_WGS_1984_24; 1 points successfully transformed"
      ],
      "SpatialParameterTypeID": "namespace:reference-data--SpatialParameterType:Outline:",
      "SpatialGeometryTypeID": "namespace:reference-data--SpatialGeometryType:Point:"
    },
    "VersionCreationReason": "Example VersionCreationReason",
    "FacilityID": "Example FacilityID",
    "FacilityTypeID": "namespace:reference-data--FacilityType:Well:",
    "FacilityOperators": [
      {
        "FacilityOperatorID": "Example Facility Operator ID",
        "FacilityOperatorOrganisationID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
        "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
        "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00"
      }
    ],
    "InitialOperatorID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
    "CurrentOperatorID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
    "DataSourceOrganisationID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
    "OperatingEnvironmentID": "namespace:reference-data--OperatingEnvironment:Onshore:",
    "FacilityName": "Example FacilityName",
    "FacilityNameAliases": [
      {
        "AliasName": "Example AliasName",
        "AliasNameTypeID": "namespace:reference-data--AliasNameType:Regulatory%20Identifier:",
        "DefinitionOrganisationID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
        "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
        "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00"
      }
    ],
    "FacilityStates": [
      {
        "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
        "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00",
        "FacilityStateTypeID": "namespace:reference-data--FacilityStateType:SomeUniqueFacilityStateTypeID:"
      }
    ],
    "FacilityEvents": [
      {
        "FacilityEventTypeID": "namespace:reference-data--FacilityEventType:Abandon:",
        "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
        "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00"
      }
    ],
    "FacilitySpecifications": [
      {
        "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
        "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00",
        "FacilitySpecificationQuantity": 12345.6,
        "FacilitySpecificationDateTime": "2020-02-13T09:13:15.550000+00:00",
        "FacilitySpecificationIndicator": true,
        "FacilitySpecificationText": "Example FacilitySpecificationText",
        "UnitOfMeasureID": "namespace:reference-data--UnitOfMeasure:m:",
        "ParameterTypeID": "namespace:reference-data--ParameterType:Slot%20Name:"
      }
    ],
    "WellID": "namespace:master-data--Well:SomeUniqueWellID:",
    "SequenceNumber": 2,
    "VerticalMeasurements": [
      {
        "VerticalMeasurementID": "Example VerticalMeasurementID",
        "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
        "RigID": "1U:master-data--Rig:p:7",
        "VerticalMeasurement": 12345.6,
        "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00",
        "VerticalMeasurementTypeID": "namespace:reference-data--VerticalMeasurementType:Plug%20Back%20depth:",
        "VerticalMeasurementPathID": "namespace:reference-data--VerticalMeasurementPath:SomeUniqueVerticalMeasurementPathID:",
        "VerticalMeasurementSourceID": "namespace:reference-data--VerticalMeasurementSource:SomeUniqueVerticalMeasurementSourceID:",
        "WellboreTVDTrajectoryID": "namespace:work-product-component--WellboreTrajectory:WellboreTrajectory-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
        "VerticalMeasurementUnitOfMeasureID": "namespace:reference-data--UnitOfMeasure:m:",
        "VerticalCRSID": "namespace:reference-data--CoordinateReferenceSystem:SomeUniqueCoordinateReferenceSystemID:",
        "VerticalReferenceID": "Example VerticalReferenceID",
        "VerticalMeasurementDescription": "Example VerticalMeasurementDescription"
      }
    ],
    "DrillingReasons": [
      {
        "DrillingReasonTypeID": "namespace:reference-data--DrillingReasonType:Development:",
        "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
        "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00"
      }
    ],
    "KickOffWellbore": "namespace:master-data--Wellbore:SomeUniqueWellboreID:",
    "TrajectoryTypeID": "namespace:reference-data--WellboreTrajectoryType:Vertical:",
    "DefinitiveTrajectoryID": "namespace:work-product-component--WellboreTrajectory:WellboreTrajectory-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
    "TargetFormation": "namespace:reference-data--GeologicalFormation:SomeUniqueGeologicalFormationID:",
    "PrimaryMaterialID": "namespace:reference-data--MaterialType:STEEL:",
    "DefaultVerticalMeasurementID": "Example DefaultVerticalMeasurementID",
    "ProjectedBottomHoleLocation": {
      "SpatialLocationCoordinatesDate": "2020-02-13T09:13:15.550000+00:00",
      "QuantitativeAccuracyBandID": "namespace:reference-data--QuantitativeAccuracyBand:SomeUniqueQuantitativeAccuracyBandID:",
      "QualitativeSpatialAccuracyTypeID": "namespace:reference-data--QualitativeSpatialAccuracyType:SomeUniqueQualitativeSpatialAccuracyTypeID:",
      "CoordinateQualityCheckPerformedBy": "Example CoordinateQualityCheckPerformedBy",
      "CoordinateQualityCheckDateTime": "2020-02-13T09:13:15.550000+00:00",
      "CoordinateQualityCheckRemarks": [
        "Example CoordinateQualityCheckRemarks"
      ],
      "AsIngestedCoordinates": {
        "type": "AnyCrsFeatureCollection",
        "CoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:BoundCRS.SLB.32021.15851:",
        "VerticalCoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:VerticalCRS.EPSG.5773:",
        "persistableReferenceCrs": "{\"lateBoundCRS\":{\"wkt\":\"PROJCS[\\\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\\\",GEOGCS[\\\"GCS_North_American_1927\\\",DATUM[\\\"D_North_American_1927\\\",SPHEROID[\\\"Clarke_1866\\\",6378206.4,294.9786982]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],PROJECTION[\\\"Lambert_Conformal_Conic\\\"],PARAMETER[\\\"False_Easting\\\",2000000.0],PARAMETER[\\\"False_Northing\\\",0.0],PARAMETER[\\\"Central_Meridian\\\",-100.5],PARAMETER[\\\"Standard_Parallel_1\\\",46.1833333333333],PARAMETER[\\\"Standard_Parallel_2\\\",47.4833333333333],PARAMETER[\\\"Latitude_Of_Origin\\\",45.6666666666667],UNIT[\\\"Foot_US\\\",0.304800609601219],AUTHORITY[\\\"EPSG\\\",32021]]\",\"ver\":\"PE_10_3_1\",\"name\":\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\",\"authCode\":{\"auth\":\"EPSG\",\"code\":\"32021\"},\"type\":\"LBC\"},\"singleCT\":{\"wkt\":\"GEOGTRAN[\\\"NAD_1927_To_WGS_1984_79_CONUS\\\",GEOGCS[\\\"GCS_North_American_1927\\\",DATUM[\\\"D_North_American_1927\\\",SPHEROID[\\\"Clarke_1866\\\",6378206.4,294.9786982]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],GEOGCS[\\\"GCS_WGS_1984\\\",DATUM[\\\"D_WGS_1984\\\",SPHEROID[\\\"WGS_1984\\\",6378137.0,298.257223563]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],METHOD[\\\"NADCON\\\"],PARAMETER[\\\"Dataset_conus\\\",0.0],AUTHORITY[\\\"EPSG\\\",15851]]\",\"ver\":\"PE_10_3_1\",\"name\":\"NAD_1927_To_WGS_1984_79_CONUS\",\"authCode\":{\"auth\":\"EPSG\",\"code\":\"15851\"},\"type\":\"ST\"},\"ver\":\"PE_10_3_1\",\"name\":\"NAD27 * OGP-Usa Conus / North Dakota South [32021,15851]\",\"authCode\":{\"auth\":\"SLB\",\"code\":\"32021079\"},\"type\":\"EBC\"}",
        "persistableReferenceVerticalCrs": "{\"authCode\":{\"auth\":\"EPSG\",\"code\":\"5773\"},\"type\":\"LBC\",\"ver\":\"PE_10_3_1\",\"name\":\"EGM96_Geoid\",\"wkt\":\"VERTCS[\\\"EGM96_Geoid\\\",VDATUM[\\\"EGM96_Geoid\\\"],PARAMETER[\\\"Vertical_Shift\\\",0.0],PARAMETER[\\\"Direction\\\",1.0],UNIT[\\\"Meter\\\",1.0],AUTHORITY[\\\"EPSG\\\",5773]]\"}",
        "persistableReferenceUnitZ": "{\"scaleOffset\":{\"scale\":1.0,\"offset\":0.0},\"symbol\":\"m\",\"baseMeasurement\":{\"ancestry\":\"Length\",\"type\":\"UM\"},\"type\":\"USO\"}",
        "features": [
          {
            "type": "AnyCrsFeature",
            "properties": {},
            "geometry": {
              "type": "AnyCrsPoint",
              "coordinates": [
                12345.6,
                12345.6
              ],
              "bbox": [
                12345.6,
                12345.6,
                12345.6,
                12345.6
              ]
            },
            "bbox": [
              12345.6,
              12345.6,
              12345.6,
              12345.6
            ]
          }
        ],
        "bbox": [
          12345.6,
          12345.6,
          12345.6,
          12345.6
        ]
      },
      "Wgs84Coordinates": {
        "type": "FeatureCollection",
        "features": [
          {
            "type": "Feature",
            "properties": {},
            "geometry": {
              "type": "Point",
              "coordinates": [
                12345.6,
                12345.6
              ],
              "bbox": [
                12345.6,
                12345.6,
                12345.6,
                12345.6
              ]
            },
            "bbox": [
              12345.6,
              12345.6,
              12345.6,
              12345.6
            ]
          }
        ],
        "bbox": [
          12345.6,
          12345.6,
          12345.6,
          12345.6
        ]
      },
      "AppliedOperations": [
        "conversion from ED_1950_UTM_Zone_31N to GCS_European_1950; 1 points converted",
        "transformation GCS_European_1950 to GCS_WGS_1984 using ED_1950_To_WGS_1984_24; 1 points successfully transformed"
      ],
      "SpatialParameterTypeID": "namespace:reference-data--SpatialParameterType:Outline:",
      "SpatialGeometryTypeID": "namespace:reference-data--SpatialGeometryType:Point:"
    },
    "GeographicBottomHoleLocation": {
      "SpatialLocationCoordinatesDate": "2020-02-13T09:13:15.550000+00:00",
      "QuantitativeAccuracyBandID": "namespace:reference-data--QuantitativeAccuracyBand:SomeUniqueQuantitativeAccuracyBandID:",
      "QualitativeSpatialAccuracyTypeID": "namespace:reference-data--QualitativeSpatialAccuracyType:SomeUniqueQualitativeSpatialAccuracyTypeID:",
      "CoordinateQualityCheckPerformedBy": "Example CoordinateQualityCheckPerformedBy",
      "CoordinateQualityCheckDateTime": "2020-02-13T09:13:15.550000+00:00",
      "CoordinateQualityCheckRemarks": [
        "Example CoordinateQualityCheckRemarks"
      ],
      "AsIngestedCoordinates": {
        "type": "AnyCrsFeatureCollection",
        "CoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:BoundCRS.SLB.32021.15851:",
        "VerticalCoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:VerticalCRS.EPSG.5773:",
        "persistableReferenceCrs": "{\"lateBoundCRS\":{\"wkt\":\"PROJCS[\\\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\\\",GEOGCS[\\\"GCS_North_American_1927\\\",DATUM[\\\"D_North_American_1927\\\",SPHEROID[\\\"Clarke_1866\\\",6378206.4,294.9786982]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],PROJECTION[\\\"Lambert_Conformal_Conic\\\"],PARAMETER[\\\"False_Easting\\\",2000000.0],PARAMETER[\\\"False_Northing\\\",0.0],PARAMETER[\\\"Central_Meridian\\\",-100.5],PARAMETER[\\\"Standard_Parallel_1\\\",46.1833333333333],PARAMETER[\\\"Standard_Parallel_2\\\",47.4833333333333],PARAMETER[\\\"Latitude_Of_Origin\\\",45.6666666666667],UNIT[\\\"Foot_US\\\",0.304800609601219],AUTHORITY[\\\"EPSG\\\",32021]]\",\"ver\":\"PE_10_3_1\",\"name\":\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\",\"authCode\":{\"auth\":\"EPSG\",\"code\":\"32021\"},\"type\":\"LBC\"},\"singleCT\":{\"wkt\":\"GEOGTRAN[\\\"NAD_1927_To_WGS_1984_79_CONUS\\\",GEOGCS[\\\"GCS_North_American_1927\\\",DATUM[\\\"D_North_American_1927\\\",SPHEROID[\\\"Clarke_1866\\\",6378206.4,294.9786982]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],GEOGCS[\\\"GCS_WGS_1984\\\",DATUM[\\\"D_WGS_1984\\\",SPHEROID[\\\"WGS_1984\\\",6378137.0,298.257223563]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],METHOD[\\\"NADCON\\\"],PARAMETER[\\\"Dataset_conus\\\",0.0],AUTHORITY[\\\"EPSG\\\",15851]]\",\"ver\":\"PE_10_3_1\",\"name\":\"NAD_1927_To_WGS_1984_79_CONUS\",\"authCode\":{\"auth\":\"EPSG\",\"code\":\"15851\"},\"type\":\"ST\"},\"ver\":\"PE_10_3_1\",\"name\":\"NAD27 * OGP-Usa Conus / North Dakota South [32021,15851]\",\"authCode\":{\"auth\":\"SLB\",\"code\":\"32021079\"},\"type\":\"EBC\"}",
        "persistableReferenceVerticalCrs": "{\"authCode\":{\"auth\":\"EPSG\",\"code\":\"5773\"},\"type\":\"LBC\",\"ver\":\"PE_10_3_1\",\"name\":\"EGM96_Geoid\",\"wkt\":\"VERTCS[\\\"EGM96_Geoid\\\",VDATUM[\\\"EGM96_Geoid\\\"],PARAMETER[\\\"Vertical_Shift\\\",0.0],PARAMETER[\\\"Direction\\\",1.0],UNIT[\\\"Meter\\\",1.0],AUTHORITY[\\\"EPSG\\\",5773]]\"}",
        "persistableReferenceUnitZ": "{\"scaleOffset\":{\"scale\":1.0,\"offset\":0.0},\"symbol\":\"m\",\"baseMeasurement\":{\"ancestry\":\"Length\",\"type\":\"UM\"},\"type\":\"USO\"}",
        "features": [
          {
            "type": "AnyCrsFeature",
            "properties": {},
            "geometry": {
              "type": "AnyCrsPoint",
              "coordinates": [
                12345.6,
                12345.6
              ],
              "bbox": [
                12345.6,
                12345.6,
                12345.6,
                12345.6
              ]
            },
            "bbox": [
              12345.6,
              12345.6,
              12345.6,
              12345.6
            ]
          }
        ],
        "bbox": [
          12345.6,
          12345.6,
          12345.6,
          12345.6
        ]
      },
      "Wgs84Coordinates": {
        "type": "FeatureCollection",
        "features": [
          {
            "type": "Feature",
            "properties": {},
            "geometry": {
              "type": "Point",
              "coordinates": [
                12345.6,
                12345.6
              ],
              "bbox": [
                12345.6,
                12345.6,
                12345.6,
                12345.6
              ]
            },
            "bbox": [
              12345.6,
              12345.6,
              12345.6,
              12345.6
            ]
          }
        ],
        "bbox": [
          12345.6,
          12345.6,
          12345.6,
          12345.6
        ]
      },
      "AppliedOperations": [
        "conversion from ED_1950_UTM_Zone_31N to GCS_European_1950; 1 points converted",
        "transformation GCS_European_1950 to GCS_WGS_1984 using ED_1950_To_WGS_1984_24; 1 points successfully transformed"
      ],
      "SpatialParameterTypeID": "namespace:reference-data--SpatialParameterType:Outline:",
      "SpatialGeometryTypeID": "namespace:reference-data--SpatialGeometryType:Point:"
    },
      "HistoricalInterests": [
        {
          "InterestTypeID": "namespace:reference-data--WellInterestType:Yes:",
          "EffectiveDateTime": "2020-02-13",
          "TerminationDateTime": "2020-02-13"
        }
      ],
      "WasBusinessInterestFinancialOperated": true,
      "WasBusinessInterestFinancialNonOperated": true,
      "WasBusinessInterestObligatory": true,
      "WasBusinessInterestTechnical": true,
      "TrajectoryTypeID": "namespace:reference-data--WellboreTrajectoryType:Vertical:",
      "PrimaryProductTypeID": "namespace:reference-data--WellProductType:Gas:",
      "SecondaryProductTypeID": "namespace:reference-data--WellProductType:Gas:",
      "TertiaryProductTypeID": "namespace:reference-data--WellProductType:Gas:",
      "ShowProductTypeID": "namespace:reference-data--WellProductType:Gas:",
      "ConditionID": "namespace:reference-data--WellCondition:Active:",
      "FluidDirectionID": "namespace:reference-data--WellFluidDirection:DualFlow:",
      "OutcomeID": "namespace:reference-data--WellBusinessIntentionOutcome:Achieved:",
      "StatusSummaryID": "namespace:reference-data--WellStatusSummary:Planning:",
      "ExtensionProperties": {}
  }
}
]""",
    )
    return RequestRunner(rq_proto)


def get_cleaned_ref_and_res() -> dict:
    ref = {
        "tags": {"NameOfKey": "String value"},
        "createTime": "2020-12-16T11:46:20.163Z",
        "createUser": "some-user@some-company-cloud.com",
        "modifyTime": "2020-12-16T11:52:24.477Z",
        "modifyUser": "some-user@some-company-cloud.com",
        "meta": [],
        "data": {
            "ResourceHomeRegionID": "namespace:reference-data--OSDURegion:SomeUniqueOSDURegionID:",
            "ResourceHostRegionIDs": [
                "namespace:reference-data--OSDURegion:SomeUniqueOSDURegionID:"
            ],
            "ResourceCurationStatus": "namespace:reference-data--ResourceCurationStatus:CREATED:",
            "ResourceLifecycleStatus": "namespace:reference-data--ResourceLifecycleStatus:LOADING:",
            "ResourceSecurityClassification": "namespace:reference-data--ResourceSecurityClassification:RESTRICTED:",
            "Source": "Example Data Source",
            "ExistenceKind": "namespace:reference-data--ExistenceKind:Prototype:",
            "NameAliases": [
                {
                    "AliasName": "Example AliasName",
                    "AliasNameTypeID": "namespace:reference-data--AliasNameType:Regulatory%20Identifier:",
                    "DefinitionOrganisationID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
                    "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
                    "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00",
                }
            ],
            "GeoContexts": [
                {
                    "BasinID": "namespace:master-data--Basin:SomeUniqueBasinID:",
                    "GeoTypeID": "namespace:reference-data--BasinType:SomeUniqueBasinTypeID:",
                }
            ],
            "SpatialLocation": {
                "SpatialLocationCoordinatesDate": "2020-02-13T09:13:15.550000+00:00",
                "QuantitativeAccuracyBandID": "namespace:reference-data--QuantitativeAccuracyBand:SomeUniqueQuantitativeAccuracyBandID:",
                "QualitativeSpatialAccuracyTypeID": "namespace:reference-data--QualitativeSpatialAccuracyType:SomeUniqueQualitativeSpatialAccuracyTypeID:",
                "CoordinateQualityCheckPerformedBy": "Example CoordinateQualityCheckPerformedBy",
                "CoordinateQualityCheckDateTime": "2020-02-13T09:13:15.550000+00:00",
                "CoordinateQualityCheckRemarks": [
                    "Example CoordinateQualityCheckRemarks"
                ],
                "AsIngestedCoordinates": {
                    "type": "AnyCrsFeatureCollection",
                    "CoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:BoundCRS.SLB.32021.15851:",
                    "VerticalCoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:VerticalCRS.EPSG.5773:",
                    "persistableReferenceCrs": '{"lateBoundCRS":{"wkt":"PROJCS[\\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\\",GEOGCS[\\"GCS_North_American_1927\\",DATUM[\\"D_North_American_1927\\",SPHEROID[\\"Clarke_1866\\",6378206.4,294.9786982]],PRIMEM[\\"Greenwich\\",0.0],UNIT[\\"Degree\\",0.0174532925199433]],PROJECTION[\\"Lambert_Conformal_Conic\\"],PARAMETER[\\"False_Easting\\",2000000.0],PARAMETER[\\"False_Northing\\",0.0],PARAMETER[\\"Central_Meridian\\",-100.5],PARAMETER[\\"Standard_Parallel_1\\",46.1833333333333],PARAMETER[\\"Standard_Parallel_2\\",47.4833333333333],PARAMETER[\\"Latitude_Of_Origin\\",45.6666666666667],UNIT[\\"Foot_US\\",0.304800609601219],AUTHORITY[\\"EPSG\\",32021]]","ver":"PE_10_3_1","name":"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302","authCode":{"auth":"EPSG","code":"32021"},"type":"LBC"},"singleCT":{"wkt":"GEOGTRAN[\\"NAD_1927_To_WGS_1984_79_CONUS\\",GEOGCS[\\"GCS_North_American_1927\\",DATUM[\\"D_North_American_1927\\",SPHEROID[\\"Clarke_1866\\",6378206.4,294.9786982]],PRIMEM[\\"Greenwich\\",0.0],UNIT[\\"Degree\\",0.0174532925199433]],GEOGCS[\\"GCS_WGS_1984\\",DATUM[\\"D_WGS_1984\\",SPHEROID[\\"WGS_1984\\",6378137.0,298.257223563]],PRIMEM[\\"Greenwich\\",0.0],UNIT[\\"Degree\\",0.0174532925199433]],METHOD[\\"NADCON\\"],PARAMETER[\\"Dataset_conus\\",0.0],AUTHORITY[\\"EPSG\\",15851]]","ver":"PE_10_3_1","name":"NAD_1927_To_WGS_1984_79_CONUS","authCode":{"auth":"EPSG","code":"15851"},"type":"ST"},"ver":"PE_10_3_1","name":"NAD27 * OGP-Usa Conus / North Dakota South [32021,15851]","authCode":{"auth":"SLB","code":"32021079"},"type":"EBC"}',
                    "persistableReferenceVerticalCrs": '{"authCode":{"auth":"EPSG","code":"5773"},"type":"LBC","ver":"PE_10_3_1","name":"EGM96_Geoid","wkt":"VERTCS[\\"EGM96_Geoid\\",VDATUM[\\"EGM96_Geoid\\"],PARAMETER[\\"Vertical_Shift\\",0.0],PARAMETER[\\"Direction\\",1.0],UNIT[\\"Meter\\",1.0],AUTHORITY[\\"EPSG\\",5773]]"}',
                    "persistableReferenceUnitZ": '{"scaleOffset":{"scale":1.0,"offset":0.0},"symbol":"m","baseMeasurement":{"ancestry":"Length","type":"UM"},"type":"USO"}',
                    "features": [
                        {
                            "type": "AnyCrsFeature",
                            "properties": {},
                            "geometry": {
                                "type": "AnyCrsPoint",
                                "coordinates": [12345.6, 12345.6],
                                "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                            },
                            "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                        }
                    ],
                    "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                },
                "Wgs84Coordinates": {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {},
                            "geometry": {
                                "type": "Point",
                                "coordinates": [12345.6, 12345.6],
                                "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                            },
                            "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                        }
                    ],
                    "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                },
                "AppliedOperations": [
                    "conversion from ED_1950_UTM_Zone_31N to GCS_European_1950; 1 points converted",
                    "transformation GCS_European_1950 to GCS_WGS_1984 using ED_1950_To_WGS_1984_24; 1 points successfully transformed",
                ],
                "SpatialParameterTypeID": "namespace:reference-data--SpatialParameterType:Outline:",
                "SpatialGeometryTypeID": "namespace:reference-data--SpatialGeometryType:Point:",
            },
            "VersionCreationReason": "Example VersionCreationReason",
            "FacilityID": "Example FacilityID",
            "FacilityTypeID": "namespace:reference-data--FacilityType:Well:",
            "FacilityOperators": [
                {
                    "FacilityOperatorID": "Example Facility Operator ID",
                    "FacilityOperatorOrganisationID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
                    "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
                    "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00",
                }
            ],
            "InitialOperatorID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
            "CurrentOperatorID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
            "DataSourceOrganisationID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
            "OperatingEnvironmentID": "namespace:reference-data--OperatingEnvironment:Onshore:",
            "FacilityName": "Example FacilityName",
            "FacilityNameAliases": [
                {
                    "AliasName": "Example AliasName",
                    "AliasNameTypeID": "namespace:reference-data--AliasNameType:Regulatory%20Identifier:",
                    "DefinitionOrganisationID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
                    "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
                    "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00",
                }
            ],
            "FacilityStates": [
                {
                    "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
                    "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00",
                    "FacilityStateTypeID": "namespace:reference-data--FacilityStateType:SomeUniqueFacilityStateTypeID:",
                }
            ],
            "FacilityEvents": [
                {
                    "FacilityEventTypeID": "namespace:reference-data--FacilityEventType:Abandon:",
                    "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
                    "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00",
                }
            ],
            "FacilitySpecifications": [
                {
                    "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
                    "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00",
                    "FacilitySpecificationQuantity": 12345.6,
                    "FacilitySpecificationDateTime": "2020-02-13T09:13:15.550000+00:00",
                    "FacilitySpecificationIndicator": True,
                    "FacilitySpecificationText": "Example FacilitySpecificationText",
                    "UnitOfMeasureID": "namespace:reference-data--UnitOfMeasure:m:",
                    "ParameterTypeID": "namespace:reference-data--ParameterType:Slot%20Name:",
                }
            ],
            "WellID": "namespace:master-data--Well:SomeUniqueWellID:",
            "SequenceNumber": 2,
            "VerticalMeasurements": [
                {
                    "VerticalMeasurementID": "Example VerticalMeasurementID",
                    "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
                    "RigID": "1U:master-data--Rig:p:7",
                    "VerticalMeasurement": 12345.6,
                    "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00",
                    "VerticalMeasurementTypeID": "namespace:reference-data--VerticalMeasurementType:Plug%20Back%20depth:",
                    "VerticalMeasurementPathID": "namespace:reference-data--VerticalMeasurementPath:SomeUniqueVerticalMeasurementPathID:",
                    "VerticalMeasurementSourceID": "namespace:reference-data--VerticalMeasurementSource:SomeUniqueVerticalMeasurementSourceID:",
                    "WellboreTVDTrajectoryID": "namespace:work-product-component--WellboreTrajectory:WellboreTrajectory-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
                    "VerticalMeasurementUnitOfMeasureID": "namespace:reference-data--UnitOfMeasure:m:",
                    "VerticalCRSID": "namespace:reference-data--CoordinateReferenceSystem:SomeUniqueCoordinateReferenceSystemID:",
                    "VerticalReferenceID": "Example VerticalReferenceID",
                    "VerticalMeasurementDescription": "Example VerticalMeasurementDescription",
                }
            ],
            "DrillingReasons": [
                {
                    "DrillingReasonTypeID": "namespace:reference-data--DrillingReasonType:Development:",
                    "EffectiveDateTime": "2020-02-13T09:13:15.550000+00:00",
                    "TerminationDateTime": "2020-02-13T09:13:15.550000+00:00",
                }
            ],
            "KickOffWellbore": "namespace:master-data--Wellbore:SomeUniqueWellboreID:",
            "TrajectoryTypeID": "namespace:reference-data--WellboreTrajectoryType:Vertical:",
            "DefinitiveTrajectoryID": "namespace:work-product-component--WellboreTrajectory:WellboreTrajectory-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
            "TargetFormation": "namespace:reference-data--GeologicalFormation:SomeUniqueGeologicalFormationID:",
            "PrimaryMaterialID": "namespace:reference-data--MaterialType:STEEL:",
            "DefaultVerticalMeasurementID": "Example DefaultVerticalMeasurementID",
            "ProjectedBottomHoleLocation": {
                "SpatialLocationCoordinatesDate": "2020-02-13T09:13:15.550000+00:00",
                "QuantitativeAccuracyBandID": "namespace:reference-data--QuantitativeAccuracyBand:SomeUniqueQuantitativeAccuracyBandID:",
                "QualitativeSpatialAccuracyTypeID": "namespace:reference-data--QualitativeSpatialAccuracyType:SomeUniqueQualitativeSpatialAccuracyTypeID:",
                "CoordinateQualityCheckPerformedBy": "Example CoordinateQualityCheckPerformedBy",
                "CoordinateQualityCheckDateTime": "2020-02-13T09:13:15.550000+00:00",
                "CoordinateQualityCheckRemarks": [
                    "Example CoordinateQualityCheckRemarks"
                ],
                "AsIngestedCoordinates": {
                    "type": "AnyCrsFeatureCollection",
                    "CoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:BoundCRS.SLB.32021.15851:",
                    "VerticalCoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:VerticalCRS.EPSG.5773:",
                    "persistableReferenceCrs": '{"lateBoundCRS":{"wkt":"PROJCS[\\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\\",GEOGCS[\\"GCS_North_American_1927\\",DATUM[\\"D_North_American_1927\\",SPHEROID[\\"Clarke_1866\\",6378206.4,294.9786982]],PRIMEM[\\"Greenwich\\",0.0],UNIT[\\"Degree\\",0.0174532925199433]],PROJECTION[\\"Lambert_Conformal_Conic\\"],PARAMETER[\\"False_Easting\\",2000000.0],PARAMETER[\\"False_Northing\\",0.0],PARAMETER[\\"Central_Meridian\\",-100.5],PARAMETER[\\"Standard_Parallel_1\\",46.1833333333333],PARAMETER[\\"Standard_Parallel_2\\",47.4833333333333],PARAMETER[\\"Latitude_Of_Origin\\",45.6666666666667],UNIT[\\"Foot_US\\",0.304800609601219],AUTHORITY[\\"EPSG\\",32021]]","ver":"PE_10_3_1","name":"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302","authCode":{"auth":"EPSG","code":"32021"},"type":"LBC"},"singleCT":{"wkt":"GEOGTRAN[\\"NAD_1927_To_WGS_1984_79_CONUS\\",GEOGCS[\\"GCS_North_American_1927\\",DATUM[\\"D_North_American_1927\\",SPHEROID[\\"Clarke_1866\\",6378206.4,294.9786982]],PRIMEM[\\"Greenwich\\",0.0],UNIT[\\"Degree\\",0.0174532925199433]],GEOGCS[\\"GCS_WGS_1984\\",DATUM[\\"D_WGS_1984\\",SPHEROID[\\"WGS_1984\\",6378137.0,298.257223563]],PRIMEM[\\"Greenwich\\",0.0],UNIT[\\"Degree\\",0.0174532925199433]],METHOD[\\"NADCON\\"],PARAMETER[\\"Dataset_conus\\",0.0],AUTHORITY[\\"EPSG\\",15851]]","ver":"PE_10_3_1","name":"NAD_1927_To_WGS_1984_79_CONUS","authCode":{"auth":"EPSG","code":"15851"},"type":"ST"},"ver":"PE_10_3_1","name":"NAD27 * OGP-Usa Conus / North Dakota South [32021,15851]","authCode":{"auth":"SLB","code":"32021079"},"type":"EBC"}',
                    "persistableReferenceVerticalCrs": '{"authCode":{"auth":"EPSG","code":"5773"},"type":"LBC","ver":"PE_10_3_1","name":"EGM96_Geoid","wkt":"VERTCS[\\"EGM96_Geoid\\",VDATUM[\\"EGM96_Geoid\\"],PARAMETER[\\"Vertical_Shift\\",0.0],PARAMETER[\\"Direction\\",1.0],UNIT[\\"Meter\\",1.0],AUTHORITY[\\"EPSG\\",5773]]"}',
                    "persistableReferenceUnitZ": '{"scaleOffset":{"scale":1.0,"offset":0.0},"symbol":"m","baseMeasurement":{"ancestry":"Length","type":"UM"},"type":"USO"}',
                    "features": [
                        {
                            "type": "AnyCrsFeature",
                            "properties": {},
                            "geometry": {
                                "type": "AnyCrsPoint",
                                "coordinates": [12345.6, 12345.6],
                                "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                            },
                            "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                        }
                    ],
                    "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                },
                "Wgs84Coordinates": {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {},
                            "geometry": {
                                "type": "Point",
                                "coordinates": [12345.6, 12345.6],
                                "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                            },
                            "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                        }
                    ],
                    "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                },
                "AppliedOperations": [
                    "conversion from ED_1950_UTM_Zone_31N to GCS_European_1950; 1 points converted",
                    "transformation GCS_European_1950 to GCS_WGS_1984 using ED_1950_To_WGS_1984_24; 1 points successfully transformed",
                ],
                "SpatialParameterTypeID": "namespace:reference-data--SpatialParameterType:Outline:",
                "SpatialGeometryTypeID": "namespace:reference-data--SpatialGeometryType:Point:",
            },
            "GeographicBottomHoleLocation": {
                "SpatialLocationCoordinatesDate": "2020-02-13T09:13:15.550000+00:00",
                "QuantitativeAccuracyBandID": "namespace:reference-data--QuantitativeAccuracyBand:SomeUniqueQuantitativeAccuracyBandID:",
                "QualitativeSpatialAccuracyTypeID": "namespace:reference-data--QualitativeSpatialAccuracyType:SomeUniqueQualitativeSpatialAccuracyTypeID:",
                "CoordinateQualityCheckPerformedBy": "Example CoordinateQualityCheckPerformedBy",
                "CoordinateQualityCheckDateTime": "2020-02-13T09:13:15.550000+00:00",
                "CoordinateQualityCheckRemarks": [
                    "Example CoordinateQualityCheckRemarks"
                ],
                "AsIngestedCoordinates": {
                    "type": "AnyCrsFeatureCollection",
                    "CoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:BoundCRS.SLB.32021.15851:",
                    "VerticalCoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:VerticalCRS.EPSG.5773:",
                    "persistableReferenceCrs": '{"lateBoundCRS":{"wkt":"PROJCS[\\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\\",GEOGCS[\\"GCS_North_American_1927\\",DATUM[\\"D_North_American_1927\\",SPHEROID[\\"Clarke_1866\\",6378206.4,294.9786982]],PRIMEM[\\"Greenwich\\",0.0],UNIT[\\"Degree\\",0.0174532925199433]],PROJECTION[\\"Lambert_Conformal_Conic\\"],PARAMETER[\\"False_Easting\\",2000000.0],PARAMETER[\\"False_Northing\\",0.0],PARAMETER[\\"Central_Meridian\\",-100.5],PARAMETER[\\"Standard_Parallel_1\\",46.1833333333333],PARAMETER[\\"Standard_Parallel_2\\",47.4833333333333],PARAMETER[\\"Latitude_Of_Origin\\",45.6666666666667],UNIT[\\"Foot_US\\",0.304800609601219],AUTHORITY[\\"EPSG\\",32021]]","ver":"PE_10_3_1","name":"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302","authCode":{"auth":"EPSG","code":"32021"},"type":"LBC"},"singleCT":{"wkt":"GEOGTRAN[\\"NAD_1927_To_WGS_1984_79_CONUS\\",GEOGCS[\\"GCS_North_American_1927\\",DATUM[\\"D_North_American_1927\\",SPHEROID[\\"Clarke_1866\\",6378206.4,294.9786982]],PRIMEM[\\"Greenwich\\",0.0],UNIT[\\"Degree\\",0.0174532925199433]],GEOGCS[\\"GCS_WGS_1984\\",DATUM[\\"D_WGS_1984\\",SPHEROID[\\"WGS_1984\\",6378137.0,298.257223563]],PRIMEM[\\"Greenwich\\",0.0],UNIT[\\"Degree\\",0.0174532925199433]],METHOD[\\"NADCON\\"],PARAMETER[\\"Dataset_conus\\",0.0],AUTHORITY[\\"EPSG\\",15851]]","ver":"PE_10_3_1","name":"NAD_1927_To_WGS_1984_79_CONUS","authCode":{"auth":"EPSG","code":"15851"},"type":"ST"},"ver":"PE_10_3_1","name":"NAD27 * OGP-Usa Conus / North Dakota South [32021,15851]","authCode":{"auth":"SLB","code":"32021079"},"type":"EBC"}',
                    "persistableReferenceVerticalCrs": '{"authCode":{"auth":"EPSG","code":"5773"},"type":"LBC","ver":"PE_10_3_1","name":"EGM96_Geoid","wkt":"VERTCS[\\"EGM96_Geoid\\",VDATUM[\\"EGM96_Geoid\\"],PARAMETER[\\"Vertical_Shift\\",0.0],PARAMETER[\\"Direction\\",1.0],UNIT[\\"Meter\\",1.0],AUTHORITY[\\"EPSG\\",5773]]"}',
                    "persistableReferenceUnitZ": '{"scaleOffset":{"scale":1.0,"offset":0.0},"symbol":"m","baseMeasurement":{"ancestry":"Length","type":"UM"},"type":"USO"}',
                    "features": [
                        {
                            "type": "AnyCrsFeature",
                            "properties": {},
                            "geometry": {
                                "type": "AnyCrsPoint",
                                "coordinates": [12345.6, 12345.6],
                                "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                            },
                            "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                        }
                    ],
                    "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                },
                "Wgs84Coordinates": {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {},
                            "geometry": {
                                "type": "Point",
                                "coordinates": [12345.6, 12345.6],
                                "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                            },
                            "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                        }
                    ],
                    "bbox": [12345.6, 12345.6, 12345.6, 12345.6],
                },
                "AppliedOperations": [
                    "conversion from ED_1950_UTM_Zone_31N to GCS_European_1950; 1 points converted",
                    "transformation GCS_European_1950 to GCS_WGS_1984 using ED_1950_To_WGS_1984_24; 1 points successfully transformed",
                ],
                "SpatialParameterTypeID": "namespace:reference-data--SpatialParameterType:Outline:",
                "SpatialGeometryTypeID": "namespace:reference-data--SpatialGeometryType:Point:",
            },
            "HistoricalInterests": [
                {
                    "InterestTypeID": "namespace:reference-data--WellInterestType:Yes:",
                    "EffectiveDateTime": "2020-02-13",
                    "TerminationDateTime": "2020-02-13"
                }
            ],
            "WasBusinessInterestFinancialOperated": True,
            "WasBusinessInterestFinancialNonOperated": True,
            "WasBusinessInterestObligatory": True,
            "WasBusinessInterestTechnical": True,
            "TrajectoryTypeID": "namespace:reference-data--WellboreTrajectoryType:Vertical:",
            "PrimaryProductTypeID": "namespace:reference-data--WellProductType:Gas:",
            "SecondaryProductTypeID": "namespace:reference-data--WellProductType:Gas:",
            "TertiaryProductTypeID": "namespace:reference-data--WellProductType:Gas:",
            "ShowProductTypeID": "namespace:reference-data--WellProductType:Gas:",
            "ConditionID": "namespace:reference-data--WellCondition:Active:",
            "FluidDirectionID": "namespace:reference-data--WellFluidDirection:DualFlow:",
            "OutcomeID": "namespace:reference-data--WellBusinessIntentionOutcome:Achieved:",
            "StatusSummaryID": "namespace:reference-data--WellStatusSummary:Planning:",

            "ExtensionProperties": {},
        },
    }

    # Add mandatory fields
    ref["kind"] = "{{authorityKind}}:wks:master-data--Wellbore:1.1.1"
    ref["acl"] = {
        "owners": ["{{acl_owner}}"],
        "viewers": ["{{acl_viewer}}"],
    }
    ref["legal"] = {
        "legaltags": ["{{legal_tag}}"],
        "otherRelevantDataCountries": ["US"],
        "status": "compliant",
    }

    return ref
