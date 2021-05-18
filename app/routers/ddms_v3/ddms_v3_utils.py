import re
from typing import List, Set

import pandas as pd
from app.bulk_persistence import DataframeSerializer
from app.bulk_persistence.tenant_provider import resolve_tenant
from app.converter.converter_utils import ConverterUtils
from app.bulk_persistence.dask.blob_storage import DaskBlobStorageBase
from app.model.model_chunking import GetDataParams
from app.utils import Context
from fastapi import HTTPException, Request, status
from fastapi.responses import Response
from starlette.datastructures import FormData

OSDU_WELLBORE_VERSION_REGEX = re.compile(r'^([\w\-\.]+:master-data\-\-Wellbore:[\w\-\.\:\%]+):([0-9]*)$')
OSDU_WELLBORE_REGEX = re.compile(r'^[\w\-\.]+:master-data\-\-Wellbore:[\w\-\.\:\%]+$')
OSDU_WELL_VERSION_REGEX = re.compile(r'^([\w\-\.]+:master-data\-\-Well:[\w\-\.\:\%]+):([0-9]*)$')
OSDU_WELL_REGEX = re.compile(r'^[\w\-\.]+:master-data\-\-Well:[\w\-\.\:\%]+$')
DELFI_REGEX = re.compile(r'^[\w\-\.]+:[\w\-\.]+:[\w\-\.]+$')


class DMSV3RouterUtils:
    @staticmethod
    def is_osdu_wellbore_id(entity_id: str) -> bool:
        return OSDU_WELLBORE_REGEX.match(entity_id) is not None

    @staticmethod
    def is_osdu_well_id(entity_id: str) -> bool:
        return OSDU_WELL_REGEX.match(entity_id) is not None

    @staticmethod
    def is_osdu_versionned_entity_id(entity_regexp, entity_id: str) -> (bool, str, str):
        """
        :param entity_regexp: regexp to test the entity (one regexp per entity)
        :param entity_id: id of the entity to test
        :return: The first item of the tuple True if the entity is and osdu versioned entity
        The second parameter is the osdu entity id without the version or None
        The third is the version of osdu entity or None
        """
        matches = entity_regexp.match(entity_id)
        if matches is None:
            return False, None, None
        return True, matches.group(1), matches.group(2)

    @staticmethod
    def is_osdu_versionned_wellbore_id(entity_id: str) -> (bool, str, str):
        return DMSV3RouterUtils.is_osdu_versionned_entity_id(OSDU_WELLBORE_VERSION_REGEX, entity_id)

    @staticmethod
    def is_osdu_versionned_well_id(entity_id: str) -> (bool, str, str):
        return DMSV3RouterUtils.is_osdu_versionned_entity_id(OSDU_WELL_VERSION_REGEX, entity_id)

    @staticmethod
    def is_delfi_id(entity_id: str) -> bool:
        return DELFI_REGEX.match(entity_id) is not None

    @staticmethod
    def is_osdu_entity_fake_id(entity_id: str) -> (bool, str):
        try:
            delfi_id = ConverterUtils.decode_id(entity_id)
            return DMSV3RouterUtils.is_delfi_id(delfi_id), delfi_id
        except ValueError as e:
            return False, None

    @staticmethod
    async def get_df_from_request(request: Request, orient: str) -> pd.DataFrame:
        '''
        TODO manage with MimeTypes class
        '''
        # try:
        #     mime_type = MimeTypes.from_str(request.headers.get('Content-Type', ''))
        # except ValueError:
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail="unknown content_type " +
        #         request.headers.get('Content-Type', ''),
        #     )

        def try_read_parquet(parquet_data):
            try:
                return DataframeSerializer.read_parquet(parquet_data)
            except OSError as err:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f'{err}')  # TODO

        ct = request.headers.get('Content-Type', '')
        if 'multipart/form-data' in ct:
            form: FormData = await request.form()
            assert(len(form) == 1)
            for _file_name, file in form.items(): #TODO can contains multiple files ?
                if file.content_type.lower() == 'application/x-parquet':
                    return try_read_parquet(file.file)

        if 'application/x-parquet' in ct:
            content = await request.body()  # request.stream()
            return try_read_parquet(content)

        if 'application/json' in ct:
            content = await request.json()  # request.stream()
            try:
                return DataframeSerializer.read_json(content, orient)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail='invalid body')  # TODO

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=ct + " is not supported")

    @staticmethod
    async def with_dask_blob_storage() -> DaskBlobStorageBase:
        ctx = Context.current()
        tenant = await resolve_tenant(ctx.partition_id)
        builder = await ctx.app_injector.get(DaskBlobStorageBase)
        return await builder.build_dask_blob_storage(tenant)

class DataFrameRender:
    @staticmethod
    async def compute(df):
        if isinstance(df, pd.DataFrame):
            return df
        driver = await DMSV3RouterUtils.with_dask_blob_storage()
        return await driver.client.compute(df)

    @staticmethod
    async def get_size(df):
        if isinstance(df, pd.DataFrame):
            return len(df.index)
        driver = await DMSV3RouterUtils.with_dask_blob_storage()
        return await driver.client.submit(lambda: len(df.index))

    @staticmethod
    def get_matching_column(selection: List[str], cols: Set[str]):
        import re
        pat = re.compile(r'\[(?P<index>[0-9]+)\]$')
        pat2 = re.compile(r'\[(?P<range>[0-9]+:[0-9]+)\]$')
        selected = set()
        for to_find in selection:
            m = pat2.search(to_find)
            if m:
                r = range(*map(int, m['range'].split(':')))
                def is_matching(c):
                    if c == to_find:
                        return True
                    i = pat.search(c)
                    return i and int(i['index']) in r
            else:
                def is_matching(c):
                    return c == to_find or to_find == pat.sub('', c)
            selected.update(filter(is_matching, cols.difference(selected)))
        return list(selected)

    @staticmethod
    async def process_params(df, params: GetDataParams):
        if params.curves:
            selection = list(map(str.strip, params.curves.split(',')))
            columns = DataFrameRender.get_matching_column(selection, set(df))
            df = df[sorted(columns)]

        if params.offset:
            head_index = df.head(params.offset, npartitions=-1, compute=False).index
            index = await DataFrameRender.compute(head_index) # TODO could be slow!
            df = df.loc[~df.index.isin(index)]

        if params.limit and params.limit > 0:
            try:
                df = df.head(params.limit, npartitions=-1, compute=False) # dask async
            except:
                df = df.head(params.limit)
        return df

    @staticmethod
    async def df_render(df, params: GetDataParams, accept: str = None):
        if params.describe:
            return {
                "numberOfRows": await DataFrameRender.get_size(df),
                "columns" : [c for c in df.columns]
            }

        pdf = await DataFrameRender.compute(df)
        pdf.index.name = None # TODO

        if 'application/x-parquet' in accept:
            return Response(pdf.to_parquet(engine="pyarrow"), media_type="application/x-parquet")

        if 'text/csv' in accept:
            return Response(pdf.to_csv(), media_type="text/csv")

        return Response(pdf.to_json(index=True, date_format='iso'), media_type="application/json")
