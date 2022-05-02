import fractions
import typing
from collections import deque
from datetime import timedelta

import pydantic
from string import printable

import pytest
from hypothesis import given, example, settings, Verbosity, HealthCheck
from hypothesis import strategies as st
from pydantic import ValidationError

import app.model.model_curated as model

# need to import all data fixtures as we use them in decorators here
from app.model.model_utils import from_record, to_record
from ..data import *
from ..data.model_examples import load_model_example_file_contents


# typing utils
def is_union_hint(hint):
    return getattr(hint, "__origin__", None) is typing.Union


def is_list_hint(hint):
    return getattr(hint, "__origin__", None) is list


def is_optional_hint(hint):
    return is_union_hint(hint) and type(None) in hint.__args__


# useful strategies
def everything_except(*excluded_types):
    """Strategy to generate anything from type except excluded_types
    Ref: https://hypothesis.readthedocs.io/en/latest/data.html#hypothesis.strategies.from_type
    """

    def isinstance_check_hint(
        inst: typing.Any, type_hints: typing.Iterable[typing.Type]
    ) -> typing.Optional[typing.Type]:
        """ad-hock method to find the actual runtime type we can check for, using isinstance with a type hint.
        This cannot be perfect, nor generalizable, but we can come up with something useful enough for our specific usecase.

        It returns the **first** type hint that isinstance() deemed valid for inst, or None otherwise.
        It should except for any unsupported hint.
        """
        for hint in type_hints:

            # skipping type or it would result in a useless strategy
            # we need it to be explicit, because type(type) == type and it would match the next condition
            if hint is type:
                pass

            # if it is a specific type from pydantic
            elif getattr(hint, "__name__", None) in dir(pydantic.types):
                # TODO: this can be refined to improve validation checks of pydantic types
                # check the type hierarchy for the fist match found
                instance_of = isinstance_check_hint(inst, hint.mro()[1:])
                return instance_of

            # hint is an actual runtime datatype, we can check for it
            elif type(hint) == type:
                if isinstance(inst, hint):
                    instance_of = hint
                    return instance_of

            # same check as in pydantic core.py::_from_type for Union
            elif is_union_hint(hint):
                # recurse nested types while flattening the list
                instance_of = isinstance_check_hint(inst, hint.__args__)
                return instance_of

            # we can check for a list immediately
            elif is_list_hint(hint):
                # Ref: https://pydantic-docs.helpmanual.io/usage/types/#standard-library-types
                if isinstance(inst, (list, tuple, set, frozenset, deque)):
                    # make sure we check all elements of the list
                    if all(
                        isinstance_check_hint(inst_elem, hint.__args__)
                        for inst_elem in inst
                    ):
                        instance_of = hint
                        return instance_of

            else:
                raise NotImplemented(
                    f"isinstance_check_hint not implemented for {hint}"
                )

    return (
        st.from_type(type).flatmap(st.from_type)
        # filter out the instance of excluded_types that can be identified
        # meaning we let through only what does not seem to be an instance of any one of the excluded_types
        .filter(lambda x: isinstance_check_hint(x, excluded_types) is None)
    )


# Ref: https://github.com/samuelcolvin/pydantic/issues/3757
# fix pydantic strategy
json_strategy = st.recursive(
    st.none() | st.booleans() | st.floats() | st.text(printable),
    lambda children: st.lists(children, max_size=5)
    | st.dictionaries(st.text(printable), children, max_size=5),
    max_leaves=20,
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
        properties=st.dictionaries(
            keys=st.text(printable), values=json_strategy, max_size=5
        ),
        type=st.from_type(geojson_feature_type_hints["type"]),
    ),
)

geojson_feature_collection_type_hints = typing.get_type_hints(
    model.GeoJsonFeatureCollection
)
st.register_type_strategy(
    model.GeoJsonFeatureCollection,
    st.builds(
        model.GeoJsonFeatureCollection,
        bbox=st.from_type(geojson_feature_collection_type_hints["bbox"]),
        features=st.lists(st.from_type(model.GeoJsonFeature), max_size=5),
        type=st.from_type(geojson_feature_collection_type_hints["type"]),
    ),
)


