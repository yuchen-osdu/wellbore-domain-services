from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.model.entity_utils import Entity
from app.routers.ddms_v3.ddms_v3_utils import DMSV3RouterUtils


def _record(kind: str):
    return SimpleNamespace(kind=kind)


def _state(entity: Entity):
    return SimpleNamespace(version="V3", entity_type=entity)


def test_ppfgdataset_rejects_a_different_kind():
    record = _record("osdu:wks:work-product-component--WellLog:1.0.0")
    with pytest.raises(HTTPException):
        DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, _state(Entity.PPFGDATASET))


def test_ppfgdataset_accepts_its_kind():
    record = _record("osdu:wks:work-product-component--PPFGDataset:1.2.0")
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, _state(Entity.PPFGDATASET))


def test_welllogacquisition_rejects_a_different_kind():
    record = _record("osdu:wks:work-product-component--WellLog:1.0.0")
    with pytest.raises(HTTPException):
        DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, _state(Entity.WELLLOGACQUISITION))


def test_welllogacquisition_accepts_its_kind():
    record = _record("osdu:wks:master-data--WellLogAcquisition:1.0.0")
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, _state(Entity.WELLLOGACQUISITION))


def test_unmapped_v3_entity_is_rejected():
    record = _record("osdu:wks:work-product-component--Dip:1.0.0")
    with pytest.raises(HTTPException):
        DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, _state(Entity.DIP))
