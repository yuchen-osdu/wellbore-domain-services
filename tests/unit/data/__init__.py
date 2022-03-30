from typing import List

import pytest
import os
import json

from odes_storage.models import Record

from .model_examples import (well_v2_file_contents, well_v3_file_contents, wellbore_v2_file_contents, wellbore_v3_file_contents, domain, data_partition, legal_tags,
                              well_v2_record_list, well_v3_record_list, wellbore_v2_record_list, wellbore_v3_record_list)


@pytest.fixture(scope="session")
def well_wks_record() -> Record:
    with open(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "well_wks.json"
        )
    ) as f:
        file_content = json.load(f)

    return Record.parse_obj(file_content)


@pytest.fixture(scope="session")
def well_wks_mini_record() -> Record:
    with open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "well_wks_mini.json"
            )
    ) as f:
        file_content = json.load(f)

    return Record.parse_obj(file_content)


@pytest.fixture(scope="session")
def wellbore_wks_record() -> Record:
    with open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "wellbore_wks.json"
            )
    ) as f:
        file_content = json.load(f)

    return Record.parse_obj(file_content)


@pytest.fixture(scope="session")
def wellbore_wks_mini_record() -> Record:
    with open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "wellbore_wks_mini.json"
            )
    ) as f:
        file_content = json.load(f)

    return Record.parse_obj(file_content)
