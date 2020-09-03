from typing import List

from fastapi import HTTPException
import starlette.status as status

import app.routers.search.search_wrapper as search_wrapper
from app.clients import *
from odes_search.models import *


class StorageHelper:

    @staticmethod
    async def delete_recursively(entity_id: str,
                                 relationship: str,
                                 kind_list: List[str],
                                 data_partition_id: str,
                                 search_service: SearchServiceClient,
                                 storage_service: StorageRecordServiceClient):
        request = QueryRequest(kind='*:wks:*:*',
                               query=f'data.relationships.{relationship}.id: \\\"{entity_id}\\\"',
                               returned_fields=["id", "kind", "cursor", f"data.relationships.{relationship}.id"])

        aggregated_result: CursorQueryResponse = await search_wrapper.SearchWrapper.query_cursorless(
            search_service=search_service,
            data_partition_id=data_partition_id,
            query_request=request
        )
        entities_to_remove = [entity["id"] for entity in aggregated_result.results if entity["kind"].lower() in kind_list]
        entities_to_remove.append(entity_id)

        for entity in entities_to_remove:
            try:
                await storage_service.delete_record(id=entity, data_partition_id=data_partition_id)
            except HTTPException as e:
                #ignore 404 if we have 404, item has already been removed
                if not (e.status_code == status.HTTP_404_NOT_FOUND):
                    raise

