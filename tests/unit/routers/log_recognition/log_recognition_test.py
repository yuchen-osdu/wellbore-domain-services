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

import time
from unittest import mock
import pytest

from fastapi import status
from odes_storage import models as m
from odes_storage.exceptions import UnexpectedResponse
from odes_storage.models import CreateUpdateRecordsResponse

from app.clients import StorageRecordServiceClient
from app.routers.log_recognition.family_processor_manager import FamilyProcessorManager

from tests.unit.middleware.traces_middleware_test import ExporterInTest


@pytest.fixture
def log_recognition_testing_setup(app_configurable_with_testclient):
    """ fixture yields tuple: TestClient, storage_client_mock, family processor """
    fp_manager = FamilyProcessorManager(1337)  # want a fresh and independent instance for each test
    with mock.patch('app.routers.log_recognition.log_recognition.family_processor_manager', fp_manager):
        mock_storage = mock.AsyncMock(spec=StorageRecordServiceClient)
        _, client = app_configurable_with_testclient(
                storage_client_mock=mock_storage,
                trace_exporter=ExporterInTest(),
                fake_opendes_authorized_user=True
        )
        yield client, mock_storage, fp_manager


@pytest.mark.parametrize("label, unit, expected", [
    ('GR', 'gAPI', {'family': 'Gamma Ray', 'family_type': ['Gamma Ray'], 'log_unit': 'gAPI', 'base_unit': 'gAPI'}),
    ('TVD', 'cm', {'family': 'True Vertical Depth', 'family_type': ['Reference'], 'log_unit': 'cm', 'base_unit': 'ft'}),
    ('DTC', 'us/cm',
     {'family': 'Compressional Slowness', 'family_type': ['Slowness'], 'log_unit': 'us/cm', 'base_unit': 'us/ft'}),
    ('TRUESTRATIGRAPHICTHICKNESS1', 'ft',
     {"family": "Thickness", "family_type": ["Formation Geometry", "Rock Quality"], "log_unit": "ft", "base_unit": "ft"})
])
def test_family_assignment_rules(log_recognition_testing_setup, label, unit, expected):
    client, mock_storage, _ = log_recognition_testing_setup
    mock_storage.configure_mock(**{
        'get_record.side_effect':
            UnexpectedResponse(status_code=status.HTTP_404_NOT_FOUND, reason_phrase="", content=None, headers=None)
    })

    response = client.post("/log-recognition/family",
                           json={"label": label,
                                 "log_unit": unit})
    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    assert response_json == expected


def test_family_assignment_rules_not_found(log_recognition_testing_setup):
    client, mock_storage, _ = log_recognition_testing_setup
    mock_storage.configure_mock(**{
        'get_record.side_effect':
            UnexpectedResponse(status_code=status.HTTP_404_NOT_FOUND, reason_phrase="", content=None, headers=None)
    })

    response = client.post("/log-recognition/family",
                           json={"label": "unknown", "log_unit": ""})
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_upload_good_catalog(log_recognition_testing_setup):
    good_catalog = {
        "data": {
            "family_catalog": [{"unit": "f", "family": "fake family", "rule": "FF"},
                               {"unit": "g", "family": "other fake family", "rule": "OF"}],
            "main_family_catalog": [{"MainFamily": "Fake", "Family": "fake family", "Unit": "ef"},
                                    {"MainFamily": "Other Fake", "Family": "other fake family", "Unit": "jai"}]
        },
        "legal": {
            "legaltags": [
                "opendes-public-usa-dataset-1"
            ],
            "otherRelevantDataCountries": [
                "US"
            ],
            "status": "compliant"
        },
        "acl": {
            "viewers": [
                "data.default.viewers@opendes.p4d.cloud.slb-ds.com"
            ],
            "owners": [
                "data.default.owners@opendes.p4d.cloud.slb-ds.com"
            ]
        }
    }

    expected_response = CreateUpdateRecordsResponse(recordCount=1, recordIds=['rec1'])

    client, mock_storage, _ = log_recognition_testing_setup
    mock_storage.configure_mock(**{
        'create_or_update_records.return_value': expected_response
    })

    response = client.put("/log-recognition/upload-catalog", json=good_catalog)
    assert response.status_code == status.HTTP_200_OK
    assert CreateUpdateRecordsResponse.parse_raw(response.text) == expected_response


