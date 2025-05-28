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

from enum import Enum
from odes_storage.models import Record
from app.model import schema_version

class Entity(Enum):
    LOG = 'log'
    MARKER = 'marker'
    WELLBOREINTERVALSET = 'wellboreintervalset'
    WELLLOGACQUISITION = 'welllogacquisition'
    TRAJECTORY = 'trajectory'
    WELL = 'well'
    WELL_LOG = 'welllog'
    WELLBORE = 'wellbore'
    DIP = 'dip'
    DIPSET = 'dipSet'
    PPFGDATASET = 'ppfgdataset'


class KindMetaData:
    def __init__(self, authority: str, source: str, entity_type: str, version: str):
        self.authority = authority
        self.source = source
        self.entity_type = entity_type
        self.version = version

    def __eq__(self, other):
        if not isinstance(other, KindMetaData):
            return False

        return self.authority == other.authority and \
               self.source == other.source and \
               self.entity_type == other.entity_type and \
               self.version == other.version


current_version = \
    {
        Entity.LOG: schema_version.log_version,
        Entity.MARKER: schema_version.marker_version,
        Entity.WELLBOREINTERVALSET: schema_version.wellboreintervalset_version,
        Entity.TRAJECTORY: schema_version.trajectory_version,
        Entity.WELL: schema_version.well_version,
        Entity.WELLBORE: schema_version.wellbore_version,
        Entity.DIP: schema_version.dip_version,
        Entity.DIPSET: schema_version.dipset_version
    }


def get_version(entity: Entity):
    return current_version.get(entity)


def get_data_partition_from_record_id(record: Record):
    return record.id.split(":")[0]


def format_kind(authority: str, source: str, entity: str, version: str):
    return f'{authority}:{source}:{entity}:{version}'


def get_kind(authority: str, source: str, entity: Entity):
    version = get_version(entity)
    return format_kind(authority, source, entity.value, version)


def get_kind_meta(kind: str) -> KindMetaData:
    # Split kind literal into {authority}:{source}:{entity-type}:{version}
    meta = kind.split(':', maxsplit=4)
    if len(meta) == 4:
        return KindMetaData(authority=meta[0],
                            source=meta[1],
                            entity_type=meta[2],
                            version=meta[3])
    raise ValueError(f'Invalid kind format in {kind}.')
