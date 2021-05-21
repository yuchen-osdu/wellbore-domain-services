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
from pydantic import ValidationError

from app.model.model_curated import ValueWithUnit
from app.routers.dipset.dip_model import Dip


def test_dip_model_nominal():

    try:
        Dip(
        reference=ValueWithUnit(unitKey="meter", value=1000.0),
        azimuth=ValueWithUnit(unitKey="dega", value=34),
        inclination=ValueWithUnit(unitKey="dega", value=18.0),
        quality=ValueWithUnit(unitKey="unitless", value=0.5),
        xCoordinate=ValueWithUnit(unitKey="meter", value=18.0),
        yCoordinate=ValueWithUnit(unitKey="meter", value=18.0),
        zCoordinate=ValueWithUnit(unitKey="meter", value=18.0),
        classification="fracture",
    )
    except Exception:
        pytest.fail("should not fail")


def test_dip_model_optional_fields():
    Dip(
        reference=ValueWithUnit(unitKey="meter", value=1000.0),
        azimuth=ValueWithUnit(unitKey="dega", value=34),
        inclination=ValueWithUnit(unitKey="dega", value=18.0),
    )


def test_dip_model_missing_all_mandatory_field():
    with pytest.raises(ValidationError):
        Dip(
            quality=ValueWithUnit(unitKey="unitless", value=0.5),
            xCoordinate=ValueWithUnit(unitKey="meter", value=18.0),
            yCoordinate=ValueWithUnit(unitKey="meter", value=18.0),
            zCoordinate=ValueWithUnit(unitKey="meter", value=18.0),
            classification="fracture",
        )


def test_dip_model_missing_reference():
    with pytest.raises(ValidationError):
        Dip(azimuth=ValueWithUnit(unitKey="dega", value=34), inclination=ValueWithUnit(unitKey="dega", value=18.0))


def test_dip_model_missing_azimuth():
    with pytest.raises(ValidationError):
        Dip(
            reference=ValueWithUnit(unitKey="meter", value=1000.0),
            inclination=ValueWithUnit(unitKey="dega", value=18.0),
        )


def test_dip_model_missing_inclination():
    with pytest.raises(ValidationError):
        Dip(
            reference=ValueWithUnit(unitKey="meter", value=1000.0), azimuth=ValueWithUnit(unitKey="dega", value=18.0),
        )


def test_dip_model_missing_reference_and_azimuth():
    with pytest.raises(ValidationError):
        Dip(inclination=ValueWithUnit(unitKey="dega", value=18.0))


@pytest.mark.parametrize("unit", ["m", "meter", "Meter", "METER", "meters", "Meters", "METERS"])
def test_dip_model_validator_unit(unit):
    Dip(
        reference=ValueWithUnit(unitKey=unit, value=1000.0),
        azimuth=ValueWithUnit(unitKey="dega", value=34),
        inclination=ValueWithUnit(unitKey="dega", value=18.0),
    )


@pytest.mark.parametrize("unit", ["ft", "", None])
def test_dip_model_reference_with_wrong_unit(unit):
    with pytest.raises(ValidationError) as excinfo:
        Dip(
            reference=ValueWithUnit(unitKey=unit, value=1000.0),
            azimuth=ValueWithUnit(unitKey="dega", value=34),
            inclination=ValueWithUnit(unitKey="dega", value=18.0),
        )


@pytest.mark.parametrize("unit", ["rad", "", None])
def test_dip_model_azimuth_with_wrong_unit(unit):
    with pytest.raises(ValidationError) as excinfo:
        Dip(
            reference=ValueWithUnit(unitKey="m", value=1000.0),
            azimuth=ValueWithUnit(unitKey=unit, value=34),
            inclination=ValueWithUnit(unitKey="dega", value=18.0),
        )


@pytest.mark.parametrize("unit", ["rad", "", None])
def test_dip_model_inclination_with_wrong_unit(unit):
    with pytest.raises(ValidationError) as excinfo:
        Dip(
            reference=ValueWithUnit(unitKey="m", value=1000.0),
            azimuth=ValueWithUnit(unitKey="dega", value=34),
            inclination=ValueWithUnit(unitKey=unit, value=18.0),
        )


@pytest.mark.parametrize("unit", ["unitless", "Unitless", "UNITLESS", "UnitLess"])
def test_dip_model_quality_unit(unit):
    Dip(
        reference=ValueWithUnit(unitKey="m", value=1000.0),
        azimuth=ValueWithUnit(unitKey="dega", value=34),
        inclination=ValueWithUnit(unitKey="dega", value=18.0),
        quality=ValueWithUnit(unitKey=unit, value=0.5),
    )


@pytest.mark.parametrize("unit", ["m", "", None])
def test_dip_model_quality_unit_negative(unit):
    with pytest.raises(ValidationError) as excinfo:
        Dip(
            reference=ValueWithUnit(unitKey="m", value=1000.0),
            azimuth=ValueWithUnit(unitKey="dega", value=34),
            inclination=ValueWithUnit(unitKey="dega", value=18.0),
            quality=ValueWithUnit(unitKey=unit, value=0.5),
        )


@pytest.mark.parametrize("value", [0, 0.42, 1])
def test_dip_model_quality_value_validation(value):
    Dip(
        reference=ValueWithUnit(unitKey="m", value=1000.0),
        azimuth=ValueWithUnit(unitKey="dega", value=34),
        inclination=ValueWithUnit(unitKey="dega", value=18.0),
        quality=ValueWithUnit(unitKey="unitless", value=value),
    )


@pytest.mark.parametrize("value", [-1, 1.0001, 42])
def test_dip_model_quality_value_validation_negative(value):
    with pytest.raises(ValidationError) as excinfo:
        Dip(
            reference=ValueWithUnit(unitKey="m", value=1000.0),
            azimuth=ValueWithUnit(unitKey="dega", value=34),
            inclination=ValueWithUnit(unitKey="dega", value=18.0),
            quality=ValueWithUnit(unitKey="unitless", value=value),
        )

def test_dip_model_zero_values():
        Dip(
            reference=ValueWithUnit(unitKey="m", value=0),
            azimuth=ValueWithUnit(unitKey="dega", value=0),
            inclination=ValueWithUnit(unitKey="dega", value=0),
            quality=ValueWithUnit(unitKey="unitless", value=0)
        )