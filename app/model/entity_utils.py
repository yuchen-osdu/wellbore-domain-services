from enum import Enum

from app.model import schema_version


class Entity(Enum):
    LOG = 'log'
    LOGSET = 'logSet'
    MARKER = 'marker'
    TRAJECTORY = 'trajectory'
    WELL = 'well'
    WELLBORE = 'wellbore'
    DIP = 'dip'
    DIPSET = 'dipSet'


class KindMetaData:
    def __init__(self, data_partition_id: str, source: str, entity_type: str, version: str):
        self.data_partition_id = data_partition_id
        self.source = source
        self.entity_type = entity_type
        self.version = version

    def __eq__(self, other):
        if not isinstance(other, KindMetaData):
            return False

        return self.data_partition_id == other.data_partition_id and \
               self.source == other.source and \
               self.entity_type == other.entity_type and \
               self.version == other.version


current_version = \
    {
        Entity.LOG: schema_version.log_version,
        Entity.LOGSET: schema_version.log_version,
        Entity.MARKER: schema_version.marker_version,
        Entity.TRAJECTORY: schema_version.trajectory_version,
        Entity.WELL: schema_version.well_version,
        Entity.WELLBORE: schema_version.wellbore_version,
        Entity.DIP: schema_version.dip_version,
        Entity.DIPSET: schema_version.dipset_version
    }


def get_version(entity: Entity):
    return current_version.get(entity)


def format_kind(data_partition: str, source: str, entity: str, version: str):
    return f'{data_partition}:{source}:{entity}:{version}'


def get_kind(data_partition: str, source: str, entity: Entity):
    version = get_version(entity)
    return format_kind(data_partition, source, entity.value, version)


def get_kind_meta(kind: str) -> KindMetaData:
    # Split kind literal into {data-partition-id}:{source}:{entity-type}:{version}
    meta = kind.split(':', maxsplit=4)
    if len(meta) == 4:
        return KindMetaData(data_partition_id=meta[0],
                            source=meta[1],
                            entity_type=meta[2],
                            version=meta[3])
    raise ValueError(f'Invalid kind format in {kind}.')
