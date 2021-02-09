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
