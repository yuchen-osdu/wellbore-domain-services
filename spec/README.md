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

## Publishing to community documentation repo
A sanitized version of the OpenAPI specification including only the OSDU v3 APIs is published
in the [platform/api/Wellbore-DDMS](https://community.opengroup.org/osdu/documentation/-/tree/master/platform/api/Wellbore-DDMS)
section of the OSDU community documentation repo.

_**Latest synced version:**_ (Jun/09/2021)
