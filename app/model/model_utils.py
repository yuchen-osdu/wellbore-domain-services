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

from typing import Dict, Optional, Type

from odes_storage.models import Record
from pydantic import BaseModel, Field, field_validator


class SessionMeta(BaseModel):
    meta: Optional[Dict[str, str]] = Field(
        None,
        description="miscellaneous metadata associated to the session. The session creator can set some data here."
    )
     
    @field_validator("meta", mode="before")
    def coerce_meta_values_to_str(cls, v):
        if v is None:
            return v
        return {k: str(val) for k, val in v.items()}

# translate any model to a record

def to_record(obj: BaseModel) -> Record:
    """
    create a Record instance from another model which should shared Record schema.
    :param obj: input model instance, expected to be 'compatible' with Record model
    :return: record object
    """
    return Record(**obj.model_dump(exclude_unset=True, by_alias=True))


def from_record(cls: Type[BaseModel], record: Record):
    """
    create a Record instance from another model which should shared Record schema.
    :param cls: model class use to instantiate the object
    :param record: input record object
    :return: object instantiate (of class 'cls')
    """
    return cls(**record.model_dump(exclude_unset=True, by_alias=True))


def record_to_dict(record: BaseModel) -> dict:
    """ Generate a dictionary representation of the model, use exclude_unset=True and by_alias=True"""
    return record.model_dump(exclude_unset=True, by_alias=True)


def record_to_json(record: BaseModel) -> str:
    """ Generate a JSON representation of the model, use exclude_unset=True and by_alias=True"""
    return record.model_dump_json(exclude_unset=True, by_alias=True)
