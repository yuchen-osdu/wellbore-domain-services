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
    assert model.MetaItem(**ddms_base_record.dict()) == ddms_base_record
