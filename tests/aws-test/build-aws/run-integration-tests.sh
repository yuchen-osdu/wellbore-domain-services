#!/usr/bin/env bash
# from tests/aws-test/build-aws/ goes up to the tests dir.
cd ../../../

# Install venv for python3
which apt-get && sudo apt-get install -y python3 python3-pip python3-venv || echo "Not Ubuntu, skipping"
which yum && sudo yum install -y python3 python3-pip python3-venv || echo "Not RHEL, skipping"

python3 -m venv env
source env/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r frozenrequirements.txt
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements_dev.txt
python3 -m pip install wheel pytest pytest-cov

svc_url=$WELLBORE_DDMS_URL
tenant='opendes'
acl_domain='example.com'
legal_tag='opendes-sdmstestlegaltag'
svctoken=$(python3 tests/aws-test/build-aws/aws_jwt_client.py)

cd tests/integration

python3 gen_postman_env.py --token $svctoken --base_url $svc_url --cloud_provider "aws" --acl_domain $acl_domain --legal_tag $legal_tag --data_partition $tenant

pytest ./functional --environment="./generated/postman_environment.json" --filter-tag=basic
