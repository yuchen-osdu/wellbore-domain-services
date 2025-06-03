from typing import List

import pytest
import os
import json

from odes_storage.models import Record

from .model_examples import (
    well_v3_file_contents,
    well_v3_110_file_contents,
    well_v3_120_file_contents,
    wellbore_v3_file_contents,
    wellbore_v3_110_file_contents,
    wellbore_v3_111_file_contents,
    wellbore_v3_120_file_contents,
    wellbore_v3_130_file_contents,
    marker_v3_file_contents,
    marker_v3_120_file_contents,
    marker_v3_121_file_contents,
    wellboreintervalset_v3_100_file_contents,
    trajectory_v3_file_contents,
    welllog_v3_110_file_contents,
    welllog_v3_120_file_contents,
    domain, data_partition, legal_tags,
    well_v3_record_list,
    well_v3_110_record_list,
    well_v3_120_record_list,
    wellbore_v3_record_list,
    wellbore_v3_110_record_list,
    wellbore_v3_111_record_list,
    wellbore_v3_120_record_list,
    wellbore_v3_130_record_list,
    marker_v3_record_list,
    marker_v3_120_record_list,
    marker_v3_121_record_list,
    wellboreintervalset_v3_100_record_list,
    trajectory_v3_record_list,
    welllog110_v3_record_list,
    welllog120_v3_record_list,
)


@pytest.fixture(scope="session")
def well_wks_record() -> Record:
    with open(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "well_wks.json"
        )
    ) as f:
        file_content = json.load(f)

    return Record.model_validate(file_content)


@pytest.fixture(scope="session")
def well_wks_mini_record() -> Record:
    with open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "well_wks_mini.json"
            )
    ) as f:
        file_content = json.load(f)

    return Record.model_validate(file_content)


@pytest.fixture(scope="session")
def wellbore_wks_record() -> Record:
    with open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "wellbore_wks.json"
            )
    ) as f:
        file_content = json.load(f)

    return Record.model_validate(file_content)


@pytest.fixture(scope="session")
def wellbore_wks_mini_record() -> Record:
    with open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "wellbore_wks_mini.json"
            )
    ) as f:
        file_content = json.load(f)

    return Record.model_validate(file_content)
