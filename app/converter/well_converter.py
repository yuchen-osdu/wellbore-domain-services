from jsonbender import bend, S, F, K, OptionalS, If
from jsonbender.control_flow import Alternation
from app.converter.converter_utils import ConverterUtils, BENDINGCONTEXT, SEP, EMPTY, WDMS_FRAGMENT, DELFI_SOURCE



class WellConverter:
    WELL_WKS_OSDU_MAPPING = {
        "id": OptionalS("id") >> F(ConverterUtils.fix_id, "master-data--Well"),
        "kind": S("kind") >> F(ConverterUtils.well_kind_transform),
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
            "CurrentOperatorID": None,
            "DataSourceOrganisationID": None,
            "DefaultVerticalCRSID": S(BENDINGCONTEXT, "namespace") + K(SEP) + (OptionalS("meta") >> F(ConverterUtils.find_in_meta, "kind", "CRS", "name")) >> F(ConverterUtils.lookup, "reference-data--CoordinateReferenceSystem"),
            "DefaultVerticalMeasurementID": OptionalS("data", "elevationReference", "name"),
            "ExistenceKind": None,
            "ExtensionProperties": {
                "slb": {
                    "directionWell": OptionalS("data", "directionWell"),
                    "externalIds": OptionalS("data", "externalIds"),
                    "fluidWell": OptionalS("data", "fluidWell"),
                    "kind": K("slb:wbddms:WellExtensions:1.0.0"),
                    "plssLocation": {
                        "aliquotPart": OptionalS("data", "plssLocation", "aliquotPart"),
                        "range": OptionalS("data", "plssLocation", "range"),
                        "section": OptionalS("data", "plssLocation", "section"),
                        "township": OptionalS("data", "plssLocation", "township"),
                    },
                    "propertyDictionary": OptionalS("data", "propertyDictionary"),
                    "relationships": {
                        "asset": {
                            "confidence": OptionalS("data", "relationships", "asset", "confidence"),
                            "id": OptionalS("data", "relationships", "asset", "id"),
                            "name": OptionalS("data", "relationships", "asset", "name"),
                            "version": OptionalS("data", "relationships", "asset", "version")
                        }
                    },
                    "wellPurpose": OptionalS("data", "wellPurpose"),
                    "wellStatus": OptionalS("data", "wellStatus"),
                    "wellType": OptionalS("data", "wellType"),
                    "operatorDivision": OptionalS("data", "operatorDivision"),
                    "operatorInterest": OptionalS("data", "operatorInterest"),
                    "basinName": OptionalS("data", "basinContext", "basinName"),
                    "subBasinName": OptionalS("data", "basinContext", "subBasinName"),
                    "locationWGS84": OptionalS("data", "locationWGS84"),
                    "wellHeadGeographic": OptionalS("data", "wellHeadGeographic")
                },
                WDMS_FRAGMENT: {
                    DELFI_SOURCE: {
                        "id": OptionalS("id"),
                        "data": {
                            "operator": OptionalS("data", "operator"),
                            "country": OptionalS("data", "country"),
                            "county": OptionalS("data", "county"),
                            "block": OptionalS("data", "block"),
                            "state": OptionalS("data", "state"),
                            "region": OptionalS("data", "region"),
                            "district": OptionalS("data", "district"),
                            "basinContext": OptionalS("data", "basinContext"),
                            "field": OptionalS("data", "field"),
                            "operatorOriginal": OptionalS("data", "operatorOriginal"),
                            "wellLocationType": OptionalS("data", "wellLocationType"),
                            "wellHeadProjected": OptionalS("data", "wellHeadProjected"),
                            "elevationReference": OptionalS("data", "elevationReference"),
                            "wellHeadElevation": OptionalS("data", "wellHeadElevation"),
                            "waterDepth": OptionalS("data", "waterDepth"),
                            "groundElevation": OptionalS("data", "groundElevation"),
                        }
                    }
                }
            },
            "FacilityEvents": [
                {
                    "EffectiveDateTime": OptionalS("data", "dateSpudded") >> F(ConverterUtils.date_to_datetime),
                    "FacilityEventTypeID": If(OptionalS("data", "dateSpudded"), S(BENDINGCONTEXT, "namespace")
                                           + K(":reference-data--FacilityEventType:Spud:")),
                    "TerminationDateTime": None,
                },
                {
                    "EffectiveDateTime": OptionalS("data", "dateLicenseIssued"),
                    "FacilityEventTypeID": If(OptionalS("data", "dateLicenseIssued"), S(BENDINGCONTEXT, "namespace")
                                           + K(":reference-data--FacilityEventType:Permit:"))
                },
                {
                    "EffectiveDateTime": OptionalS("data", "datePluggedAbandoned"),
                    "FacilityEventTypeID": If(OptionalS("data", "datePluggedAbandoned"), S(BENDINGCONTEXT, "namespace")
                                           + K(":reference-data--FacilityEventType:Abandon:"))
                },
            ],
            "FacilityID": None,
            "FacilityName": OptionalS("data", "name"),
            "FacilityNameAliases": [
                {
                    "AliasName": OptionalS("data", "uwi"),
                    "AliasNameTypeID": If(OptionalS("data", "uwi"),
                                          S(BENDINGCONTEXT, "namespace")
                                       + K(":reference-data--AliasNameType:UniqueIdentifier:")),
                    "DefinitionOrganisationID": None,
                    "EffectiveDateTime": None,
                    "TerminationDateTime": None,
                },
                {
                    "AliasName": OptionalS("data", "wellNumberGovernment"),
                    "AliasNameTypeID": If(OptionalS("data", "datePlugwellNumberGovernmentgedAbandoned"),
                                          S(BENDINGCONTEXT, "namespace")
                                       + K(":reference-data--AliasNameType:RegulatoryIdentifier:")),
                    "DefinitionOrganisationID": None,
                    "EffectiveDateTime": None,
                    "TerminationDateTime": None,
                },
                {
                    "AliasName": OptionalS("data", "wellNumberLicense"),
                    "AliasNameTypeID": If(OptionalS("data", "wellNumberLicense"),
                                          S(BENDINGCONTEXT, "namespace")
                                       + K(":reference-data--AliasNameType:LeaseIdentifier:")),
                    "DefinitionOrganisationID": None,
                    "EffectiveDateTime": None,
                    "TerminationDateTime": None,
                },
                {
                    "AliasName": OptionalS("data", "wellNumberOperator"),
                    "AliasNameTypeID": If(OptionalS("data", "wellNumberOperator"),
                                          S(BENDINGCONTEXT, "namespace")
                                       + K(":reference-data--AliasNameType:IndustryName:")),
                    "DefinitionOrganisationID": None,
                    "EffectiveDateTime": None,
                    "TerminationDateTime": None,
                }
            ],
            "FacilityOperators": [
                {
                    "EffectiveDateTime": None,
                    "FacilityOperatorID": None,
                    "FacilityOperatorOrganisationID":
                        S(BENDINGCONTEXT, "namespace")
                        + K(SEP)
                        + S("data", "operator").optional(EMPTY)
                        >> F(ConverterUtils.lookup, "master-data--Organisation"),
                    "TerminationDateTime": None,
                }
            ],
            "FacilitySpecifications": None,
            "FacilityStates": None,
            "FacilityTypeID": S(BENDINGCONTEXT, "namespace")
                              + K(":reference-data--FacilityType:Well:"),
            "GeoContexts": [
                {
                    "GeoPoliticalEntityID": S(BENDINGCONTEXT, "namespace")
                                            + K(SEP)
                                            + S("data", "country").optional(EMPTY)
                                            >> F(ConverterUtils.lookup, "master-data--GeoPoliticalEntity"),
                    "GeoTypeID": If(OptionalS("data", "country"), S(BENDINGCONTEXT, "namespace")
                                 + K(":reference-data--GeoPoliticalEntityType:Country:")),
                },
                {
                    "GeoPoliticalEntityID": S(BENDINGCONTEXT, "namespace")
                                            + K(SEP)
                                            + S("data", "county").optional(EMPTY)
                                            >> F(ConverterUtils.lookup, "master-data--GeoPoliticalEntity"),
                    "GeoTypeID": If(OptionalS("data", "county"), S(BENDINGCONTEXT, "namespace")
                                 + K(":reference-data--GeoPoliticalEntityType:County:")),
                },
                {
                    "GeoPoliticalEntityID": S(BENDINGCONTEXT, "namespace")
                                            + K(SEP)
                                            + S("data", "block").optional(EMPTY)
                                            >> F(ConverterUtils.lookup, "master-data--GeoPoliticalEntity"),
                    "GeoTypeID": If(OptionalS("data", "block"), S(BENDINGCONTEXT, "namespace")
                                 + K(":reference-data--GeoPoliticalEntityType:LicenseBlock:")),
                },
                {
                    "GeoPoliticalEntityID": S(BENDINGCONTEXT, "namespace")
                                            + K(SEP)
                                            + S("data", "state").optional(EMPTY)
                                            >> F(ConverterUtils.lookup, "master-data--GeoPoliticalEntity"),
                    "GeoTypeID": If(OptionalS("data", "state"), S(BENDINGCONTEXT, "namespace")
                                 + K(":reference-data--GeoPoliticalEntityType:State:")),
                },
                {
                    "GeoPoliticalEntityID": S(BENDINGCONTEXT, "namespace")
                                            + K(SEP)
                                            + S("data", "region").optional(EMPTY)
                                            >> F(ConverterUtils.lookup, "master-data--GeoPoliticalEntity"),
                    "GeoTypeID": If(OptionalS("data", "region"), S(BENDINGCONTEXT, "namespace")
                                 + K(":reference-data--GeoPoliticalEntityType:Region:")),
                },
                {
                    "GeoPoliticalEntityID": S(BENDINGCONTEXT, "namespace")
                                            + K(SEP)
                                            + S("data", "district").optional(EMPTY)
                                            >> F(ConverterUtils.lookup, "master-data--GeoPoliticalEntity"),
                    "GeoTypeID": If(OptionalS("data", "district"), S(BENDINGCONTEXT, "namespace")
                                 + K(":reference-data--GeoPoliticalEntityType:District:")),
                },
                {
                    "BasinID": S(BENDINGCONTEXT, "namespace")
                                            + K(SEP)
                                            + S("data", "basinContext", "basinCode").optional(EMPTY)
                                            >> F(ConverterUtils.lookup, "master-data--Basin"),
                    "PlayID": None,
                    "ProspectID": None,
                    "GeoPoliticalEntityID": None,
                    "GeoTypeID": If(OptionalS("data", "basinContext", "basinCode"), S(BENDINGCONTEXT, "namespace")
                                 + K(":reference-data--GeoPoliticalEntityType:Basin:")),
                },
                {
                    "BasinID": S(BENDINGCONTEXT, "namespace")
                               + K(SEP)
                               + S("data", "basinContext", "subBasinCode").optional(EMPTY)
                               >> F(ConverterUtils.lookup, "master-data--Basin"),
                    "PlayID": None,
                    "ProspectID": None,
                    "GeoPoliticalEntityID": None,
                    "GeoTypeID": If(OptionalS("data", "basinContext", "subBasinCode"), S(BENDINGCONTEXT, "namespace")
                                 + K(":reference-data--GeoPoliticalEntityType:SubBasin:")),
                },
                {
                    "BasinID": None,
                    "PlayID": None,
                    "ProspectID": None,
                    "FieldID": S(BENDINGCONTEXT, "namespace")
                               + K(SEP)
                               + S("data", "field").optional(EMPTY)
                               >> F(ConverterUtils.lookup, "master-data--Field"),
                    "GeoTypeID": "Field",
                },
            ],
            "InitialOperatorID": S(BENDINGCONTEXT, "namespace")
                               + K(SEP)
                               + S("data", "operatorOriginal").optional(EMPTY)
                               >> F(ConverterUtils.lookup, "master-data--Organisation"),
            "InterestTypeID": None,
            "NameAliases": None,
            "OperatingEnvironmentID": S(BENDINGCONTEXT, "namespace")
                               + K(SEP)
                               + S("data", "wellLocationType").optional(EMPTY)
                               >> F(ConverterUtils.lookup, "reference-data--OperatingEnvironment"),
            "ResourceCurationStatus": None,
            "ResourceHomeRegionID": None,
            "ResourceHostRegionIDs": None,
            "ResourceLifecycleStatus": None,
            "ResourceSecurityClassification": None,
            "Source": None,
            "SpatialLocation": {
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
                "AsIngestedCoordinates": {
                    "CoordinateReferenceSystemID": S(BENDINGCONTEXT, "namespace")
                                                   + K(SEP)
                                                   + S("data", "wellHeadProjected", "crsKey").optional(EMPTY)
                                                   >> F(
                        ConverterUtils.lookup, "reference-data--CoordinateReferenceSystem"),
                    "features": [
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
                                "type": If(OptionalS("data", "wellHeadProjected"), K("AnyCrsPoint")),
                            },
                            "type": If(OptionalS("data", "wellHeadProjected"), K("AnyCrsFeature")),
                        }
                    ],
                    "persistableReferenceCrs": If(OptionalS("data", "wellHeadProjected"), OptionalS("meta") >> F(ConverterUtils.find_in_meta, "kind", "CRS", "persistableReference")),
                    "persistableReferenceUnitZ": If(OptionalS("data", "wellHeadProjected"), OptionalS("data", "wellHeadProjected", "elevationFromMsl", "unitKey")),
                    "persistableReferenceVerticalCrs": If(OptionalS("data", "wellHeadProjected"), OptionalS("meta") >> F(ConverterUtils.find_in_meta, "kind", "CRS", "persistableReference")),
                    "type": If(OptionalS("data", "wellHeadProjected"), K("AnyCrsFeatureCollection")),
                    "VerticalCoordinateReferenceSystemID": None,
                },
                "SpatialGeometryTypeID": If(OptionalS("data", "wellHeadProjected"), S(BENDINGCONTEXT, "namespace") + K(":reference-data--SpatialGeometryType:Point:")),
                "SpatialParameterTypeID": None
            },
            "VersionCreationReason": None,
            "VerticalMeasurements": [
                {
                    "EffectiveDateTime": None,
                    "TerminationDateTime": None,
                    "VerticalCRSID": If(OptionalS("data", "elevationReference"),
                                        S(BENDINGCONTEXT, "namespace") + K(SEP) + (OptionalS("meta") >> F(ConverterUtils.find_in_meta, "kind", "CRS", "name")) >> F(ConverterUtils.lookup, "reference-data--CoordinateReferenceSystem")),
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
                    "VerticalMeasurement": OptionalS("data", "wellHeadElevation", "value"),
                    "VerticalMeasurementID": If(OptionalS("data", "wellHeadElevation"), K("Well Head Elevation")),
                    "VerticalMeasurementPathID": If(OptionalS("data", "wellHeadElevation"), S(BENDINGCONTEXT, "namespace")
                                                    + K(":reference-data--VerticalMeasurementPath:ELEV:")),
                    "VerticalMeasurementUnitOfMeasureID": S(
                        BENDINGCONTEXT, "namespace"
                    )
                                                          + K(SEP)
                                                          + S("data", "wellHeadElevation", "unitKey").optional(EMPTY)
                                                          >> F(ConverterUtils.lookup, "reference-data--UnitOfMeasure"),
                },
                {
                    "VerticalMeasurement": OptionalS(
                        "data", "waterDepth", "value"
                    ),
                    "VerticalMeasurementID": If(OptionalS("data", "waterDepth"), K("Water Depth")),
                    "VerticalMeasurementPathID": If(OptionalS("data", "waterDepth"),
                                                    S(BENDINGCONTEXT, "namespace")
                                                    + K(":reference-data--VerticalMeasurementPath:ELEV:")),
                    "VerticalMeasurementUnitOfMeasureID": S(
                        BENDINGCONTEXT, "namespace"
                    )
                                                          + K(SEP)
                                                          + S("data", "waterDepth", "unitKey").optional(EMPTY)
                                                          >> F(ConverterUtils.lookup, "reference-data--UnitOfMeasure"),
                },
                {
                    "VerticalMeasurement": OptionalS(
                        "data", "groundElevation", "value"
                    ),
                    "VerticalMeasurementID": If(OptionalS("data", "groundElevation"), K("Ground Elevation")),
                    "VerticalMeasurementPathID": If(OptionalS("data", "groundElevation"),
                                                    S(BENDINGCONTEXT, "namespace")
                                                    + K(":reference-data--VerticalMeasurementPath:ELEV:")),
                    "VerticalMeasurementUnitOfMeasureID": S(
                        BENDINGCONTEXT, "namespace"
                    )
                                                          + K(SEP)
                                                          + S("data", "groundElevation", "unitKey").optional(EMPTY)
                                                          >> F(ConverterUtils.lookup, "reference-data--UnitOfMeasure"),
                },
            ],
        }
    }

    @classmethod
    def convert_delfi_to_osdu(cls, delfi_dict: dict, context: dict) -> dict:
        """
        :param delfi_dict:
        :param context: the context must contains at least namespace variable corresponding to the authority
        :return:
        """
        delfi_dict = ConverterUtils.remove_none_from_dict(delfi_dict)
        # inject context in input dict, to make it available easily during bending
        delfi_dict[BENDINGCONTEXT] = context
        res = bend(cls.WELL_WKS_OSDU_MAPPING, delfi_dict)
        res = ConverterUtils.remove_none(res)
        return res