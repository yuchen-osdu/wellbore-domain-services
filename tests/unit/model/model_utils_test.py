import pydantic

import json

import pydantic
import pytest
from odes_storage.models import Record
from pydantic import Extra, ValidationError

import app.model.model_curated as models
import app.model.model_utils as utils


@pytest.mark.parametrize("ddms_model", [models.log,
                                        models.logset,
                                        models.well,
                                        models.wellbore,
                                        models.trajectory,
                                        models.marker,
                                        models.dipset])
def test_list_record_models(ddms_model):
    # the main goal here is to spot any new record model
    # If OK and a valid 'record' kind model, add it to the expected list
    # otherwise the list function must be reviewed
    assert 'data' in ddms_model.__fields__.keys()
    assert Extra.forbid == ddms_model.Config.extra
    assert Extra.allow == ddms_model.__fields__['data'].type_.__config__.extra


def test_check_record_model_base_config():
    # this the base config make sure that this has not changed
    assert Record.__config__.extra == Extra.ignore


wellbore_str = """
{
    "kind": "opendes:osdu:wellbore:2.0.0",
    "acl": {
        "viewers": ["data.default.viewers@opendes.p4d.cloud.slb-ds.com"],
        "owners": ["data.default.owners@opendes.p4d.cloud.slb-ds.com"]
    },
    "legal": {
        "legaltags": ["opendes-public-usa-dataset-1"],
        "otherRelevantDataCountries": ["US"]
    },
    "data": {
        "country": "FR",
        "name": "toto",
        "airGap": {
            "unitKey": "m",
            "value": 123
        },
        "xxx_color": "#56AF8E"
    }
}
"""

# This object should be serialized correctly by Record model
# And also by wdms models (log, logset, ...)
wellbore_str_with_meta_valid_ddms = """
{
   "kind":"opendes:osdu:wellbore:2.0.0",
   "acl":{
      "viewers":[
         "data.default.viewers@opendes.p4d.cloud.slb-ds.com"
      ],
      "owners":[
         "data.default.owners@opendes.p4d.cloud.slb-ds.com"
      ]
   },
   "legal":{
      "legaltags":[
         "opendes-public-usa-dataset-1"
      ],
      "otherRelevantDataCountries":[
         "US"
      ]
   },
   "data":{
      "country":"FR",
      "name":"toto",
      "airGap":{
         "unitKey":"m",
         "value":123
      },
      "md":{
         "unitKey":"some unit",
         "value":12.0
      },
      "xxx_color":"#56AF8E"
   },
   "meta":[
      {
         "name":"Some name",
         "kind":"CRS",
         "persistableReference":"ref",
         "propertyNames":[
            "name"
         ],
         "propertyValues":[
            "value"
         ],
         "uncertainty":0.9
      }
   ]
}
"""

# This object should be serialized correctly by Record model
# But not by wdms models (log, logset, ...)
wellbore_str_with_meta_not_valid_ddms = """
{
    "kind": "opendes:osdu:wellbore:2.0.0",
    "acl": {
        "viewers": ["data.default.viewers@opendes.p4d.cloud.slb-ds.com"],
        "owners": ["data.default.owners@opendes.p4d.cloud.slb-ds.com"]
    },
    "legal": {
        "legaltags": ["opendes-public-usa-dataset-1"],
        "otherRelevantDataCountries": ["US"]
    },
    "data": {
        "country": "FR",
        "name": "toto",
        "airGap": {
            "unitKey": "m",
            "value": 123
        },
        "xxx_color": "#56AF8E"
    },
    "meta": [
        {"notValidMetaKey": "Some value"}
    ]
}
"""


def test_extra_allow_in_data_on_wellbore_record():
    wellbore_obj = models.wellbore.parse_raw(wellbore_str)
    wellbore_dict = wellbore_obj.dict(exclude_unset=True)

    assert wellbore_dict['data']['xxx_color'] == '#56AF8E'


@pytest.mark.parametrize("ddms_model",
                         [models.log, models.logset, models.well, models.wellbore, models.trajectory, models.marker,
                          models.dipset])