def dict_strategy(model_class):
    return st.fixed_dictionaries(
        mapping={
            f: st.from_type(th)
            for f, th in typing.get_type_hints(model_class).items()
            if not is_optional_hint(th)
        },
        optional={
            f: st.from_type(th)
            for f, th in typing.get_type_hints(model_class).items()
            if is_optional_hint(th)
        },
    )


def adverse_dict_strategy(model_class):
    return st.fixed_dictionaries(
        mapping={
            f: everything_except(th)
            for f, th in typing.get_type_hints(model_class).items()
            if not is_optional_hint(th)
        },
        optional={
            f: everything_except(th)
            for f, th in typing.get_type_hints(model_class).items()
            if is_optional_hint(th)
        },
    ).filter(
        lambda d: len(d) != 0
    )  # empty dict is possible, but can be validated


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


@given(kind=st.from_type(model.Kind))
def test_kind_dict_init_symmetric(kind):
    """.value/init symmetry for Kind enum"""
    assert model.Kind(kind.value) == kind


@given(meta_item=st.from_type(model.MetaItem))
def test_meta_item_dict_init_symmetric(meta_item):
    """tests dict/init symmetry for MetaItem model"""
    assert model.MetaItem(**meta_item.dict()) == meta_item


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


@given(dipset_relationships_instance=st.from_type(model.dipsetrelationships))
def test_dipset_relationships_dict_init_symmetric(dipset_relationships_instance):
    """tests dict/init symmetry for dipsetrelationships model"""
    assert (
        model.dipsetrelationships(**dipset_relationships_instance.dict())
        == dipset_relationships_instance
    )


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


@pytest.mark.parametrize(
    "named_property_dict",
    [
        {"value": None},
        {"value": 42},  # behaviour here is still non-deterministic with smart_unions
        # to illustrate, add "import requests" in model_curated.py
        {"value": "42"},
        {"value": 42.0},
        {"value": "42.0"},
        {"value": "1.23456789"},
        {"value": "Lorem Ipsum"},
    ],
)
def test_named_property_dict_maybe_coerce_value_to_float(named_property_dict):
    """tests dict/init symmetry for namedProperty model"""
    original_value_type = type(named_property_dict["value"])
    named_property = model.namedProperty(**named_property_dict)

    # pydantic 1.8 with default union behavior:
    # when creating the instance, the value is coerced to one (non-deterministic) of the union type.
    # In our specific usecase it should be float where possible:
    # assert isinstance(named_property.value, float)
    # assert isinstance(named_property.dict()["value"], float)

    # pydantic 1.9 with smart union:
    # named_property.value depends on what the original data was
    # but can be implicitly coerced (non-deterministically) if the type is not strict.
    # For instance implicit conversion from int to float might occur if int is not in the Union args...
    hints = typing.get_type_hints(model.namedProperty)["value"].__args__
    expected_types = [h.mro()[-2] for h in hints]  # retrieve builtins python types
    if original_value_type in expected_types:
        expected_type = original_value_type
        assert type(named_property.value) == expected_type
        assert type(named_property.dict()["value"]) == expected_type
    else:
        # to detect unexpected behaviour.
        assert False, f"{original_value_type} not taken into account in test"


@given(named_property_dict=dict_strategy(model.namedProperty))
def test_named_property_init_dict_symmetric(named_property_dict):
    """tests for unexpected coercion for namedProperty model"""
    assert (
        model.namedProperty(**named_property_dict).dict(exclude_unset=True)
        == named_property_dict
    )


@pytest.mark.xfail(
    reason="fields are not strict, model accepts most values and then coerce them to string"
)
@given(not_named_property_dict=adverse_dict_strategy(model.namedProperty))
@settings(
    verbosity=Verbosity.normal,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_named_property_refuses_unexpected(not_named_property_dict):
    """tests for strictness and expected validation errors"""
    with pytest.raises(ValidationError) as exc:
        model.namedProperty(**not_named_property_dict)
    assert len(exc.value.errors()) > 0  # we have some error info


@given(logchannel_instance=st.from_type(model.logchannel))
def test_logchannel_dict_init_symmetric(logchannel_instance):
    """tests dict/init symmetry for logchannel model"""
    assert model.logchannel(**logchannel_instance.dict()) == logchannel_instance


@given(log_data=st.from_type(model.logData))
def test_log_data_dict_init_symmetric(log_data):
    """tests dict/init symmetry for logData model"""
    assert model.logData(**log_data.dict()) == log_data


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


@given(wellbore_instance=st.from_type(model.wellbore))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])  # , verbosity=Verbosity.verbose)
def test_wellbore_dict_init_symmetric(wellbore_instance):
    """tests dict/init symmetry for wellbore model"""
    assert from_record(model.wellbore, to_record(wellbore_instance)) == wellbore_instance


