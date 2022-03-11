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
from app.routers.ddms_v3.ddms_v3_utils import DMSV3RouterUtils, OSDU_WELL_VERSION_REGEX, OSDU_WELLBORE_VERSION_REGEX, \
    OSDU_WELLLOG_VERSION_REGEX, OSDU_WELLBORETRAJECTORY_VERSION_REGEX, OSDU_WELLBOREMARKERSET_VERSION_REGEX


GET_WO_VERSION_PARAMS = [
    (OSDU_WELL_VERSION_REGEX, "", ""),
    (OSDU_WELL_VERSION_REGEX, "9nlnBplxN:master-data--Well:g657DSIO", "9nlnBplxN:master-data--Well:g657DSIO"),
    (OSDU_WELL_VERSION_REGEX, "9nlnBplxN:master-data--Well:g657DSIO:", "9nlnBplxN:master-data--Well:g657DSIO"),
    (OSDU_WELL_VERSION_REGEX, "9nlnBplxN:master-data--Well:g657DSIO:123456", "9nlnBplxN:master-data--Well:g657DSIO"),
    (OSDU_WELLBORE_VERSION_REGEX, "", ""),
    (OSDU_WELLBORE_VERSION_REGEX, "9nlnBplxN:master-data--Wellbore:g657DSIO", "9nlnBplxN:master-data--Wellbore:g657DSIO"),
    (OSDU_WELLBORE_VERSION_REGEX, "9nlnBplxN:master-data--Wellbore:g657DSIO:", "9nlnBplxN:master-data--Wellbore:g657DSIO"),
    (OSDU_WELLBORE_VERSION_REGEX, "9nlnBplxN:master-data--Wellbore:g657DSIO:123456", "9nlnBplxN:master-data--Wellbore:g657DSIO"),
    (OSDU_WELLLOG_VERSION_REGEX, "", ""),
    (OSDU_WELLLOG_VERSION_REGEX, "9nlnBplxN:work-product-component--WellLog:g657DSIO", "9nlnBplxN:work-product-component--WellLog:g657DSIO"),
    (OSDU_WELLLOG_VERSION_REGEX, "9nlnBplxN:work-product-component--WellLog:g657DSIO:", "9nlnBplxN:work-product-component--WellLog:g657DSIO"),
    (OSDU_WELLLOG_VERSION_REGEX, "9nlnBplxN:work-product-component--WellLog:g657DSIO:123456", "9nlnBplxN:work-product-component--WellLog:g657DSIO"),
    (OSDU_WELLBORETRAJECTORY_VERSION_REGEX, "", ""),
    (OSDU_WELLBORETRAJECTORY_VERSION_REGEX, "9nlnBplxN:work-product-component--WellboreTrajectory:g657DSIO", "9nlnBplxN:work-product-component--WellboreTrajectory:g657DSIO"),
    (OSDU_WELLBORETRAJECTORY_VERSION_REGEX, "9nlnBplxN:work-product-component--WellboreTrajectory:g657DSIO:", "9nlnBplxN:work-product-component--WellboreTrajectory:g657DSIO"),
    (OSDU_WELLBORETRAJECTORY_VERSION_REGEX, "9nlnBplxN:work-product-component--WellboreTrajectory:g657DSIO:123456", "9nlnBplxN:work-product-component--WellboreTrajectory:g657DSIO"),
    (OSDU_WELLBOREMARKERSET_VERSION_REGEX, "", ""),
    (OSDU_WELLBOREMARKERSET_VERSION_REGEX, "9nlnBplxN:work-product-component--WellboreMarkerSet:g657DSIO", "9nlnBplxN:work-product-component--WellboreMarkerSet:g657DSIO"),
    (OSDU_WELLBOREMARKERSET_VERSION_REGEX, "9nlnBplxN:work-product-component--WellboreMarkerSet:g657DSIO:", "9nlnBplxN:work-product-component--WellboreMarkerSet:g657DSIO"),
    (OSDU_WELLBOREMARKERSET_VERSION_REGEX, "9nlnBplxN:work-product-component--WellboreMarkerSet:g657DSIO:123456", "9nlnBplxN:work-product-component--WellboreMarkerSet:g657DSIO"),
]


@pytest.mark.parametrize("version_regexp, record_id, expected_id", GET_WO_VERSION_PARAMS)
def test_get_id_without_version(version_regexp, record_id, expected_id):
    record_wo_version = DMSV3RouterUtils.get_id_without_version(version_regexp, record_id)
    assert record_wo_version == expected_id



@pytest.mark.parametrize(
    "record_id_version, expected",
    [
        (
            "opendes:work-product-component--WellLog:713b4988cca14719867ae3b1004edf4e:1234",
            1234
        ),
        (
            "opendes:work-product-component--WellboreTrajectory:713b4988cca14719867ae3b1004edf4e:465",
            465
        ),
        (
            "data-partition:work-product-component--WellLog:713b4988cca14719867ae3b1004edf4e:1646997150219714",
            1646997150219714
        ),
        (
            "osdu:log:a01d160506bd4f22a323eb2734cb370c:1991106102849593087389851558600877159",
            1991106102849593087389851558600877159
        ),

    ]
)
def test_get_version_from_record_id_version(record_id_version, expected):
    computed = DMSV3RouterUtils.get_version_from_record_id_version(record_id_version)
    assert computed == expected


@pytest.mark.parametrize(
    "record_id_version",
    [
        "opendes:work-product-component--WellLog:713b4988cca14719867ae3b1004edf4e:",
        "opendes:work-product-component--WellLog:713b4988cca14719867ae3b1004edf4e",
        "dummy",
        ":::1324"
    ]
)
def test_get_version_from_record_id_version_raise(record_id_version):
    with pytest.raises(RuntimeError):
        DMSV3RouterUtils.get_version_from_record_id_version(record_id_version)