def test_record_should_not_serialize_known_meta(ddms_model):
    expected_keys = ["kind", "name", "persistableReference", "propertyNames", "propertyValues", "uncertainty"]
    expected_values = ["CRS", "Some name", "ref", ["name"], ["value"], 0.9]

    parsed = ddms_model.parse_raw(wellbore_str_with_meta_valid_ddms)
    parsed_meta_dict = parsed.meta[0].dict()

    for index in range(len(expected_keys)):
        key = expected_keys[index]
        value = expected_values[index]
        assert parsed_meta_dict[key] == value

    record = utils.to_record(parsed)
    assert "meta" in record.__fields__.keys()

    for index in range(len(expected_keys)):
        key = expected_keys[index]
        value = expected_values[index]
        assert record.meta[0][key] == value


@pytest.mark.parametrize("ddms_model",
                         [models.log, models.logset, models.well, models.wellbore, models.trajectory, models.marker,
                          models.dipset])
def test_record_should_not_serialize_unknown_meta(ddms_model):
    # Record model should handle unknown meta fields
    record = Record.parse_raw(wellbore_str_with_meta_not_valid_ddms)
    meta_obj_keys = record.meta[0].keys()

    assert "notValidMetaKey" in meta_obj_keys
    assert "Some value" == record.meta[0]['notValidMetaKey']

    # But wellbore ddms model should not handle unknown meta fields
    with pytest.raises(pydantic.ValidationError) as execinfo:
        ddms_model.parse_obj(record)
        assert "extra fields not permitted" in str(execinfo)


def test_extra_forbidden_at_root_on_wellbore_record():
    # given json string with extra at root level
    json_with_root_extra_str = json.dumps({'extra': '', **json.loads(wellbore_str)})
    with pytest.raises(ValidationError):
        models.wellbore.parse_raw(json_with_root_extra_str)


def test_no_data_lost_after_convert_to_record():
    # testing whether the model conversion is correct or not
    wellbore_obj = models.wellbore.parse_raw(wellbore_str)
    wellbore_obj.type = 'dummy_type'

    # from dict
    record_dict = Record(**wellbore_obj.dict()).dict()
    # we check if the record model has ignored the extra passed to it
    assert 'type' not in record_dict.keys()

    # from json
    record_dict_from_json = Record.parse_raw(wellbore_obj.json()).dict()
    assert 'type' not in record_dict_from_json.keys()

    parsed_record_dict = Record.parse_raw(wellbore_obj.json()).dict()
    assert 'xxx_color' in parsed_record_dict['data'].keys()

    assert '#56AF8E' == parsed_record_dict['data']['xxx_color']


def test_to_record_do_not_populate_unset():
    wellbore_obj = models.wellbore.parse_raw(wellbore_str)
    record = utils.to_record(wellbore_obj)

    reloaded_wellbore_dict = json.loads(record.json())
    origin_wellbore_dict = json.loads(wellbore_str)
    # checking the data part, must be same as the inputs
    assert origin_wellbore_dict['data'] == reloaded_wellbore_dict['data']


def test_to_record_compatibility_snake_camel_case():
    # as otherRelevantDataCountries is declared in camel case in wdms model
    # as other_relevant_data_countries in Record with 'otherRelevantDataCountries' as alias

    wellbore_obj = models.wellbore.parse_raw(wellbore_str)
    assert wellbore_obj.legal.otherRelevantDataCountries == ["US"]

    record = utils.to_record(wellbore_obj)
    assert record.legal.other_relevant_data_countries == ["US"]

    assert json.loads(record.json(by_alias=True))['legal']['otherRelevantDataCountries'] == ["US"]


def test_from_record_compatibility_snake_camel_case():
    # as otherRelevantDataCountries is declared in camel case in wdms model
    # as other_relevant_data_countries in Record with 'otherRelevantDataCountries' as alias

    record = Record.parse_raw(wellbore_str)
    wellbore_from_record = utils.from_record(models.wellbore, record)
    assert wellbore_from_record.legal.otherRelevantDataCountries == ["US"]


def test_back_and_forth_from_to_record():
    expected_dict = json.loads(wellbore_str)

    # case wellbore -> record -> wellbore
    wellbore = utils.from_record(models.wellbore,
                                 utils.to_record(models.wellbore.parse_raw(wellbore_str)))

    assert utils.record_to_dict(wellbore) == expected_dict

    # case record -> wellbore -> record
    record = utils.to_record(
        utils.from_record(models.wellbore, Record.parse_raw(wellbore_str)))

    assert utils.record_to_dict(record) == expected_dict

    # compare json outputs
    assert json.loads(utils.record_to_json(record)) == json.loads(utils.record_to_json(wellbore))
