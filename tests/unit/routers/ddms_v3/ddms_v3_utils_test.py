import numpy as np
import pandas as pd
from typing import Dict, Any
import json
import pytest
from app.bulk_persistence import JSONOrient
from app.routers.ddms_v3.ddms_v3_utils import DMSV3RouterUtils
from fastapi import HTTPException
from dataclasses import dataclass


def generate_df(column_names, nb_rows):
    index = list(range(nb_rows))
    df = pd.DataFrame(
        np.random.randint(-100, 1000, size=(nb_rows, len(column_names))), index=index)
    df.columns = column_names
    return df


@dataclass()
class FakeRequest:
    headers: Dict[str, str]
    body_content: Any

    async def body(self):
        return self.body_content

    async def json(self):
        return json.loads(self.body_content)


@pytest.mark.asyncio
@pytest.mark.parametrize("orient", [o for o in JSONOrient])
async def test_get_df_from_request_in_json(orient):
    expected_df = generate_df(['MD', 'X'], 8)
    request = FakeRequest(
        headers={"Content-Type": "application/json"},
        body_content=expected_df.to_json(orient=orient))

    actual_df = await DMSV3RouterUtils.get_df_from_request(request, orient)
    pd.testing.assert_frame_equal(actual_df, expected_df, check_dtype=False)  # because from json can switch int32/int64


@pytest.mark.asyncio
@pytest.mark.parametrize("content_type", ["", "image/png"])
async def test_get_df_from_request_invalid_content_type(content_type):
    request = FakeRequest(
        headers={"Content-Type": content_type},
        body_content=None)

    with pytest.raises(HTTPException) as ex_info:
        await DMSV3RouterUtils.get_df_from_request(request)

    assert ex_info.value.status_code == 400
