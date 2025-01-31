import typing
from collections import deque

import pydantic
from string import printable

import pytest
from hypothesis import (
    given,
    example,
    settings,
    Verbosity,
    HealthCheck,
)
from hypothesis import strategies as st
from pydantic import ValidationError

import app.model.model_curated as model

# need to import all data fixtures as we use them in decorators here
from app.model.model_utils import from_record, to_record
from ..data import *


# pytestmark = [pytest.mark.slow, pytest.mark.hypothesis, pytest.mark.serial]
pytestmark = pytest.mark.skip  # skip these long tests since there are targeting deprecated V2 schemas


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
                raise NotImplementedError(
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


# register specific strategy for Legal
st.register_type_strategy(
    model.Legal,
    st.builds(
        model.Legal,
        legaltags=st.from_type(typing.Optional[List[str]]),
        otherRelevantDataCountries=st.from_type(typing.Optional[List[str]]),
        # status should be None, to allow round-trip to Record
        status=st.none(),
    ),
)


@given(legal=st.from_type(model.Legal))
def test_legal_dict_init_symmetric(legal):
    """tests dict/init symmetry for Legal model"""
    assert model.Legal(**legal.dict()) == legal


# register specific strategy for TagDictionary
st.register_type_strategy(
    model.TagDictionary,
    # TagDictionary should NOT be empty, to allow round-trip to Record
    st.builds(
        model.TagDictionary.parse_obj,
        st.fixed_dictionaries(
            {
                "viewers": st.lists(elements=st.from_type(str), max_size=2),
                "owners": st.lists(elements=st.from_type(str), max_size=2),
            }
        ),
    ),
)


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


@given(data_type=st.from_type(model.DataType))
def test_data_type_value_init_symmetric(data_type):
    """.value/init symmetry for DataType enum"""
    assert model.DataType(data_type.value) == data_type


@given(format=st.from_type(model.Format))
def test_format_value_init_symmetric(format):
    """.value/init symmetry for Format enum"""
    assert model.Format(format.value) == format


@given(dipset_relationships_instance=st.from_type(model.dipsetrelationships))
def test_dipset_relationships_dict_init_symmetric(dipset_relationships_instance):
    """tests dict/init symmetry for dipsetrelationships model"""
    assert (
        model.dipsetrelationships(**dipset_relationships_instance.dict())
        == dipset_relationships_instance
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


@given(dip_set_data=st.from_type(model.dipSetData))
def test_dip_set_data_dict_init_symmetric(dip_set_data):
    """tests dict/init symmetry for dipSetData model"""
    assert model.dipSetData(**dip_set_data.dict()) == dip_set_data


@given(dip_set_instance=st.from_type(model.dipset))
def test_dip_set_dict_init_symmetric(dip_set_instance):
    """tests dict/init symmetry for dipset model"""
    assert model.dipset(**dip_set_instance.dict()) == dip_set_instance
