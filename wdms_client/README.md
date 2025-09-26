WDMS client CLI

# Usage example

`python -m wdms_client --help` to list available commands.

## list callable apis

Callable apis can be listed using command `list`:

```
:$ python -m wdms_client list
available apis:
  - crud.osdu_wellbore.delete_osdu_wellbore
  - crud.osdu_wellbore.get_osdu_wellbore_specific_version
  - crud.osdu_wellbore.get_osdu_wellbore
  - crud.osdu_wellbore.get_versions_of_osdu_wellbore
  - crud.osdu_wellbore.create_osdu_wellbore
  - crud.osdu_wellbore_100.delete_osdu_wellbore_100
  - crud.osdu_wellbore_100.get_osdu_wellbore_100_specific_version
  - crud.osdu_wellbore_100.get_osdu_wellbore_100
  - crud.osdu_wellbore_100.get_versions_of_osdu_wellbore_100
...
```

## Show environment

Describe environment variables using command `show-env`. Can pass an environment file:

```
:$ python -m wdms_client show-env --environment "tests/integration/functional/local_environment.json"

environments variables given environment tests/integration/functional/local_environment.json
  - base_url = http://localhost:8080/api/os-wellbore-ddms
  - token = MY_TOKEN
  - cloud_provider = local
  - wellKind = osdu:wks:well:1.0.2
  - wellboreKind = osdu:wks:wellbore:1.0.6
  - trajectoryKind = osdu:wks:trajectory:1.0.5
  - trajectory_data = {'name': 'wdms_e2e_trajectory'}
  - authorityKind = osdu
  - osduWellboreKind = osdu:wks:master-data--Wellbore:1.3.0
  - osduWellKind = osdu:wks:master-data--Well:1.2.0
...
```

## Describe api before call

Use command `describe` with an `api` and optionally an environment file. It will print details of corresponding request:


```
python -m wdms_client describe crud.osdu_wellbore.create_osdu_wellbore --environment "tests/integration/functional/local_environment.json"
using environment file tests/integration/functional/local_environment.json
URL: [POST] http://localhost:8080/api/os-wellbore-ddms/ddms/v3/wellbores)
headers:
    - accept: application/json
    - Content-Type: application/json
    - data-partition-id: local-partition
    - Connection: close
    - Authorization: Bearer R4nd0******Tr1nG
    - correlation-id: wdms_e2e/3585c399-1bde-4966-8d79-53064f4661c1
body: -------------------------------------------
[{
  "acl": {
"owners": [
"data.default.owners@local-partition.p4d.cloud.slb-ds.com"
],
"viewers": [
"data.default.viewers@local-partition.p4d.cloud.slb-ds.com"
]
}, "legal": {
"legaltags": [
"opendes-public-usa-dataset-1"
],
...
```


## Perform a call

Use command `describe` with an `api` and optionally an environment file. It will run it and print the result:

```
python -m wdms_client call about --environment="..\..\my_environment.json"
1 run(s) for about:

# run 1:
[200] - http://127.0.0.1:8080/api/os-wellbore-ddms/about
start: [2021-10-14 13:46:00.279199], end: 2021-10-14 13:46:00.291161, elapsed: 11 ms

============ REQUEST ===============
URL: [GET] http://127.0.0.1:8080/api/os-wellbore-ddms/about)
headers:
    - User-Agent: python-requests/2.26.0
    - Accept-Encoding: gzip, deflate
    - accept: application/json
    - Connection: close
    - correlation-id: wdms_e2e__8b7c80ea-5bdd-45d7-9738-51431efdc820


============ RESPONSE ===============
headers:
    - date: Thu, 14 Oct 2021 11:46:00 GMT
    - server: uvicorn
    - content-length: 97
    - content-type: application/json
    - Connection: close
body: -------------------------------------------
{"service":"Wellbore DDMS OSDU","version":"0.2","buildNumber":"local","cloudEnvironment":"local"}
```

## Generated basic environment file

use command `gen-env` to generate a basic environment file. By default, automatically launch editor on the created file.

```
python -m wdms_client gen-env new_environment.json

 basic environment file generated in $WORKING_DIR\new_environment.json
```

## Default environment file

If no environment file is provided, it will try to use `local_environment.json` from the working directory if exists.
