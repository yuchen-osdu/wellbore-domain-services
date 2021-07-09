# Wellbore Domain Services Extensions


> :warning: **This is an alpha feature**
> Implementation changes are expected, and will not be announced.


[[_TOC_]]

## Use cases
### Include new routers
1. Add a new directory `<extension package name>/routers` under `app/extensions`
2. Add a new python module `<router module name>.py`
```
/wellbore-domain-services
 - app
  |- extensions
    |- <extension package name>
       |- __init__.py
       |- routers
          |- <router module name>.py
          |- __init__.py
```
3. In `<router module name>.py` include: 
```python
from fastapi import APIRouter

router = APIRouter()
router.prefix = '<extension router prefix>'
router.tags = ['<extension router tags>']

def can_run() -> (bool, str):
    # Include the extension router specific checks if applicable.     
    # WDMS main app will skip loading the extension module routers if it returns False. 
    return True
```
4. Include new service endpoints to `router` in `<router module name>.py`.
   - Use `@router.[get|post|delete|put|patch|...]` fastapi decorator to include new methods to the router
   - Check WDMS routers implementation under `app/routers`
   - The same pattern is encouraged to be used in the extension routers.
   
```python
from fastapi import APIRouter, Depends, status
from app.utils import Context, get_ctx
from app.model.model_curated import *
from app.clients.storage_service_client import get_storage_record_service
from app.model.model_utils import from_record

router = APIRouter() # From previous step

# E.g.: Including a GET method API
@router.get('/markers/{marker_id}',
            response_model=marker,
            summary="Get the marker using wks:marker:1.0.4 schema",
            description="""Get the Marker object using its **id**.""",
            operation_id="get_marker",
            responses={status.HTTP_404_NOT_FOUND: {"description": "marker not found"}},
            response_model_exclude_unset=True)
async def get_marker(
        marker_id: str,
        ctx: Context = Depends(get_ctx)
) -> marker:
    storage_client = await get_storage_record_service(ctx)
    marker_record = await storage_client.get_record(id=marker_id, data_partition_id=ctx.partition_id)
    return from_record(marker, marker_record)
```

5. Include the full router module name in `EXTENSION_MODULES` environment variable
E.g.: `app.extensions.<extension package name>.routers.<router module name>`


6. Update the deployment scripts accordingly.

  
7. Run WDMS service, and check in the logs for the messages 
```
Loading `app.extensions.<extension package>.routers.<router module>` extension
	Done. `app.extensions.<extension package>.routers.<router module>` loaded
```

8. Verify the new API endpoints were added under the provided tag, 
   and with the given prefix. `https://{base_url}/api/os-wellbore-ddms/docs/{Tag}` 

9. Include test
   - Unit tests are to be placed under `tests/unit/extensions/<extension package name>`
   - Integration tests are to be placed under `tests/integration/functional/extensions/<extension package name>`

#### Troubleshooting
##### A. Wrong router module configuration

Check step 3 above
```shell
Loading `app.extensions.{}.routers.{}` extension
	Failed to load `app.extensions.{}.routers.{}` extension. 
	Module not configured properly. module 'app.extensions.{}.routers.{}' has no attribute 'router'
```
##### B. Wrong module name

Review steps 2 and 4 above
```shell
Loading `app.extensions.{}.routers.{}` extension
	Failed to load `app.extensions.{}.routers.{}` extension. 
	Module not found. 
	No module named 'app.extensions.{}.routers.{}'
```
##### C. Trailing comma in `EXTENSION_MODULES` list

Review step 4 above, make sure there is no trailing comma in the `EXTENSION_MODULES` list.
```shell
Loading `` extension
	Failed to load `` extension. Empty module name
```
##### D. Empty router prefix or tags

Check step 3 above
```shell
Loading `app.extensions.{}.routers.{}` extension
	Failed to load `app.extensions.{}.routers.{}` extension. 
	Module not configured properly. Router prefix cannot be empty.
```