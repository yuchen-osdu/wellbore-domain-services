from typing import Type

from odes_storage.models import Record
from pydantic import BaseModel

# translate any model to a record

def to_record(obj: BaseModel) -> Record:
    """
    create a Record instance from another model which should shared Record schema.
    :param obj: input model instance, expected to be 'compatible' with Record model
    :return: record object
    """
    return Record(**obj.dict(exclude_unset=True, by_alias=True))


def from_record(cls: Type[BaseModel], record: Record):
    """
    create a Record instance from another model which should shared Record schema.
    :param cls: model class use to instantiate the object
    :param record: input record object
    :return: object instantiate (of class 'cls')
    """
    return cls(**record.dict(exclude_unset=True, by_alias=True))


def record_to_dict(record: BaseModel) -> dict:
    """ Generate a dictionary representation of the model, use exclude_unset=True and by_alias=True"""
    return record.dict(exclude_unset=True, by_alias=True)


def record_to_json(record: BaseModel) -> str:
    """ Generate a JSON representation of the model, use exclude_unset=True and by_alias=True"""
    return record.json(exclude_unset=True, by_alias=True)
