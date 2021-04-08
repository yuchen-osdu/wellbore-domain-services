from jsonbender import bend, S, F, K, OptionalS
from jsonbender.control_flow import Alternation, If

from app.converter.converter_utils import ConverterUtils, BENDINGCONTEXT, SEP, EMPTY, WDMS_FRAGMENT, DELFI_SOURCE


class WellboreConverter:
    WELLBORE_WKS_OSDU_MAPPING = {
        "id": OptionalS("id") >> F(ConverterUtils.fix_id, "master-data--Wellbore"),
        "kind": S("kind") >> F(ConverterUtils.wellbore_kind_transform),
        "version": OptionalS("version"),
        "acl": S("acl"),
        "legal": S("legal"),
        "tags": OptionalS("tags"),
        "createUser": OptionalS("createUser"),
        "modifyUser": OptionalS("modifyUser"),
        "createTime": Alternation(S("createTime"), OptionalS("data", "dateCreated")),
        "modifyTime": Alternation(S("modifyTime"), OptionalS("data", "dateModified")),
        "ancestry": OptionalS("ancestry"),
        "meta": OptionalS("meta"),
        "data": {
            "CurrentOperatorID": S(BENDINGCONTEXT, "namespace") + K(SEP)
                                 + S("data", "operator").optional(EMPTY)
                                 >> F(ConverterUtils.lookup, "master-data--Organisation"),
            "DataSourceOrganisationID": None,
            "DefaultVerticalMeasurementID": OptionalS(
                "data", "elevationReference", "name"
            ),
            "DefinitiveTrajectoryID": OptionalS(
                "data", "relationships", "definitiveTrajectory", "id"
            )
                                      >> F(ConverterUtils.fix_id, "work-product-component--WellboreTrajectory"),
            "DrillingReasons": None,
            "ExistenceKind": None,
            "ExtensionProperties": {
                "slb": {
                    "kind": S(BENDINGCONTEXT, "namespace")
                            + K(":wbddms:WellboreExtensions:1.0.0"),
                    "airGap": {
                        "unitKey": OptionalS("data", "airGap", "unitKey"),
                        "value": OptionalS("data", "airGap", "value"),
                    },
                    "drillingDaysTarget": {
                        "unitKey": OptionalS("data", "drillingDaysTarget", "unitKey"),
                        "value": OptionalS("data", "drillingDaysTarget", "value"),
                    },
                    "externalIds": OptionalS("data", "externalIds"),
                    "formationProjected": OptionalS("data", "formationProjected"),
                    "hasAchievedTotalDepth": OptionalS("data", "hasAchievedTotalDepth"),
                    "isActive": OptionalS("data", "isActive"),
                    "locationWGS84": OptionalS("data", "locationWGS84"),
                    "permitDate": OptionalS("data", "permitDate"),
                    "permitNumber": OptionalS("data", "permitNumber"),
                    "plssLocation": {
                        "aliquotPart": OptionalS("data", "plssLocation", "aliquotPart"),
                        "range": OptionalS("data", "plssLocation", "range"),
                        "section": OptionalS("data", "plssLocation", "section"),
                        "township": OptionalS("data", "plssLocation", "township"),
                    },
                    "propertyDictionary": OptionalS("data.propertyDictionary"),
                    "relationships": {
                        "definitiveTimeDepthRelation": {
                            "confidence": OptionalS(
                                "data",
                                "relationships",
                                "definitiveTimeDepthRelation",
                                "confidence",
                            ),
                            "id": OptionalS(
                                "data",
                                "relationships",
                                "definitiveTimeDepthRelation",
                                "id",
                            ),
                            "name": OptionalS(
                                "data",
                                "relationships",
                                "definitiveTimeDepthRelation",
                                "name",
                            ),
                            "version": OptionalS(
                                "data",
                                "relationships",
                                "definitiveTimeDepthRelation",
                                "version",
                            ),
                        }
                    },
                    "wellborePurpose": OptionalS("data", "wellborePurpose"),
                    "wellboreStatus": OptionalS("data", "wellboreStatus"),
                    "wellboreType": OptionalS("data", "wellboreType"),
                    "wellHeadGeographic": OptionalS("data", "wellHeadGeographic"),
                },
                WDMS_FRAGMENT: {
                    DELFI_SOURCE: {
                        "id": OptionalS("id"),
                        "data": {
                            "relationships": {
                                "definitiveTrajectory": {
                                    "id": OptionalS("data", "relationships", "definitiveTrajectory", "id")
                                },
                                "tieInWellbore": {
                                    "id": OptionalS("data", "relationships", "tieInWellbore", "id")
                                },
                                "well": {
                                    "id": OptionalS("data", "relationships", "well", "id")
                                }
                            },
                            "operator": OptionalS("data", "operator"),
                            "country": OptionalS("data", "country"),
                            "county": OptionalS("data", "county"),
                            "block": OptionalS("data", "block"),
                            "state": OptionalS("data", "state"),
                            "field": OptionalS("data", "field"),
                            "wellHeadProjected": {
                                "crsKey": OptionalS("data", "wellHeadProjected", "crsKey")
                            },
                            "formationAtTd": OptionalS("data", "formationAtTd"),
                            "shape": OptionalS("data", "shape"),
                            "elevationReference": {
                                "name": OptionalS("data", "elevationReference", "name"),
                                "elevationFromMsl": {
                                    "unitKey": OptionalS("data", "elevationReference", "elevationFromMsl", "unitKey")
                                }
                            },
                            "totalDepthMd": {
                                "unitKey": OptionalS("data", "totalDepthMd", "unitKey")
                            },
                            "totalDepthMdDriller": {
                                "unitKey": OptionalS("data", "totalDepthMdDriller", "unitKey")
                            },
                            "totalDepthMdPlanned": {
                                "unitKey": OptionalS("data", "totalDepthMdPlanned", "unitKey")
                            },
                            "totalDepthMdSubSeaPlanned": {
                                "unitKey": OptionalS("data", "totalDepthMdSubSeaPlanned", "unitKey")
                            },
                            "totalDepthProjectedMd": {
                                "unitKey": OptionalS("data", "totalDepthProjectedMd", "unitKey")
                            },
                            "totalDepthTvd": {
                                "unitKey": OptionalS("data", "totalDepthTvd", "unitKey")
                            },
                            "totalDepthTvdDriller": {
                                "unitKey": OptionalS("data", "totalDepthTvdDriller", "unitKey")
                            },
                            "totalDepthTvdPlanned": {
                                "unitKey": OptionalS("data", "totalDepthTvdPlanned", "unitKey")
                            },
                            "totalDepthTvdSubSeaPlanned": {
                                "unitKey": OptionalS("data", "totalDepthTvdSubSeaPlanned", "unitKey")
                            },
                            "wellHeadElevation": {
                                "unitKey": OptionalS("data", "wellHeadElevation", "unitKey")
                            },
                            "kickOffMd": {
                                "unitKey": OptionalS("data", "kickOffMd", "unitKey")
                            },
                            "kickOffTvd": {
                                "unitKey": OptionalS("data", "kickOffTvd", "unitKey")
                            }
                        }
                    }
                }
            },
            "FacilityEvents": [
                {
                    "EffectiveDateTime": OptionalS("data", "spudDate") >> F(ConverterUtils.date_to_datetime),
                    "FacilityEventTypeID": If(OptionalS("data", "spudDate"), S(BENDINGCONTEXT, "namespace")
                                              + K(":reference-data--FacilityEventType:Spud:")),
                    "TerminationDateTime": None,
                }
            ],
            "FacilityID": None,
            "FacilityName": OptionalS("data", "name"),
            "FacilityNameAliases": [
                {
                    "AliasName": OptionalS("data", "uwi"),
                    "AliasNameTypeID": If(OptionalS("data", "uwi"), S(BENDINGCONTEXT, "namespace")
                                          + K(":reference-data--AliasNameType:UniqueIdentifier:")),
                    "DefinitionOrganisationID": None,
                    "EffectiveDateTime": None,
                    "TerminationDateTime": None,
                },
                {
                    "AliasName": OptionalS("data", "wellboreNumberGovernment"),
                    "AliasNameTypeID": If(OptionalS("data", "wellboreNumberGovernment"), S(BENDINGCONTEXT, "namespace")
                                          + K(":reference-data--AliasNameType:RegulatoryIdentifier:")),
                    "DefinitionOrganisationID": None,
                    "EffectiveDateTime": None,
                    "TerminationDateTime": None,
                },
                {
                    "AliasName": OptionalS("data", "wellboreNumberOperator"),
                    "AliasNameTypeID": If(OptionalS("data", "wellboreNumberOperator"), S(BENDINGCONTEXT, "namespace")
                                          + K(":reference-data--AliasNameType:IndustryName:")),
                    "DefinitionOrganisationID": None,
                    "EffectiveDateTime": None,
                    "TerminationDateTime": None,
                },
            ],
            "FacilityOperators": None,
            "FacilitySpecifications": None,
            "FacilityStates": None,
            "FacilityTypeID": S(BENDINGCONTEXT, "namespace")
                              + K(":reference-data--FacilityType:Wellbore:"),
            "GeoContexts": [
                {
                    "BasinID": None,
                    "PlayID": None,
                    "ProspectID": None,
                    "GeoPoliticalEntityID": S(BENDINGCONTEXT, "namespace")
                                            + K(SEP)
                                            + S("data", "country").optional(EMPTY)
                                            >> F(ConverterUtils.lookup, "master-data--GeoPoliticalEntity"),
                    "GeoTypeID": If(OptionalS("data", "country"), S(BENDINGCONTEXT, "namespace")
                                    + K(":reference-data--GeoPoliticalEntityType:Country:")),
                },
                {
                    "BasinID": None,
                    "PlayID": None,
                    "ProspectID": None,
                    "GeoPoliticalEntityID": S(BENDINGCONTEXT, "namespace")
                                            + K(SEP)
                                            + S("data", "county").optional(EMPTY)
                                            >> F(ConverterUtils.lookup, "master-data--GeoPoliticalEntity"),
                    "GeoTypeID": If(OptionalS("data", "county"), S(BENDINGCONTEXT, "namespace")
                                    + K(":reference-data--GeoPoliticalEntityType:County:")),
                },
                {
                    "BasinID": None,
                    "PlayID": None,
                    "ProspectID": None,
                    "GeoPoliticalEntityID": S(BENDINGCONTEXT, "namespace")
                                            + K(SEP)
                                            + S("data", "block").optional(EMPTY)
                                            >> F(ConverterUtils.lookup, "master-data--GeoPoliticalEntity"),
                    "GeoTypeID": If(OptionalS("data", "block"), S(BENDINGCONTEXT, "namespace")
                                    + K(":reference-data--GeoPoliticalEntityType:LicenseBlock:")),
                },
                {
                    "BasinID": None,
                    "PlayID": None,
                    "ProspectID": None,
                    "GeoPoliticalEntityID": S(BENDINGCONTEXT, "namespace")
                                            + K(SEP)
                                            + S("data", "state").optional(EMPTY)
                                            >> F(ConverterUtils.lookup, "master-data--GeoPoliticalEntity"),
                    "GeoTypeID": If(OptionalS("data", "state"), S(BENDINGCONTEXT, "namespace")
                                    + K(":reference-data--GeoPoliticalEntityType:State:")),
                },
                {
                    "BasinID": None,
                    "PlayID": None,
                    "ProspectID": None,
                    "FieldID": S(BENDINGCONTEXT, "namespace")
                               + K(SEP)
                               + S("data", "field").optional(EMPTY)
                               >> F(ConverterUtils.lookup, "master-data--Field"),
                    "GeoTypeID": If(OptionalS("data", "field"), K("Field")),
                    # mapping says {namespace}:reference-data--GeoPoliticalEntityType:Area:"
                },
            ],
            "GeographicBottomHoleLocation": None,
            "InitialOperatorID": None,
            "KickOffWellbore": OptionalS("data", "relationships", "tieInWellbore", "id")
                               >> F(ConverterUtils.fix_id, "master-data--Wellbore"),
            "NameAliases": None,
            "OperatingEnvironmentID": None,
            "PrimaryMaterialID": None,
            "ProjectedBottomHoleLocation": None,
            "ResourceCurationStatus": None,
            "ResourceHomeRegionID": None,
            "ResourceHostRegionIDs": None,
            "ResourceLifecycleStatus": None,
            "ResourceSecurityClassification": None,
            "SequenceNumber": None,
            "Source": None,
            "SpatialLocation": {
                "AsIngestedCoordinates": {
                    "CoordinateReferenceSystemID": S(BENDINGCONTEXT, "namespace")
                                                   + K(SEP)
                                                   + S("data", "wellHeadProjected", "crsKey").optional(EMPTY)
                                                   >> F(
                        ConverterUtils.lookup,
                        "reference-data--CoordinateReferenceSystem",
                    ),
                    "features":
                        [
                            {
                                "geometry": {
                                    "coordinates": [
                                        OptionalS("data", "wellHeadProjected", "x"),
                                        OptionalS("data", "wellHeadProjected", "y"),
                                        OptionalS(
                                            "data",
                                            "wellHeadProjected",
                                            "elevationFromMsl",
                                            "value",
                                        ),
                                    ],
                                    "type": If(OptionalS("data", "wellHeadProjected"), K("AnyCrsPoint"), K(None))
                                },
                                "type": If(OptionalS("data", "wellHeadProjected"), K("AnyCrsFeature"), K(None))
                            }
                        ],
                    "persistableReferenceCrs": If(OptionalS("data", "wellHeadProjected"),
                                                  (OptionalS("meta") >> F(ConverterUtils.find_in_meta, "kind", "CRS",
                                                                          "persistableReference")), K(None)),
                    "persistableReferenceUnitZ": If(OptionalS("data", "wellHeadProjected"),
                                                    OptionalS("data", "wellHeadProjected", "elevationFromMsl",
                                                              "unitKey"), K(None)),
                    "persistableReferenceVerticalCrs": If(OptionalS("data", "wellHeadProjected"),
                                                          OptionalS("meta") >> F(ConverterUtils.find_in_meta, "kind",
                                                                                 "CRS", "persistableReference"),
                                                          K(None)),
                    "type": If(OptionalS("data", "wellHeadProjected"), K(
                        "AnyCrsFeatureCollection")
                               ),
                    "VerticalCoordinateReferenceSystemID": None,
                },
                "SpatialGeometryTypeID": If(OptionalS("data", "wellHeadWgs84"), S(BENDINGCONTEXT, "namespace")
                                            + K(":reference-data--SpatialGeometryType:Point:")),
                "Wgs84Coordinates": {
                    "features": [
                        {
                            "geometry": {
                                "coordinates": [
                                    OptionalS("data", "wellHeadWgs84", "longitude"),
                                    OptionalS("data", "wellHeadWgs84", "latitude"),
                                ],
                                "type": If(OptionalS("data", "wellHeadWgs84"), K("Point")),
                            },
                            "type": If(OptionalS("data", "wellHeadWgs84"), K("Feature")),
                        }
                    ],
                    "type": If(OptionalS("data", "wellHeadWgs84"), K("FeatureCollection")),
                },
            },
            "TargetFormation": S(BENDINGCONTEXT, "namespace")
                               + K(SEP)
                               + S("data", "formationAtTd").optional(EMPTY)
                               >> F(ConverterUtils.lookup, "reference-data--GeologicalFormation"),
            "TrajectoryTypeID": S(BENDINGCONTEXT, "namespace")
                                + K(SEP)
                                + S("data", "shape").optional(EMPTY)
                                >> F(ConverterUtils.lookup, "reference-data--WellboreTrajectoryType"),
            "VersionCreationReason": None,
            "VerticalMeasurements": [
                {
                    "EffectiveDateTime": None,
                    "TerminationDateTime": None,
                    "VerticalCRSID": None,
                    "VerticalMeasurement": OptionalS(
                        "data", "elevationReference", "elevationFromMsl", "value"
                    ),
                    "VerticalMeasurementDescription": None,
                    "VerticalMeasurementID": OptionalS(
                        "data", "elevationReference", "name"
                    ),
                    "VerticalMeasurementPathID": If(OptionalS("data", "elevationReference"),
                                                    S(BENDINGCONTEXT, "namespace")
                                                    + K(":reference-data--VerticalMeasurementPath:ELEV:")),
                    "VerticalMeasurementSourceID": None,
                    "VerticalMeasurementTypeID": S(BENDINGCONTEXT, "namespace")
                                                 + K(SEP)
                                                 + S("data", "elevationReference", "name").optional(EMPTY)
                                                 >> F(
                        ConverterUtils.lookup, "reference-data--VerticalMeasurementType"
                    ),
                    "VerticalMeasurementUnitOfMeasureID": S(
                        BENDINGCONTEXT, "namespace"
                    )
                                                          + K(SEP)
                                                          + S(
                        "data", "elevationReference", "elevationFromMsl", "unitKey"
                    ).optional(EMPTY)
                                                          >> F(ConverterUtils.lookup, "reference-data--UnitOfMeasure"),
                    "VerticalReferenceID": None,
                    "WellboreTVDTrajectoryID": None,
                },
                {
                    "VerticalMeasurement": OptionalS("data", "totalDepthMd", "value"),
                    "VerticalMeasurementID": If(OptionalS("data", "totalDepthMd"), K("Total Depth MD")),
                    "VerticalMeasurementPathID": If(OptionalS("data", "totalDepthMd"), S(BENDINGCONTEXT, "namespace")
                                                    + K(":reference-data--VerticalMeasurementPath:MD:")),
                    "VerticalMeasurementUnitOfMeasureID": S(
                        BENDINGCONTEXT, "namespace"
                    )
                                                          + K(SEP)
                                                          + S("data", "totalDepthMd", "unitKey").optional(EMPTY)
                                                          >> F(ConverterUtils.lookup, "reference-data--UnitOfMeasure"),
                },
                {
                    "VerticalMeasurement": OptionalS(
                        "data", "totalDepthMdDriller", "value"
                    ),
                    "VerticalMeasurementID": If(OptionalS("data", "totalDepthMdDriller"), K("Total Depth Driller MD")),
                    "VerticalMeasurementPathID": If(OptionalS("data", "totalDepthMdDriller"),
                                                    S(BENDINGCONTEXT, "namespace")
                                                    + K(":reference-data--VerticalMeasurementPath:MD:")),
                    "VerticalMeasurementUnitOfMeasureID": S(
                        BENDINGCONTEXT, "namespace"
                    )
                                                          + K(SEP)
                                                          + S("data", "totalDepthMdDriller", "unitKey").optional(EMPTY)
                                                          >> F(ConverterUtils.lookup, "reference-data--UnitOfMeasure"),
                },
                {
                    "VerticalMeasurement": OptionalS(
                        "data", "totalDepthMdPlanned", "value"
                    ),
                    "VerticalMeasurementID": If(OptionalS("data", "totalDepthMdPlanned"), K("Total Depth Planned MD")),
                    "VerticalMeasurementPathID": If(OptionalS("data", "totalDepthMdPlanned"),
                                                    S(BENDINGCONTEXT, "namespace")
                                                    + K(":reference-data--VerticalMeasurementPath:MD:")),
                    "VerticalMeasurementUnitOfMeasureID": S(
                        BENDINGCONTEXT, "namespace"
                    )
                                                          + K(SEP)
                                                          + S("data", "totalDepthMdPlanned", "unitKey").optional(EMPTY)
                                                          >> F(ConverterUtils.lookup, "reference-data--UnitOfMeasure"),
                },
                {
                    "VerticalMeasurement": OptionalS(
                        "data", "totalDepthMdSubSeaPlanned", "value"
                    ),
                    "VerticalMeasurementID": If(OptionalS("data", "totalDepthMdSubSeaPlanned"),
                                                K("Total Depth Sub Sea Planned MD")),
                    "VerticalMeasurementPathID": If(OptionalS("data", "totalDepthMdSubSeaPlanned"),
                                                    S(BENDINGCONTEXT, "namespace")
                                                    + K(":reference-data--VerticalMeasurementPath:MD:")),
                    "VerticalMeasurementUnitOfMeasureID": S(
                        BENDINGCONTEXT, "namespace"
                    )
                                                          + K(SEP)
                                                          + S("data", "totalDepthMdSubSeaPlanned", "unitKey").optional(
                        EMPTY)
                                                          >> F(ConverterUtils.lookup, "reference-data--UnitOfMeasure"),
                },
                {
                    "VerticalMeasurement": OptionalS(
                        "data", "totalDepthProjectedMd", "value"
                    ),
                    "VerticalMeasurementID": If(OptionalS("data", "totalDepthProjectedMd"),
                                                K("Total Depth Projected MD")),
                    "VerticalMeasurementPathID": If(OptionalS("data", "totalDepthProjectedMd"),
                                                    S(BENDINGCONTEXT, "namespace")
                                                    + K(":reference-data--VerticalMeasurementPath:MD:")),
                    "VerticalMeasurementUnitOfMeasureID": S(
                        BENDINGCONTEXT, "namespace"
                    )
                                                          + K(SEP)
                                                          + S("data", "totalDepthProjectedMd", "unitKey").optional(
                        EMPTY)
                                                          >> F(ConverterUtils.lookup, "reference-data--UnitOfMeasure"),
                },
                {
                    "VerticalMeasurement": OptionalS("data", "totalDepthTvd", "value"),
                    "VerticalMeasurementID": If(OptionalS("data", "totalDepthTvd"), K("Total Depth TVD")),
                    "VerticalMeasurementPathID": If(OptionalS("data", "totalDepthTvd"), S(BENDINGCONTEXT, "namespace")
                                                    + K(":reference-data--VerticalMeasurementPath:TVD:")),
                    "VerticalMeasurementUnitOfMeasureID": S(
                        BENDINGCONTEXT, "namespace"
                    )
                                                          + K(SEP)
                                                          + S("data", "totalDepthTvd", "unitKey").optional(EMPTY)
                                                          >> F(ConverterUtils.lookup, "reference-data--UnitOfMeasure"),
                },
                {
                    "VerticalMeasurement": OptionalS(
                        "data", "totalDepthTvdDriller", "value"
                    ),
                    "VerticalMeasurementID": If(OptionalS("data", "totalDepthTvdDriller"),
                                                K("Total Depth Driller TVD")),
                    "VerticalMeasurementPathID": If(OptionalS("data", "totalDepthTvdDriller"),
                                                    S(BENDINGCONTEXT, "namespace")
                                                    + K(":reference-data--VerticalMeasurementPath:TVD:")),
                    "VerticalMeasurementUnitOfMeasureID": S(
                        BENDINGCONTEXT, "namespace"
                    )
                                                          + K(SEP)
                                                          + S("data", "totalDepthTvdDriller", "unitKey").optional(EMPTY)
                                                          >> F(ConverterUtils.lookup, "reference-data--UnitOfMeasure"),
                },
                {
                    "VerticalMeasurement": OptionalS(
                        "data", "totalDepthTvdPlanned", "value"
                    ),
                    "VerticalMeasurementID": If(OptionalS("data", "totalDepthTvdPlanned"),
                                                K("Total Depth Planned TVD")),
                    "VerticalMeasurementPathID": If(OptionalS("data", "totalDepthTvdPlanned"),
                                                    S(BENDINGCONTEXT, "namespace")
                                                    + K(":reference-data--VerticalMeasurementPath:TVD:")),
                    "VerticalMeasurementUnitOfMeasureID": S(
                        BENDINGCONTEXT, "namespace"
                    )
                                                          + K(SEP)
                                                          + S("data", "totalDepthTvdPlanned", "unitKey").optional(EMPTY)
                                                          >> F(ConverterUtils.lookup, "reference-data--UnitOfMeasure"),
                },
                {
                    "VerticalMeasurement": OptionalS(
                        "data", "totalDepthTvdSubSeaPlanned", "value"
                    ),
                    "VerticalMeasurementID": If(OptionalS("data", "totalDepthTvdSubSeaPlanned"),
                                                K("Total Depth Sub Sea Planned TVD")),
                    "VerticalMeasurementPathID": If(OptionalS("data", "totalDepthTvdSubSeaPlanned"),
                                                    S(BENDINGCONTEXT, "namespace")
                                                    + K(":reference-data--VerticalMeasurementPath:TVD:")),
                    "VerticalMeasurementUnitOfMeasureID": S(
                        BENDINGCONTEXT, "namespace"
                    )
                                                          + K(SEP)
                                                          + S("data", "totalDepthTvdSubSeaPlanned", "unitKey").optional(
                        EMPTY)
                                                          >> F(ConverterUtils.lookup, "reference-data--UnitOfMeasure"),
                },
                {
                    "VerticalMeasurement": OptionalS(
                        "data", "wellHeadElevation", "value"
                    ),
                    "VerticalMeasurementID": If(OptionalS("data", "wellHeadElevation"), K("Well Head Elevation")),
                    "VerticalMeasurementPathID": If(OptionalS("data", "wellHeadElevation"),
                                                    S(BENDINGCONTEXT, "namespace")
                                                    + K(":reference-data--VerticalMeasurementPath:ELEV:")),
                    "VerticalMeasurementUnitOfMeasureID": S(
                        BENDINGCONTEXT, "namespace"
                    )
                                                          + K(SEP)
                                                          + S("data", "wellHeadElevation", "unitKey").optional(EMPTY)
                                                          >> F(ConverterUtils.lookup, "reference-data--UnitOfMeasure"),
                },
                {
                    "VerticalMeasurement": OptionalS("data", "kickOffMd", "value"),
                    "VerticalMeasurementID": If(OptionalS("data", "kickOffMd"), K("Kick-off Depth MD")),
                    "VerticalMeasurementPathID": If(OptionalS("data", "kickOffMd"), S(BENDINGCONTEXT, "namespace")
                                                    + K(":reference-data--VerticalMeasurementPath:MD:")),
                    "VerticalMeasurementUnitOfMeasureID": S(
                        BENDINGCONTEXT, "namespace"
                    )
                                                          + K(SEP)
                                                          + S("data", "kickOffMd", "unitKey").optional(EMPTY)
                                                          >> F(ConverterUtils.lookup, "reference-data--UnitOfMeasure"),
                },
                {
                    "VerticalMeasurement": OptionalS("data", "kickOffTvd", "value"),
                    "VerticalMeasurementID": If(OptionalS("data", "kickOffTvd"), K("Kick-off Depth TVD")),
                    "VerticalMeasurementPathID": If(OptionalS("data", "kickOffTvd"), S(BENDINGCONTEXT, "namespace")
                                                    + K(":reference-data--VerticalMeasurementPath:TVD:")),
                    "VerticalMeasurementUnitOfMeasureID": S(
                        BENDINGCONTEXT, "namespace"
                    )
                                                          + K(SEP)
                                                          + S("data", "kickOffTvd", "unitKey").optional(EMPTY)
                                                          >> F(ConverterUtils.lookup, "reference-data--UnitOfMeasure"),
                },
            ],
            "WellID": OptionalS("data", "relationships", "well", "id")
                      >> F(ConverterUtils.fix_id, "master-data--Well"),
        },
    }

    @classmethod
    def convert_wks_to_osdu(cls, wks_dict: dict, context: dict) -> dict:
        """
        :param wks_dict:
        :param context: the context must contains at least namespace variable corresponding to the authority
        :return:
        """
        wks_dict = ConverterUtils.remove_none_from_dict(wks_dict)
        # inject context in input dict, to make it available easily during bending
        wks_dict[BENDINGCONTEXT] = context
        res = bend(cls.WELLBORE_WKS_OSDU_MAPPING, wks_dict)
        res = ConverterUtils.remove_none(res)
        return res
