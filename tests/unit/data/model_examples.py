import uuid
from typing import List

import pytest
import os
import json

from odes_storage.models import Record

from wdms_client.variables import Variables


@pytest.fixture(scope="session")
def well_v2_file_contents() -> str:

    with open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "../../../app/model_examples/well_v2.json"
            )
    ) as f:

        return json.load(f)


@pytest.fixture(scope="session")
def well_v3_file_contents() -> str:

    with open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "../../../app/model_examples/well_v3.json"
            )
    ) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def wellbore_v2_file_contents() -> str:

    with open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "../../../app/model_examples/wellbore_v2.json"
            )
    ) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def wellbore_v3_file_contents() -> str:

    with open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "../../../app/model_examples/wellbore_v3.json"
            )
    ) as f:
        return json.load(f)


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
def well_v2_record_list(well_v2_file_contents, domain, data_partition, legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
    })

    return [Record.parse_obj(vars_to_replace.resolve(file_content)) for file_content in well_v2_file_contents]


@pytest.fixture
def well_v3_record_list(well_v3_file_contents, domain, data_partition, legal_tags) -> List[Record]:

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
def wellbore_v2_record_list(wellbore_v2_file_contents, domain, data_partition, legal_tags) -> List[Record]:

    vars_to_replace = Variables.from_dict({
        "domain": domain,
        "datapartitionid": data_partition,
        "legaltags": legal_tags,
    })

    return [Record.parse_obj(vars_to_replace.resolve(file_content)) for file_content in wellbore_v2_file_contents]


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
