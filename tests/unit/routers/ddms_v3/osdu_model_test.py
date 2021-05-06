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
from pydantic import BaseModel
from app.model.osdu_model import Wellbore, Well, WellLog, WellboreTrajectory, WellboreMarkerSet


test_parameters = [
    (Wellbore, "Wellbore_unit.json"),
    (Well, "Well_unit.json"),
    (WellLog, "WellLog_unit.json"),
    (WellboreTrajectory, "WellboreTrajectory_unit.json"),
    (WellboreMarkerSet, "WellboreMarkerSet_unit.json"),
]


@pytest.mark.parametrize("cls, json_file", test_parameters)
def test_osdu_models(cls: Type[BaseModel], json_file):
    with open(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), json_file)
    ) as f:
        file_contents = json.load(f)

    for file_content in file_contents:
        cls.validate(file_content)
