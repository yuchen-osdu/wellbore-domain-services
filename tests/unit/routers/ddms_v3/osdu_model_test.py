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

import pytest
import json
import os
from typing import Type
from pydantic import BaseModel, ValidationError
from app.model.osdu_model import Wellbore, Well, WellLog, WellboreTrajectory, WellboreMarkerSet, \
    WellLog110, WellboreTrajectory110, WellboreMarkerSet110, \
    WellLog120


test_parameters = [
    (Wellbore, "Wellbore_unit.json", None),
    (Well, "Well_unit.json", None),
    (WellLog, "WellLog_unit.json", None),
    (WellLog, "WellLog110_unit.json", ValidationError), #WellLog 100 must not accept to load WellLog 110
    (WellLog, "WellLog120_unit.json", ValidationError), #WellLog 100 must not accept to load WellLog 120
    (WellLog110, "WellLog_unit.json", None), #WellLog 110 accepts to load WellLog 100
    (WellLog110, "WellLog110_unit.json", None),
    (WellLog110, "WellLog120_unit.json", ValidationError), #WellLog 110 must not accept to load WellLog 120
    (WellLog120, "WellLog_unit.json", None), #WellLog 120 accepts to load WellLog 100
    (WellLog120, "WellLog110_unit.json", None), #WellLog 120 accepts to load WellLog 110
    (WellLog120, "WellLog120_unit.json", None),
    (WellboreTrajectory, "WellboreTrajectory_unit.json", None),
    (WellboreTrajectory, "WellboreTrajectory_unit.json", None),
    (WellboreTrajectory, "WellboreTrajectory110_unit.json", ValidationError),
    (WellboreTrajectory110, "WellboreTrajectory_unit.json", None),
    (WellboreTrajectory110, "WellboreTrajectory110_unit.json", None),
    (WellboreMarkerSet, "WellboreMarkerSet_unit.json", None),
    (WellboreMarkerSet110, "WellboreMarkerSet110_unit.json", None),
]


@pytest.mark.parametrize("cls, json_file, expected_exception", test_parameters)
def test_osdu_models(cls: Type[BaseModel], json_file, expected_exception):
    with open(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), json_file)
    ) as f:
        file_contents = json.load(f)

    for file_content in file_contents:
        if expected_exception is not None:
            with pytest.raises(expected_exception):
                cls.validate(file_content)
        else:
            cls.validate(file_content)
