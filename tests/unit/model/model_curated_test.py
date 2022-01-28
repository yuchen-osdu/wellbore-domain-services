import pytest
from hypothesis import given, settings, Verbosity
from hypothesis import strategies as st
from pydantic import ValidationError

import app.model.model_curated as model


@given(tag=st.from_type(model.Tags))
@settings(verbosity=Verbosity.verbose)
def test_tags_dict_init_symmetric(tag):
    """tests dict/init symmetry for Tags model"""
    assert model.Tags(**tag.dict()) == tag


@given(ddms_basemodel=st.from_type(model.DDMSBaseModel))
@settings(verbosity=Verbosity.verbose)
def test_ddms_base_model_forbids_extra(ddms_basemodel):
    """tests DDMSBaseModel forbids extra fields"""
    with pytest.raises(ValidationError):
        model.DDMSBaseModel(
            **{**ddms_basemodel.dict(), "another_key": "the other value"}
        )


@given(ddms_basemodel_with_extra=st.from_type(model.DDMSBaseModelWithExtra))
@settings(verbosity=Verbosity.verbose)
def test_ddms_base_model_with_extra_allows_extra(ddms_basemodel_with_extra):
    """tests DDMSBaseModel allows extra fields"""

    instance = model.DDMSBaseModelWithExtra(
        **{**ddms_basemodel_with_extra.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"


@given(link_list=st.from_type(model.LinkList))
@settings(verbosity=Verbosity.verbose)
def test_link_list_allows_extra(link_list):
    """tests LinkList allows extra fields"""

    instance = model.LinkList(**{**link_list.dict(), "another_key": "the other value"})
    assert instance.another_key == "the other value"


@given(kind=st.from_type(model.Kind))
@settings(verbosity=Verbosity.verbose)
def test_kind_dict_init_symmetric(kind):
    """.value/init symmetry for Kind enum"""
    assert model.Kind(kind.value) == kind


@given(meta_item=st.from_type(model.MetaItem))
@settings(verbosity=Verbosity.verbose)
def test_meta_item_dict_init_symmetric(meta_item):
    """tests dict/init symmetry for MetaItem model"""
    assert model.MetaItem(**meta_item.dict()) == meta_item


@given(meta_item=st.from_type(model.MetaItem))
@settings(verbosity=Verbosity.verbose)
def test_meta_item_allows_extra(meta_item):
    """tests MetaItem allows extra fields"""

    instance = model.MetaItem(**{**meta_item.dict(), "another_key": "the other value"})
    assert instance.another_key == "the other value"


@given(ddms_base_record=st.from_type(model.DDMSBaseRecord))
@settings(verbosity=Verbosity.verbose)
def test_ddms_base_record_dict_init_symmetric(ddms_base_record):
    """tests dict/init symmetry for MetaItem model"""
    assert model.DDMSBaseRecord(**ddms_base_record.dict()) == ddms_base_record


@given(point=st.from_type(model.Point))
@settings(verbosity=Verbosity.verbose)
def test_point_dict_init_symmetric(point):
    """tests dict/init symmetry for Point model"""
    assert model.Point(**point.dict()) == point


@given(legal=st.from_type(model.Legal))
@settings(verbosity=Verbosity.verbose)
def test_legal_dict_init_symmetric(legal):
    """tests dict/init symmetry for Legal model"""
    assert model.Legal(**legal.dict()) == legal


@given(tag_dictionary=st.from_type(model.TagDictionary))
@settings(verbosity=Verbosity.verbose)
def test_tag_dictionary_dict_init_symmetric(tag_dictionary):
    """tests dict/init symmetry for TagDictionary model"""
    assert model.TagDictionary(**tag_dictionary.dict()) == tag_dictionary


@given(tag_dictionary=st.from_type(model.TagDictionary))
@settings(verbosity=Verbosity.verbose)
def test_tag_dictionary_allows_extra(tag_dictionary):
    """tests TagDictionary allows extra fields"""

    instance = model.TagDictionary(
        **{**tag_dictionary.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"


@given(to_one_relationship=st.from_type(model.ToOneRelationship))
@settings(verbosity=Verbosity.verbose)
def test_to_one_relationship_dict_init_symmetric(to_one_relationship):
    """tests dict/init symmetry for ToOneRelationship model"""
    assert model.ToOneRelationship(**to_one_relationship.dict()) == to_one_relationship


@given(value_with_unit=st.from_type(model.ValueWithUnit))
@settings(verbosity=Verbosity.verbose)
def test_to_one_relationship_dict_init_symmetric(value_with_unit):
    """tests dict/init symmetry for ValueWithUnit model"""
    assert model.ValueWithUnit(**value_with_unit.dict()) == value_with_unit


@given(mtype=st.from_type(model.Type))
@settings(verbosity=Verbosity.verbose)
def test_type_value_init_symmetric(mtype):
    """.value/init symmetry for Type enum"""
    assert model.Type(mtype.value) == mtype


@given(mtype=st.from_type(model.Type_1))
@settings(verbosity=Verbosity.verbose)
def test_type1_value_init_symmetric(mtype):
    """.value/init symmetry for Type_1 enum"""
    assert model.Type_1(mtype.value) == mtype


@given(mtype=st.from_type(model.Type_2))
@settings(verbosity=Verbosity.verbose)
def test_type2_value_init_symmetric(mtype):
    """.value/init symmetry for Type_2 enum"""
    assert model.Type_2(mtype.value) == mtype


@given(mtype=st.from_type(model.Type_3))
@settings(verbosity=Verbosity.verbose)
def test_type3_value_init_symmetric(mtype):
    """.value/init symmetry for Type_3 enum"""
    assert model.Type_3(mtype.value) == mtype


@given(mtype=st.from_type(model.Type_4))
@settings(verbosity=Verbosity.verbose)
def test_type4_value_init_symmetric(mtype):
    """.value/init symmetry for Type_4 enum"""
    assert model.Type_4(mtype.value) == mtype


@given(geojson_multiline_string=st.from_type(model.GeoJsonMultiLineString))
@settings(verbosity=Verbosity.verbose)
def test_geojson_multiline_string_dict_init_symmetric(geojson_multiline_string):
    """tests dict/init symmetry for GeoJsonMultiLineString model"""
    assert (
        model.GeoJsonMultiLineString(**geojson_multiline_string.dict())
        == geojson_multiline_string
    )


@given(mtype=st.from_type(model.Type_5))
@settings(verbosity=Verbosity.verbose)
def test_type5_value_init_symmetric(mtype):
    """.value/init symmetry for Type_5 enum"""
    assert model.Type_5(mtype.value) == mtype


@given(mtype=st.from_type(model.Type_6))
@settings(verbosity=Verbosity.verbose)
def test_type6_value_init_symmetric(mtype):
    """.value/init symmetry for Type_6 enum"""
    assert model.Type_6(mtype.value) == mtype


@given(mtype=st.from_type(model.Type_7))
@settings(verbosity=Verbosity.verbose)
def test_type7_value_init_symmetric(mtype):
    """.value/init symmetry for Type_7 enum"""
    assert model.Type_7(mtype.value) == mtype


@given(geojson_point=st.from_type(model.GeoJsonPoint))
@settings(verbosity=Verbosity.verbose)
def test_geojson_point_dict_init_symmetric(geojson_point):
    """tests dict/init symmetry for GeoJsonPoint model"""
    assert model.GeoJsonPoint(**geojson_point.dict()) == geojson_point


@given(point_3d_non_geojson=st.from_type(model.Point3dNonGeoJson))
@settings(verbosity=Verbosity.verbose)
def test_geojson_point_dict_init_symmetric(point_3d_non_geojson):
    """tests dict/init symmetry for Point3dNonGeoJson model"""
    assert (
        model.Point3dNonGeoJson(**point_3d_non_geojson.dict()) == point_3d_non_geojson
    )


@given(mtype=st.from_type(model.Type_8))
@settings(verbosity=Verbosity.verbose)
def test_type8_value_init_symmetric(mtype):
    """.value/init symmetry for Type_8 enum"""
    assert model.Type_8(mtype.value) == mtype


@given(polygon=st.from_type(model.Polygon))
@settings(verbosity=Verbosity.verbose)
def test_polygon_dict_init_symmetric(polygon):
    """tests dict/init symmetry for Polygon model"""
    assert model.Polygon(**polygon.dict()) == polygon


@given(value_array_with_unit=st.from_type(model.valueArrayWithUnit))
@settings(verbosity=Verbosity.verbose)
def test_value_array_with_unit_dict_init_symmetric(value_array_with_unit):
    """tests dict/init symmetry for valueArrayWithUnit model"""
    assert (
        model.valueArrayWithUnit(**value_array_with_unit.dict())
        == value_array_with_unit
    )


@given(core_dl_geopoint_instance=st.from_type(model.core_dl_geopoint))
@settings(verbosity=Verbosity.verbose)
def test_core_dl_geopoint_dict_init_symmetric(core_dl_geopoint_instance):
    """tests dict/init symmetry for core_dl_geopoint model"""
    assert (
        model.core_dl_geopoint(**core_dl_geopoint_instance.dict())
        == core_dl_geopoint_instance
    )


@given(geographic_position=st.from_type(model.geographicPosition))
@settings(verbosity=Verbosity.verbose)
def test_geographic_position_dict_init_symmetric(geographic_position):
    """tests dict/init symmetry for geographicPosition model"""
    assert model.geographicPosition(**geographic_position.dict()) == geographic_position


@given(plss_location=st.from_type(model.PlssLocation))
@settings(verbosity=Verbosity.verbose)
def test_plss_location_dict_init_symmetric(plss_location):
    """tests dict/init symmetry for PlssLocation model"""
    assert model.PlssLocation(**plss_location.dict()) == plss_location


@given(projected_position=st.from_type(model.projectedPosition))
@settings(verbosity=Verbosity.verbose)
def test_projected_position_dict_init_symmetric(projected_position):
    """tests dict/init symmetry for projectedPosition model"""
    assert model.projectedPosition(**projected_position.dict()) == projected_position


@given(wellbore_relationships_instance=st.from_type(model.wellborerelationships))
@settings(verbosity=Verbosity.verbose)
def test_projected_position_dict_init_symmetric(wellbore_relationships_instance):
    """tests dict/init symmetry for wellborerelationships model"""
    assert (
        model.wellborerelationships(**wellbore_relationships_instance.dict())
        == wellbore_relationships_instance
    )


@given(projected_position=st.from_type(model.projectedPosition))
@settings(verbosity=Verbosity.verbose)
def test_projected_position_dict_init_symmetric(projected_position):
    """tests dict/init symmetry for projectedPosition model"""
    assert model.projectedPosition(**projected_position.dict()) == projected_position


@given(shape=st.from_type(model.Shape))
@settings(verbosity=Verbosity.verbose)
def test_shape_value_init_symmetric(shape):
    """.value/init symmetry for Shape enum"""
    assert model.Shape(shape.value) == shape


@given(wellbore_purpose=st.from_type(model.WellborePurpose))
@settings(verbosity=Verbosity.verbose)
def test_wellbore_purpose_value_init_symmetric(wellbore_purpose):
    """.value/init symmetry for WellborePurpose enum"""
    assert model.WellborePurpose(wellbore_purpose.value) == wellbore_purpose


@given(wellbore_status=st.from_type(model.WellboreStatus))
@settings(verbosity=Verbosity.verbose)
def test_wellbore_status_value_init_symmetric(wellbore_status):
    """.value/init symmetry for WellboreStatus enum"""
    assert model.WellboreStatus(wellbore_status.value) == wellbore_status


@given(wellbore_type=st.from_type(model.WellboreType))
@settings(verbosity=Verbosity.verbose)
def test_wellbore_type_value_init_symmetric(wellbore_type):
    """.value/init symmetry for WellboreType enum"""
    assert model.WellboreType(wellbore_type.value) == wellbore_type


@given(data_type=st.from_type(model.DataType))
@settings(verbosity=Verbosity.verbose)
def test_data_type_value_init_symmetric(data_type):
    """.value/init symmetry for DataType enum"""
    assert model.DataType(data_type.value) == data_type


@given(format=st.from_type(model.Format))
@settings(verbosity=Verbosity.verbose)
def test_format_value_init_symmetric(format):
    """.value/init symmetry for Format enum"""
    assert model.Format(format.value) == format
