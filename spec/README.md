# Wellbore DMS OpenAPI Specification

The OpenAPI specification for Wellbore DMS is reverse generated from the source code - 
as opposed to generating the implementation from the specification.

## Where to find it
The Swagger page for WDMS is available along the running service at,
`https://{hostname}/docs`. 
And the OpenAPI specification file will be at `https://{hostname}/openapi.json`

E.g.: For EVT enviroment, `https://evt-mvp.managed-osdu.cloud.slb-ds.com/api/os-wellbore-ddms/openapi.json`

The `spec` directory contains the OpenAPI specification files for Wellbore DMS.

Under `spec/generated`, the OpenAPI in JSON format is saved as-is.

## Publishing to Developer Portal
API products are grouped in families as described in the table below.

API reference/Swagger |	API Product |	Path | Objects/services 
--- | --- | --- | --- 
Wellbore Objects Generic data types	| OSDU Wellbore DMS - Data Access |	baseURL/osdu/wdms/wellbore/v2 |	Well, Wellbore, Logset, Log, Trajectory, Geology
Dips & Markers | OSDU Wellbore DMS - Data Access | baseURL/osdu/wdms/geology/v2 | Dip & DipSet, Maker
Search | OSDU Wellbore DMS - Data Access | baseURL/osdu/wdms/search/v2 | Search (aka Contextualization)
Log Recognition	| OSDU Wellbore DMS - Data Services | baseURL/osdu/wdms/log-recognition/v2 | Rule Based Log Recognition

### Steps 
1. Convert generated JSON to YAML. Use swagger-codegen-cli locally, or Swagger Editor UI locally.
2. The converted YAML had syntax errors that were corrected in `spec/edited/openapi.yaml`
3. `spec/edited/openapi.yaml` was split according to the API groups defined above, 
`geology.yaml`, `log-recognition.yaml`, `search.yaml`, and `wellbore.yaml`, placed under `spec/edited`.


_**Latest synced version:**_ Commit 6bad362 (Dec/10/2020)