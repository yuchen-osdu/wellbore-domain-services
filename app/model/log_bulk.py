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

from typing import Optional, Union

from jsonpath_ng import parse as parse_jsonpath
from jsonpath_ng.jsonpath import Parent as JsonParent
from odes_storage.models import Record

from app.bulk_persistence.bulk_uri import BulkURI


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
    def _get_bulk_uri_from_wks(cls, record: Record) -> Optional[str]:
        bulk_uri = (
            cls._get_record_data_dict(record)
            .get("log", {})
            .get("bulkURI", None)
        )
        return bulk_uri

    @classmethod
    def update_bulk_uri(cls, record: Record, bulk_uri: BulkURI, custom_bulk_id_path: Optional[str] = None):
        """
        Update bulk id within a log record. Note that the custom path cannot be applied when using a strict structured model
        It creates the field if not exist
        :param record: record to update.
        :param bulk_uri: either already encode uri as string or BulkURI
        :param custom_bulk_id_path: !! incompatible with log model
        """
        uri_value = bulk_uri.encode()
        if custom_bulk_id_path is None:  # what about empty string ?
            cls._get_record_data_dict(record).setdefault('log', {})['bulkURI'] = uri_value
        else:
            record_dict = {"data": record.data}

            # experimentation, no error management
            field_name = custom_bulk_id_path.split(".")[-1]
            json_exp = parse_jsonpath(custom_bulk_id_path).child(JsonParent())

            json_exp.find(record_dict)[0].value[field_name] = uri_value
            # if only support existing field, it can be done with a simple update call
            # parse_jsonpath(custom_bulk_id_path).update(record, bulk_ref)
            record.data = record_dict["data"]

    @classmethod
    def get_bulk_uri(cls, record: Record, custom_bulk_id_path: Optional[str] = None) -> BulkURI:
        """
        :param record:
        :param custom_bulk_id_path: !! incompatible with log model
        :return: BulkURI, could be invalid if none
        """
        if custom_bulk_id_path is None:  # what about empty string ?
            return BulkURI.decode(cls._get_bulk_uri_from_wks(record))

        record_dict = {"data": record.data}
        matches = parse_jsonpath(custom_bulk_id_path).find(record_dict)
        if len(matches) > 0:
            return BulkURI.decode(matches[0].value)
        return BulkURI.invalid()
