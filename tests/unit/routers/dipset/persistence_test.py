import pandas as pd
import pytest

from app.model.model_curated import ValueWithUnit
from app.routers.dipset.dip_model import Dip
from app.routers.dipset.persistence import series_to_dip


@pytest.mark.parametrize(
    "series,dip",
    [
        (
            pd.Series(
                {"reference": 1000.0, "azimuth": 34.0, "inclination": 18.0, "classification": "fracture"},
                dtype="object",
            ),
            Dip(
                reference=ValueWithUnit(unitKey="meter", value=1000.0),
                azimuth=ValueWithUnit(unitKey="dega", value=34),
                inclination=ValueWithUnit(unitKey="dega", value=18.0),
                classification="fracture",
            ),
        ),
        (
            pd.Series(
                {
                    "reference": 1000.0,
                    "azimuth": 34.0,
                    "inclination": 18.0,
                    "classification": "fracture",
                    "quality": float("nan"),
                    "xCoordinate": float("nan"),
                    "yCoordinate": float("nan"),
                    "zCoordinate": float("nan"),
                },
                dtype="object",
            ),
            Dip(
                reference=ValueWithUnit(unitKey="meter", value=1000.0),
                azimuth=ValueWithUnit(unitKey="dega", value=34),
                inclination=ValueWithUnit(unitKey="dega", value=18.0),
                classification="fracture",
                quality=None,
                xCoordinate=None,
                yCoordinate=None,
                zCoordinate=None,
            ),
        ),
        (
            pd.Series(
                {
                    "reference": 0.REMOVED_FOR_CICD_SCAN,
                    "azimuth": 34.0,
                    "inclination": 18.0,
                    "classification": None,
                    "quality": float("nan"),
                    "xCoordinate": float("nan"),
                    "yCoordinate": float("nan"),
                    "zCoordinate": float("nan"),
                },
                dtype="object",
            ),
            Dip(
                reference=ValueWithUnit(unitKey="meter", value=0.REMOVED_FOR_CICD_SCAN),
                azimuth=ValueWithUnit(unitKey="dega", value=34),
                inclination=ValueWithUnit(unitKey="dega", value=18.0),
                classification=None,
                quality=None,
                xCoordinate=None,
                yCoordinate=None,
                zCoordinate=None,
            ),
        ),
    ],
)
def test_series_to_dip(series, dip):
    computed_dip = series_to_dip(series)
    assert computed_dip == dip


def test_dip_to_series():
    expected = Dip(
        reference=ValueWithUnit(unitKey="meter", value=0.REMOVED_FOR_CICD_SCAN),
        azimuth=ValueWithUnit(unitKey="dega", value=34),
        inclination=ValueWithUnit(unitKey="dega", value=18.0),
        classification=None,
        quality=None,
        xCoordinate=None,
        yCoordinate=None,
        zCoordinate=None,
    )
    data = pd.Series(
        {
            "reference": 0.REMOVED_FOR_CICD_SCAN,
            "azimuth": 34.0,
            "inclination": 18.0,
            "classification": None,
            "quality": float("nan"),
            "xCoordinate": float("nan"),
            "yCoordinate": float("nan"),
            "zCoordinate": float("nan"),
        },
        dtype="object"
    )

    computed_dip = series_to_dip(data)
    assert computed_dip == expected