# Introduction

Wellbore Domain Data Management Services (Wellbore-DDMS) Open Subsurface Data Universe (OSDU) is one of the several backend services that comprise OSDU software ecosystem. It is a single, containerized service written in Python that provides an API for wellbore related data.

[[_TOC_]]

## Install Software and Packages

1. Clone the os-wellbore-ddms [repository](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/wellbore/wellbore-domain-services.git)
2. Download [Python](https://www.python.org/downloads/) >=3.7
3. Ensure pip, a pre-installed package manager and installer for Python, is installed and is upgraded to the latest version.

      ```bash
      # Windows
      python -m pip install --upgrade pip
      python -m pip --version

      # macOS and Linux
      python3 -m pip install --upgrade pip
      python3 -m pip --version
      ```

4. Using pip, download [FastAPI](https://fastapi.tiangolo.com/), the main framework to build the service APIs. To install fastapi and uvicorn (to work as the server), run the following command:

    ```bash
    pip install fastapi[all]
    ```

5. [venv](https://docs.python.org/3/library/venv.html) allows you to manage separate package installations for different projects. They essentially allow you to create a "virtual" isolated Python installation and packages into that virtual environment. venv is already included in the Python standard library and requires no additional installation.

### Fast API Dependencies

- [pydantic](https://pydantic-docs.helpmanual.io/): provides the ability to do data validation using python type annotations. It enforces type hints at runtime provide a more robust data validation option.
  - [dataclasses](https://pydantic-docs.helpmanual.io/usage/dataclasses/): module in python which provides a decorator and functions for automatically adding generated special methods to user-defined classes.
- [starlette](https://fastapi.tiangolo.com/features/#starlette-features): lightweight ASGI framework. FastAPI is a sub-class of Starlette and includes features such as websocket support, startup and shutdown events, session and cookie support.

### Additional Dependencies

- [uvicorn](https://www.uvicorn.org/) used as ASGI server to run Wellbore-DDMS app
- [cachetools](https://pypi.org/project/cachetools/)
- [pyjwt](https://pypi.org/project/PyJWT/) and [cryptography](https://pypi.org/project/cryptography/) for auth purposes
- [pandas](https://pandas.pydata.org/) and [numpy](https://numpy.org/) for data manipulation
- [pyarrow](https://pypi.org/project/pyarrow/) for load and save data into parquet format
- [opencensus](https://opencensus.io/guides/grpc/python/) for tracing and logging on cloud provider

### Library Dependencies

- Common parts and interfaces
  - osdu-core-lib-python

- Implementation of blob storage on GCP
  - osdu-core-lib-python-gcp

- Implementation of blob storage and partition service on Azure
  - osdu-core-lib-python-azure

- Client libraries for OSDU data ecosystem services
  - osdu-data-ecosystem-search
  - osdu-data-ecosystem-storage

## Project Startup

### Run the service locally

1. Create virtual environment in the wellbore project directory. This will create a folder inside of the wellbore project directory. For example: ~/os-wellbore-ddms/nameofvirtualenv

    ```bash
    # Windows
    python -m venv env

    # macOS/Linux
    python3 -m venv env
    ```

2. Activate the virtual environment

    ```bash
    # Windows
    source env/Scripts/activate

    # macOS/Linux
    source env/bin/activate
    ```

5. Install dependencies

    ```bash
    pip install -r requirements.txt
    ```

    Or, for a developer setup, this will install tools to help you work with the code.
    ```bash
    pip install -r requirements.txt -r requirements_dev.txt
    ```
    

6. Run the service

    ```bash
    # Run the service which will default to http://127.0.0.1:8080
    python main.py

    # Run on specific host, port and enforce dev mode
    python main.py --host MY_HOST --port MY_PORT --dev_mode 1
    ```

    If host is `127.0.0.1` or `localhost`, the dev_mode is automatically set to True.
    The only significant change if dev_mode is on, is that configuration errors at startup are logged but don’t prevent the service to run, and allow to override some implementations.

The hosts for the search and storage services have to be provided as environment variables, or on the command line.

```bash
python main.py -e SERVICE_HOST_STORAGE https://api.example.com/storage -e SERVICE_HOST_SEARCH https://api.example.com/search
```

### Connect and Run Endpoints

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

### Setting the Cloud Provider Environment Variables

- The following environment variables are required when the cloud provider is set to GCP:
  - OS_WELLBORE_DDMS_DATA_PROJECT_ID: GCP Data Tenant ID
  - OS_WELLBORE_DDMS_DATA_PROJECT_CREDENTIALS: path to the key file of the SA to access the data tenant
  - SERVICE_HOST_SEARCH: The Search Service host
  - SERVICE_HOST_STORAGE: The Storage Service host

  ```bash
  python main.py -e CLOUD_PROVIDER gcp \
  -e OS_WELLBORE_DDMS_DATA_PROJECT_ID projectid \
  -e OS_WELLBORE_DDMS_DATA_PROJECT_CREDENTIALS pathtokeyfile \
  -e SERVICE_HOST_SEARCH search_host \
  -e SERVICE_HOST_STORAGE storage_host
  ```

- The following environment variables are required when the cloud provider is set to Azure:
  - AZ_AI_INSTRUMENTATION_KEY: Azure Application Insights instrumentation key
  - SERVICE_HOST_SEARCH: The Search Service host
  - SERVICE_HOST_STORAGE: The Storage Service host
  - SERVICE_HOST_PARTITION: The Partition Service internal host
  - KEYVAULT_URL: The Key Vault url (needed by the Partition Service)
  - USE_PARTITION_SERVICE: `enabled` when Partition Service is available in the environment. Needs to be `disabled` for `dev` or to run locally.

  ```bash
  python main.py -e CLOUD_PROVIDER az \
  -e AZ_AI_INSTRUMENTATION_KEY instrumentationkey \
  -e SERVICE_HOST_SEARCH search_host \
  -e SERVICE_HOST_STORAGE storage_host \
  -e SERVICE_HOST_PARTITION partition_host \
  -e KEYVAULT_URL keyvault_url \
  -e USE_PARTITION_SERVICE disabled
  ```

Note: If you're running locally, you may need to provide environmental variables in your IDE. Here is a sample for providing a `.env` file.

As default, all Core Services endpoint values are set to `None` in `app/conf.py`, you can update `.env` file for core services endpoints based on your cloud provider.

### Create a log record

To create a `WellLog` record, below is a payload sample for the POST `/ddms/v3/welllogs` API. The response will contain an id you can use to create some bulk data.

```json
[
  {
    "acl": {
      "viewers": [
        "data.default.viewers@{{datapartitionid}}.{{domain}}"
      ],
      "owners": [
        "data.default.owners@{{datapartitionid}}.{{domain}}"
      ]
    },
    "data": {
      "Curves": [
        {
          "CurveID": "GR_ID",
          "Mnemonic": "GR",
          "CurveUnit": "{{datapartitionid}}:reference-data--UnitOfMeasure:m:",
          "LogCurveFamilyID": "{{datapartitionid}}:reference-data--LogCurveFamily:GammaRay:"
        },
        {
          "CurveID": "POR_ID",
          "Mnemonic": "NPOR",
          "CurveUnit": "{{datapartitionid}}:reference-data--UnitOfMeasure:m:",
          "LogCurveFamilyID": "{{datapartitionid}}:reference-data--LogCurveFamily:NeutronPorosity:"
        },
        {
          "CurveID": "Bulk Density",
          "Mnemonic": "RHOB",
          "CurveUnit": "{{datapartitionid}}:reference-data--UnitOfMeasure:m:",
          "LogCurveFamilyID": "{{datapartitionid}}:reference-data--LogCurveFamily:BulkDensity:"
        }
      ],
      "WellboreID": "{{datapartitionid}}:master-data--Wellbore:{{wellboreId}}:",
      "CreationDateTime": "2013-03-22T11:16:03Z",
      "VerticalMeasurement": {
        "VerticalMeasurement": 2680.5,
        "VerticalMeasurementPathID": "{{datapartitionid}}:reference-data--VerticalMeasurementPath:MD:",
        "VerticalMeasurementUnitOfMeasureID": "{{datapartitionid}}:reference-data--UnitOfMeasure:ft:"
      },
      "TopMeasuredDepth": 12345.6,
      "BottomMeasuredDepth": 13856.25,
      "Name": "{{welllogName}}",
      "ExtensionProperties": {
        "step": {
          "unitKey": "ft",
          "value": 0.1
        },
        "dateModified": "2013-03-22T11:16:03Z"
      }
    },
    "id": "{{datapartitionid}}:work-product-component--WellLog:{{welllogId}}",
    "kind": "osdu:wks:work-product-component--WellLog:1.0.0",
    "legal": {
      "legaltags": [
        "{{legaltags}}"
      ],
      "otherRelevantDataCountries": [
        "US",
        "FR"
      ]
    },
    "meta": [
      {
        "kind": "Unit",
        "name": "ft",
        "persistableReference": "{\"scaleOffset\":{\"scale\":0.3048,\"offset\":0.0},\"symbol\":\"ft\",\"baseMeasurement\":{\"ancestry\":\"Length\",\"type\":\"UM\"},\"type\":\"USO\"}",
        "propertyNames": [
          "stop.value",
          "elevationReference.elevationFromMsl.value",
          "start.value",
          "step.value",
          "reference.unitKey"
        ],
        "propertyValues": [
          "ft"
        ]
      },
      {
        "kind": "DateTime",
        "name": "datetime",
        "persistableReference": "{\"format\":\"yyyy-MM-ddTHH:mm:ssZ\",\"timeZone\":\"UTC\",\"type\":\"DTM\"}",
        "propertyNames": [
          "dateModified",
          "dateCreated"
        ]
      }
    ]
  }
]
```


### Run with Uvicorn

```bash
uvicorn app.wdms_app:wdms_app --port LOCAL_PORT
```

Then access app on `http://127.0.0.1:<LOCAL_PORT>/api/os-wellbore-ddms/docs`

### Run with Docker

#### Build Image

```bash
# Set IMAGE_TAG
IMAGE_TAG="os-wellbore-ddms:dev"

# Build Image
docker build -t=$IMAGE_TAG --rm . -f ./build/dockerfile --build-arg PIP_WHEEL_DIR=python-packages
```

#### Run Image

1. Run the image

    Replace the LOCAL_PORT value with a local port

    ```bash
    LOCAL_PORT=<local_port>

    docker run -d -p $LOCAL_PORT:8080 -e OS_WELLBORE_DDMS_DEV_MODE=1 -e USE_LOCALFS_BLOB_STORAGE_WITH_PATH=1 $IMAGE_TAG
    ```

2. Access app on `http://127.0.0.1:<LOCAL_PORT>/api/os-wellbore-ddms/docs`

3. The environment variable `OS_WELLBORE_DDMS_DEV_MODE=1` enables dev mode

4. Logs can be checked by running

    ```bash
    docker logs CONTAINER_ID
    ```

### Run Unit Tests Locally

```bash
# Install test dependencies
pip install -r requirements.txt -r requirements_dev.txt

python -m pytest --junit-xml=unit_tests_report.xml --cov=app --cov-report=html --cov-report=xml ./tests/unit
```

Coverage reports can be viewed after the command is run. The HMTL reports are saved in the htmlcov directory.

### Run Integration Tests locally

This example runs basic tests using the local filesystem for blob storage and storage service. There's no search or entilements service, everything runs locally.  

First, create the temp storage folders and run the service.

```bash
mkdir -p tmpstorage
mkdir -p tmpblob
python main.py -e USE_INTERNAL_STORAGE_SERVICE_WITH_PATH $(pwd)/tmpstorage -e USE_LOCALFS_BLOB_STORAGE_WITH_PATH $(pwd)/tmpblob -e CLOUD_PROVIDER local
```

In another terminal, generate a minimum configuration file and run the integration tests.

```bash
cd tests/integration
python gen_postman_env.py --token $(pyjwt --key=secret encode email=nobody@example.com) --base_url "http://127.0.0.1:8080/api/os-wellbore-ddms" --cloud_provider "local" --data_partition "dummy"
pytest ./functional --environment="./generated/postman_environment.json" --filter-tag=basic
```

For more information see the [integration tests README](tests/integration/README.md)

### Manage package dependencies

Anytime, you may want to ensure your virtual environment is in sync with your requirements specification.
For this you can use:

```bash
pip-sync
```

If you want to work with other requirements file, you can specify them
```bash
pip-sync requirements.txt requirements_dev.txt
```

If you want to update `requirements.txt` to retrieve the most recent version, respecting bounds set in `requirements.in`, you can use:

```bash
pip-compile
```

For more information: https://github.com/jazzband/pip-tools/


### Port Forward from Kubernetes

 1. List the pods: `kubectl get pods`
 2. Port forward: `kubectl port-forward pods/POD_NAME LOCAL_PORT:8080`
 3. Access it on `http://127.0.0.1:<LOCAL_PORT>/api/os-wellbore-ddms/docs`

### Tracing

OpenCensus libraries are used to record incoming requests metrics (execution time, result code, etc...).
At the moment, 100% of the requests are saved.
