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

import concurrent.futures
from app.bulk_persistence.blob_storage import create_and_write_blob, BlobFileExporters, load_from_parquet
import pytest
import pandas as pd
from os import path

Process_pool_executor = concurrent.futures.ProcessPoolExecutor(2)
Thread_pool_executor = concurrent.futures.ThreadPoolExecutor(2)

DUMMY_CONTENT_BYTES = b'dummy content'
CONSTANT_PLAIN_TEXT = "plain/text"


def fake_exporter(file_path: str, *args, **kwargs):
    # print('fake exporter received id=', file_id)
    with open(file_path, 'wb') as file:
        file.write(DUMMY_CONTENT_BYTES)
    return file_path, {'content-type': CONSTANT_PLAIN_TEXT}


def fake_exporter_as_bytes(file_id: str, *args, **kwargs):
    return DUMMY_CONTENT_BYTES, {'content-type': CONSTANT_PLAIN_TEXT}


async def async_fake_exporter(file_id: str, *args, **kwargs):
    return fake_exporter(file_id)


def sync_to_async(sync):
    async def sync_wrapped_in_async(*args, **kwargs):
        sync(*args, **kwargs)

    return sync_wrapped_in_async


VALID_VALUES_FORMS = [
    ([[10, 11], [20, 21], [30, 31]]),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "executor,exporter", [
        (None, async_fake_exporter),
        (None, fake_exporter),
        (None, fake_exporter_as_bytes),
        (Process_pool_executor, fake_exporter),
        (Thread_pool_executor, fake_exporter)
    ])
async def test_executor_exported_combination(executor, exporter):
    table = pd.DataFrame([[10, 11], [20, 21], [30, 31]], index=[1, 2, 3], columns=['c1', 'c2'])

    async with create_and_write_blob(table,
                                     executor=executor,
                                     custom_export_to_file_fn=exporter) as blob:
        assert blob.content_type == CONSTANT_PLAIN_TEXT
        assert blob.data.read() == DUMMY_CONTENT_BYTES
        assert blob.metadata['content-type'] == CONSTANT_PLAIN_TEXT


@pytest.mark.asyncio
@pytest.mark.parametrize("values_form", VALID_VALUES_FORMS)
async def test_create_blob_various_valid_values(values_form):
    table = pd.DataFrame(values_form, index=[1, 2, 3], columns=['c1', 'c2'])

    async with create_and_write_blob(table,
                                     executor=None,
                                     file_exporter=BlobFileExporters.PARQUET) as bulk_blob:
        df = load_from_parquet(bulk_blob.data)
        assert df.columns.tolist() == table.columns.tolist()
        assert df.index.tolist() == table.index.tolist()
        assert df['c1'].tolist() == [10, 20, 30]
        assert df['c2'].tolist() == [11, 21, 31]


@pytest.mark.asyncio
@pytest.mark.parametrize("values_form", VALID_VALUES_FORMS)
async def test_create_blob_various_valid_values_no_column(values_form):
    table = pd.DataFrame(values_form, index=[1, 2, 3])

    async with create_and_write_blob(table,
                                     executor=None,
                                     file_exporter=BlobFileExporters.PARQUET) as bulk_blob:
        df = load_from_parquet(bulk_blob.data)
        assert df.columns.tolist() == [0, 1]
        assert df.index.tolist() == table.index.tolist()
        assert df[0].tolist() == [10, 20, 30]
        assert df[1].tolist() == [11, 21, 31]


@pytest.mark.asyncio
async def test_create_blob_should_forward_filename_and_df():
    def capture_it(*args, **kwargs):
        capture_it.args = args
        capture_it.kwargs = kwargs
        return b'', {}

    table = pd.DataFrame([[10, 11], [20, 21], [30, 31]], index=[1, 2, 3])
    async with create_and_write_blob(table,
                                     executor=None,
                                     custom_export_to_file_fn=capture_it,
                                     blob_id='my_custom_filename') as blob:
        assert blob.id == 'my_custom_filename'
        assert capture_it.args[0] is not None
        dir_path, file_name = path.split(capture_it.args[0])
        assert path.exists(dir_path)
        df = capture_it.args[1]
        assert df.columns.tolist() == [0, 1]
        assert df.index.tolist() == [1, 2, 3]
        assert df[0].tolist() == [10, 20, 30]
        assert df[1].tolist() == [11, 21, 31]
