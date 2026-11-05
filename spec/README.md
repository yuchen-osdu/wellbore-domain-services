# Wellbore DMS OpenAPI Specification

The OpenAPI specification for Wellbore DMS is reverse generated from the source code - 
as opposed to generating the implementation from the specification.

## Where to find it
The Swagger page for WDMS is available along the running service, at
`https://{hostname}/docs`. 
And the OpenAPI specification file will be at `https://{hostname}/openapi.json`

E.g.: On local deployment, `http://127.0.0.1:8080/api/os-wellbore-ddms/openapi.json`

The committed baseline is [`docs/api/community/v1/openapi.json`](../docs/api/community/v1/openapi.json),
generated from the FastAPI application. JSON is used for both the baseline and
the live endpoint, so the shared CIMPL OpenAPI check can compare them without
format conversion or a service-local job override.

The `v1` directory is the shared CI job's default documentation location, not
the version of the WDMS entity API. The specification includes `/ddms/v3` and
the service's other exposed routes.

## Updating the baseline

From the repository root, with development dependencies installed:

```bash
uv run --frozen --no-sync python -m pytest tests/unit/spec/
```

When the schema changes, `test_api_spec` writes the updated JSON and fails.
Review and commit that file, then rerun the tests. The output uses sorted keys
and two-space indentation. The test adds the relative `servers` URL from
`Config.openapi_prefix`, which FastAPI normally adds on the first HTTP request.
The other spec tests validate the schema, check operation-ID uniqueness, and
compare it with the HTTP endpoint.

The unit tests provide the pre-merge check; the shared CIMPL job compares the
committed baseline with the deployed service after deployment.

## Generating a partial OpenAPI for documentation purposes

The spec unit tests can also generate a partial OpenAPI spec by setting the
OPENAPI_FILTER_PREFIX and OPENAPI_FILTER_TAGS environment variables. Do not
commit a filtered document over the complete baseline.

Example:
```
export OPENAPI_FILTER_PREFIX='/ddms/v3'
export OPENAPI_FILTER_TAGS='Wellbore,WellLog'
python -m pytest ./tests/unit/spec/
```
