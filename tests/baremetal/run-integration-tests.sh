#!/bin/bash
cd $CI_PROJECT_DIR

# Install necessary tools
wget -O /usr/local/bin/jq https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64
chmod +x /usr/local/bin/jq

# Get token
export TOKEN=$(curl --location --request POST "$TEST_OPENID_PROVIDER_URL/protocol/openid-connect/token" \
--header "Content-Type: application/x-www-form-urlencoded" \
--data-urlencode "client_id=$TEST_OPENID_PROVIDER_CLIENT_ID" \
--data-urlencode "client_secret=$TEST_OPENID_PROVIDER_CLIENT_SECRET" \
--data-urlencode "scope=openid" \
--data-urlencode "grant_type=client_credentials" | jq -r ".id_token")

# Setup Python environment
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install wheel

# Install Python requirements
for REQ in $PIP_REQUIREMENTS $PIP_REQUIREMENTS_TOOLING_ONLY; do
  pip install -r $REQ
done

# Change to test directory
cd tests/integration

# Generate Postman environment
python gen_postman_env.py \
--token $TOKEN \
--base_url $CIMPL_WELLBORE_BASE_URL \
--cloud_provider "baremetal" \
--data_partition $CIMPL_TENANT \
--acl_domain $GROUP_ID \
--legal_tag $LEGAL_TAG

# Run pytest
pytest ./functional --environment="./generated/postman_environment.json" --filter-tag='!search|!chunking|!bulk|!describe' -p no:randomly
