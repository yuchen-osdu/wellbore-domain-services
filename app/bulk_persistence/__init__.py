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

from .bulk_uri import BulkURI
from .bulk_filter import BulkReadFilters, BulkReadFilterOperator
from .model_chunking import GetDataParams, DataframeBasicDescribe, DataframeDescribe
from .dask.dask_bulk_storage import DaskBulkStorage
from .dask.dask_bulk_storage_local import make_local_dask_bulk_storage
from .dask.storage_path_builder import hash_record_id
from .dask.traces import trace_dataframe_attributes, submit_with_trace, trace_attributes_root_span
from .dataframe_persistence import create_and_store_dataframe, get_dataframe, download_bulk
from .dataframe_serializer import DataframeSerializerAsync, DataframeSerializerSync
from .dataframe_validators import auto_cast_columns_to_string, columns_type_must_be_string, DataFrameValidationFunc, no_validation
from .json_orient import JSONOrient
from .mime_types import MimeTypes, MimeType
from .tenant_provider import resolve_tenant
from .exceptions import UnknownChannelsException, InvalidBulkException, NoBulkException, NoDataException, RecordNotFoundException
from .consistency_checks import ConsistencyException, DataConsistencyChecks
from .dask.client import DaskClient
from .dask.localcluster import DaskException
from .capture_timings import capture_timings
from .sessions_storage import Session, SessionsStorage, \
            SessionNotFound, SessionInvalidState, SessionUpdatedEtagUnmatched, SessionException, \
            SessionState, SessionUpdateMode, SessionInternal, CommitSessionResponse

# TMP: this should probably not be exposed outside of the bulk_persistence package
from .temp_dir import get_temp_dir
