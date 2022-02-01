import typing
from string import printable

import pytest
from hypothesis import given, example
from hypothesis import strategies as st
from pydantic import ValidationError

import app.model.model_curated as model

# Ref: https://github.com/samuelcolvin/pydantic/issues/3757
# fix pydantic strategy
json_strategy = st.recursive(
    st.none() | st.booleans() | st.floats() | st.text(printable),
    lambda children: st.lists(children, max_size=5)
    | st.dictionaries(st.text(printable), children, max_size=5),
    max_leaves=20
)

# From https://datatracker.ietf.org/doc/html/rfc7946
# A Feature object has a member with the name "properties".  The
#   value of the properties member is an object (any JSON object or a
#   JSON null value).
geojson_feature_type_hints = typing.get_type_hints(model.GeoJsonFeature)
st.register_type_strategy(
    model.GeoJsonFeature,
    st.builds(
        model.GeoJsonFeature,
        bbox=st.from_type(geojson_feature_type_hints["bbox"]),
        geometry=st.from_type(geojson_feature_type_hints["geometry"]),
        properties=st.dictionaries(keys=st.text(printable), values=json_strategy),
        type=st.from_type(geojson_feature_type_hints["type"]),
    ),
)


@given(tag=st.from_type(model.Tags))
def test_tags_dict_init_symmetric(tag):
    """tests dict/init symmetry for Tags model"""
    assert model.Tags(**tag.dict()) == tag


@given(ddms_basemodel=st.from_type(model.DDMSBaseModel))
def test_ddms_base_model_forbids_extra(ddms_basemodel):
    """tests DDMSBaseModel forbids extra fields"""
    with pytest.raises(ValidationError):
        model.DDMSBaseModel(
            **{**ddms_basemodel.dict(), "another_key": "the other value"}
        )


