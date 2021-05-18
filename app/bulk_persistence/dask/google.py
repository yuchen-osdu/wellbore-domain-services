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


from osdu_gcp.storage.blob_storage_gcp import GCloudAioStorage
from app.bulk_persistence.dask.blob_storage import DaskBlobStorageBase, DaskDriverBlobStorage


class DaskBlobStorageGoogle(DaskBlobStorageBase):
    """Instantiate a DaskDriverBlobStorage with the google blob storage file system."""

    async def build_dask_blob_storage(self, tenant):  # TODO
        gcp_store = GCloudAioStorage(service_account_file=tenant.credentials)
        token = await gcp_store._get_access_token(tenant.project_id, tenant.bucket_name)
        storage_options = {'token': token}

        base_directory = f'{tenant.bucket_name}/dask_data' # TODO remove dask_data

        _dask = DaskDriverBlobStorage(protocol='gs',
                                      base_directory=base_directory,
                                      storage_options=storage_options)
        await _dask.init_client()
        return _dask
