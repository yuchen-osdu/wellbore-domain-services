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

from typing import List
import asyncio
from functools import reduce
from collections import namedtuple

from fastapi import HTTPException, status
from odes_search.models import QueryRequest, CursorQueryResponse

from app.routers.search import search_wrapper
from app.clients import SearchServiceClient, StorageRecordServiceClient
from app.model.entity_utils import Entity, format_kind, get_kind_meta
from app.utils import Context


class StorageHelper:
    @staticmethod
    def _status_code_from_exception(exp) -> int:
        if not isinstance(exp, Exception):
            return status.HTTP_200_OK

        # in order to get status code from various exception without explicitly typing it
        return int(getattr(exp, 'status_code', status.HTTP_500_INTERNAL_SERVER_ERROR))

    @staticmethod
    async def delete_recursively(
            ctx: Context,
            entity_id: str,
            relationship: str,
            entity_list: List[Entity],
            data_partition_id: str,
            search_service: SearchServiceClient,
            storage_service: StorageRecordServiceClient):
        """
        Delete the given entity and all related entity that declares a relationship to that entity.
        :param ctx: Context
        :param entity_id: id of the entity source
        :param relationship: name of the relationship that refers the source entity. For instance relationship='well'
        then the method will search for record 'data.relationships.well.id: "entity_id"'
        :param entity_list: filter for entity type to delete aside the source entity
        :param data_partition_id:
        :param search_service: search client
        :param storage_service: storage client
        :return: None
        """

        record = await storage_service.get_record(entity_id, data_partition_id)
        source = get_kind_meta(record.kind).source  # use same source than the given entity ?? e.g. wks ?

        request = QueryRequest(kind=format_kind(data_partition_id, source, '*', '*'),
                               query=f'data.relationships.{relationship}.id: \"{entity_id}\"',
                               returned_fields=["id", "kind"])

        aggregated_result: CursorQueryResponse = await search_wrapper.SearchWrapper.query_cursorless(
            search_service=search_service,
            data_partition_id=data_partition_id,
            query_request=request
        )

        # gather ids only if entity type matches the given list
        entities_to_remove = [
            entity for entity in aggregated_result.results
            if get_kind_meta(entity["kind"]).entity_type in map(lambda i: i.value, entity_list)
        ]

        # first delete the source entity, if it fail, we must not delete the others
        await storage_service.delete_record(id=entity_id, data_partition_id=data_partition_id)
        ctx.logger.debug(f'record {entity_id} successfully deleted')

        # execute all deletion concurrently, do not stop at first fail
        delete_results = await asyncio.gather(*[
            storage_service.delete_record(id=entity['id'], data_partition_id=data_partition_id)
            for entity in entities_to_remove
        ], return_exceptions=True)

        # make list of entity result for error management
        EntityResult = namedtuple('EntityResult', 'entity result status_code')
        results = [
            EntityResult(entity=e,
                         result=r,
                         status_code=StorageHelper._status_code_from_exception(r))
            for e, r in zip(entities_to_remove, delete_results)
        ]

        # log successfully deleted entities for debugging purposes
        for r in filter(lambda r: r.status_code == status.HTTP_200_OK, results):
            ctx.logger.debug(f'{r.entity["id"]} of kind {r.entity["kind"]} '
                             f'successfully deleted (from recursive delete of {entity_id})')

        # warn for already deleted entity
        for r in filter(lambda r: r.status_code == status.HTTP_404_NOT_FOUND, results):
            ctx.logger.warning(f'entity {r.entity["id"]} of kind {r.entity["kind"]} was already deleted')

        # errors treatment (i.e. not 200, not 404), gather them by status
        in_errors = list(filter(
            lambda r: r.status_code not in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND],
            results
        ))

        # log errors
        for r in in_errors:
            ctx.logger.error(f'error on deleted entity {r.entity["id"]} of kind {r.entity["kind"]},'
                             f'status code: {r.status_code}, detail: {str(r.result)}')

        if len(in_errors) == 1:  # a single error, just forward
            raise in_errors[0]

        if len(in_errors) > 1:
            distinct_error_statuses = list({r.status_code for r in in_errors})
            if len(distinct_error_statuses) == 1:
                # for homogenous status code, keep the same
                final_status_code = distinct_error_statuses[0]
            else:
                # for heterogeneous status code, set to 500
                final_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            raise HTTPException(
                status_code=final_status_code,
                # build detail from all distinct (not empty) error messages
                detail='Errors: ' + ', '.join({str(r.result) for r in in_errors if str(r.result)}) + '.')
