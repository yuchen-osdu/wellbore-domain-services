#!/bin/bash
# Ensure a long-lived LegalTag for WDMS CIMPL e2e tests.
# CI LEGAL_TAG=osdu-demo-legaltag can expire; Storage then returns 400 Invalid legal tags.
# Updating an expired tag does not make it valid until Legal's daily job, so create/reuse
# a dedicated WDMS tag instead. Do not delete it: integration and acceptance can overlap.

_legal_api="${LEGAL_URL:-${LEGAL_HOST:-${LEGAL_BASE_URL:-}}}"
if [ -z "${_legal_api}" ]; then
  echo "LEGAL_URL/LEGAL_HOST/LEGAL_BASE_URL not set; skipping legal tag ensure"
  unset _legal_api
  return 0 2>/dev/null || true
fi
_legal_api="${_legal_api%/}"

_partition="${CIMPL_TENANT:-${DATA_PARTITION_ID:-osdu}}"
export LEGAL_TAG="${_partition}-wdms-e2e-legaltag"
_short_name="wdms-e2e-legaltag"

if [ -z "${TOKEN:-}" ]; then
  echo "TOKEN is not set; cannot ensure LegalTag ${LEGAL_TAG}"
  unset _legal_api _partition _short_name
  return 1 2>/dev/null || exit 1
fi

echo "Ensuring LegalTag ${LEGAL_TAG} at ${_legal_api} ..."

_http_code=$(curl -sS -o /tmp/wdms_legaltag.json -w "%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "data-partition-id: ${_partition}" \
  -H "accept: application/json" \
  "${_legal_api}/legaltags/${LEGAL_TAG}" || true)

if [ "${_http_code}" = "200" ]; then
  echo "LegalTag ${LEGAL_TAG} already exists"
  unset _legal_api _partition _short_name _http_code
  return 0 2>/dev/null || true
fi

echo "Creating LegalTag ${_short_name} (GET HTTP ${_http_code}) ..."
_create_code=$(curl -sS -o /tmp/wdms_legaltag_create.json -w "%{http_code}" \
  -X POST "${_legal_api}/legaltags" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "data-partition-id: ${_partition}" \
  -H "content-type: application/json" \
  -H "accept: application/json" \
  --data "{
    \"name\": \"${_short_name}\",
    \"description\": \"Legal tag for Wellbore DMS CIMPL integration tests\",
    \"properties\": {
      \"countryOfOrigin\": [\"US\"],
      \"contractId\": \"A1234\",
      \"expirationDate\": \"2099-12-31\",
      \"dataType\": \"Public Domain Data\",
      \"originator\": \"OSDU\",
      \"securityClassification\": \"Public\",
      \"exportClassification\": \"EAR99\",
      \"personalData\": \"No Personal Data\"
    }
  }" || true)

echo "Create LegalTag HTTP ${_create_code}"
cat /tmp/wdms_legaltag_create.json || true
echo

if [ "${_create_code}" != "201" ] && [ "${_create_code}" != "200" ] && [ "${_create_code}" != "409" ]; then
  echo "Failed to ensure LegalTag ${LEGAL_TAG}"
  unset _legal_api _partition _short_name _http_code _create_code
  return 1 2>/dev/null || exit 1
fi

unset _legal_api _partition _short_name _http_code _create_code
