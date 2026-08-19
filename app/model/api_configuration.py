from dataclasses import dataclass
from typing import Annotated, Callable

from odes_storage.models import Record
from pydantic import StringConstraints

from app.consistency import check_ppfgdataset_consistency
from app.consistency.wellpressuretestrawmeasurement_consistency import \
    check_well_pressure_test_raw_measurement_consistency
from app.model.entity_utils import Entity
from app.model.osdu_record_id import PPFGDatasetId, WellPressureTestRawMeasurementId


@dataclass(frozen=True)
class APIConfiguration:
    tag: str  # API Tag
    entity_uri: str  # This would be part of API URL
    entity: Entity
    record_id_constraint: Annotated[str, StringConstraints]  # recordID regex pattern
    record_consistency_check_function: Callable[[Record], None]  # record consistency check function


PPFGDatasetAPI = APIConfiguration(tag="PPFGDataset v3", entity_uri="/ppfgdataset", entity=Entity.PPFGDATASET,
                                  record_id_constraint=PPFGDatasetId,
                                  record_consistency_check_function=check_ppfgdataset_consistency)

WellPressureTestRawMeasurementAPI = APIConfiguration(tag="WellPressureTestRawMeasurement v3",
                                                     entity_uri="/wellpressuretestrawmeasurement",
                                                     entity=Entity.WELLPRESSURETESTRAWMEASUREMENT,
                                                     record_id_constraint=WellPressureTestRawMeasurementId,
                                                     record_consistency_check_function=check_well_pressure_test_raw_measurement_consistency)
