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


from .bulk_filter import BulkFilter, BulkReadFilterOperator, BulkReadFilters
from .bulk_persistence_config import (
    MAX_COLUMNS_RETURN,
    MAX_COLUMNS_WRITE_CHUNK,
    BulkPersistenceConfig,
    get_config,
    set_config_getter,
)
from .bulk_uri import BulkURI
from .capture_timings import capture_timings
from .consistency_checks import ConsistencyException, DataConsistencyChecks
from .dask import client as dask_client
from .dask.bulk_catalog import (
    BulkCatalog,
    async_load_bulk_catalog_with_blob_storage,
    async_save_bulk_catalog_with_blob_storage,
)
from .dask.client import DaskDistributedClient
from .dask.dask_bulk_storage import DaskBulkStorage
from .dask.dask_bulk_storage_local import (
    make_local_dask_bulk_storage,
    make_local_dask_storage_parameters,
)

# bulk reader
from .bulk_reader_dask import BulkReaderDask
from .bulk_reader_wdms_worker import BulkReaderWdmsWorker

from .dask.errors import (
    BulkCurvesNotFound,
    BulkError,
    BulkRecordNotFound,
    FilterError,
    TooManyColumnsRequested,
    internal_bulk_exceptions,
)
from .dask.localcluster import DaskException
from .dask.storage_path_builder import hash_record_id
from .dask.traces import (
    submit_with_trace,
    trace_attributes_root_span,
    trace_dataframe_attributes,
)
from .dataframe_persistence import (
    create_and_store_dataframe,
    download_bulk,
    get_dataframe,
)
from .dataframe_serializer import (
    DataframeSerializerAsync,
    DataframeSerializerSync,
)
from .dataframe_validators import (
    DataFrameValidationFunc,
    auto_cast_columns_to_string,
    columns_type_must_be_string,
    no_validation,
)
from .exceptions import (
    InvalidBulkException,
    NoBulkException,
    NoDataException,
    RecordNotFoundException,
    UnknownChannelsException,
)
from .json_orient import JSONOrient
from .mime_types import MimeType, MimeTypes
from .model_chunking import (
    DataframeBasicDescribe,
    DataframeDescribe,
    GetDataParams,
)
from .sessions_storage import (
    CommitSessionResponse,
    Session,
    SessionException,
    SessionInternal,
    SessionInvalidState,
    SessionNotFound,
    SessionsStorage,
    SessionState,
    SessionUpdatedEtagUnmatched,
    SessionUpdateMode,
)
from .statistics import BulkStatistics, exceptions
from .statistics.models import BulkDataStatisticsResponse

# TMP: this should probably not be exposed outside the bulk_persistence package
from .temp_dir import get_temp_dir
