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

from typing import Optional

from pydantic import BaseModel, Field, validator

from app.model.model_curated import ValueWithUnit

meter_alias = ["m", "meter", "Meter", "METER", "meters", "Meters", "METERS"]
dega_alias = ["dega", "Dega", "DEGA"]
unitless_alias = ["unitless", "Unitless", "UNITLESS", "UnitLess"]


def value_must_be_in_meter(cls, v):
    if v is not None and v.unitKey not in meter_alias:
        raise ValueError("unit must be meter")
    return v


def value_must_be_in_dega(cls, v):
    if v is not None and v.unitKey not in dega_alias:
        raise ValueError("unit must be dega")
    return v


class Dip(BaseModel):
    reference: ValueWithUnit = Field(
        ..., title="Reference of the dip", description="Only Measured Depth in meter is supported for the moment",
    )
    azimuth: ValueWithUnit = Field(
        ..., title="Azimuth value of the dip", description="Only degrees unit is supported for the moment"
    )
    inclination: ValueWithUnit = Field(
        ..., title="Inclination value of the dip", description="Only degrees unit is supported for the moment",
    )
    quality: Optional[ValueWithUnit] = Field(
        None,
        title="Quality of the dip",
        description="Decimal number between 0 and 1"
    )
    xCoordinate: Optional[ValueWithUnit] = Field(
        None, title="The X coordinate of the dip", description="Only meter unit is supported for the moment"
    )
    yCoordinate: Optional[ValueWithUnit] = Field(
        None, title="The Y coordinate of the dip", description="Only meter unit is supported for the moment"
    )
    zCoordinate: Optional[ValueWithUnit] = Field(
        None, title="The Z coordinate of the dip", description="Only meter unit is supported for the moment"
    )
    classification: Optional[str] = Field(
        None, title="Classification of the dip", description="Any string is accepted."
    )

    _reference_unit_validator = validator("reference", allow_reuse=True)(value_must_be_in_meter)
    _x_coordinate_unit_validator = validator("xCoordinate", allow_reuse=True)(value_must_be_in_meter)
    _y_coordinate_unit_validator = validator("yCoordinate", allow_reuse=True)(value_must_be_in_meter)
    _z_coordinate_unit_validator = validator("zCoordinate", allow_reuse=True)(value_must_be_in_meter)
    _azimuth_unit_validator = validator("azimuth", allow_reuse=True)(value_must_be_in_dega)
    _inclination_unit_validator = validator("inclination", allow_reuse=True)(value_must_be_in_dega)

    @validator("quality")
    def quality_validator(cls, v):
        if v is not None and (v.value < 0 or v.value > 1):
            raise ValueError("value must be greater or egal to 0 and less or egal to 1")
        if v is not None and v.unitKey not in unitless_alias:
            raise ValueError("unit must be unitless")
        return v

    class Config:
        schema_extra = {
            "example": {
                "reference": {"unitKey": "meter", "value": 1000.5},
                "azimuth": {"unitKey": "dega", "value": 42},
                "inclination": {"unitKey": "dega", "value": 9},
                "quality": {"unitKey": "unitless", "value": 0.5},
                "xCoordinate": {"unitKey": "meter", "value": 2},
                "yCoordinate": {"unitKey": "meter", "value": 45},
                "zCoordinate": {"unitKey": "meter", "value": 7},
                "classification": "fracture",
            }
        }
