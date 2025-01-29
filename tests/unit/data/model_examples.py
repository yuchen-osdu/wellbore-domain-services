from typing import List

import pytest
import os
import json

from odes_storage.models import Record
from app.model.osdu_model import Well, Well110, Well120, Wellbore, Wellbore110, Wellbore120, Wellbore130, \
    WellboreMarkerSet110, WellboreMarkerSet120, WellboreTrajectory110, WellLog110, WellLog120, Wellbore111, \
    WellboreMarkerSet121, WellboreIntervalSet100

from wdms_client.variables import Variables


def load_model_example_file_contents(file_name: str):
    with open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), f"../../../app/model_examples/{file_name}"
            )
    ) as f:

        return json.load(f)


@pytest.fixture(scope="session")
def well_v3_file_contents() -> str:
    return load_model_example_file_contents("well_v3.json")


@pytest.fixture(scope="session")
def well_v3_110_file_contents() -> str:
    return load_model_example_file_contents("well_v3_110.json")


@pytest.fixture(scope="session")
def well_v3_120_file_contents() -> str:
    return load_model_example_file_contents("well_v3_120.json")

@pytest.fixture(scope="session")
def wellbore_v3_file_contents() -> str:
    return load_model_example_file_contents("wellbore_v3.json")


@pytest.fixture(scope="session")
def wellbore_v3_110_file_contents() -> str:
    return load_model_example_file_contents("wellbore_v3_110.json")


@pytest.fixture(scope="session")
def wellbore_v3_111_file_contents() -> str:
    return load_model_example_file_contents("wellbore_v3_111.json")


@pytest.fixture(scope="session")
def wellbore_v3_120_file_contents() -> str:
    return load_model_example_file_contents("wellbore_v3_120.json")


@pytest.fixture(scope="session")
def wellbore_v3_130_file_contents() -> str:
    return load_model_example_file_contents("wellbore_v3_130.json")


@pytest.fixture(scope="session")
def marker_v3_file_contents() -> str:
    return load_model_example_file_contents("marker_v3.json")


@pytest.fixture(scope="session")
def marker_v3_120_file_contents() -> str:
    return load_model_example_file_contents("marker_v3_120.json")


@pytest.fixture(scope="session")
def marker_v3_121_file_contents() -> str:
    return load_model_example_file_contents("marker_v3_121.json")


@pytest.fixture(scope="session")
def wellboreintervalset_v3_100_file_contents() -> str:
    return load_model_example_file_contents("wellboreintervalset_v3_100.json")


@pytest.fixture(scope="session")
def trajectory_v3_file_contents() -> str:
    return load_model_example_file_contents("trajectory_v3.json")


@pytest.fixture(scope="session")
def welllog_v3_110_file_contents():
    return load_model_example_file_contents("wellLog_v3_110.json")


@pytest.fixture(scope="session")
def welllog_v3_120_file_contents():
    return load_model_example_file_contents("wellLog_v3_120.json")


@pytest.fixture
def domain():
    return 'test-domain.com'


@pytest.fixture
def data_partition():
    return 'test-data-partition'


@pytest.fixture
def legal_tags():
    return 'test-legal-tag1, test-legal-tag2'


@pytest.fixture
def well_v3_record_list(well_v3_file_contents, domain, data_partition, legal_tags) -> List[Record]:
    """ list of Well as Record model object loaded for model_example """
    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
        # to replace missing data in example
        "wellName": "my-example-well",
        "wellId": "my-well-v3-example",
    })

    return [Record.parse_obj(vars_to_replace.resolve(file_content)) for file_content in well_v3_file_contents]


@pytest.fixture
def well_v3_110_record_list(well_v3_110_file_contents, domain, data_partition, legal_tags) -> List[Record]:
    """ list of Well as Record model object loaded for model_example """
    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
        # to replace missing data in example
        "wellName": "my-example-well",
        "wellId": "my-well-v3-example",
    })

    return [Record.parse_obj(vars_to_replace.resolve(file_content)) for file_content in well_v3_110_file_contents]


@pytest.fixture
def well_v3_120_record_list(well_v3_120_file_contents, domain, data_partition, legal_tags) -> List[Record]:
    """ list of Well as Record model object loaded for model_example """
    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
        "wellName": "my-example-well",
        "wellId": "my-well-v3-example",
    })

    return [Record.parse_obj(vars_to_replace.resolve(file_content)) for file_content in well_v3_120_file_contents]


