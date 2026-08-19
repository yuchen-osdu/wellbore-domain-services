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
from typing import Dict

from ....request_runner import RequestRunner, Request


def build_request_delete_osdu_ppfgdataset(record_id='{{osdu_ppfgdataset_record_id}}') -> RequestRunner:
    rq_proto = Request(
        name="Delete PPFGDataset",
        method="DELETE",
        url="{{base_url}}/ddms/v3/ppfgdataset/"+record_id,
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_osdu_ppfgdataset_specific_version() -> RequestRunner:
    rq_proto = Request(
        name="Get PPFGDataset specific version",
        method="GET",
        url="{{base_url}}/ddms/v3/ppfgdataset/{{osdu_ppfgdataset_record_id}}/versions/{{osdu_ppfgdataset_record_version}}",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_osdu_ppfgdataset() -> RequestRunner:
    rq_proto = Request(
        name="Get PPFGDataset",
        method="GET",
        url="{{base_url}}/ddms/v3/ppfgdataset/{{osdu_ppfgdataset_record_id}}",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
    )
    return RequestRunner(rq_proto)


def build_request_get_versions_of_osdu_ppfgdataset() -> RequestRunner:
    rq_proto = Request(
        name="Get versions of PPFGDataset",
        method="GET",
        url="{{base_url}}/ddms/v3/ppfgdataset/{{osdu_ppfgdataset_record_id}}/versions",
        headers={
            "accept": "application/json",
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
    )
    return RequestRunner(rq_proto)


def build_request_create_osdu_ppfgdataset(b_use_fixed_id=True, curves: Dict[str, int] = dict()) -> RequestRunner:
    if b_use_fixed_id:
        id_field = '"id": "{{data_partition}}:work-product-component--PPFGDataset:bb2f4d26-6446-508a-b137-7239ee1bbea1",'
    else:
        id_field = ''

    payload = '[{' + id_field + r"""
            "kind": "{{osduPPFGDatasetKind}}",
          "version": 1562066009929332,
          "acl": {{record_acl}},
          "legal": {{record_legal}},
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
                "VerticalMeasurement.VerticalMeasurement"
              ]
            }
          ],
          "data": {
            "ResourceHomeRegionID": "namespace:reference-data--OSDURegion:AWSEastUSA:",
            "ResourceHostRegionIDs": [
              "namespace:reference-data--OSDURegion:AWSEastUSA:"
            ],
            "ResourceCurationStatus": "namespace:reference-data--ResourceCurationStatus:Created:",
            "ResourceLifecycleStatus": "namespace:reference-data--ResourceLifecycleStatus:Loading:",
            "Source": "Example Data Source",
            "ExistenceKind": "namespace:reference-data--ExistenceKind:Prototype:",
            "Datasets": [
              "namespace:dataset--AnyDataset:SomeUniqueAnyDatasetID:"
            ],
            "DDMSDatasets": [
              "urn://wddms-3/uuid:20840361-adc0-4842-999b-5639bd07bb38",
              "eml://rddms-1/dataspace('demo/Volve')/resqml20.obj_ContinuousProperty(1615d8d2-2a2d-482c-885e-14225b89e90c)"
            ],
            "Artefacts": [
              {
                "RoleID": "namespace:reference-data--ArtefactRole:AdaptedContent:",
                "ResourceKind": "namespace:source_name:group_type--IndividualType:0.0.0",
                "ResourceID": "namespace:dataset--AnyDataset:SomeUniqueAnyDatasetID:"
              }
            ],
            "IsExtendedLoad": true,
            "IsDiscoverable": true,
            "TechnicalAssurances": [
              {
                "TechnicalAssuranceTypeID": "namespace:reference-data--TechnicalAssuranceType:Trusted:",
                "Reviewers": [
                  {
                    "RoleTypeID": "namespace:reference-data--ContactRoleType:AccountOwner:",
                    "DataGovernanceRoleTypeID": "namespace:reference-data--DataGovernanceRoleType:SME:",
                    "WorkflowPersonaTypeID": "namespace:reference-data--WorkflowPersonaType:SeismicProcessor:",
                    "OrganisationID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
                    "Name": "John Smith"
                  }
                ],
                "AcceptableUsage": [
                  {
                    "WorkflowUsageTypeID": "namespace:reference-data--WorkflowUsageType:SeismicProcessing:",
                    "WorkflowPersonaTypeID": "namespace:reference-data--WorkflowPersonaType:SeismicProcessor:",
                    "DataQualityRuleSetID": "namespace:reference-data--DataQualityRuleSet:SeismicProcessingQCRuleSet:",
                    "DataQualityID": "namespace:work-product-component--DataQuality:6a433d16-07c8-4f4d-9ddc-5608e2ec4234:1562066077849221",
                    "ValueChainStatusTypeID": "namespace:reference-data--ValueChainStatusType:Exploration:"
                  }
                ],
                "UnacceptableUsage": [
                  {
                    "WorkflowUsageTypeID": "namespace:reference-data--WorkflowUsageType:SeismicInterpretation:",
                    "WorkflowPersonaTypeID": "namespace:reference-data--WorkflowPersonaType:SeismicInterpreter:",
                    "DataQualityRuleSetID": "namespace:reference-data--DataQualityRuleSet:SeismicInterpretationQCRuleSet:",
                    "DataQualityID": "namespace:work-product-component--DataQuality:d79bf97c-ff7c-4b82-89b5-c88520c15017:1562066009929332",
                    "ValueChainStatusTypeID": "namespace:reference-data--ValueChainStatusType:FieldDevelopment:"
                  }
                ],
                "EffectiveDate": "2020-02-13",
                "Comment": "This is free form text from reviewer, e.g. restrictions on use"
              }
            ],
            "NameAliases": [
              {
                "AliasName": "Example AliasName",
                "AliasNameTypeID": "namespace:reference-data--AliasNameType:RegulatoryIdentifier:",
                "DefinitionOrganisationID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
                "EffectiveDateTime": "2020-02-13T09:13:15.55Z",
                "TerminationDateTime": "2020-02-13T09:13:15.55Z"
              }
            ],
            "Name": "Example Name",
            "Description": "Example Description",
            "CreationDateTime": "2020-02-13T09:13:15.55Z",
            "Tags": [
              "Example Tags"
            ],
            "SpatialPoint": {
              "SpatialLocationCoordinatesDate": "2020-02-13T09:13:15.55Z",
              "QuantitativeAccuracyBandID": "namespace:reference-data--QuantitativeAccuracyBand:Length.LessThan1m:",
              "QualitativeSpatialAccuracyTypeID": "namespace:reference-data--QualitativeSpatialAccuracyType:Assumed:",
              "CoordinateQualityCheckPerformedBy": "Example CoordinateQualityCheckPerformedBy",
              "CoordinateQualityCheckDateTime": "2020-02-13T09:13:15.55Z",
              "CoordinateQualityCheckRemarks": [
                "Example CoordinateQualityCheckRemarks"
              ],
              "AsIngestedCoordinates": {
                "type": "AnyCrsFeatureCollection",
                "CoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:BoundProjected:EPSG::32021_EPSG::15851:",
                "VerticalCoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:Vertical:EPSG::5714:",
                "VerticalUnitID": "namespace:reference-data--UnitOfMeasure:m:",
                "persistableReferenceCrs": "{\"authCode\":{\"auth\":\"OSDU\",\"code\":\"32021079\"},\"lateBoundCRS\":{\"authCode\":{\"auth\":\"EPSG\",\"code\":\"32021\"},\"name\":\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\",\"type\":\"LBC\",\"ver\":\"PE_10_9_1\",\"wkt\":\"PROJCS[\\\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\\\",GEOGCS[\\\"GCS_North_American_1927\\\",DATUM[\\\"D_North_American_1927\\\",SPHEROID[\\\"Clarke_1866\\\",6378206.4,294.9786982]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],PROJECTION[\\\"Lambert_Conformal_Conic\\\"],PARAMETER[\\\"False_Easting\\\",2000000.0],PARAMETER[\\\"False_Northing\\\",0.0],PARAMETER[\\\"Central_Meridian\\\",-100.5],PARAMETER[\\\"Standard_Parallel_1\\\",46.18333333333333],PARAMETER[\\\"Standard_Parallel_2\\\",47.48333333333333],PARAMETER[\\\"Latitude_Of_Origin\\\",45.66666666666666],UNIT[\\\"Foot_US\\\",0.3048006096012192],AUTHORITY[\\\"EPSG\\\",32021]]\"},\"name\":\"NAD27 * OGP-Usa Conus / North Dakota CS27 South zone [32021,15851]\",\"singleCT\":{\"authCode\":{\"auth\":\"EPSG\",\"code\":\"15851\"},\"name\":\"NAD_1927_To_WGS_1984_79_CONUS\",\"type\":\"ST\",\"ver\":\"PE_10_9_1\",\"wkt\":\"GEOGTRAN[\\\"NAD_1927_To_WGS_1984_79_CONUS\\\",GEOGCS[\\\"GCS_North_American_1927\\\",DATUM[\\\"D_North_American_1927\\\",SPHEROID[\\\"Clarke_1866\\\",6378206.4,294.9786982]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],GEOGCS[\\\"GCS_WGS_1984\\\",DATUM[\\\"D_WGS_1984\\\",SPHEROID[\\\"WGS_1984\\\",6378137.0,298.257223563]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],METHOD[\\\"NADCON\\\"],PARAMETER[\\\"Dataset_conus\\\",0.0],OPERATIONACCURACY[5.0],AUTHORITY[\\\"EPSG\\\",15851]]\"},\"type\":\"EBC\",\"ver\":\"PE_10_9_1\"}",
                "persistableReferenceVerticalCrs": "{\"authCode\":{\"auth\":\"EPSG\",\"code\":\"5714\"},\"name\":\"MSL_Height\",\"type\":\"LBC\",\"ver\":\"PE_10_9_1\",\"wkt\":\"VERTCS[\\\"MSL_Height\\\",VDATUM[\\\"Mean_Sea_Level\\\"],PARAMETER[\\\"Vertical_Shift\\\",0.0],PARAMETER[\\\"Direction\\\",1.0],UNIT[\\\"Meter\\\",1.0],AUTHORITY[\\\"EPSG\\\",5714]]\"}",
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
            "SpatialArea": {
              "SpatialLocationCoordinatesDate": "2020-02-13T09:13:15.55Z",
              "QuantitativeAccuracyBandID": "namespace:reference-data--QuantitativeAccuracyBand:Length.LessThan1m:",
              "QualitativeSpatialAccuracyTypeID": "namespace:reference-data--QualitativeSpatialAccuracyType:Assumed:",
              "CoordinateQualityCheckPerformedBy": "Example CoordinateQualityCheckPerformedBy",
              "CoordinateQualityCheckDateTime": "2020-02-13T09:13:15.55Z",
              "CoordinateQualityCheckRemarks": [
                "Example CoordinateQualityCheckRemarks"
              ],
              "AsIngestedCoordinates": {
                "type": "AnyCrsFeatureCollection",
                "CoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:BoundProjected:EPSG::32021_EPSG::15851:",
                "VerticalCoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:Vertical:EPSG::5714:",
                "VerticalUnitID": "namespace:reference-data--UnitOfMeasure:m:",
                "persistableReferenceCrs": "{\"authCode\":{\"auth\":\"OSDU\",\"code\":\"32021079\"},\"lateBoundCRS\":{\"authCode\":{\"auth\":\"EPSG\",\"code\":\"32021\"},\"name\":\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\",\"type\":\"LBC\",\"ver\":\"PE_10_9_1\",\"wkt\":\"PROJCS[\\\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\\\",GEOGCS[\\\"GCS_North_American_1927\\\",DATUM[\\\"D_North_American_1927\\\",SPHEROID[\\\"Clarke_1866\\\",6378206.4,294.9786982]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],PROJECTION[\\\"Lambert_Conformal_Conic\\\"],PARAMETER[\\\"False_Easting\\\",2000000.0],PARAMETER[\\\"False_Northing\\\",0.0],PARAMETER[\\\"Central_Meridian\\\",-100.5],PARAMETER[\\\"Standard_Parallel_1\\\",46.18333333333333],PARAMETER[\\\"Standard_Parallel_2\\\",47.48333333333333],PARAMETER[\\\"Latitude_Of_Origin\\\",45.66666666666666],UNIT[\\\"Foot_US\\\",0.3048006096012192],AUTHORITY[\\\"EPSG\\\",32021]]\"},\"name\":\"NAD27 * OGP-Usa Conus / North Dakota CS27 South zone [32021,15851]\",\"singleCT\":{\"authCode\":{\"auth\":\"EPSG\",\"code\":\"15851\"},\"name\":\"NAD_1927_To_WGS_1984_79_CONUS\",\"type\":\"ST\",\"ver\":\"PE_10_9_1\",\"wkt\":\"GEOGTRAN[\\\"NAD_1927_To_WGS_1984_79_CONUS\\\",GEOGCS[\\\"GCS_North_American_1927\\\",DATUM[\\\"D_North_American_1927\\\",SPHEROID[\\\"Clarke_1866\\\",6378206.4,294.9786982]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],GEOGCS[\\\"GCS_WGS_1984\\\",DATUM[\\\"D_WGS_1984\\\",SPHEROID[\\\"WGS_1984\\\",6378137.0,298.257223563]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],METHOD[\\\"NADCON\\\"],PARAMETER[\\\"Dataset_conus\\\",0.0],OPERATIONACCURACY[5.0],AUTHORITY[\\\"EPSG\\\",15851]]\"},\"type\":\"EBC\",\"ver\":\"PE_10_9_1\"}",
                "persistableReferenceVerticalCrs": "{\"authCode\":{\"auth\":\"EPSG\",\"code\":\"5714\"},\"name\":\"MSL_Height\",\"type\":\"LBC\",\"ver\":\"PE_10_9_1\",\"wkt\":\"VERTCS[\\\"MSL_Height\\\",VDATUM[\\\"Mean_Sea_Level\\\"],PARAMETER[\\\"Vertical_Shift\\\",0.0],PARAMETER[\\\"Direction\\\",1.0],UNIT[\\\"Meter\\\",1.0],AUTHORITY[\\\"EPSG\\\",5714]]\"}",
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
            "GeoContexts": [
              {
                "GeoPoliticalEntityID": "namespace:master-data--GeoPoliticalEntity:SomeUniqueGeoPoliticalEntityID:",
                "GeoTypeID": "namespace:reference-data--GeoPoliticalEntityType:Area:"
              },
              {
                "BasinID": "namespace:master-data--Basin:SomeUniqueBasinID:",
                "GeoTypeID": "namespace:reference-data--BasinType:ArcWrenchOceanContinent:"
              },
              {
                "FieldID": "namespace:master-data--Field:SomeUniqueFieldID:",
                "GeoTypeID": "Field"
              },
              {
                "PlayID": "namespace:master-data--Play:SomeUniquePlayID:",
                "GeoTypeID": "namespace:reference-data--PlayType:CarbonCaptureAndStorage:"
              },
              {
                "ProspectID": "namespace:master-data--Prospect:SomeUniqueProspectID:",
                "GeoTypeID": "namespace:reference-data--ProspectType:Structural.Anticline:"
              }
            ],
            "SubmitterName": "Example SubmitterName",
            "BusinessActivities": [
              "Example BusinessActivities"
            ],
            "AuthorIDs": [
              "Example AuthorIDs"
            ],
            "LineageAssertions": [
              {
                "ID": "namespace:any-group-type--AnyIndividualType:SomeUniqueAnyIndividualTypeID:",
                "LineageRelationshipType": "namespace:reference-data--LineageRelationshipType:Direct:"
              }
            ],
            "WellID": "namespace:master-data--Well:SomeUniqueWellID:",
            "WellboreID": "namespace:master-data--Wellbore:SomeUniqueWellboreID:",
            "RecordDate": "2020-02-13T09:13:15.55Z",
            "ContextTypeID": "namespace:reference-data--PPFGContextType:InterpretationPreDrill:",
            "ServiceCompanyID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
            "Comment": "Example Comment",
            "ReferenceWellTrajectoryID": "namespace:work-product-component--WellboreTrajectory:WellboreTrajectory-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
            "OffsetWellboreIDs": [
              "namespace:master-data--Wellbore:SomeUniqueWellboreID:"
            ],
            "PrimaryReferenceType": "Example PrimaryReferenceType",
            "AbsentValueCharacters": "Example AbsentValueCharacters",
            "TectonicSetting": "namespace:reference-data--TectonicSettingType:Compressional:",
            "GaugeType": "Example GaugeType",
            "VerticalMeasurement": {
              "EffectiveDateTime": "2020-02-13T09:13:15.55Z",
              "VerticalMeasurement": 12345.6,
              "TerminationDateTime": "2020-02-13T09:13:15.55Z",
              "VerticalMeasurementTypeID": "namespace:reference-data--VerticalMeasurementType:ArbitraryPoint:",
              "VerticalMeasurementPathID": "namespace:reference-data--VerticalMeasurementPath:MeasuredDepth:",
              "VerticalMeasurementSourceID": "namespace:reference-data--VerticalMeasurementSource:DRL:",
              "WellboreTVDTrajectoryID": "namespace:work-product-component--WellboreTrajectory:WellboreTrajectory-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
              "VerticalMeasurementUnitOfMeasureID": "namespace:reference-data--UnitOfMeasure:m:",
              "VerticalCRSID": "namespace:reference-data--CoordinateReferenceSystem:BoundProjected:EPSG::32021_EPSG::15851:",
              "VerticalReferenceID": "Example VerticalReferenceID",
              "VerticalReferenceEntityID": "namespace:master-data--Rig:SomeUniqueRigID:",
              "VerticalMeasurementDescription": "Example VerticalMeasurementDescription"
            },
            """

    curve_items = ""
    for c, nb_c in curves.items():
        curve_items = curve_items + r'{"CurveID":' + f'"{c}",' + r"""            
                "CurveName": "Example CurveName",
                "CurveMainFamilyID": "namespace:reference-data--PPFGCurveMainFamily:PorePressure:",
                "CurveFamilyID": "namespace:reference-data--PPFGCurveFamily:TrueVerticalDepth:",
                "CurveFamilyMnemonicID": "namespace:reference-data--PPFGCurveMnemonic:TVD:",
                "CurveProbabilityID": "namespace:reference-data--PPFGCurveProbability:Most%20Likely:",
                "CurveDataProcessingTypeIDs": [
                  "namespace:reference-data--PPFGCurveProcessingType:Filtered:"
                ],
                "CurveLithologyID": "namespace:reference-data--PPFGCurveLithoType:Sand:",
                "CurveTransformModelTypeID": "namespace:reference-data--PPFGCurveTransformModelType:Eaton:",
                "CurveUOM": "namespace:reference-data--UnitOfMeasure:m:"
              },"""

    if len(curves) > 0:
        curve_items = curve_items[:-1]
    else:
        curve_items = r"""{
                "CurveID": "Example CurveID",
                "CurveName": "Example CurveName",
                "CurveMainFamilyID": "namespace:reference-data--PPFGCurveMainFamily:PorePressure:",
                "CurveFamilyID": "namespace:reference-data--PPFGCurveFamily:TrueVerticalDepth:",
                "CurveFamilyMnemonicID": "namespace:reference-data--PPFGCurveMnemonic:TVD:",
                "CurveProbabilityID": "namespace:reference-data--PPFGCurveProbability:Most%20Likely:",
                "CurveDataProcessingTypeIDs": [
                  "namespace:reference-data--PPFGCurveProcessingType:Filtered:"
                ],
                "CurveLithologyID": "namespace:reference-data--PPFGCurveLithoType:Sand:",
                "CurveTransformModelTypeID": "namespace:reference-data--PPFGCurveTransformModelType:Eaton:",
                "CurveUOM": "namespace:reference-data--UnitOfMeasure:m:"
              }"""

    curves_payload = f'"Curves": [{curve_items}]'
    payload = payload + curves_payload + ',"ExtensionProperties": {} } }]'

    rq_proto = Request(
        name="Create OSDU PPFGDataset",
        method="POST",
        url="{{base_url}}/ddms/v3/ppfgdataset",
        headers={
            "accept": "application/json",
            'Content-Type': 'application/json',
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
        payload = payload
    )
    return RequestRunner(rq_proto)


def get_cleaned_ref_and_res() -> dict:
    ref = {
        "kind": "osdu:wks:work-product-component--PPFGDataset:1.2.0",
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
                    "VerticalMeasurement.VerticalMeasurement"
                ]
            }
        ],
        "data": {
            "ResourceHomeRegionID": "namespace:reference-data--OSDURegion:AWSEastUSA:",
            "ResourceHostRegionIDs": [
                "namespace:reference-data--OSDURegion:AWSEastUSA:"
            ],
            "ResourceCurationStatus": "namespace:reference-data--ResourceCurationStatus:Created:",
            "ResourceLifecycleStatus": "namespace:reference-data--ResourceLifecycleStatus:Loading:",
            "Source": "Example Data Source",
            "ExistenceKind": "namespace:reference-data--ExistenceKind:Prototype:",
            "Datasets": [
                "namespace:dataset--AnyDataset:SomeUniqueAnyDatasetID:"
            ],
            "DDMSDatasets": [
                "urn://wddms-3/uuid:20840361-adc0-4842-999b-5639bd07bb38",
                "eml://rddms-1/dataspace('demo/Volve')/resqml20.obj_ContinuousProperty(1615d8d2-2a2d-482c-885e-14225b89e90c)"
            ],
            "Artefacts": [
                {
                    "RoleID": "namespace:reference-data--ArtefactRole:AdaptedContent:",
                    "ResourceKind": "namespace:source_name:group_type--IndividualType:0.0.0",
                    "ResourceID": "namespace:dataset--AnyDataset:SomeUniqueAnyDatasetID:"
                }
            ],
            "IsExtendedLoad": True,
            "IsDiscoverable": True,
            "TechnicalAssurances": [
                {
                    "TechnicalAssuranceTypeID": "namespace:reference-data--TechnicalAssuranceType:Trusted:",
                    "Reviewers": [
                        {
                            "RoleTypeID": "namespace:reference-data--ContactRoleType:AccountOwner:",
                            "DataGovernanceRoleTypeID": "namespace:reference-data--DataGovernanceRoleType:SME:",
                            "WorkflowPersonaTypeID": "namespace:reference-data--WorkflowPersonaType:SeismicProcessor:",
                            "OrganisationID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
                            "Name": "John Smith"
                        }
                    ],
                    "AcceptableUsage": [
                        {
                            "WorkflowUsageTypeID": "namespace:reference-data--WorkflowUsageType:SeismicProcessing:",
                            "WorkflowPersonaTypeID": "namespace:reference-data--WorkflowPersonaType:SeismicProcessor:",
                            "DataQualityRuleSetID": "namespace:reference-data--DataQualityRuleSet:SeismicProcessingQCRuleSet:",
                            "DataQualityID": "namespace:work-product-component--DataQuality:6a433d16-07c8-4f4d-9ddc-5608e2ec4234:1562066077849221",
                            "ValueChainStatusTypeID": "namespace:reference-data--ValueChainStatusType:Exploration:"
                        }
                    ],
                    "UnacceptableUsage": [
                        {
                            "WorkflowUsageTypeID": "namespace:reference-data--WorkflowUsageType:SeismicInterpretation:",
                            "WorkflowPersonaTypeID": "namespace:reference-data--WorkflowPersonaType:SeismicInterpreter:",
                            "DataQualityRuleSetID": "namespace:reference-data--DataQualityRuleSet:SeismicInterpretationQCRuleSet:",
                            "DataQualityID": "namespace:work-product-component--DataQuality:d79bf97c-ff7c-4b82-89b5-c88520c15017:1562066009929332",
                            "ValueChainStatusTypeID": "namespace:reference-data--ValueChainStatusType:FieldDevelopment:"
                        }
                    ],
                    "EffectiveDate": "2020-02-13",
                    "Comment": "This is free form text from reviewer, e.g. restrictions on use"
                }
            ],
            "NameAliases": [
                {
                    "AliasName": "Example AliasName",
                    "AliasNameTypeID": "namespace:reference-data--AliasNameType:RegulatoryIdentifier:",
                    "DefinitionOrganisationID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
                    "EffectiveDateTime": "2020-02-13T09:13:15.55Z",
                    "TerminationDateTime": "2020-02-13T09:13:15.55Z"
                }
            ],
            "Name": "Example Name",
            "Description": "Example Description",
            "CreationDateTime": "2020-02-13T09:13:15.55Z",
            "Tags": [
                "Example Tags"
            ],
            "SpatialPoint": {
                "SpatialLocationCoordinatesDate": "2020-02-13T09:13:15.55Z",
                "QuantitativeAccuracyBandID": "namespace:reference-data--QuantitativeAccuracyBand:Length.LessThan1m:",
                "QualitativeSpatialAccuracyTypeID": "namespace:reference-data--QualitativeSpatialAccuracyType:Assumed:",
                "CoordinateQualityCheckPerformedBy": "Example CoordinateQualityCheckPerformedBy",
                "CoordinateQualityCheckDateTime": "2020-02-13T09:13:15.55Z",
                "CoordinateQualityCheckRemarks": [
                    "Example CoordinateQualityCheckRemarks"
                ],
                "AsIngestedCoordinates": {
                    "type": "AnyCrsFeatureCollection",
                    "CoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:BoundProjected:EPSG::32021_EPSG::15851:",
                    "VerticalCoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:Vertical:EPSG::5714:",
                    "VerticalUnitID": "namespace:reference-data--UnitOfMeasure:m:",
                    "persistableReferenceCrs": "{\"authCode\":{\"auth\":\"OSDU\",\"code\":\"32021079\"},\"lateBoundCRS\":{\"authCode\":{\"auth\":\"EPSG\",\"code\":\"32021\"},\"name\":\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\",\"type\":\"LBC\",\"ver\":\"PE_10_9_1\",\"wkt\":\"PROJCS[\\\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\\\",GEOGCS[\\\"GCS_North_American_1927\\\",DATUM[\\\"D_North_American_1927\\\",SPHEROID[\\\"Clarke_1866\\\",6378206.4,294.9786982]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],PROJECTION[\\\"Lambert_Conformal_Conic\\\"],PARAMETER[\\\"False_Easting\\\",2000000.0],PARAMETER[\\\"False_Northing\\\",0.0],PARAMETER[\\\"Central_Meridian\\\",-100.5],PARAMETER[\\\"Standard_Parallel_1\\\",46.18333333333333],PARAMETER[\\\"Standard_Parallel_2\\\",47.48333333333333],PARAMETER[\\\"Latitude_Of_Origin\\\",45.66666666666666],UNIT[\\\"Foot_US\\\",0.3048006096012192],AUTHORITY[\\\"EPSG\\\",32021]]\"},\"name\":\"NAD27 * OGP-Usa Conus / North Dakota CS27 South zone [32021,15851]\",\"singleCT\":{\"authCode\":{\"auth\":\"EPSG\",\"code\":\"15851\"},\"name\":\"NAD_1927_To_WGS_1984_79_CONUS\",\"type\":\"ST\",\"ver\":\"PE_10_9_1\",\"wkt\":\"GEOGTRAN[\\\"NAD_1927_To_WGS_1984_79_CONUS\\\",GEOGCS[\\\"GCS_North_American_1927\\\",DATUM[\\\"D_North_American_1927\\\",SPHEROID[\\\"Clarke_1866\\\",6378206.4,294.9786982]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],GEOGCS[\\\"GCS_WGS_1984\\\",DATUM[\\\"D_WGS_1984\\\",SPHEROID[\\\"WGS_1984\\\",6378137.0,298.257223563]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],METHOD[\\\"NADCON\\\"],PARAMETER[\\\"Dataset_conus\\\",0.0],OPERATIONACCURACY[5.0],AUTHORITY[\\\"EPSG\\\",15851]]\"},\"type\":\"EBC\",\"ver\":\"PE_10_9_1\"}",
                    "persistableReferenceVerticalCrs": "{\"authCode\":{\"auth\":\"EPSG\",\"code\":\"5714\"},\"name\":\"MSL_Height\",\"type\":\"LBC\",\"ver\":\"PE_10_9_1\",\"wkt\":\"VERTCS[\\\"MSL_Height\\\",VDATUM[\\\"Mean_Sea_Level\\\"],PARAMETER[\\\"Vertical_Shift\\\",0.0],PARAMETER[\\\"Direction\\\",1.0],UNIT[\\\"Meter\\\",1.0],AUTHORITY[\\\"EPSG\\\",5714]]\"}",
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
            "SpatialArea": {
                "SpatialLocationCoordinatesDate": "2020-02-13T09:13:15.55Z",
                "QuantitativeAccuracyBandID": "namespace:reference-data--QuantitativeAccuracyBand:Length.LessThan1m:",
                "QualitativeSpatialAccuracyTypeID": "namespace:reference-data--QualitativeSpatialAccuracyType:Assumed:",
                "CoordinateQualityCheckPerformedBy": "Example CoordinateQualityCheckPerformedBy",
                "CoordinateQualityCheckDateTime": "2020-02-13T09:13:15.55Z",
                "CoordinateQualityCheckRemarks": [
                    "Example CoordinateQualityCheckRemarks"
                ],
                "AsIngestedCoordinates": {
                    "type": "AnyCrsFeatureCollection",
                    "CoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:BoundProjected:EPSG::32021_EPSG::15851:",
                    "VerticalCoordinateReferenceSystemID": "namespace:reference-data--CoordinateReferenceSystem:Vertical:EPSG::5714:",
                    "VerticalUnitID": "namespace:reference-data--UnitOfMeasure:m:",
                    "persistableReferenceCrs": "{\"authCode\":{\"auth\":\"OSDU\",\"code\":\"32021079\"},\"lateBoundCRS\":{\"authCode\":{\"auth\":\"EPSG\",\"code\":\"32021\"},\"name\":\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\",\"type\":\"LBC\",\"ver\":\"PE_10_9_1\",\"wkt\":\"PROJCS[\\\"NAD_1927_StatePlane_North_Dakota_South_FIPS_3302\\\",GEOGCS[\\\"GCS_North_American_1927\\\",DATUM[\\\"D_North_American_1927\\\",SPHEROID[\\\"Clarke_1866\\\",6378206.4,294.9786982]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],PROJECTION[\\\"Lambert_Conformal_Conic\\\"],PARAMETER[\\\"False_Easting\\\",2000000.0],PARAMETER[\\\"False_Northing\\\",0.0],PARAMETER[\\\"Central_Meridian\\\",-100.5],PARAMETER[\\\"Standard_Parallel_1\\\",46.18333333333333],PARAMETER[\\\"Standard_Parallel_2\\\",47.48333333333333],PARAMETER[\\\"Latitude_Of_Origin\\\",45.66666666666666],UNIT[\\\"Foot_US\\\",0.3048006096012192],AUTHORITY[\\\"EPSG\\\",32021]]\"},\"name\":\"NAD27 * OGP-Usa Conus / North Dakota CS27 South zone [32021,15851]\",\"singleCT\":{\"authCode\":{\"auth\":\"EPSG\",\"code\":\"15851\"},\"name\":\"NAD_1927_To_WGS_1984_79_CONUS\",\"type\":\"ST\",\"ver\":\"PE_10_9_1\",\"wkt\":\"GEOGTRAN[\\\"NAD_1927_To_WGS_1984_79_CONUS\\\",GEOGCS[\\\"GCS_North_American_1927\\\",DATUM[\\\"D_North_American_1927\\\",SPHEROID[\\\"Clarke_1866\\\",6378206.4,294.9786982]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],GEOGCS[\\\"GCS_WGS_1984\\\",DATUM[\\\"D_WGS_1984\\\",SPHEROID[\\\"WGS_1984\\\",6378137.0,298.257223563]],PRIMEM[\\\"Greenwich\\\",0.0],UNIT[\\\"Degree\\\",0.0174532925199433]],METHOD[\\\"NADCON\\\"],PARAMETER[\\\"Dataset_conus\\\",0.0],OPERATIONACCURACY[5.0],AUTHORITY[\\\"EPSG\\\",15851]]\"},\"type\":\"EBC\",\"ver\":\"PE_10_9_1\"}",
                    "persistableReferenceVerticalCrs": "{\"authCode\":{\"auth\":\"EPSG\",\"code\":\"5714\"},\"name\":\"MSL_Height\",\"type\":\"LBC\",\"ver\":\"PE_10_9_1\",\"wkt\":\"VERTCS[\\\"MSL_Height\\\",VDATUM[\\\"Mean_Sea_Level\\\"],PARAMETER[\\\"Vertical_Shift\\\",0.0],PARAMETER[\\\"Direction\\\",1.0],UNIT[\\\"Meter\\\",1.0],AUTHORITY[\\\"EPSG\\\",5714]]\"}",
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
            "GeoContexts": [
                {
                    "GeoPoliticalEntityID": "namespace:master-data--GeoPoliticalEntity:SomeUniqueGeoPoliticalEntityID:",
                    "GeoTypeID": "namespace:reference-data--GeoPoliticalEntityType:Area:"
                },
                {
                    "BasinID": "namespace:master-data--Basin:SomeUniqueBasinID:",
                    "GeoTypeID": "namespace:reference-data--BasinType:ArcWrenchOceanContinent:"
                },
                {
                    "FieldID": "namespace:master-data--Field:SomeUniqueFieldID:",
                    "GeoTypeID": "Field"
                },
                {
                    "PlayID": "namespace:master-data--Play:SomeUniquePlayID:",
                    "GeoTypeID": "namespace:reference-data--PlayType:CarbonCaptureAndStorage:"
                },
                {
                    "ProspectID": "namespace:master-data--Prospect:SomeUniqueProspectID:",
                    "GeoTypeID": "namespace:reference-data--ProspectType:Structural.Anticline:"
                }
            ],
            "SubmitterName": "Example SubmitterName",
            "BusinessActivities": [
                "Example BusinessActivities"
            ],
            "AuthorIDs": [
                "Example AuthorIDs"
            ],
            "LineageAssertions": [
                {
                    "ID": "namespace:any-group-type--AnyIndividualType:SomeUniqueAnyIndividualTypeID:",
                    "LineageRelationshipType": "namespace:reference-data--LineageRelationshipType:Direct:"
                }
            ],
            "WellID": "namespace:master-data--Well:SomeUniqueWellID:",
            "WellboreID": "namespace:master-data--Wellbore:SomeUniqueWellboreID:",
            "RecordDate": "2020-02-13T09:13:15.55Z",
            "ContextTypeID": "namespace:reference-data--PPFGContextType:InterpretationPreDrill:",
            "ServiceCompanyID": "namespace:master-data--Organisation:SomeUniqueOrganisationID:",
            "Comment": "Example Comment",
            "ReferenceWellTrajectoryID": "namespace:work-product-component--WellboreTrajectory:WellboreTrajectory-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
            "OffsetWellboreIDs": [
                "namespace:master-data--Wellbore:SomeUniqueWellboreID:"
            ],
            "PrimaryReferenceType": "Example PrimaryReferenceType",
            "AbsentValueCharacters": "Example AbsentValueCharacters",
            "TectonicSetting": "namespace:reference-data--TectonicSettingType:Compressional:",
            "GaugeType": "Example GaugeType",
            "VerticalMeasurement": {
                "EffectiveDateTime": "2020-02-13T09:13:15.55Z",
                "VerticalMeasurement": 12345.6,
                "TerminationDateTime": "2020-02-13T09:13:15.55Z",
                "VerticalMeasurementTypeID": "namespace:reference-data--VerticalMeasurementType:ArbitraryPoint:",
                "VerticalMeasurementPathID": "namespace:reference-data--VerticalMeasurementPath:MeasuredDepth:",
                "VerticalMeasurementSourceID": "namespace:reference-data--VerticalMeasurementSource:DRL:",
                "WellboreTVDTrajectoryID": "namespace:work-product-component--WellboreTrajectory:WellboreTrajectory-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
                "VerticalMeasurementUnitOfMeasureID": "namespace:reference-data--UnitOfMeasure:m:",
                "VerticalCRSID": "namespace:reference-data--CoordinateReferenceSystem:BoundProjected:EPSG::32021_EPSG::15851:",
                "VerticalReferenceID": "Example VerticalReferenceID",
                "VerticalReferenceEntityID": "namespace:master-data--Rig:SomeUniqueRigID:",
                "VerticalMeasurementDescription": "Example VerticalMeasurementDescription"
            },
            "Curves": [
                {
                    "CurveID": "Example CurveID",
                    "CurveName": "Example CurveName",
                    "CurveMainFamilyID": "namespace:reference-data--PPFGCurveMainFamily:PorePressure:",
                    "CurveFamilyID": "namespace:reference-data--PPFGCurveFamily:TrueVerticalDepth:",
                    "CurveFamilyMnemonicID": "namespace:reference-data--PPFGCurveMnemonic:TVD:",
                    "CurveProbabilityID": "namespace:reference-data--PPFGCurveProbability:Most%20Likely:",
                    "CurveDataProcessingTypeIDs": [
                        "namespace:reference-data--PPFGCurveProcessingType:Filtered:"
                    ],
                    "CurveLithologyID": "namespace:reference-data--PPFGCurveLithoType:Sand:",
                    "CurveTransformModelTypeID": "namespace:reference-data--PPFGCurveTransformModelType:Eaton:",
                    "CurveUOM": "namespace:reference-data--UnitOfMeasure:m:"
                }
            ],
            "ExtensionProperties": {}
        }
    }
    # Remove fields generated by server
    del ref["createTime"]
    del ref["createUser"]
    del ref["modifyUser"]
    del ref["modifyTime"]
    # Add mandatory fields
    ref["kind"] = "opendes:wks:work-product-component--PPFGDataset:1.2.0"
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
