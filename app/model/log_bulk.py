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

from typing import Optional, Tuple

from jsonpath_ng import parse as parse_jsonpath
from jsonpath_ng.jsonpath import Parent as JsonParent
from odes_storage.models import Record

from app.bulk_persistence import BulkId


class LogBulkHelper:
    # TODO find a better name, LogRecordHelper. but I don't like 'helper', its just a synonymous of bag of several thing
    # breaking single responsibility principle
    """ gather common bulk manipulation of a log record"""

    @classmethod
    def _get_record_data_dict(cls, record: Record) -> dict:
        if record.data is None:
            record.data = {}
        return record.data

    @classmethod
    def _set_bulk_id_in_wks(cls, record: Record, bulk_id, prefix: str) -> None:
        """ for now it used externalIds, to _get_bulk_id_from_wksbe updated once schema is fixed with log.data.bulkId """
        bulk_urn = BulkId.bulk_urn_encode(bulk_id, prefix=prefix)
        cls._get_record_data_dict(record).setdefault('log', {})['bulkURI'] = bulk_urn

    @classmethod
    def _get_bulk_id_from_wks(cls, record: Record) -> Optional[str]:
        bulk_uri = (
            cls._get_record_data_dict(record)
            .get("log", {})
            .get("bulkURI", None)
        )
        return BulkId.bulk_urn_decode(bulk_uri) if bulk_uri else (None, None)

    @classmethod
    def update_bulk_id(
        cls, record: Record, bulk_id, custom_bulk_id_path: Optional[str] = None, prefix: Optional[str] = None
    ):
        """
        Update bulk id within a log record. Note that the custom path cannot be applied when using a strict structured model
        It creates the field if not exist
        :param record: record to update.
        :param bulk_id: bulk reference (id, uri ...) to set
        :param custom_bulk_id_path: !! incompatible with log model
        """
        if custom_bulk_id_path is None:  # what about empty string ?
            cls._set_bulk_id_in_wks(record, bulk_id, prefix)
        else:
            record_dict = {"data": record.data}

            # experimentation, no error management
            field_name = custom_bulk_id_path.split(".")[-1]
            json_exp = parse_jsonpath(custom_bulk_id_path).child(JsonParent())

            json_exp.find(record_dict)[0].value[
                field_name
            ] = BulkId.bulk_urn_encode(bulk_id, prefix=prefix)
            # if only support existing field, it can be done with a simple update call
            # parse_jsonpath(custom_bulk_id_path).update(record, bulk_ref)
            record.data = record_dict["data"]

    @classmethod
    def get_bulk_id(
        cls, record: Record, custom_bulk_id_path: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        :param record:
        :param custom_bulk_id_path: !! incompatible with log model
        :return: bulk id if any else None
        """
        if custom_bulk_id_path is None:  # what about empty string ?
            return cls._get_bulk_id_from_wks(record)

        record_dict = {"data": record.data}
        matches = parse_jsonpath(custom_bulk_id_path).find(record_dict)
        if len(matches) > 0:
            return BulkId.bulk_urn_decode(matches[0].value)
        return None, None
        
