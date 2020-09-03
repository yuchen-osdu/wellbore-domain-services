# Introduction

Wellbore Data Management Services (WDMS) Open Subsurface Data Universe (OSDU) is one of the several backend services that comprise Schlumberger's Exploration and Production (E&P) software ecosystem. It is a single, containerized service written in Python that provides an API for wellbore related data.

## Install Software and Packages

1. Clone the os-wellbore-ddms repository
2. Download [Python](https://www.python.org/downloads/) >=3.7
3. Ensure pip, a pre-installed package manager and installer for Python, is installed and is upgraded to the latest version.

Windows:

  ```bash
  py -m pip install --upgrade pip
  py -m pip --version
  ```

Linux and macOS:

  ```bash
  python3 -m pip install --upgrade pip
  python3 -m pip --version
  ```

4. Using pip, download [FastAPI](https://fastapi.tiangolo.com/), the main framework to build the service APIs. To install fastapi and uvicorn (to work as the server), run the following command:

  ```bash
  pip install fastapi[all]
  ```

5. venv - venv allows you to manage separate package installations for different projects. They essentially allow you to create a "virtual" isolated Python installation and packages into that virtual environment. venv is already included in the Python standard library and requires no addtional installation.

### Fast API Dependencies

- [pydantic](https://pydantic-docs.helpmanual.io/): provides the ability to do data validation using python type annotations. It enforces type hints at runtime provide a more robust data validation option.
  - [dataclasses](https://pydantic-docs.helpmanual.io/usage/dataclasses/): module in python which provides a decorator and functions for automatically adding generated special methods to user-defined classes.
- [starlette](https://fastapi.tiangolo.com/features/#starlette-features): lightweight ASGI framework. FastAPI is a sub-class of Starlette and includes features such as websocket support, startup and shutdown events, session and cookie support.

### Additional Dependencies

- [uvicorn](https://www.uvicorn.org/) used as ASGI server to run WDMS app
- [cachetools](https://pypi.org/project/cachetools/)
- [pyjwt](https://pypi.org/project/PyJWT/) and [cryptography](https://pypi.org/project/cryptography/) for auth purposes
- [pandas](https://pandas.pydata.org/) and [numpy](https://numpy.org/) for data manipulation
- [pyarrow](https://pypi.org/project/pyarrow/) for load and save data into parquet format
- [opencensus](https://opencensus.io/guides/grpc/python/) for tracing and logging on cloud provider

### Library Dependencies

- Common parts and interfaces
  - osdu-core-python

- Implementation of blob storage on GCP
  - osdu-core-python-gcp

- Storage, search and entitlements
  - osdu-python-clients

## Project Startup

### Run the service locally

1. Create [virtual](https://pypi.org/project/virtualenv/) environment in the wellbore project directory. This will create a folder inside of the wellbore project directory. For example: ~/os-wellbore-ddms/nameofvirtualenv

Windows:

```bash
py -m venv env
```

on macOS and Linux:

```bash
python3 -m venv env
```

2. Activate the virtual environment

Windows:

```bash
env/Scripts/activate
```

macOS and Linux:

```bash
source env/bin/activate
```

3. Create pip.ini (Windows) or pip.conf (Mac) file inside the venv directory. This allows us to set a global index url which can download packages from specific sources. 

Note: It is also possible to use [--extra-index-url parameter](https://pip.pypa.io/en/stable/reference/pip_install/#install-extra-index-url) to specify it on the pip install cmd inline

4. Install dependencies

```bash
pip install -r requirements.txt
```

5. Run the service

```bash
# Run the service which will default to http://127.0.0.1:8097
python main.py

# Run on specific host, port and enforce dev mode
python main.py --host MY_HOST --port MY_PORT --dev_mode 1
```

If host is `127.0.0.1` or `localhost`, the dev_mode is automatically set to True.
The only significant change if dev_mode is on, is that configuration errors at startup are logged but don’t prevent the service to run, and allow to override some implementations.

The hosts for the entitlements, search and storage services have to be provided as environment variables, or on the command line.

```bash
python main.py -e SERVICE_HOST_ENTITLEMENTS https://api.example.com/entitlements -e SERVICE_HOST_STORAGE https://api.example.com/storage -e SERVICE_HOST_SEARCH https://api.example.com/search
```

### Connect and Run Endpoints

1. Generate bearer token as all APIs but `/about` require authentication.

- Navigate to `http://127.0.0.1:8097/token` and follow the steps to generate a bearer token.

- Navigate to `http://127.0.0.1:8097/docs`. Click `Authorize` and enter your token. That will allow for authenticated requests.

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

To create a `log` record, below is a payload sample for the PUT `/ddms/v2/logs` API. The response will contain an id you can use on the `/ddms/v2/logs/{logid}/data` to create some bulk data.

```bash
[{
        "data": {
            "log": {
                "family": "Gamma Ray",
                "familyType": "Gamma Ray",
                "format": "float64",
                "mnemonic": "GR",
                "name": "GAMM",
                "unitKey": "gAPI"
            }
        },
        "kind": "opendes:osdu:log:1.0.5",
        "namespace": "opendes:osdu",
        "legal": {
            "legaltags": [
                "opendes-public-usa-dataset-1"
            ],
            "otherRelevantDataCountries": [
                "US"
            ],
            "status": "compliant"
        },
        "acl": {
            "viewers": [
                "data.default.viewers@opendes.p4d.cloud.slb-ds.com"
            ],
            "owners": [
                "data.default.owners@opendes.p4d.cloud.slb-ds.com"
            ]
        },
        "type": "log"
    }
]
```

### Run with Uvicorn

```bash
uvicorn app.wdms_app:wdms_app --port LOCAL_PORT
```

Then access app on `http://localhost:LOCAL_PORT/docs`

### Run with Docker

#### Build Image

A Personal Access Token (PAT) is required to pull all the python packages.

```bash
USER=<username>
PAT=<PAT>

# Set PIP_EXTRA_URL
PIP_EXTRA_URL="<URL>"

# Set IMAGE_TAG
IMAGE_TAG="os-wellbore-ddms:dev"

# Build Image
docker build -t=$IMAGE_TAG --rm . -f ./build/dockerfile --build-arg PIP_EXTRA_URL=$PIP_EXTRA_URL --build-arg PIP_WHEEL_DIR=python-packages
```

#### Run Image

1. Run the image

Replace the LOCAL_PORT value with a local port

```bash
LOCAL_PORT=<local_port>

docker run -d -p $LOCAL_PORT:8097 -e OS_WELLBORE_DDMS_DEV_MODE=1 -e USE_LOCALFS_BLOB_STORAGE_WITH_PATH=1 $IMAGE_TAG
```

2. Access app on `http://localhost:LOCAL_PORT/docs`

3. The environment variable `OS_WELLBORE_DDMS_DEV_MODE=1` enables dev mode

4. Logs can be checked by running

```bash
docker logs CONTAINER_ID
```

### Run Unit Tests Locally

```bash
# Install test dependencies
pip install -r requirements_dev.txt

python -m pytest --junit-xml=unit_tests_report.xml --cov=app --cov-report=html --cov-report=xml ./tests/unit
```

Coverage reports can be viewed after the command is run. The HMTL reports are saved in the htmlcov directory.

### Port Forward from Kubernetes

1.List the pods

```bash
kubectl get pods
```

2.Port forward

```bash
kubectl port-forward pods/POD_NAME LOCAL_PORT:8097
```

3.Access it on `http://localhost:LOCAL_PORT/docs`
