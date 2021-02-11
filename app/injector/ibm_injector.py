from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from app.utils import get_http_client_session
from osdu_ibm.storage.blob_storage_ibm import IBMObjectStorage
from .app_injector import AppInjector, AppInjectorModule
from app.utils import Context
from app.bulk_persistence import resolve_tenant


class IBMInjector(AppInjectorModule):
    def configure(self, app_injector: AppInjector):
        app_injector.register(BlobStorageBase, IBMInjector.build_ibm_blob_storage)

    @staticmethod
    async def build_ibm_blob_storage(*args, **kwargs) -> BlobStorageBase:
        ctx: Context = Context.current()
        # TODO to be reviewed
        tenant = await resolve_tenant(ctx.partition_id)
        return IBMObjectStorage(
            session=get_http_client_session(),
            service_account_file=tenant.credentials
        )
