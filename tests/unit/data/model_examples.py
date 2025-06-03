from typing import List

import pytest
import os
import json

from odes_storage.models import Record

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

    return [Record.model_validate(vars_to_replace.resolve(file_content)) for file_content in well_v3_file_contents]


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

    return [Record.model_validate(vars_to_replace.resolve(file_content)) for file_content in well_v3_110_file_contents]


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

    return [Record.model_validate(vars_to_replace.resolve(file_content)) for file_content in well_v3_120_file_contents]


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

    return [Record.model_validate(vars_to_replace.resolve(file_content)) for file_content in wellbore_v3_file_contents]


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

    return [Record.model_validate(vars_to_replace.resolve(file_content)) for file_content in wellbore_v3_110_file_contents]


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

    return [Record.model_validate(vars_to_replace.resolve(file_content)) for file_content in wellbore_v3_111_file_contents]


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

    return [Record.model_validate(vars_to_replace.resolve(file_content)) for file_content in wellbore_v3_120_file_contents]


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

    return [Record.model_validate(vars_to_replace.resolve(file_content)) for file_content in wellbore_v3_130_file_contents]


@pytest.fixture
def marker_v3_record_list(marker_v3_file_contents, domain, data_partition, legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
    })

    # single record content
    return [Record.model_validate(vars_to_replace.resolve(marker_v3_file_contents))]


@pytest.fixture
def marker_v3_120_record_list(marker_v3_120_file_contents, domain, data_partition, legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
    })

    # single record content
    return [Record.model_validate(vars_to_replace.resolve(marker_v3_120_file_contents))]


@pytest.fixture
def marker_v3_121_record_list(marker_v3_121_file_contents, domain, data_partition, legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
    })

    # single record content
    return [Record.model_validate(vars_to_replace.resolve(marker_v3_121_file_contents))]


@pytest.fixture
def wellboreintervalset_v3_100_record_list(wellboreintervalset_v3_100_file_contents, domain, data_partition,
                                           legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
    })

    return [Record.model_validate(vars_to_replace.resolve(file_content))
            for file_content in wellboreintervalset_v3_100_file_contents]


@pytest.fixture
def trajectory_v3_record_list(trajectory_v3_file_contents, domain, data_partition, legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
    })

    return [Record.model_validate(vars_to_replace.resolve(file_content)) for file_content in trajectory_v3_file_contents]


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
    return [Record.model_validate(vars_to_replace.resolve(file_content)) for file_content in welllog_v3_110_file_contents]


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
    return [Record.model_validate(vars_to_replace.resolve(file_content)) for file_content in welllog_v3_120_file_contents]