# module fixture to dynamically add hypothesis examples from model_examples data fixture
@pytest.fixture
def setup_wellbore_examples(wellbore_v3_record_list, wellbore_v2_record_list):
    for w in [from_record(model.wellbore, w3) for w3 in wellbore_v3_record_list] +\
             [from_record(model.wellbore, w2) for w2 in wellbore_v2_record_list]:
        example(wellbore_instance=w)(test_wellbore_dict_init_symmetric)
    return


@given(channel_instance=st.from_type(model.channel))
def test_channel_dict_init_symmetric(channel_instance):
    """tests dict/init symmetry for channel model"""
    assert model.channel(**channel_instance.dict()) == channel_instance


@given(log_set_data=st.from_type(model.logSetData))
def test_log_set_data_dict_init_symmetric(log_set_data):
    """tests dict/init symmetry for logSetData model"""
    assert model.logSetData(**log_set_data.dict()) == log_set_data


@given(dip_set_data=st.from_type(model.dipSetData))
def test_dip_set_data_dict_init_symmetric(dip_set_data):
    """tests dict/init symmetry for dipSetData model"""
    assert model.dipSetData(**dip_set_data.dict()) == dip_set_data


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


@given(trajectory_instance=st.from_type(model.trajectory))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])  # , verbosity=Verbosity.verbose)
def test_trajectory_dict_init_symmetric(trajectory_instance, setup_trajectory_examples):
    """tests dict/init symmetry for trajectory model"""
    assert from_record(model.trajectory, to_record(trajectory_instance)) == trajectory_instance


# module fixture to dynamically add hypothesis examples from model_examples data fixture
@pytest.fixture
def setup_trajectory_examples(trajectory_v3_record_list):
    for t in [from_record(model.trajectory, tt) for tt in trajectory_v3_record_list]:
        example(trajectory_instance=t)(test_trajectory_dict_init_symmetric)
    return


@given(marker_data=st.from_type(model.markerData))
def test_marker_data_dict_init_symmetric(marker_data):
    """tests dict/init symmetry for markerData model"""
    assert model.markerData(**marker_data.dict()) == marker_data


@given(marker_instance=st.from_type(model.marker))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])  # , verbosity=Verbosity.verbose)
def test_marker_dict_init_symmetric(marker_instance, setup_marker_examples):
    """tests dict/init symmetry for marker model"""
    assert from_record(model.marker, to_record(marker_instance)) == marker_instance


# module fixture to dynamically add hypothesis examples from model_examples data fixture
@pytest.fixture
def setup_marker_examples(marker_v2_record_list):
    for m in [from_record(model.marker, mm) for mm in marker_v2_record_list]:
        example(marker_instance=m)(test_marker_dict_init_symmetric)
    return


@given(well_data=st.from_type(model.wellData))
def test_well_data_dict_init_symmetric(well_data):
    """tests dict/init symmetry for wellData model"""
    assert model.wellData(**well_data.dict()) == well_data


@given(well_instance=st.from_type(model.well))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])  # , verbosity=Verbosity.verbose)
def test_well_dict_init_symmetric(well_instance, setup_well_examples):
    """tests dict/init symmetry for well model"""
    assert from_record(model.well, to_record(well_instance)) == well_instance


# module fixture to dynamically add hypothesis examples from model_examples data fixture
@pytest.fixture
def setup_well_examples(well_v3_record_list, well_v2_record_list):
    for w in [from_record(model.well, w3) for w3 in well_v3_record_list] +\
             [from_record(model.well, w2) for w2 in well_v2_record_list]:
        example(well_instance=w)(test_well_dict_init_symmetric)
    return
