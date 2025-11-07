# Overview

Wellbore Data Management Services (Wellbore-DMS) Open Subsurface Data Universe (OSDU) is one of the several backend services that comprise OSDU software ecosystem.  
It can be run as a single service WDMS, or divided into 2 services WDMS + [WDMS-worker](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services-worker). They are containerized services written in Python that provides an API for wellbore related data.

Wiki page about [general architecture](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services/-/wikis/Architecture-overview).

[[_TOC_]]

## Wellbore DMS bulk data layer

### Bulk data IO interface  
In order to operate over bulk data, we designed an abstract class  [BulkIO class](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services/-/blob/master/app/bulk_persistence/bulk_io.py)
This interface is reimplemented by Dask and WDMS-worker detailed below.  

### Dask (legacy)
To perform data manipulation (read and write) of Wellbore bulk data, Wellbore DMS started with [Dask](https://docs.dask.org/en/stable/index.html), it is a Python library for parallel and distributed computing.  
But we faced too many problems:
- high memory consumption (6GiB per pod are required to be production-ready)
- memory leaks cause pod restarts impacting SLOs
- complexity to implement robust upscaling strategy due to inconsistent usage of CPU and memory   
- poor performances when high number of requests

**NOTE**: _It is OK for testing purpose but not recommended for production._

#### Dask configuration - locally
By default, It will use all memory available and use CPU resources through workers. The number of workers is determined by the quantity of core the current local machine has.

#### Dask configuration - in a cluster
In a container context, such as Kubernetes we recommend to set container memory limit at 3Gi of RAM and 4-8 CPUs.
At the minimum 1.2Gi and 1 cpu but performance will be reduced, but enough to handle WellLogs of 10 curves with 1M values each.

Note: container memory is not entirely dedicated to Dask workers, other Python libraries also require ~400MiB.  

### WDMS worker (recommended)

Since M20 (2023 July), we implemented a new dedicated service to operate on bulk data:
[Wellbore Domain Services Worker](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services-worker).
This service uses the same technology stack that WDMS, it only provides APIs to manipulate bulk data.  
This ADR [issue #73](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services/-/issues/73) explains the motivation and the architecture of WDMS worker.

#### WDMS worker configuration - in a cluster
In order to enable usage of WDMS worker service you need to set environment variable `SERVICE_HOST_WDMS_WORKER` defined [here](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services/-/blob/master/app/conf.py#L129).  If activated, Dask cluster won't be launched and all the bulk data operations will be delegated to WDMS worker service.

To verify that WDMS worker deployment is correctly enabled, you can run:  
```bash
OSDU_BASE_URL= ""
TOKEN= ""
curl -X 'GET' '$OSDU_BASE_URL/api/os-wellbore-ddms/version' -H 'Authorization: Bearer $TOKEN'

// Response
{
  "details": {
    ... Other properties before  ...
    "enable_wdms_bulk_worker": "True"  <======== If True, WDMS worker deployment is avaialble
  }
}
```



## OSDU dependencies

**Wellbore-core libraries** [OSDU Wellbore-core](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/lib/wellbore-core)

- Wellbore core lib: common parts and interfaces.
- Wellbore-client-storage
- Wellbore-client-search
- Wellbore-client-schema
- Wellbore-client-wdms: Python client to target WDMS 
- Wellbore-log-recognition: library to infer logs unit. 
- Wellbore-schema-manipulation: osdu schema validator


# How to contribute
## Install Software and Packages

1. Clone the os-wellbore-ddms [repository](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services.git)
2. Download [Python](https://www.python.org/downloads/) **>=3.13**
3. Create virtual environment in the wellbore project directory. This will create a folder inside the wellbore project directory. Typically a hidden folder  will be created, for example: ~/os-wellbore-ddms/.venv

    ```bash
    # Windows
    python -m venv .venv

    # macOS/Linux
    python3 -m venv .venv
    ```
   
4. Activate the virtual environment

    ```bash
    # Windows
    .\.venv\Scripts\activate

    # macOS/Linux
    source .venv/bin/activate
    ```
   
5. Ensure pip, a pre-installed package manager and installer for Python, is installed and is upgraded to the latest version.

      ```bash
      # Windows
      python -m pip install --upgrade pip
      python -m pip --version

      # macOS and Linux
      python3 -m pip install --upgrade pip
      python3 -m pip --version
      ```

5. Install dependencies

    ```bash
    pip install -r requirements.txt --extra-index-url "https://community.opengroup.org/api/v4/projects/465/packages/pypi/simple/"

    ```

    Or, for a developer setup, this will install tools to help you work with the code.

    ```bash
    pip install -r requirements_dev.txt --extra-index-url "https://community.opengroup.org/api/v4/projects/465/packages/pypi/simple/"

    ```
    *Note*: The `requirements_dev.txt` includes the dependencies from `requirements.txt` as well so you only need to run one of the above commands.

## Unit Tests

```bash
# Install test dependencies
pip install -r requirements_dev.txt --extra-index-url "https://community.opengroup.org/api/v4/projects/465/packages/pypi/simple/"


# run tests
python -m pytest --junit-xml=unit_tests_report.xml --cov=app --cov-report=html --cov-report=xml tests/unit
```

Coverage reports can be viewed after the command is run. The HTML reports are saved in the htmlcov directory.

### Control order of the tests

To detect inter-test dependencies and ensure that each test can pass both in isolation and when run in a suite  **test items are randomly shuffled**
thanks to the dependencies of the [pytest-randomly](https://pypi.org/project/pytest-xdist/) plugin.

The output will start with an extra line that tells you the random seed. For instance:

```
Using --randomly-seed=256596674
```

If  tests fail due to ordering, you can  repeat the last ordering:

```
--randomly-seed=last
```

or repeat a specific ordering:

```
--randomly-seed=1234
```

If necessary you can  make the tests run in order:

```
-p no:randomly
```

### Control the tests to be run

Some unit test are flagged with the following marks:
    - slow: test that take time
    - serial: tests that fail if run in parallel
    - perf: performance test
    - hypothesis: Tests that generates test data using hypothesis
    - statistics: specific to test the functionality linked to the api of statistic

For instance use the following decorator to mark a test as slow

```
@pytest.mark.slow
```

To control the test to run according those mark it is possible to pass to pytest the '-m'  option flag, for instance to disable the serial and slow test:

```
-m 'not serial and not slow"
```

to run only perf test:

```
-m 'serial'
```

### Distribute tests across multiple CPUs

Thanks to plugin [pytest-xdist](https://pypi.org/project/pytest-xdist/) in dependencies,  it is possible to run the tests in parallel which can reduce the execution time.
to activate it add the following option:

```
-n auto -m "not serial"
```

With the option `-m "not serial` **Tests that do not support distribution can be marked with 'pytest.mark.serial' and will be ignored.**
You can run them specifically in sequence in a second step by replacing the previous option with the following:

```
-n 0 -m "serial"
```

In addition to speeding up the execution time of a large set of tests, it challenges the isolation of the tests more strongly than randomization.
That is, a test that depends on the state left by the execution of another test is much more likely to be detected by parallel execution
than the sequential execution of tests in a random order.
In the case of execution of subset of tests, the speed gain can be lower than the overhead.

## Integration Tests

This example runs basic tests using the local filesystem for blob storage and storage service. There's no search or entilements service, everything runs locally.  

First create the temp storage folders and set necessary environment variables:
```bash
mkdir -p tmpstorage tmpblob

export CLOUD_PROVIDER=local
export USE_INTERNAL_STORAGE_SERVICE_WITH_PATH=$(pwd)/tmpstorage
export USE_LOCALFS_BLOB_STORAGE_WITH_PATH=$(pwd)/tmpblob
```
second, run the worker service in background:
```bash
uvicorn wdmsworker.app:app --port 8081 &
```
third, run the WDMS service and point to the worker service:
```bash
python main.py -e SERVICE_HOST_WDMS_WORKER http://localhost:8081
```

In another terminal, generate a minimum configuration file and run the integration tests.

```bash
cd tests/integration
python gen_postman_env.py --token $(pyjwt --key=secret encode email=nobody@example.com) --base_url "http://127.0.0.1:8080/api/os-wellbore-ddms" --cloud_provider "local" --data_partition "dummy"
pytest ./functional --environment="./generated/postman_environment.json" --filter-tag=basic -p no:randomly
```

For more information see the [integration tests README](tests/integration/README.md)

## Performance Tests
We build a dedicated solution "[Wellbore Domain Services Performance Tests](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services-performance-tests)" to run benchmarks against Wellbore DMS.  
WDMS Performance Test Client is a client that runs various test scenarios to collect metrics about the Wellbore DDMS service.
The project is donated as it is. Although the client can be adapted to any service, its primary purpose is to test the
Wellbore Data Management Service.

## Run the service locally
1. Run the service

    ```bash
    # Directly with Python
    
   # Run on specific port and enforce dev mode
    python main.py --port MY_PORT --dev_mode 1
    ```
    ```bash
    # With Uvicorn (package) into venv already activated
   
   # Run on specific port
    uvicorn app.wdms_app:wdms_app --port LOCAL_PORT
    ```

Then access app on `http://localhost:<LOCAL_PORT>/api/os-wellbore-ddms/docs`

    If host is `127.0.0.1` or `localhost`, the dev_mode is automatically set to True.
    The only significant change if dev_mode is on, is that configuration errors at startup are logged but don’t prevent the service to run, and allow to override some implementations.

The hosts for the search, storage and schema services have to be provided as environment variables, or on the command line.

```bash
python main.py -e SERVICE_HOST_STORAGE https://api.example.com/storage -e SERVICE_HOST_SEARCH https://api.example.com/search-service -e SERVICE_HOST_SCHEMA https://api.example.com/schema
```

### How to call APIs

1. Generate bearer token as all APIs but `/about` require authentication.

    - Navigate to `http://127.0.0.1:8080/api/os-wellbore-ddms/docs`. Click `Authorize` and enter your token. That will allow for authenticated requests.

2. Choose storage option

    Even if the service runs locally it still relies on osdu data ecosystem storage service to store documents and google blob store to store binary data (`bulk data`). It is possible to override this and use your local file system instead by setting the following environment variables:

    - `USE_INTERNAL_STORAGE_SERVICE_WITH_PATH` to store on a local folder instead of osdu ecosystem storage service.
    - `USE_LOCALFS_BLOB_STORAGE_WITH_PATH` to store on a local folder instead of google blob storage.

    ```bash
    # Create temp storage folders
    mkdir tmpstorage
    mkdir tmpblob

    # Set your repo path
    path="C:/source"

    python main.py -e USE_INTERNAL_STORAGE_SERVICE_WITH_PATH $path/os-wellbore-ddms/tmpstorage -e USE_LOCALFS_BLOB_STORAGE_WITH_PATH $path/os-wellbore-ddms/tmpblob
    ```

3. Choose Cloud Provider

    - The code can be run with specifying environment variables and by setting the cloud provider. The accepted values are `gcp`, `az` or `local`. When a cloud provider is passed as an environment variables, there are certain additional environment variables that become mandatory.

## Cloud Providers

**Each cloud provider need to define:**
- data access layer* (blob storage)
- helm chart templates* (into [/devops](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services/-/tree/master/devops) directory)
- observability rules (default is no monitoring)
- logging exporter (default is container logging)

*: required

Data access layer implementation are available into [Wellbore-cloud libraries](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/lib/wellbore-cloud). Here's an exaustive list:
- osdu-core-lib-python-gcp
- osdu-core-lib-python-azure
- osdu-core-lib-python-aws
- osdu-core-lib-python-ibm
- osdu-core-lib-python-baremetal


### Cloud Provider Environment Variables

#### Google Cloud

- The following environment variables are required when the cloud provider is set to Google Cloud:
  - SERVICE_HOST_SEARCH: The Search Service host
  - SERVICE_HOST_SCHEMA: The Schema Service host
  - SERVICE_HOST_STORAGE: The Storage Service host
  - SERVICE_URL_PARTITION: The Partition Service url; default: http://partition/api/partition/v1/

  ```bash
  python main.py -e CLOUD_PROVIDER gc \
  -e SERVICE_HOST_SEARCH search_host \
  -e SERVICE_HOST_SCHEMA schema_host \
  -e SERVICE_HOST_STORAGE storage_host
  -e SERVICE_URL_PARTITION partition_url
  ```
- The following values should be in Partition Service for a data partition:
  ```json
  {
    "projectId": {
      "sensitive": false,
      "value": "<gc-project-id>"
    },
    "wellbore-dms-bucket": {
      "sensitive": false,
      "value": "<gc-bucket-for-the-data-partition>"
    }
  }
  ```

#### Azure

- The following environment variables are required when the cloud provider is set to Azure:
  - AZ_AI_CONNECTION_STR: Azure Application Insights connection string key
  - SERVICE_HOST_SEARCH: The Search Service host
  - SERVICE_HOST_SCHEMA: The Schema Service host 
  - SERVICE_HOST_STORAGE: The Storage Service host
  - SERVICE_HOST_PARTITION: The Partition Service internal host
  - KEYVAULT_URL: The Key Vault url (needed by the Partition Service)
  - USE_PARTITION_SERVICE: `enabled` when Partition Service is available in the environment. Needs to be `disabled` for `dev` or to run locally.

  ```bash
  python main.py -e CLOUD_PROVIDER az \
  -e AZ_AI_CONNECTION_STR connection_str \
  -e SERVICE_HOST_SEARCH search_host \
  -e SERVICE_HOST_SCHEMA schema_host \
  -e SERVICE_HOST_STORAGE storage_host \
  -e SERVICE_HOST_PARTITION partition_host \
  -e KEYVAULT_URL keyvault_url \
  -e USE_PARTITION_SERVICE disabled
  ```

#### AWS

- The following environment variables are required when the cloud provider is set to AWS:
  - SERVICE_HOST_SEARCH: The Search Service host
  - SERVICE_HOST_SCHEMA: The Schema Service host
  - SERVICE_HOST_STORAGE: The Storage Service host
  - SERVICE_HOST_PARTITION: The Partition Service host

  ```bash
  python main.py -e CLOUD_PROVIDER aws \
  -e SERVICE_HOST_SEARCH search_host \
  -e SERVICE_HOST_SCHEMA schema_host \
  -e SERVICE_HOST_STORAGE storage_host \
  -e SERVICE_HOST_PARTITION partition_host 
  ```

Note: If you're running locally, you may need to provide environmental variables in your IDE. Here is a sample for providing a `.env` file.

As default, all Core Services endpoint values are set to `None` in `app/conf.py`, you can update `.env` file for core services endpoints based on your cloud provider.

## Wellbore DMS APIs example

### Tutorials:
  * [Bulk data APIs presentation](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services/-/wikis/Bulk-data-tutorial)
  * [Bulk data IO efficiency](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services/-/wikis/Bulk-data-tutorial)
  * [Bulk data statistics](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services/-/wikis/Bulk-statistics-tutorial)
  * [Log recognition APIs](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services/-/wikis/Log-recognition)
  * [Geology APIs](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services/-/wikis/Geology-APIs)
  * [OSDU entity examples](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services/-/tree/master/app/model_examples)

### Bulk data consistency rules:
  * [WellLog consistency rules](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services/-/wikis/WellLog-consistency-rules)
  * [WellboreTrajectory consistency rules](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services/-/wikis/WellboreTrajectory-consistency-rules)
  * [BulkURI consistency check rule](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services/-/wikis/BulkURI-consistency-check-rule)

More document is available in the [WDMS wiki](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services/-/wikis/home).


## Build WellboreDMS

### Build Image with Docker

```bash
# Set IMAGE_TAG
IMAGE_TAG="os-wellbore-ddms:dev"

# Build Image
docker build -t=$IMAGE_TAG --rm . -f ./build/Dockerfile --build-arg PIP_WHEEL_DIR=python-packages
```

### Run Image

1. Run the image

    Replace the LOCAL_PORT value with a local port

    ```bash
    LOCAL_PORT=<local_port>
    IMAGE_TAG=<image_name>
   
    docker run -d -p $LOCAL_PORT:8080 -e CLOUD_PROVIDER=local -e USE_LOCALFS_BLOB_STORAGE_WITH_PATH="/tmp" -e USE_INTERNAL_STORAGE_SERVICE_WITH_PATH="/tmp" -e OS_WELLBORE_DDMS_DEV_MODE=True -e USE_PARTITION_SERVICE=disabled $IMAGE_TAG
    ```

2. Access app on `http://127.0.0.1:<LOCAL_PORT>/api/os-wellbore-ddms/docs`

3. The environment variable `OS_WELLBORE_DDMS_DEV_MODE=1` enables dev mode

4. Logs can be checked by running

    ```bash
    docker logs CONTAINER_ID
    ```

## How to update Python dependencies

Anytime, you may want to ensure your virtual environment is in sync with your requirements specification.
For this you can use:

```bash
pip-sync requirements.txt
```

If you want to work with other requirements file, you can specify them

```bash
pip-sync requirements_dev.txt
```

**Note:** On a Windows workstation, platform-specific modules such as `pywin32` are also needed. In this case don't use `pip-sync` but `pip install` instead.

```bash
pip install -r requirements_dev.txt --extra-index-url "https://community.opengroup.org/api/v4/projects/465/packages/pypi/simple/"
```

If you want to update `requirements.txt` and/or `requirements_dev.txt` to retrieve the most recent version, respecting bounds set in `pyproject.toml`, you can use:

```bash
pip-compile --output-file requirements.txt --extra-index-url "https://community.opengroup.org/api/v4/projects/465/packages/pypi/simple/"
pip-compile --extra dev --output-file requirements_dev.txt --extra-index-url "https://community.opengroup.org/api/v4/projects/465/packages/pypi/simple/"
```

If you want to update the version of only one dependency, for instance fastapi:

```bash
pip install --upgrade fastapi
```
Then to add the new version to the requirements file, you can use:

```bash
pip freeze > requirements.txt
```

**Note:** On a Windows workstation, **don't** commit the `pywin32` back to the `requirements.txt` file, that will cause CICD to fail.

For more information: <https://github.com/jazzband/pip-tools/>

### Debugging

#### Port Forward from Kubernetes

 1. List the pods: `kubectl get pods`
 2. Port forward: `kubectl port-forward pods/POD_NAME LOCAL_PORT:8080`
 3. Access it on `http://127.0.0.1:<LOCAL_PORT>/api/os-wellbore-ddms/docs`

### Tracing

OpenTelemetry libraries are used to record incoming requests metrics (execution time, result code, etc...).
At the moment, 100% of the requests are recorded.
