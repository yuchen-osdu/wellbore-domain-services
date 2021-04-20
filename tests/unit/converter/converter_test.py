import json
import os

import pytest
from odes_storage.models import Record

from app.converter.wellbore_converter import WellboreConverter
from app.converter.well_converter import WellConverter
from app.model.osdu_model import Wellbore, Well

RECORD_SAMPLE = [
    (WellboreConverter, {
        "acl": {
            "viewers": [
                "vieweremail@domain.com"
            ],
            "owners": [
                "owneremail@domain.com"
            ]
        },
        "data": {},
        "meta": [{
            "kind": "Unit",
            "name": "Measure depth default unit",
            "persistableReference": "persistableReference",
            "propertyNames": ["symbol"],
            "propertyValues": ["ft"]
        }],
        "id": "datapartitionid:wellbore:myWellbore",
        "kind": "datapartitionid:wks:wellbore:1.0.6",
        "legal": {
            "legaltags": [
                "{{legaltags}}"
            ],
            "otherRelevantDataCountries": [
                "FR",
                "US"
            ],
            "status": "compliant"
        },
        "version": 1245,
        "ancestry": {
            "parents": [
                "BP:ihs:7a336d62-ffc4-5a91-b550-f04218579828:1543413435034177",
                "common:welldb:6e32f18e-2e51-512e-b982-09c7b6a11663:1543414413403142",
                "BP:corp:249edfff-4c6c-538e-8c03-b3b142e45f33:1285161040815393"
            ]},
        "tags": {"key": "value", "simple": "dict"},
        "createUser": "fserin",
        "modifyUser": "fserin2",
        "createTime": "1961-08-25T03:55:42.109Z",
        "modifyTime": "1962-11-02T15:39:57.25Z",
    }),
    (WellConverter, {
        "acl": {
            "viewers": [
                "vieweremail@domain.com"
            ],
            "owners": [
                "owneremail@domain.com"
            ]
        },
        "data": {},
        "meta": [{
            "kind": "Unit",
            "name": "Measure depth default unit",
            "persistableReference": "persistableReference",
            "propertyNames": ["symbol"],
            "propertyValues": ["ft"]
        }],
        "id": "datapartitionid:wellbore:myWellbore",
        "kind": "datapartitionid:wks:wellbore:1.0.6",
        "legal": {
            "legaltags": [
                "{{legaltags}}"
            ],
            "otherRelevantDataCountries": [
                "FR",
                "US"
            ],
            "status": "compliant"
        },
        "version": 1245,
        "ancestry": {
            "parents": [
                "BP:ihs:7a336d62-ffc4-5a91-b550-f04218579828:1543413435034177",
                "common:welldb:6e32f18e-2e51-512e-b982-09c7b6a11663:1543414413403142",
                "BP:corp:249edfff-4c6c-538e-8c03-b3b142e45f33:1285161040815393"
            ]},
        "tags": {"key": "value", "simple": "dict"},
        "createUser": "fserin",
        "modifyUser": "fserin2",
        "createTime": "1961-08-25T03:55:42.109Z",
        "modifyTime": "1962-11-02T15:39:57.25Z",
    })
]


@pytest.mark.parametrize("ConverterClass, input_record", RECORD_SAMPLE)
def test_record_conversion(ConverterClass, input_record: dict):
    # The transformation should let the record fields unchanged (except for data, kind)
    record: Record = Record.parse_obj(input_record)

    res: dict = ConverterClass.convert_delfi_to_osdu(record.dict(by_alias=True, exclude_none=True, exclude_unset=True),
                                                     context={"namespace": "test_namespace"})
    # Let's ignore the data part and the kind
    res["id"] = input_record["id"]
    res["data"] = input_record["data"]
    res["kind"] = input_record["kind"]

    res_record: Record = Record.parse_obj(res)
    assert record == res_record


OSDU_TYPES_CONVERTER = [
    ("wellbore_wks.json", Wellbore, WellboreConverter),
    ("wellbore_wks_mini.json", Wellbore, WellboreConverter),
    ("../../../app/model_examples/wellbore_v2.json", Wellbore, WellboreConverter),
    ("well_wks.json", Well, WellConverter),
    ("well_wks_mini.json", Well, WellConverter),
    ("../../../app/model_examples/well_v2.json", Well, WellConverter),
]

def replace_template(source_obj_str: str) -> str:
    source_obj_str = source_obj_str.replace("{{datapartitionid}}", "datapartitionid")\
        .replace("{datapartitionid}", "datapartitionid").replace("{{domain}}", "domain")
    return source_obj_str

@pytest.mark.parametrize("input_file, ObjectClass, ConverterClass", OSDU_TYPES_CONVERTER)
def test_conversion(input_file, ObjectClass, ConverterClass):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, input_file)) as f:
        source_obj_str = replace_template(f.read())
        source_obj_dict = json.loads(source_obj_str)
    if isinstance(source_obj_dict, list):
        source_obj_dict = source_obj_dict[0]
    source_obj: Record = Record.parse_obj(source_obj_dict)

    res: dict = ConverterClass.convert_delfi_to_osdu(
        source_obj.dict(by_alias=True, exclude_none=True, exclude_unset=True),
        context={"namespace": "test_namespace"})
    # Uncomment those lines to dump the actual result of the conversion
    # with open("dumpsresdict.json", 'w') as fp:
    #     json.dump(res, fp, indent=2, default=str)
    ObjectClass.validate(res)
