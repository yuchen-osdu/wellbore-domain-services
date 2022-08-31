# Copyright 2022 Schlumberger
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

from typing import Callable, Awaitable, Optional

from odes_storage.models import Record

from app.model.osdu_model import RecordId, RecordVersion
from .request_dependency import RequestDependencyBase, RequestDependencyMetaClass

GetRecordFunction = Callable[[RecordId, Optional[RecordVersion]], Awaitable[Record]]


class FetchRecordDependency(RequestDependencyBase, metaclass=RequestDependencyMetaClass):
    """ async function to fetch the whole record """
    pass


class FetchRecordPartialDependency(RequestDependencyBase, metaclass=RequestDependencyMetaClass):
    """ async function to fetch partial record with only BulkURI field"""
    pass