@given(ddms_basemodel_with_extra=st.from_type(model.DDMSBaseModelWithExtra))
def test_ddms_base_model_with_extra_allows_extra(ddms_basemodel_with_extra):
    """tests DDMSBaseModel allows extra fields"""

    instance = model.DDMSBaseModelWithExtra(
        **{**ddms_basemodel_with_extra.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"


@given(link_list=st.from_type(model.LinkList))
def test_link_list_allows_extra(link_list):
    """tests LinkList allows extra fields"""

    instance = model.LinkList(**{**link_list.dict(), "another_key": "the other value"})
    assert instance.another_key == "the other value"


@given(kind=st.from_type(model.Kind))
def test_kind_dict_init_symmetric(kind):
    """.value/init symmetry for Kind enum"""
    assert model.Kind(kind.value) == kind


@given(meta_item=st.from_type(model.MetaItem))
def test_meta_item_dict_init_symmetric(meta_item):
    """tests dict/init symmetry for MetaItem model"""
    assert model.MetaItem(**meta_item.dict()) == meta_item


@given(meta_item=st.from_type(model.MetaItem))
def test_meta_item_allows_extra(meta_item):
    """tests MetaItem allows extra fields"""

    instance = model.MetaItem(**{**meta_item.dict(), "another_key": "the other value"})
    assert instance.another_key == "the other value"


@given(ddms_base_record=st.from_type(model.DDMSBaseRecord))
def test_ddms_base_record_dict_init_symmetric(ddms_base_record):
    """tests dict/init symmetry for MetaItem model"""
    assert model.DDMSBaseRecord(**ddms_base_record.dict()) == ddms_base_record


@given(point=st.from_type(model.Point))
def test_point_dict_init_symmetric(point):
    """tests dict/init symmetry for Point model"""
    assert model.Point(**point.dict()) == point


@given(legal=st.from_type(model.Legal))
def test_legal_dict_init_symmetric(legal):
    """tests dict/init symmetry for Legal model"""
    assert model.Legal(**legal.dict()) == legal


@given(tag_dictionary=st.from_type(model.TagDictionary))
def test_tag_dictionary_dict_init_symmetric(tag_dictionary):
    """tests dict/init symmetry for TagDictionary model"""
    assert model.TagDictionary(**tag_dictionary.dict()) == tag_dictionary


@given(tag_dictionary=st.from_type(model.TagDictionary))
def test_tag_dictionary_allows_extra(tag_dictionary):
    """tests TagDictionary allows extra fields"""

    instance = model.TagDictionary(
        **{**tag_dictionary.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"


@given(to_one_relationship=st.from_type(model.ToOneRelationship))
def test_to_one_relationship_dict_init_symmetric(to_one_relationship):
    """tests dict/init symmetry for ToOneRelationship model"""
    assert model.ToOneRelationship(**to_one_relationship.dict()) == to_one_relationship


@given(value_with_unit=st.from_type(model.ValueWithUnit))
def test_to_one_relationship_dict_init_symmetric(value_with_unit):
    """tests dict/init symmetry for ValueWithUnit model"""
    assert model.ValueWithUnit(**value_with_unit.dict()) == value_with_unit


@given(mtype=st.from_type(model.Type))
def test_type_value_init_symmetric(mtype):
    """.value/init symmetry for Type enum"""
    assert model.Type(mtype.value) == mtype


@given(mtype=st.from_type(model.Type_1))
def test_type1_value_init_symmetric(mtype):
    """.value/init symmetry for Type_1 enum"""
    assert model.Type_1(mtype.value) == mtype


@given(mtype=st.from_type(model.Type_2))
def test_type2_value_init_symmetric(mtype):
    """.value/init symmetry for Type_2 enum"""
    assert model.Type_2(mtype.value) == mtype


@given(mtype=st.from_type(model.Type_3))
def test_type3_value_init_symmetric(mtype):
    """.value/init symmetry for Type_3 enum"""
    assert model.Type_3(mtype.value) == mtype


@given(mtype=st.from_type(model.Type_4))
def test_type4_value_init_symmetric(mtype):
    """.value/init symmetry for Type_4 enum"""
    assert model.Type_4(mtype.value) == mtype


@given(geojson_multiline_string=st.from_type(model.GeoJsonMultiLineString))
def test_geojson_multiline_string_dict_init_symmetric(geojson_multiline_string):
    """tests dict/init symmetry for GeoJsonMultiLineString model"""
    assert (
        model.GeoJsonMultiLineString(**geojson_multiline_string.dict())
        == geojson_multiline_string
    )


@given(mtype=st.from_type(model.Type_5))
def test_type5_value_init_symmetric(mtype):
    """.value/init symmetry for Type_5 enum"""
    assert model.Type_5(mtype.value) == mtype


@given(mtype=st.from_type(model.Type_6))
def test_type6_value_init_symmetric(mtype):
    """.value/init symmetry for Type_6 enum"""
    assert model.Type_6(mtype.value) == mtype


@given(mtype=st.from_type(model.Type_7))
def test_type7_value_init_symmetric(mtype):
    """.value/init symmetry for Type_7 enum"""
    assert model.Type_7(mtype.value) == mtype


@given(geojson_point=st.from_type(model.GeoJsonPoint))
def test_geojson_point_dict_init_symmetric(geojson_point):
    """tests dict/init symmetry for GeoJsonPoint model"""
    assert model.GeoJsonPoint(**geojson_point.dict()) == geojson_point


@given(point_3d_non_geojson=st.from_type(model.Point3dNonGeoJson))
def test_geojson_point_dict_init_symmetric(point_3d_non_geojson):
    """tests dict/init symmetry for Point3dNonGeoJson model"""
    assert (
        model.Point3dNonGeoJson(**point_3d_non_geojson.dict()) == point_3d_non_geojson
    )


@given(mtype=st.from_type(model.Type_8))
def test_type8_value_init_symmetric(mtype):
    """.value/init symmetry for Type_8 enum"""
    assert model.Type_8(mtype.value) == mtype


@given(polygon=st.from_type(model.Polygon))
def test_polygon_dict_init_symmetric(polygon):
    """tests dict/init symmetry for Polygon model"""
    assert model.Polygon(**polygon.dict()) == polygon


@given(value_array_with_unit=st.from_type(model.valueArrayWithUnit))
def test_value_array_with_unit_dict_init_symmetric(value_array_with_unit):
    """tests dict/init symmetry for valueArrayWithUnit model"""
    assert (
        model.valueArrayWithUnit(**value_array_with_unit.dict())
        == value_array_with_unit
    )


@given(core_dl_geopoint_instance=st.from_type(model.core_dl_geopoint))
def test_core_dl_geopoint_dict_init_symmetric(core_dl_geopoint_instance):
    """tests dict/init symmetry for core_dl_geopoint model"""
    assert (
        model.core_dl_geopoint(**core_dl_geopoint_instance.dict())
        == core_dl_geopoint_instance
    )


@given(geographic_position=st.from_type(model.geographicPosition))
def test_geographic_position_dict_init_symmetric(geographic_position):
    """tests dict/init symmetry for geographicPosition model"""
    assert model.geographicPosition(**geographic_position.dict()) == geographic_position


@given(plss_location=st.from_type(model.PlssLocation))
def test_plss_location_dict_init_symmetric(plss_location):
    """tests dict/init symmetry for PlssLocation model"""
    assert model.PlssLocation(**plss_location.dict()) == plss_location


@given(projected_position=st.from_type(model.projectedPosition))
def test_projected_position_dict_init_symmetric(projected_position):
    """tests dict/init symmetry for projectedPosition model"""
    assert model.projectedPosition(**projected_position.dict()) == projected_position


@given(wellbore_relationships_instance=st.from_type(model.wellborerelationships))
def test_projected_position_dict_init_symmetric(wellbore_relationships_instance):
    """tests dict/init symmetry for wellborerelationships model"""
    assert (
        model.wellborerelationships(**wellbore_relationships_instance.dict())
        == wellbore_relationships_instance
    )


@given(projected_position=st.from_type(model.projectedPosition))
def test_projected_position_dict_init_symmetric(projected_position):
    """tests dict/init symmetry for projectedPosition model"""
    assert model.projectedPosition(**projected_position.dict()) == projected_position


@given(shape=st.from_type(model.Shape))
def test_shape_value_init_symmetric(shape):
    """.value/init symmetry for Shape enum"""
    assert model.Shape(shape.value) == shape


@given(wellbore_purpose=st.from_type(model.WellborePurpose))
def test_wellbore_purpose_value_init_symmetric(wellbore_purpose):
    """.value/init symmetry for WellborePurpose enum"""
    assert model.WellborePurpose(wellbore_purpose.value) == wellbore_purpose


@given(wellbore_status=st.from_type(model.WellboreStatus))
def test_wellbore_status_value_init_symmetric(wellbore_status):
    """.value/init symmetry for WellboreStatus enum"""
    assert model.WellboreStatus(wellbore_status.value) == wellbore_status


@given(wellbore_type=st.from_type(model.WellboreType))
def test_wellbore_type_value_init_symmetric(wellbore_type):
    """.value/init symmetry for WellboreType enum"""
    assert model.WellboreType(wellbore_type.value) == wellbore_type


@given(data_type=st.from_type(model.DataType))
def test_data_type_value_init_symmetric(data_type):
    """.value/init symmetry for DataType enum"""
    assert model.DataType(data_type.value) == data_type


@given(format=st.from_type(model.Format))
def test_format_value_init_symmetric(format):
    """.value/init symmetry for Format enum"""
    assert model.Format(format.value) == format


@given(logset_relationships_instance=st.from_type(model.logsetrelationships))
def test_logset_relationships_dict_init_symmetric(logset_relationships_instance):
    """tests dict/init symmetry for logsetrelationships model"""
    assert (
        model.logsetrelationships(**logset_relationships_instance.dict())
        == logset_relationships_instance
    )


@given(logset_relationships_instance=st.from_type(model.logsetrelationships))
def test_logset_relationships_allows_extra(logset_relationships_instance):
    """tests logsetrelationships allows extra fields"""

    instance = model.logsetrelationships(
        **{**logset_relationships_instance.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"


@given(dipset_relationships_instance=st.from_type(model.dipsetrelationships))
def test_dipset_relationships_dict_init_symmetric(dipset_relationships_instance):
    """tests dict/init symmetry for dipsetrelationships model"""
    assert (
        model.dipsetrelationships(**dipset_relationships_instance.dict())
        == dipset_relationships_instance
    )


@given(dipset_relationships_instance=st.from_type(model.dipsetrelationships))
def test_dipset_relationships_allows_extra(dipset_relationships_instance):
    """tests dipsetrelationships allows extra fields"""

    instance = model.dipsetrelationships(
        **{**dipset_relationships_instance.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"


@given(data_type=st.from_type(model.DataType_1))
def test_data_type_1_value_init_symmetric(data_type):
    """.value/init symmetry for DataType_1 enum"""
    assert model.DataType_1(data_type.value) == data_type


@given(format=st.from_type(model.Format_1))
def test_format_1_value_init_symmetric(format):
    """.value/init symmetry for Format_1 enum"""
    assert model.Format_1(format.value) == format


@given(trajectory_channel_instance=st.from_type(model.trajectorychannel))
def test_trajectory_channel_dict_init_symmetric(trajectory_channel_instance):
    """tests dict/init symmetry for trajectorychannel model"""
    assert (
        model.trajectorychannel(**trajectory_channel_instance.dict())
        == trajectory_channel_instance
    )


@given(trajectory_relationships_instance=st.from_type(model.trajectoryrelationships))
def test_trajectory_relationships_dict_init_symmetric(
    trajectory_relationships_instance,
):
    """tests dict/init symmetry for trajectoryrelationships model"""
    assert (
        model.trajectoryrelationships(**trajectory_relationships_instance.dict())
        == trajectory_relationships_instance
    )


@given(trajectory_relationships_instance=st.from_type(model.trajectoryrelationships))
def test_trajectory_relationships_allows_extra(trajectory_relationships_instance):
    """tests trajectoryrelationships allows extra fields"""

    instance = model.dipsetrelationships(
        **{**trajectory_relationships_instance.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"


@given(wgs84_position=st.from_type(model.wgs84Position))
def test_wgs84_position_dict_init_symmetric(wgs84_position):
    """tests dict/init symmetry for wgs84Position model"""
    assert model.wgs84Position(**wgs84_position.dict()) == wgs84_position


@given(marker_relationships_instance=st.from_type(model.markerrelationships))
def test_marker_relationships_dict_init_symmetric(marker_relationships_instance):
    """tests dict/init symmetry for markerrelationships model"""
    assert (
        model.markerrelationships(**marker_relationships_instance.dict())
        == marker_relationships_instance
    )


@given(marker_relationships_instance=st.from_type(model.markerrelationships))
def test_marker_relationships_allows_extra(marker_relationships_instance):
    """tests markerrelationships allows extra fields"""

    instance = model.markerrelationships(
        **{**marker_relationships_instance.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"


@given(data_type_2=st.from_type(model.DataType_2))
def test_data_type_2_value_init_symmetric(data_type_2):
    """.value/init symmetry for DataType_2 enum"""
    assert model.DataType_2(data_type_2.value) == data_type_2


@given(format_2=st.from_type(model.Format_2))
def test_format_2_value_init_symmetric(format_2):
    """.value/init symmetry for Format_2 enum"""
    assert model.Format_2(format_2.value) == format_2


@given(history_record=st.from_type(model.historyRecord))
def test_history_record_dict_init_symmetric(history_record):
    """tests dict/init symmetry for historyRecord model"""
    assert model.historyRecord(**history_record.dict()) == history_record


@given(reference_type=st.from_type(model.ReferenceType))
def test_reference_type_value_init_symmetric(reference_type):
    """.value/init symmetry for ReferenceType enum"""
    assert model.ReferenceType(reference_type.value) == reference_type


@given(log_relationships_instance=st.from_type(model.logRelationships))
def test_log_relationships_dict_init_symmetric(log_relationships_instance):
    """tests dict/init symmetry for logRelationships model"""
    assert (
        model.logRelationships(**log_relationships_instance.dict())
        == log_relationships_instance
    )


@given(log_relationships_instance=st.from_type(model.logRelationships))
def test_log_relationships_allows_extra(log_relationships_instance):
    """tests logRelationships allows extra fields"""

    instance = model.logRelationships(
        **{**log_relationships_instance.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"


@given(basin_context=st.from_type(model.basinContext))
def test_basin_context_dict_init_symmetric(basin_context):
    """tests dict/init symmetry for basinContext model"""
    assert model.basinContext(**basin_context.dict()) == basin_context


@given(well_relationships_instance=st.from_type(model.wellrelationships))
def test_well_relationships_dict_init_symmetric(well_relationships_instance):
    """tests dict/init symmetry for wellrelationships model"""
    assert (
        model.wellrelationships(**well_relationships_instance.dict())
        == well_relationships_instance
    )


@given(well_relationships_instance=st.from_type(model.wellrelationships))
def test_well_relationships_allows_extra(well_relationships_instance):
    """tests wellrelationships allows extra fields"""

    instance = model.wellrelationships(
        **{**well_relationships_instance.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"


@given(direction_well=st.from_type(model.DirectionWell))
def test_direction_well_value_init_symmetric(direction_well):
    """.value/init symmetry for DirectionWell enum"""
    assert model.DirectionWell(direction_well.value) == direction_well


@given(fluid_well=st.from_type(model.FluidWell))
def test_fluid_well_value_init_symmetric(fluid_well):
    """.value/init symmetry for FluidWell enum"""
    assert model.FluidWell(fluid_well.value) == fluid_well


@given(well_location_type=st.from_type(model.WellLocationType))
def test_well_location_type_value_init_symmetric(well_location_type):
    """.value/init symmetry for WellLocationType enum"""
    assert model.WellLocationType(well_location_type.value) == well_location_type


@given(well_purpose=st.from_type(model.WellPurpose))
def test_well_purpose_value_init_symmetric(well_purpose):
    """.value/init symmetry for WellPurpose enum"""
    assert model.WellPurpose(well_purpose.value) == well_purpose


@given(well_status=st.from_type(model.WellStatus))
def test_well_status_value_init_symmetric(well_status):
    """.value/init symmetry for WellStatus enum"""
    assert model.WellStatus(well_status.value) == well_status


@given(well_type=st.from_type(model.WellType))
def test_well_type_value_init_symmetric(well_type):
    """.value/init symmetry for WellType enum"""
    assert model.WellType(well_type.value) == well_type


@given(by_bounding_box=st.from_type(model.ByBoundingBox))
def test_by_bounding_box_dict_init_symmetric(by_bounding_box):
    """tests dict/init symmetry for ByBoundingBox model"""
    assert model.ByBoundingBox(**by_bounding_box.dict()) == by_bounding_box


@given(by_distance=st.from_type(model.ByDistance))
def test_by_distance_dict_init_symmetric(by_distance):
    """tests dict/init symmetry for ByDistance model"""
    assert model.ByDistance(**by_distance.dict()) == by_distance


@given(by_geo_polygon=st.from_type(model.ByGeoPolygon))
def test_by_geo_polygon_dict_init_symmetric(by_geo_polygon):
    """tests dict/init symmetry for ByGeoPolygon model"""
    assert model.ByGeoPolygon(**by_geo_polygon.dict()) == by_geo_polygon


@given(simple_elevation_reference=st.from_type(model.SimpleElevationReference))
def test_simple_elevation_reference_dict_init_symmetric(simple_elevation_reference):
    """tests dict/init symmetry for SimpleElevationReference model"""
    assert (
        model.SimpleElevationReference(**simple_elevation_reference.dict())
        == simple_elevation_reference
    )


@given(geo_json_line_string=st.from_type(model.GeoJsonLineString))
def test_geo_json_line_string_dict_init_symmetric(geo_json_line_string):
    """tests dict/init symmetry for GeoJsonLineString model"""
    assert (
        model.GeoJsonLineString(**geo_json_line_string.dict()) == geo_json_line_string
    )


@given(geo_json_multi_point=st.from_type(model.GeoJsonMultiPoint))
def test_geo_json_multi_point_dict_init_symmetric(geo_json_multi_point):
    """tests dict/init symmetry for GeoJsonMultiPoint model"""
    assert (
        model.GeoJsonMultiPoint(**geo_json_multi_point.dict()) == geo_json_multi_point
    )


@given(geo_json_multi_polygon=st.from_type(model.GeoJsonMultiPolygon))
def test_geo_json_multi_polygon_dict_init_symmetric(geo_json_multi_polygon):
    """tests dict/init symmetry for GeoJsonMultiPolygon model"""
    assert (
        model.GeoJsonMultiPolygon(**geo_json_multi_polygon.dict())
        == geo_json_multi_polygon
    )


@given(named_property=st.from_type(model.namedProperty))
def test_named_property_dict_init_symmetric(named_property):
    """tests dict/init symmetry for namedProperty model"""
    assert model.namedProperty(**named_property.dict()) == named_property


@given(logchannel_instance=st.from_type(model.logchannel))
def test_logchannel_dict_init_symmetric(logchannel_instance):
    """tests dict/init symmetry for logchannel model"""
    assert model.logchannel(**logchannel_instance.dict()) == logchannel_instance


@given(log_data=st.from_type(model.logData))
def test_log_data_dict_init_symmetric(log_data):
    """tests dict/init symmetry for logData model"""
    assert model.logData(**log_data.dict()) == log_data


@given(log_data=st.from_type(model.logData))
def test_log_data_allows_extra(log_data):
    """tests logData allows extra fields"""

    instance = model.logData(**{**log_data.dict(), "another_key": "the other value"})
    assert instance.another_key == "the other value"


@given(log_instance=st.from_type(model.log))
def test_log_dict_init_symmetric(log_instance):
    """tests dict/init symmetry for log model"""
    assert model.log(**log_instance.dict()) == log_instance


@given(spatial_filter=st.from_type(model.SpatialFilter))
def test_spatial_filter_dict_init_symmetric(spatial_filter):
    """tests dict/init symmetry for SpatialFilter model"""
    assert model.SpatialFilter(**spatial_filter.dict()) == spatial_filter


@given(geometry_item=st.from_type(model.geometryItem))
def test_geometry_item_dict_init_symmetric(geometry_item):
    """tests dict/init symmetry for geometryItem model"""
    assert model.geometryItem(**geometry_item.dict()) == geometry_item


@given(geojson_feature=st.from_type(model.GeoJsonFeature))
def test_geojson_feature_dict_init_symmetric(geojson_feature):
    """tests dict/init symmetry for GeoJsonFeature model"""
    assert model.GeoJsonFeature(**geojson_feature.dict()) == geojson_feature


@given(geojson_feature_collection=st.from_type(model.GeoJsonFeatureCollection))
def test_geojson_feature_collection_dict_init_symmetric(geojson_feature_collection):
    """tests dict/init symmetry for GeoJsonFeatureCollection model"""
    assert (
        model.GeoJsonFeatureCollection(**geojson_feature_collection.dict())
        == geojson_feature_collection
    )


@given(wellbore_data=st.from_type(model.wellboreData))
def test_wellbore_data_dict_init_symmetric(wellbore_data):
    """tests dict/init symmetry for wellboreData model"""
    assert model.wellboreData(**wellbore_data.dict()) == wellbore_data


@given(wellbore_data=st.from_type(model.wellboreData))
def test_wellbore_data_allows_extra(wellbore_data):
    """tests wellboreData allows extra fields"""

    instance = model.wellboreData(
        **{**wellbore_data.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"


@given(wellbore_instance=st.from_type(model.wellbore))
def test_wellbore_dict_init_symmetric(wellbore_instance):
    """tests dict/init symmetry for wellbore model"""
    assert model.wellbore(**wellbore_instance.dict()) == wellbore_instance


@given(channel_instance=st.from_type(model.channel))
def test_channel_dict_init_symmetric(channel_instance):
    """tests dict/init symmetry for channel model"""
    assert model.channel(**channel_instance.dict()) == channel_instance


@given(log_set_data=st.from_type(model.logSetData))
def test_log_set_data_dict_init_symmetric(log_set_data):
    """tests dict/init symmetry for logSetData model"""
    assert model.logSetData(**log_set_data.dict()) == log_set_data


@given(log_set_data=st.from_type(model.logSetData))
def test_log_set_data_allows_extra(log_set_data):
    """tests logSetData allows extra fields"""

    instance = model.logSetData(
        **{**log_set_data.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"


@given(dip_set_data=st.from_type(model.dipSetData))
def test_dip_set_data_dict_init_symmetric(dip_set_data):
    """tests dict/init symmetry for dipSetData model"""
    assert model.dipSetData(**dip_set_data.dict()) == dip_set_data


@given(dip_set_data=st.from_type(model.dipSetData))
def test_dip_set_data_allows_extra(dip_set_data):
    """tests dipSetData allows extra fields"""

    instance = model.dipSetData(
        **{**dip_set_data.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"


@given(log_set_instance=st.from_type(model.logset))
def test_log_set_dict_init_symmetric(log_set_instance):
    """tests dict/init symmetry for logset model"""
    assert model.logset(**log_set_instance.dict()) == log_set_instance


@given(dip_set_instance=st.from_type(model.dipset))
def test_dip_set_dict_init_symmetric(dip_set_instance):
    """tests dict/init symmetry for dipset model"""
    assert model.dipset(**dip_set_instance.dict()) == dip_set_instance


@given(trajectory_data=st.from_type(model.trajectoryData))
def test_trajectory_data_dict_init_symmetric(trajectory_data):
    """tests dict/init symmetry for trajectoryData model"""
    assert model.trajectoryData(**trajectory_data.dict()) == trajectory_data


@given(trajectory_data=st.from_type(model.trajectoryData))
def test_trajectory_data_allows_extra(trajectory_data):
    """tests trajectoryData allows extra fields"""

    instance = model.trajectoryData(
        **{**trajectory_data.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"


@given(trajectory_instance=st.from_type(model.trajectory))
def test_trajectory_dict_init_symmetric(trajectory_instance):
    """tests dict/init symmetry for trajectory model"""
    assert model.trajectory(**trajectory_instance.dict()) == trajectory_instance


@given(marker_data=st.from_type(model.markerData))
def test_marker_data_dict_init_symmetric(marker_data):
    """tests dict/init symmetry for markerData model"""
    assert model.markerData(**marker_data.dict()) == marker_data


@given(marker_data=st.from_type(model.markerData))
def test_marker_data_allows_extra(marker_data):
    """tests markerData allows extra fields"""

    instance = model.markerData(
        **{**marker_data.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"


@given(marker_instance=st.from_type(model.marker))
def test_marker_dict_init_symmetric(marker_instance):
    """tests dict/init symmetry for marker model"""
    assert model.marker(**marker_instance.dict()) == marker_instance


@given(well_data=st.from_type(model.wellData))
def test_well_data_dict_init_symmetric(well_data):
    """tests dict/init symmetry for wellData model"""
    assert model.wellData(**well_data.dict()) == well_data


@given(well_data=st.from_type(model.wellData))
def test_well_data_allows_extra(well_data):
    """tests wellData allows extra fields"""

    instance = model.wellData(
        **{**well_data.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"


@given(well_instance=st.from_type(model.well))
def test_marker_dict_init_symmetric(well_instance):
    """tests dict/init symmetry for well model"""
    assert model.well(**well_instance.dict()) == well_instance
