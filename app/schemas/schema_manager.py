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

import json
from copy import deepcopy
from enum import IntEnum
from os import path, listdir
from typing import Union, List, Tuple

import jsonschema
from fastapi.encoders import jsonable_encoder
from odes_storage.models import Record
from wellbore_schema_manipulation.schema_manipulation import JSonSchemaManipulator
from wellbore_schema_manipulation.schema_validation import JSonValidator

from app.clients.wellbore_schema_client import get_schema_service
from app.context import Context


class SchemaMode(IntEnum):
    ORIGINAL = 0
    OPTIMISED = 1
    EXTRA_FORBID = 2
    EXTRA_FORBID_OPTIMISED = 3


class SchemaManager:
    schema_library: dict = {}  # dictionary associating Kind to json schema
    optimised_schema_library: dict = {}  # dictionary associating Kind to json validator
    schema_forbid_extra_library: dict = {}  # dictionary associating Kind to json schema
    optimised_schema_forbid_extra_library: dict = {}  # dictionary associating Kind to json validator

    @staticmethod
    def _create_versions_of_schema(original_schema: dict) -> Tuple:
        """

        :param original_schema:
        :return: (original_schema, optimised_schema, forbid_extra_schema, optimised_forbid_extra_schema)
        """
        JSonSchemaManipulator.remove_unsupported_id(original_schema)

        # Optimise schema
        json_optimised_schema = JSonSchemaManipulator.optimise_schema(original_schema)

        # forbid extra schema
        json_forbid_extra_schema_content = deepcopy(original_schema)
        JSonSchemaManipulator.forbid_extra(json_forbid_extra_schema_content)

        # optimise forbid extra schema
        json_optimised_forbid_extra_schema = JSonSchemaManipulator.optimise_schema(
            json_forbid_extra_schema_content)

        return original_schema, json_optimised_schema, json_forbid_extra_schema_content, json_optimised_forbid_extra_schema

    @staticmethod
    def load_known_schemas():
        """
        Load all schemas stored in the known_schemas folder and store them in the schema library
        :return:
        """
        schema_directory = path.join(path.dirname(path.realpath(__file__)), "known_schemas")
        json_files = [json_file for json_file in listdir(schema_directory) if json_file.endswith('.json')]
        for json_file in json_files:
            with open(path.join(path.dirname(path.realpath(__file__)), "known_schemas", json_file)) as json_file_stream:
                json_schema_content = json.load(json_file_stream)

                json_schema_content, json_optimised_schema, json_forbid_extra_schema_content, \
                json_optimised_forbid_extra_schema = SchemaManager._create_versions_of_schema(json_schema_content)

                kind = json_schema_content["x-osdu-schema-source"]
                SchemaManager.schema_library[kind] = json_schema_content
                SchemaManager.optimised_schema_library[kind] = json_optimised_schema
                SchemaManager.schema_forbid_extra_library[kind] = json_forbid_extra_schema_content
                SchemaManager.optimised_schema_forbid_extra_library[kind] = json_optimised_forbid_extra_schema

    @staticmethod
    async def _load_unknown_schema(kind: str, ctx: Context) -> dict:
        """
        Use schema service to get a schema.
        The call to schema service uses caller's token and cannot be cached
        :param kind:
        :param ctx:
        :return:
        """
        # Retrieve schema from schema service
        schema_client = await get_schema_service(ctx)
        schema = await schema_client.get_schema(id=kind, data_partition_id=ctx.partition_id)
        return schema

    @staticmethod
    def _get_known_schema(kind: str, mode: SchemaMode) -> Union[dict, None]:
        """
        Get known schema associated to this kind
        :param kind: schema kind
        :return:
        """
        if mode == SchemaMode.ORIGINAL:
            return SchemaManager.schema_library.get(kind, None)
        elif mode == SchemaMode.OPTIMISED:
            return SchemaManager.optimised_schema_library.get(kind, None)
        elif mode == SchemaMode.EXTRA_FORBID:
            return SchemaManager.schema_forbid_extra_library.get(kind, None)
        elif mode == SchemaMode.EXTRA_FORBID_OPTIMISED:
            return SchemaManager.optimised_schema_forbid_extra_library.get(kind, None)
        else:
            return None

    @staticmethod
    async def get_schema(kind: str, ctx: Context, mode: SchemaMode) -> Union[dict, jsonschema.protocols.Validator]:
        """

        :param kind:
        :param ctx:
        :param mode:
        :return:
        """
        schema = SchemaManager._get_known_schema(kind, mode)
        if schema is None:
            schema = await SchemaManager._load_unknown_schema(kind=kind, ctx=ctx)
            schemas = SchemaManager._create_versions_of_schema(schema)
            # TODO decide if we put the schema in cache, it can be done here
            return schemas[mode]
        return schema

    async def validate_records(self, records: List[Record], ctx: Context,
                               mode: SchemaMode = SchemaMode.EXTRA_FORBID_OPTIMISED):
        """

        :param records:
        :param ctx:
        :param mode:
        :return:
        """
        entities = [jsonable_encoder(entity_record, exclude_none=True, exclude_unset=True, by_alias=True) for
                    entity_record in records]
        await self._validate_entities(entities, ctx, mode)

    async def _validate_entities(self, entities: List[dict], ctx: Context,
                                 mode: SchemaMode = SchemaMode.EXTRA_FORBID_OPTIMISED):
        """

        :param entities:
        :param ctx:
        :param mode:
        :return:
        """
        for entity_record in entities:
            kind = entity_record["kind"]
            validator = await self.get_schema(kind, ctx=ctx, mode=mode)
            if mode in [SchemaMode.OPTIMISED, SchemaMode.EXTRA_FORBID_OPTIMISED]:
                JSonValidator.validate_optimized(entity=entity_record, validator=validator)
            else:
                JSonValidator.validate(entity=entity_record, schema=validator)
