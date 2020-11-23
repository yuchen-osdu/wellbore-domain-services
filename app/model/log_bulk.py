from typing import Optional, Union
import uuid
from jsonpath_ng import parse as parse_jsonpath
from jsonpath_ng.jsonpath import Parent as JsonParent
from odes_storage.models import Record


class LogBulkHelper:
    # TODO find a better name, LogRecordHelper. but I don't like 'helper', its just a synonymous of bag of several thing
    # breaking single responsibility principle
    """ gather common bulk manipulation of a log record"""

    @staticmethod
    def new_bulk_id() -> str:
        return str(uuid.uuid4())

    @classmethod
    def _bulk_urn_encode(cls, bulk_id: str) -> str:
        return uuid.UUID(bulk_id).urn

    @classmethod
    def _bulk_urn_decode(cls, urn: str) -> Optional[str]:
        return str(uuid.UUID(urn))

    @classmethod
    def _get_record_data_dict(cls, record: Union[dict, Record]) -> dict:
        if isinstance(record, Record):
            if record.data is None:
                record.data = {}
            else:
                assert isinstance(record.data, dict)
            data_dict = record.data
        elif isinstance(record, dict):
            data_dict = record.setdefault('data', {})
        else:
            raise ValueError(str(type(record)) + ' is invalid')
        return data_dict

    @classmethod
    def _set_bulk_id_in_wks(cls, record: Union[dict, Record], bulk_id):
        """ for now it used externalIds, to be updated once schema is fixed with log.data.bulkId """
        bulk_urn = cls._bulk_urn_encode(bulk_id)
        cls._get_record_data_dict(record).setdefault('log', {})['bulkURI'] = bulk_urn

    @classmethod
    def _get_bulk_id_from_wks(cls, record: Union[dict, Record]) -> Optional[str]:
        bulk_uri = cls._get_record_data_dict(record).get('log', {}).get('bulkURI', None)
        return cls._bulk_urn_decode(bulk_uri) if bulk_uri else None

    @classmethod
    def update_bulk_id(cls,
                       record: Union[dict, Record],
                       bulk_id,
                       custom_bulk_id_path: Optional[str] = None):
        """
        Update bulk id within a log record. Note that the custom path cannot be applied when using a strict structured model
        It creates the field if not exist
        :param record: record to update, either structured based model or dict.
        :param bulk_id: bulk reference (id, uri ...) to set
        :param custom_bulk_id_path: !! incompatible with log model
        """
        if custom_bulk_id_path is None:
            cls._set_bulk_id_in_wks(record, bulk_id)
        else:
            record_dict = record if isinstance(record, dict) else {'data': record.data}

            # experimentation, no error management
            field_name = custom_bulk_id_path.split('.')[-1]
            json_exp = parse_jsonpath(custom_bulk_id_path).child(JsonParent())
            json_exp.find(record_dict)[0].value[field_name] = bulk_id
            # if only support existing field, it can be done with a simple update call
            # parse_jsonpath(custom_bulk_id_path).update(record, bulk_ref)

            if isinstance(record, Record):
                record.data = record_dict['data']

    @classmethod
    def get_bulk_id(cls,
                    record: Union[dict, Record],
                    custom_bulk_id_path: Optional[str] = None) -> Optional[str]:
        """
        :param record:
        :param custom_bulk_id_path: !! incompatible with log model
        :return: bulk id if any else None
        """
        if custom_bulk_id_path is None:
            return cls._get_bulk_id_from_wks(record)

        record_dict = record if isinstance(record, dict) else {'data': record.data}
        matches = parse_jsonpath(custom_bulk_id_path).find(record_dict)
        return matches[0].value if len(matches) > 0 else None

