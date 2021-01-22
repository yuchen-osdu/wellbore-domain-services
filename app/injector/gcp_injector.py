from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from app.utils import get_http_client_session
from osdu_gcp.storage.blob_storage_gcp import GCloudAioStorage
from .app_injector import AppInjector, AppInjectorModule
from app.utils import Context
from app.bulk_persistence import resolve_tenant


class GCPInjector(AppInjectorModule):
    def configure(self, app_injector: AppInjector):
        app_injector.register(BlobStorageBase, GCPInjector.build_gcp_blob_storage)

    @staticmethod
    async def build_gcp_blob_storage(*args, **kwargs) -> BlobStorageBase:
        ctx: Context = Context.current()
        # TODO to be reviewed
        tenant = await resolve_tenant(ctx.partition_id)
        return GCloudAioStorage(
            session=get_http_client_session(),
            service_account_file=tenant.credentials
        )
