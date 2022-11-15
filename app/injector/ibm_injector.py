from functools import partial

from app.bulk_persistence import (
    BulkPersistenceConfig,
    DaskBulkStorage,
    DaskDistributedClient,
    get_config,
)
from app.context import Context
from app.tenant import resolve_tenant
from app.utils import get_http_client_session
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu_ibm.storage.blob_storage_ibm import IBMObjectStorage
from osdu_ibm.storage.dask_storage_parameters import (
    DaskStorageParametersFactoryIBM,
)

from .app_injector import AppInjector, AppInjectorModule


class IBMInjector(AppInjectorModule):
    def configure(self, app_injector: AppInjector):
        app_injector.register(BlobStorageBase, IBMInjector.build_ibm_blob_storage)
        app_injector.register(DaskBulkStorage, partial(IBMInjector.build_ibm_dask_blob_storage,
                                                       app_injector=app_injector,
                                                       bulk_config=get_config()))

    @staticmethod
    async def build_ibm_blob_storage(*args, **kwargs) -> BlobStorageBase:
        ctx: Context = Context.current()
        # TODO to be reviewed
        tenant = await resolve_tenant(ctx.partition_id)
        return IBMObjectStorage(
            session=get_http_client_session(),
            service_account_file=tenant.credentials
        )

    @staticmethod
    async def build_ibm_dask_blob_storage(app_injector: AppInjector, bulk_config: BulkPersistenceConfig) -> DaskBulkStorage:
        daskstoragefactory = DaskStorageParametersFactoryIBM()
        ctx: Context = Context.current()
        tenant = await resolve_tenant(ctx.partition_id)
        params = await daskstoragefactory.get_dask_storage_parameters(tenant)
        dask_client = await app_injector.get(DaskDistributedClient)
        return await DaskBulkStorage.create(params, bulk_config, dask_client)
