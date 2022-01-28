import pytest
from hypothesis import given, settings, Verbosity
from hypothesis import strategies as st
from pydantic import ValidationError

import app.model.model_curated as model


@given(tag=st.from_type(model.Tags))
@settings(verbosity=Verbosity.verbose)
def test_tags_dict_init_symmetric(tag):
    """dict/init symmetry for Tags model"""
    assert model.Tags(**tag.dict()) == tag


@given(ddms_basemodel=st.from_type(model.DDMSBaseModel))
@settings(verbosity=Verbosity.verbose)
def test_ddms_base_model_forbids_extra(ddms_basemodel):
    """dict/init symmetry for DDMSBaseModel model"""
    with pytest.raises(ValidationError):
        model.DDMSBaseModel(
            **{**ddms_basemodel.dict(), "another_key": "the other value"}
        )


@given(ddms_basemodel_with_extra=st.from_type(model.DDMSBaseModelWithExtra))
@settings(verbosity=Verbosity.verbose)
def test_ddms_base_model_with_extra_allows_extra(ddms_basemodel_with_extra):
    """dict/init symmetry for DDMSBaseModel model"""

    instance = model.DDMSBaseModelWithExtra(
        **{**ddms_basemodel_with_extra.dict(), "another_key": "the other value"}
    )
    assert instance.another_key == "the other value"