@pytest.fixture
def well100_v3_list(well_v3_record_list) -> List[Well]:
    """ provide a list of wellbore v.1.0.0"""
    return [Well(**record.dict(exclude_unset=True, by_alias=True)) for record in well_v3_record_list]


@pytest.fixture
def well110_v3_list(well_v3_110_record_list) -> List[Well110]:
    """ provide a list of wellbore v.1.1.0"""
    return [Well110(**record.dict(exclude_unset=True, by_alias=True)) for record in well_v3_110_record_list]


@pytest.fixture
def well120_v3_list(well_v3_120_record_list) -> List[Well120]:
    """ provide a list of wellbore v.1.2.0"""
    return [Well120(**record.dict(exclude_unset=True, by_alias=True)) for record in well_v3_120_record_list]


@pytest.fixture
def wellbore_v3_record_list(wellbore_v3_file_contents, domain, data_partition, legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
        # to replace missing data in example
        "wellboreName": "my-example-wellbore",
        "wellboreId": "my-wellbore-v3-example",
        "wellId": "my-well-v3-example"
    })

    return [Record.parse_obj(vars_to_replace.resolve(file_content)) for file_content in wellbore_v3_file_contents]


@pytest.fixture
def wellbore_v3_110_record_list(wellbore_v3_110_file_contents, domain, data_partition, legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
        # to replace missing data in example
        "wellboreName": "my-example-wellbore",
        "wellboreId": "my-wellbore-v3-example",
        "wellId": "my-well-v3-example"
    })

    return [Record.parse_obj(vars_to_replace.resolve(file_content)) for file_content in wellbore_v3_110_file_contents]


@pytest.fixture
def wellbore_v3_111_record_list(wellbore_v3_111_file_contents, domain, data_partition, legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
        # to replace missing data in example
        "wellboreName": "my-example-wellbore",
        "wellboreId": "my-wellbore-v3-example",
        "wellId": "my-well-v3-example"
    })

    return [Record.parse_obj(vars_to_replace.resolve(file_content)) for file_content in wellbore_v3_111_file_contents]


@pytest.fixture
def wellbore_v3_120_record_list(wellbore_v3_120_file_contents, domain, data_partition, legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
        # to replace missing data in example
        "wellboreName": "my-example-wellbore",
        "wellboreId": "my-wellbore-v3-example",
        "wellId": "my-well-v3-example"
    })

    return [Record.parse_obj(vars_to_replace.resolve(file_content)) for file_content in wellbore_v3_120_file_contents]


@pytest.fixture
def wellbore_v3_130_record_list(wellbore_v3_130_file_contents, domain, data_partition, legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
        # to replace missing data in example
        "wellboreName": "my-example-wellbore",
        "wellboreId": "my-wellbore-v3-example",
        "wellId": "my-well-v3-example"
    })

    return [Record.parse_obj(vars_to_replace.resolve(file_content)) for file_content in wellbore_v3_130_file_contents]


@pytest.fixture
def wellbore100_v3_list(wellbore_v3_record_list) -> List[Wellbore]:
    """ provide a list of wellbore v.1.0.0"""
    return [Wellbore(**record.dict(exclude_unset=True, by_alias=True)) for record in wellbore_v3_record_list]


@pytest.fixture
def wellbore110_v3_list(wellbore_v3_110_record_list) -> List[Wellbore110]:
    """ provide a list of wellbore v.1.1.0"""
    return [Wellbore110(**record.dict(exclude_unset=True, by_alias=True)) for record in wellbore_v3_110_record_list]


@pytest.fixture
def wellbore111_v3_list(wellbore_v3_111_record_list) -> List[Wellbore111]:
    """ provide a list of wellbore v.1.1.1"""
    return [Wellbore111(**record.dict(exclude_unset=True, by_alias=True)) for record in wellbore_v3_111_record_list]


@pytest.fixture
def wellbore120_v3_list(wellbore_v3_120_record_list) -> List[Wellbore120]:
    """ provide a list of wellbore v.1.2.0"""
    return [Wellbore120(**record.dict(exclude_unset=True, by_alias=True)) for record in wellbore_v3_120_record_list]


@pytest.fixture
def wellbore130_v3_list(wellbore_v3_130_record_list) -> List[Wellbore130]:
    """ provide a list of wellbore v.1.3.0"""
    return [Wellbore130(**record.dict(exclude_unset=True, by_alias=True)) for record in wellbore_v3_130_record_list]


@pytest.fixture
def marker_v3_record_list(marker_v3_file_contents, domain, data_partition, legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
    })

    # single record content
    return [Record.parse_obj(vars_to_replace.resolve(marker_v3_file_contents))]


