# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script executes the test and copies reports to the provided output directory
# To call this script from the service working directory
# ./dist/testing/tests/integration/build-aws/run-tests.sh "./reports/"
echo '********* Running Wellbore DDMS integration tests  *********'

SCRIPT_SOURCE_DIR=$(dirname "$0")
echo "Script source directory: $SCRIPT_SOURCE_DIR"

pushd "$SCRIPT_SOURCE_DIR"/../../../
echo "Current working directory: $(pwd)"

# Debug Python environment
echo "=== Python Environment Debug ==="
echo "PYENV_VERSION (global): $PYENV_VERSION"
echo "PYTHON_313_VERSION: $PYTHON_313_VERSION"
echo "Available Python versions:"
pyenv versions

# Use the CodeBuild provided PYTHON_313_VERSION or find one
if [ -z "$PYTHON_313_VERSION" ]; then
    echo "PYTHON_313_VERSION not set, finding Python 3.13 version..."
    PYTHON_313_VERSION=$(pyenv versions | grep "3\.13\." | head -1 | xargs)
    if [ -z "$PYTHON_313_VERSION" ]; then
        echo "ERROR: No Python 3.13 version found"
        exit 1
    fi
    echo "Found Python 3.13 version: $PYTHON_313_VERSION"
else
    echo "Using CodeBuild provided Python 3.13 version: $PYTHON_313_VERSION"
fi

echo "Creating virtual environment with Python $PYTHON_313_VERSION..."

# Create venv using specific Python 3.13 version
PYENV_VERSION=$PYTHON_313_VERSION pyenv exec python -m venv env

if [ ! -d "env" ]; then
    echo "ERROR: Virtual environment creation failed"
    exit 1
fi
source env/bin/activate
python3 -m pip install -r ./tests/aws-test/build-aws/requirements.txt --extra-index-url https://community.opengroup.org/api/v4/projects/465/packages/pypi/simple
python3 -m pip install -r ./tests/aws-test/build-aws/requirements_dev.txt
rm -rf test-reports/
mkdir test-reports

export AWS_COGNITO_AUTH_PARAMS_USER=${ADMIN_USER} #set by env script
export AWS_COGNITO_AUTH_PARAMS_PASSWORD=${ADMIN_PASSWORD} #set by codebuild 
tenant='opendes'
acl_domain='example.com'
legal_tag='opendes-wellddmstestlegaltag'
token=$(python3 tests/aws-test/build-aws/aws_jwt_client.py)

echo 'Register Legal tag before Integration Tests ...'
curl --location --request POST "$LEGAL_URL"'legaltags' \
  --header 'accept: application/json' \
  --header 'authorization: Bearer '"$token" \
  --header 'content-type: application/json' \
  --header 'data-partition-id: opendes' \
  --data '{
        "name": "wellddmstestlegaltag",
        "description": "legal tag for Wellbore DMS Service Integration tests",
        "properties": {
            "countryOfOrigin":["US"],
            "contractId":"A1234",
            "expirationDate":"2099-01-25",
            "dataType":"Public Domain Data", 
            "originator":"MyCompany",
            "securityClassification":"Public",
            "exportClassification":"EAR99",
            "personalData":"No Personal Data"
        }
}'
cd tests/integration

python3 gen_postman_env.py --token $token --base_url $WELLBORE_DDMS_URL --cloud_provider "aws" --acl_domain $acl_domain --legal_tag $legal_tag --data_partition $tenant

pytest ./functional --environment="./generated/postman_environment.json" --filter-tag=!search -p no:randomly

TEST_EXIT_CODE=$?

echo Delete legaltag after Integration Tests...
curl --location --request DELETE "$LEGAL_URL"'legaltags/opendes-wellddmstestlegaltag' \
--header 'Authorization: Bearer '"$token" \
--header 'data-partition-id: opendes' \
--header 'Content-Type: application/json'

deactivate


exit $TEST_EXIT_CODE