@pytest.mark.parametrize("label, unit, code, expected", [
    ('fantomas', '', status.HTTP_404_NOT_FOUND, {}),
    ('FF', 'f', status.HTTP_200_OK,
     {'family': 'fake family', 'family_type': ['Fake'], 'log_unit': 'f', 'base_unit': 'ef'}),
    ('OF', 'g', status.HTTP_200_OK,
     {'family': 'other fake family', 'family_type': ['Other Fake'], 'log_unit': 'g', 'base_unit': 'jai'}),
    ('AOF', 'gg', status.HTTP_200_OK,
     {'family': "another fake family", 'family_type': ["Other Fake", "Another fake family"],
      'log_unit': 'gg', 'base_unit': 'jaijai'}),
    ('DTC', 'us/cm', status.HTTP_200_OK,
     {'family': 'Compressional Slowness', 'family_type': ['Slowness'], 'log_unit': 'us/cm', 'base_unit': 'us/ft'})
])
def test_family_assignment_rules_custom(log_recognition_testing_setup, label, unit, code, expected):
    record_obj = m.Record(
        data={
            "family_catalog": [
                {"unit": "f", "family": "fake family", "rule": "FF"},
                {"unit": "g", "family": "other fake family", "rule": "OF"},
                {"unit": "gg", "family": "another fake family", "rule": "AOF"}
            ],
            "main_family_catalog": [
                {"MainFamily": "Fake", "Family": "fake family", "Unit": "ef"},
                {"MainFamily": "Other Fake", "Family": "other fake family", "Unit": "jai"},
                {"MainFamily": ["Other Fake", "Another fake family"], "Family": "another fake family", "Unit": "jaijai"}
            ]
        },
        kind="",
        acl=m.StorageAcl(viewers=[], owners=[]),
        legal={}
    )

    client, mock_storage, _ = log_recognition_testing_setup
    mock_storage.configure_mock(**{
        'get_record.return_value': record_obj
    })

    response = client.post("/log-recognition/family", json={"label": label, "log_unit": unit})

    assert response.status_code == code
    if code == status.HTTP_200_OK:
        response_json = response.json()
        assert response_json == expected


@pytest.mark.parametrize("label, unit, code, expected", [
    ('OF', 'F', status.HTTP_404_NOT_FOUND, {}),
    ('DTC', 'us/cm', status.HTTP_200_OK,
     {'family': 'Compressional Slowness', 'family_type': ['Slowness'], 'log_unit': 'us/cm', 'base_unit': 'us/ft'})
])
def test_family_assignment_rules_custom_catalog_not_found(log_recognition_testing_setup, label, unit, code, expected):
    client, mock_storage, _ = log_recognition_testing_setup
    mock_storage.configure_mock(**{
        'get_record.side_effect':
            UnexpectedResponse(status_code=status.HTTP_404_NOT_FOUND, reason_phrase="", content=None, headers=None)
    })

    response = client.post("/log-recognition/family", json={"label": label, "log_unit": unit})

    assert response.status_code == code
    if code == status.HTTP_200_OK:
        response_json = response.json()
        assert response_json == expected


