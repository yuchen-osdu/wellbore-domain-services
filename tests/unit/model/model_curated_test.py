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
