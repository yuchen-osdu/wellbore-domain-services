# Wellbore DMS OpenAPI Specification

The OpenAPI specification for Wellbore DMS is reverse generated from the source code - 
as opposed to generating the implementation from the specification.

## Where to find it
The Swagger page for WDMS is available along the running service, at
`https://{hostname}/docs`. 
And the OpenAPI specification file will be at `https://{hostname}/openapi.json`

E.g.: On local deployment, `http://127.0.0.1:8080/api/os-wellbore-ddms/openapi.json`

The `spec` directory contains the OpenAPI specification files for Wellbore DMS.

Under `spec/generated`, the OpenAPI in JSON format is saved as-is.

## Generating a partial OpenAPI for documentation purposes

The OpenAPI specification in `spec/generated` folder is re-created at every API change as part of the spec unit tests.
These unit tests can also be used to generate a partial OpenAPI spec by setting the OPENAPI_FILTER_PREFIX and the OPENAPI_FILTER_TAGS environment variables.

Example:
```
export OPENAPI_FILTER_PREFIX='/ddms/v3'
export OPENAPI_FILTER_TAGS='Wellbore,WellLog'
python -m pytest ./tests/unit/spec/
```

_**Latest synced version:**_ (Jun/09/2021)