def test_failing_storage(log_recognition_testing_setup):
    unexpected_response = UnexpectedResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                             reason_phrase="", content=b'content', headers=None)
    client, mock_storage, _ = log_recognition_testing_setup
    mock_storage.configure_mock(**{
        'get_record.side_effect': unexpected_response
    })

    response = client.post("/log-recognition/family", json={"label": "MD", "log_unit": "M"})
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_unvalidate_catalogs(log_recognition_testing_setup):
    record_obj = m.Record(
        data={
            "family_catalog": [{"unit": "f", "family": "fake family", "rule": "FF"},
                               {"unit": "g", "family": "other fake family", "rule": "OF"}],
            "main_family_catalog": [{"MainFamily": "Fake", "Family": "fake family", "Unit": "ef"},
                                    {"MainFamily": "Other Fake", "Family": "other fake family", "Unit": "jai"}]
        },
        kind="",
        acl=m.StorageAcl(viewers=[], owners=[]),
        legal={}
    )

    client, mock_storage, family_processor_manager = log_recognition_testing_setup
    mock_storage.configure_mock(**{
        'get_record.return_value': record_obj
    })

    # Force a big catalog_lifetime
    family_processor_manager._catalog_lifetime = 1000

    mock_storage.get_record.assert_not_called()
    response = client.post("/log-recognition/family",
                           json={"label": "FF",
                                 "log_unit": "f"})
    assert response.status_code == status.HTTP_200_OK
    assert mock_storage.get_record.call_count == 1

    response = client.post("/log-recognition/family",
                           json={"label": "FF",
                                 "log_unit": "f"})
    assert response.status_code == status.HTTP_200_OK
    assert mock_storage.get_record.call_count == 1

    # Force a small catalog_lifetime
    family_processor_manager._catalog_lifetime = 1
    # Sorry we need to sleep 1 second
    time.sleep(1)
    response = client.post("/log-recognition/family",
                           json={"label": "FF",
                                 "log_unit": "f"})
    assert response.status_code == status.HTTP_200_OK
    assert mock_storage.get_record.call_count == 2

    time.sleep(1)
    response = client.post("/log-recognition/family",
                           json={"label": "FF",
                                 "log_unit": "f"})
    assert response.status_code == status.HTTP_200_OK
    assert mock_storage.get_record.call_count == 3


def test_invalidate_default_catalogs(log_recognition_testing_setup):
    client, mock_storage, family_processor_manager = log_recognition_testing_setup
    mock_storage.configure_mock(**{
        'get_record.side_effect':
            UnexpectedResponse(status_code=status.HTTP_404_NOT_FOUND, reason_phrase="", content=None, headers=None)
    })

    response = client.post("/log-recognition/family",
                           json={"label": "GR",
                                 "log_unit": "gApi"})
    assert response.status_code == status.HTTP_200_OK
    assert mock_storage.get_record.call_count == 1

    response = client.post("/log-recognition/family",
                           json={"label": "GR",
                                 "log_unit": "gApi"})
    assert response.status_code == status.HTTP_200_OK
    assert mock_storage.get_record.call_count == 1  # we are inside the catalog_lifetime so no call to DE

    family_processor_manager._catalog_lifetime = 1
    time.sleep(1)
    response = client.post("/log-recognition/family",
                           json={"label": "GR",
                                 "log_unit": "gApi"})
    assert response.status_code == status.HTTP_200_OK
    assert mock_storage.get_record.call_count == 2  # catalog_lifetime exceeded, one more call to DE expected


def test_no_catalog(log_recognition_testing_setup):
    record_obj = m.Record(
        data={
            "main_family_catalog": [{"MainFamily": "Fake", "Family": "fake family", "Unit": "ef"},
                                    {"MainFamily": "Other Fake", "Family": "other fake family", "Unit": "jai"}]
        },
        kind="",
        acl=m.StorageAcl(viewers=[], owners=[]),
        legal={}
    )
    client, mock_storage, _ = log_recognition_testing_setup
    mock_storage.configure_mock(**{
        'get_record.return_value': record_obj
    })

    response = client.post("/log-recognition/family", json={"label": "MD", "log_unit": "m"})
    assert response.status_code == status.HTTP_200_OK


def test_no_main_family_catalog(log_recognition_testing_setup):
    record_obj = m.Record(
        data={
            "family_catalog": [{"unit": "f", "family": "fake family", "rule": "FF"},
                               {"unit": "g", "family": "other fake family", "rule": "OF"}]
        },
        kind="",
        acl=m.StorageAcl(viewers=[], owners=[]),
        legal={}
    )
    client, mock_storage, _ = log_recognition_testing_setup
    mock_storage.configure_mock(**{
        'get_record.return_value': record_obj
    })

    response = client.post("/log-recognition/family", json={"label": "OF", "log_unit": "g"})
    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    assert response_json == {"family": "other fake family", "family_type": None, "log_unit": "g", "base_unit": None}
