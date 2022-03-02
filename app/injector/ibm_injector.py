from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu_ibm.storage.blob_storage_ibm import IBMObjectStorage

from app.utils import get_http_client_session
from app.context import Context
from .app_injector import AppInjector, AppInjectorModule
from app.bulk_persistence import resolve_tenant, DaskBulkStorage
from osdu_ibm.storage.dask_storage_parameters import DaskStorageParametersFactoryIBM


class IBMInjector(AppInjectorModule):
    def configure(self, app_injector: AppInjector):
        app_injector.register(BlobStorageBase, IBMInjector.build_ibm_blob_storage)
        app_injector.register(DaskBulkStorage, IBMInjector.build_ibm_dask_blob_storage)

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
    async def build_ibm_dask_blob_storage() -> DaskBulkStorage:
        daskstoragefactory = DaskStorageParametersFactoryIBM()
        ctx: Context = Context.current()
        tenant = await resolve_tenant(ctx.partition_id)
        params = await daskstoragefactory.get_dask_storage_parameters(tenant)
        return await DaskBulkStorage.create(params)
