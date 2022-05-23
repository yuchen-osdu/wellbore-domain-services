WDMS client CLI

# Usage example

`python -m wdms_client --help` to list available commands.

## list callable apis

Callable apis can be listed using command `list`:

```
:$ python -m wdms_client list

available apis:
  - crud.well.get_well
  - crud.well.delete_well
  - crud.well.get_well_specific_version
  - crud.well.get_versions_of_well
  - crud.well.create_well
  - crud.wellbore.delete_wellbore
  - crud.wellbore.get_wellbore_specific_version
...
```

## Show environment

Describe environment variables using command `show-env`. Can pass an environment file:

```
:$ python -m wdms_client show-env "..\..\my_environment.json"

environments variables given environment C:\SRC\opengroup\wellbore-domain-services\tests\integration\functional\my_environment.json
  - base_url = http://127.0.0.1:8080/api/os-wellbore-ddms
  - token = MY_TOKEN
  - cloud_provider = local
  - base_url_entity = logs
  - entity_kind = osdu:wks:log:1.0.5
  - dipsetKind = osdu:wks:dipSet:1.0.0
  - wellKind = osdu:wks:well:1.0.2
...
```

## Describe api before call

Use command `describe` with an `api` and optionally an environment file. It will print details of corresponding request:


```
python -m wdms_client describe crud.well.create_well --environment="..\..\my_environment.json"


============ REQUEST ===============
URL: [POST] http://127.0.0.1:8080/api/os-wellbore-ddms/ddms/v2/wells)
headers:
    - accept: application/json
    - Content-Type: application/json
    - data-partition-id: part
    - Connection: close
    - Authorization: Bearer 123******r 123
    - correlation-id: wdms_e2e__30319cb0-fcc6-463b-9929-d204514d7701
body: -------------------------------------------

[
{
  "acl": {
"owners": [
"data.default.owners@part.acl"
],
"viewers": [
"data.default.viewers@part.acl"
]
}, "legal": {
"legaltags": [
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

