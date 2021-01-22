import pytest

from app.model import entity_utils, schema_version
from app.model.entity_utils import Entity, KindMetaData


def test_get_version():
    assert entity_utils.get_version(Entity.LOG) == schema_version.log_version
    assert entity_utils.get_version(Entity.LOGSET) == schema_version.logset_version
    assert entity_utils.get_version(Entity.MARKER) == schema_version.marker_version
    assert entity_utils.get_version(Entity.TRAJECTORY) == schema_version.trajectory_version
    assert entity_utils.get_version(Entity.WELL) == schema_version.well_version
    assert entity_utils.get_version(Entity.WELLBORE) == schema_version.wellbore_version
    assert entity_utils.get_version(Entity.DIP) == schema_version.dip_version
    assert entity_utils.get_version(Entity.DIPSET) == schema_version.dipset_version


def test_get_kind():
    expected_kind = 'my-data-partition:source-1:well:1.0.2'
    actual_kind = entity_utils.get_kind(data_partition='my-data-partition', source='source-1', entity=Entity.WELL)
    assert actual_kind == expected_kind


def test_get_kind_meta():
    expected_meta = KindMetaData(data_partition_id='other-data-partition',
                                 source='source-1',
                                 entity_type='my-entity',
                                 version='0.0.8')
    actual_meta = entity_utils.get_kind_meta('other-data-partition:source-1:my-entity:0.0.8')
    assert actual_meta == expected_meta


def test_get_kind_meta_invalid():
    with pytest.raises(ValueError, match=f"Invalid kind format in entity:version"):
        entity_utils.get_kind_meta('entity:version')
