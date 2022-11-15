# os-wellbore-ddms-azure

Wellbore Data Management Services (WDMS) Open Subsurface Data Universe (OSDU) is one of the several backend services that comprise Schlumberger's Exploration and Production (E&P) software ecosystem. It is a single, containerized service written in Python that provides an API for wellbore related data.

## Requirements

In order to run this service locally, you will need the following:

- [Python](https://www.python.org/downloads/) >=3.8
- [FastAPI](https://fastapi.tiangolo.com/)
- [OSDU on Azure infrastructure](https://community.opengroup.org/osdu/platform/deployment-and-operations/infra-azure-provisioning) deployed


## Service Dependencies
- [Storage Service](https://community.opengroup.org/osdu/platform/system/storage)
- [Search Service](https://community.opengroup.org/osdu/platform/system/search-service)

> Add service dependencies here

## General Tips

**Environment Variable Management**
The following tools make environment variable configuration simpler
 - [direnv](https://direnv.net/) - for a shell/terminal environment

## Environment Variables

In order to run the service locally, you will need to have the following environment variables defined. We have created a helper script to generate .yaml files to set the environment variables to run and test the service using the InteliJ IDEA plugin and generate a .envrc file to set the environment variables to run and test the service using direnv [here](https://community.opengroup.org/osdu/platform/deployment-and-operations/infra-azure-provisioning/-/blob/master/tools/variables/os-wellbore-ddms.sh).

**Note** The following command can be useful to pull secrets from keyvault:
```bash
az keyvault secret show --vault-name $KEY_VAULT_NAME --name $KEY_VAULT_SECRET_NAME --query value -otsv
```

**Required to run service**

| name | value | description | sensitive? | source |
| ---  | ---   | ---         | ---        | ---    |
| `CLOUDPROVIDER` | `azure` | Cloud provider for this deployment | no | Constant |
| `SERVICE_HOST` | `$DNS_HOST` | Description | no |  |
| `SERVICE_PORT` | `8080` | Description | no |  |
| `SERVICE_HOST_STORAGE` | `https://${ENV_HOST}/api/storage/v2` | Storage service host | no | 
| `SERVICE_HOST_SEARCH` | `https://${ENV_HOST}/api/search/v2` | Search service host | no | 
| `SERVICE_HOST_PARTITION` | `https://${ENV_HOST}/api/partition/v2` | Partition service host | no | 
| `KEYVAULT_URL` | `****` | The Key Vault url (needed by the Partition Service) | yes | 
| `AZ_AI_INSTRUMENTATION_KEY` | `****` | Azure Application Insights instrumentation key | yes | 

**Required to run integration tests**

| name | value | description | sensitive? | source |
| ---  | ---   | ---         | ---        | ---    |
| `FILTER_TAG` | `basic` | Run integration tests locally | no | Constant |


## Running Locally
| name | value | description | sensitive? | source |
| ---  | ---   | ---         | ---        | ---    |
| `CLOUDPROVIDER` | `local` | Run locally | no | Constant |
| `SERVICE_HOST` | `127.0.0.1` | Description | no |  |
| `SERVICE_PORT` | `8080` | Description | no |  |
| `STORAGE_SERVICE_PATH` | `tmpstorage` | Local record storage folder | no | 
| `BLOB_STORAGE_PATH` | `tmpblob` | Local blob storage folder | no |  |


### Configure Python environment

Refer to **Project Startup** section in the top-level [README](/README.md)

### Build and run the application

After configuring your environment as specified above, you can follow these steps to build and run the application. These steps should be invoked from the repository root.

```bash
python main.py -e USE_INTERNAL_STORAGE_SERVICE_WITH_PATH $STORAGE_SERVICE_PATH -e USE_LOCALFS_BLOB_STORAGE_WITH_PATH $BLOB_STORAGE_PATH -e CLOUD_PROVIDER $CLOUDPROVIDER
```

Use the command above to run the service locally. Other options are in the top-level [README](/README.md)


### Test the Application

_After the service has started it should be accessible via a web browser by visiting [http://127.0.0.1:8080/api/os-wellbore-ddms/docs](http://127.0.0.1:8080/api/os-wellbore-ddms/docs). If the request does not fail, you can then run the integration tests._

```bash
# setup integration tests
mkdir -p $STORAGE_SERVICE_PATH
mkdir -p $BLOB_STORAGE_PATH
python main.py -e USE_INTERNAL_STORAGE_SERVICE_WITH_PATH $STORAGE_SERVICE_PATH -e USE_LOCALFS_BLOB_STORAGE_WITH_PATH $BLOB_STORAGE_PATH -e CLOUD_PROVIDER $CLOUDPROVIDER
# Note: this assumes that the environment variables for integration tests as outlined above are already exported in your environment.
cd tests/integration
python gen_postman_env.py --token $(pyjwt --key=secret encode email=nobody@example.com) --base_url "http://$SERVICE_HOST:$SERVICE_PORT/api/os-wellbore-ddms" --cloud_provider "local" --data_partition "dummy"
pytest ./functional --environment="./generated/postman_environment.json" --filter-tag=$FILTER_TAG -p no:randomly
```

## License
Copyright © Schlumberger

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
