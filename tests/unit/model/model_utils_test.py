# Copyright 2021 Schlumberger
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

import pydantic
import pytest
from odes_storage.models import Record

import app.model.model_curated as models
import app.model.model_utils as utils


@pytest.mark.parametrize("ddms_model", [models.log,
                                        models.dipset])
def test_list_record_models(ddms_model):
    # the main goal here is to spot any new record model
    # If OK and a valid 'record' kind model, add it to the expected list
    # otherwise the list function must be reviewed
    assert 'data' in ddms_model.model_fields.keys()
    assert 'forbid' == ddms_model.model_config['extra']


def test_check_record_model_base_config():
    # this the base config make sure that this has not changed
    assert Record.model_config == {}


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
    },
    "tags":{"any": "string:string", "dict": "accepted"}
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

@pytest.mark.parametrize("ddms_model", [models.log, models.dipset])
def test_record_should_not_serialize_known_meta(ddms_model):
    expected_keys = ["kind", "name", "persistableReference", "propertyNames", "propertyValues", "uncertainty"]
    expected_values = ["CRS", "Some name", "ref", ["name"], ["value"], 0.9]

    parsed = ddms_model.model_validate_json(wellbore_str_with_meta_valid_ddms)
    parsed_meta_dict = parsed.meta[0].model_dump()

    for index in range(len(expected_keys)):
        key = expected_keys[index]
        value = expected_values[index]
        assert parsed_meta_dict[key] == value

    record = utils.to_record(parsed)
    assert "meta" in record.model_fields.keys()

    for index in range(len(expected_keys)):
        key = expected_keys[index]
        value = expected_values[index]
        assert record.meta[0][key] == value


@pytest.mark.parametrize("ddms_model", [models.log, models.dipset])
def test_record_should_not_serialize_unknown_meta(ddms_model):
    # Record model should handle unknown meta fields
    record = Record.model_validate_json(wellbore_str_with_meta_not_valid_ddms)
    meta_obj_keys = record.meta[0].keys()

    assert "notValidMetaKey" in meta_obj_keys
    assert "Some value" == record.meta[0]['notValidMetaKey']

    # But wellbore ddms model should not handle unknown meta fields
    with pytest.raises(pydantic.ValidationError) as execinfo:
        ddms_model.model_validate(record)
        assert "extra fields not permitted" in str(execinfo)


@pytest.mark.parametrize('model_cls, data_content',
                         [
                             (models.log, {"relationships": {}}),
                             (models.dipset, {"relationships": {"wellbore": {}}})
                         ])
def test_model_allow_extra_field_in_relationship_success(model_cls, data_content):
    data_content["relationships"]["extra_field_in_relationship"] = "extra_value"
    raw_base_dict = {
        "acl": {"viewers": [], "owners": []},
        "legal": {"legaltags": []},
        "id": "123456",
        "kind": "opened:osdu:dummy",
        "data": data_content
    }
    parsed_obj = model_cls.model_validate(raw_base_dict)
    # deserialized should keep it extra field
    assert parsed_obj.data.relationships.extra_field_in_relationship == "extra_value"
    # serialized should keep it
    assert parsed_obj.model_dump()['data']['relationships']['extra_field_in_relationship'] == "extra_value"
    # using utils from/to record
    record_obj = utils.to_record(parsed_obj)
    assert record_obj.data['relationships']['extra_field_in_relationship'] == "extra_value"
    parsed_obj = utils.from_record(model_cls, record_obj)
    assert parsed_obj.data.relationships.extra_field_in_relationship == "extra_value"


def test_meta_item_should_allow_extra():
    example = {
        "format": "yyyy-MM-ddTHH:mm:ssZ",
        "kind": "DateTime",
        "name": "datetime",
        "persistableReference": "UTC",
        "propertyNames": [
            "dateLicenseIssued",
            "dateModified",
            "dateCreated",
            "datePluggedAbandoned",
            "dateSpudded"
        ]
    }
    parsed = models.MetaItem.model_validate(example)
    assert 'format' in parsed.model_dump().keys()
    assert parsed.format == 'yyyy-MM-ddTHH:mm:ssZ'
