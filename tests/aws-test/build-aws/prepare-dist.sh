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

# This script prepares the dist directory for the integration tests.
# Must be run from the root of the repostiory

set -e

OUTPUT_DIR="${OUTPUT_DIR:-dist}"

INTEGRATION_TEST_OUTPUT_DIR=${INTEGRATION_TEST_OUTPUT_DIR:-$OUTPUT_DIR}/testing

rm -rf "$INTEGRATION_TEST_OUTPUT_DIR"
mkdir -p "$INTEGRATION_TEST_OUTPUT_DIR"

if [ ! -e requirements_dev.txt ]; then
    echo "File requirements_dev.txt does not exist!"
else
    cp requirements_dev.txt tests/aws-test/build-aws/requirements.txt
fi
cp  -r tests/aws-test "${INTEGRATION_TEST_OUTPUT_DIR}"
cp  -r tests/integration "${INTEGRATION_TEST_OUTPUT_DIR}"
cp  -r schema/indexation "${INTEGRATION_TEST_OUTPUT_DIR}"
cp  -r tests/dependencies "${INTEGRATION_TEST_OUTPUT_DIR}"
cp  -r tests/performance "${INTEGRATION_TEST_OUTPUT_DIR}"
cp -r tests/unit "${INTEGRATION_TEST_OUTPUT_DIR}"