@pytest.fixture
def marker_v3_120_record_list(marker_v3_120_file_contents, domain, data_partition, legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
    })

    # single record content
    return [Record.parse_obj(vars_to_replace.resolve(marker_v3_120_file_contents))]


@pytest.fixture
def marker_v3_121_record_list(marker_v3_121_file_contents, domain, data_partition, legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
    })

    # single record content
    return [Record.parse_obj(vars_to_replace.resolve(marker_v3_121_file_contents))]


@pytest.fixture
def wellboreintervalset_v3_100_record_list(wellboreintervalset_v3_100_file_contents, domain, data_partition,
                                           legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
    })

    return [Record.parse_obj(vars_to_replace.resolve(file_content))
            for file_content in wellboreintervalset_v3_100_file_contents]


@pytest.fixture
def marker110_v3_list(marker_v3_record_list) -> List[WellboreMarkerSet110]:
    """ provide a list of wellbore marker set v.1.1.0"""
    return [WellboreMarkerSet110(**record.dict(exclude_unset=True, by_alias=True)) for record in marker_v3_record_list]


@pytest.fixture
def marker120_v3_list(marker_v3_120_record_list) -> List[WellboreMarkerSet120]:
    """ provide a list of wellbore marker set v.1.1.0"""
    return [WellboreMarkerSet120(**record.dict(exclude_unset=True, by_alias=True))
            for record in marker_v3_120_record_list]


@pytest.fixture
def marker121_v3_list(marker_v3_121_record_list) -> List[WellboreMarkerSet121]:
    """ provide a list of wellbore marker set v.1.1.0"""
    return [WellboreMarkerSet121(**record.dict(exclude_unset=True, by_alias=True))
            for record in marker_v3_121_record_list]


@pytest.fixture
def wellboreintervalset100_v3_list(wellboreintervalset_v3_100_record_list) -> List[WellboreIntervalSet100]:
    """ provide a list of wellbore marker set v.1.1.0"""
    return [WellboreIntervalSet100(**record.dict(exclude_unset=True, by_alias=True))
            for record in wellboreintervalset_v3_100_record_list]


@pytest.fixture
def trajectory_v3_record_list(trajectory_v3_file_contents, domain, data_partition, legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
    })

    return [Record.parse_obj(vars_to_replace.resolve(file_content)) for file_content in trajectory_v3_file_contents]


@pytest.fixture
def trajectory110_v3_list(trajectory_v3_record_list) -> List[WellboreTrajectory110]:
    """ provide a list of wellbore trajectory v.1.1.0"""
    return [WellboreTrajectory110(**record.dict(exclude_unset=True, by_alias=True)) for record in trajectory_v3_record_list]


@pytest.fixture
def welllog110_v3_record_list(welllog_v3_110_file_contents, domain, data_partition, legal_tags):
    vars_to_replace = Variables.from_dict({
            "domain": domain,
            "datapartitionid": data_partition,
            "legaltags": legal_tags,
            # to replace missing data in example
            "wellboreId": "wellbore-id-example",
            "welllogName": "my-example-welllog",
            "welllogId": "my-welllog-v3-example",
        })
    return [Record.parse_obj(vars_to_replace.resolve(file_content)) for file_content in welllog_v3_110_file_contents]


@pytest.fixture
def welllog120_v3_record_list(welllog_v3_120_file_contents, domain, data_partition, legal_tags):
    vars_to_replace = Variables.from_dict({
            "domain": domain,
            "datapartitionid": data_partition,
            "legaltags": legal_tags,
            # to replace missing data in example
            "wellboreId": "wellbore-id-example",
            "welllogName": "my-example-welllog",
            "welllogId": "my-welllog-v3-example",
        })
    return [Record.parse_obj(vars_to_replace.resolve(file_content)) for file_content in welllog_v3_120_file_contents]


@pytest.fixture
def welllog110_v3_list(welllog110_v3_record_list) -> List[WellLog110]:
    """ provide a list of wellLog v.1.1.0"""
    return [WellLog110(**record.dict(exclude_unset=True, by_alias=True)) for record in welllog110_v3_record_list]


@pytest.fixture
def welllog120_v3_list(welllog120_v3_record_list) -> List[WellLog120]:
    """ provide a list of wellLog v.1.2.0"""
    return [WellLog120(**record.dict(exclude_unset=True, by_alias=True)) for record in welllog120_v3_record_list]
