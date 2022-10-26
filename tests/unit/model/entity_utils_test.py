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

from app.model import entity_utils, schema_version
from app.model.entity_utils import Entity, KindMetaData


@pytest.fixture(params=['authority_data_partition', 'authority_slb'])
def authority(request):
    return 'test_data_partition' if request.param == "authority_data_partition" else 'slb'


def test_get_version():
    assert entity_utils.get_version(Entity.LOG) == schema_version.log_version
    assert entity_utils.get_version(Entity.LOGSET) == schema_version.logset_version
    assert entity_utils.get_version(Entity.MARKER) == schema_version.marker_version
    assert entity_utils.get_version(Entity.TRAJECTORY) == schema_version.trajectory_version
    assert entity_utils.get_version(Entity.WELL) == schema_version.well_version
    assert entity_utils.get_version(Entity.WELLBORE) == schema_version.wellbore_version
    assert entity_utils.get_version(Entity.DIP) == schema_version.dip_version
    assert entity_utils.get_version(Entity.DIPSET) == schema_version.dipset_version


def test_get_kind(authority):
    expected_kind = f'{authority}:source-1:well:1.0.2'
    actual_kind = entity_utils.get_kind(authority=authority, source='source-1', entity=Entity.WELL)
    assert actual_kind == expected_kind


def test_get_kind_meta(authority):
    expected_meta = KindMetaData(authority=authority,
                                 source='source-1',
                                 entity_type='my-entity',
                                 version='0.0.8')
    actual_meta = entity_utils.get_kind_meta(f'{authority}:source-1:my-entity:0.0.8')
    assert actual_meta == expected_meta


def test_get_kind_meta_invalid():
    with pytest.raises(ValueError, match=f"Invalid kind format in entity:version"):
        entity_utils.get_kind_meta('entity:version')
