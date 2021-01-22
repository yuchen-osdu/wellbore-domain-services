from odes_search.models import *
from app.clients import SearchServiceClient


class SearchWrapper:

    @staticmethod
    async def query_cursorless(search_service: SearchServiceClient,
                               data_partition_id: str,
                               query_request: QueryRequest) -> CursorQueryResponse:
        """
        Repeat the search query until the returned cursor is null and concatenate the result
        :param search_service:
        :param data_partition_id:
        :param query_request: The query
        :return: The result of the query
        """
        # Convert the query string into query object
        cursor = None

        test_dict = query_request.dict(by_alias=True)
        request_with_cursor = CursorQueryRequest.parse_obj(test_dict)
        request_with_cursor.limit = 100
        request_with_cursor.cursor = cursor

        agregated_result = CursorQueryResponse()
        agregated_result.results = []

        while True:
            request_with_cursor.cursor = cursor
            query_result = await search_service.query_with_cursor(
                data_partition_id=data_partition_id,
                cursor_query_request=request_with_cursor)

            cursor = query_result.cursor
            if not cursor:
                break
            agregated_result.results.extend(query_result.results)
            agregated_result.total_count = query_result.total_count

        return agregated_result
