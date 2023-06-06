#!/bin/bash
cd $CI_PROJECT_DIR

# Install Google Cloud SDK
curl https://sdk.cloud.google.com > install.sh
bash install.sh --disable-prompts
source /root/google-cloud-sdk/completion.bash.inc
source /root/google-cloud-sdk/path.bash.inc

# Setup Python environment
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install wheel

# Install Python requirements
for REQ in $PIP_REQUIREMENTS ; do
  pip install -r $REQ
done

# Change to test directory

cd tests/integration

# Setup Google Cloud authentication
echo $GC_INTEGRATION_TESTER | base64 -d > file.json
gcloud auth activate-service-account --key-file file.json
gcloud config set project $GC_PROJECT

# Generate Postman environment
python gen_postman_env.py \
--token $(gcloud auth print-access-token) \
--base_url $GC_WELLBORE_BASE_URL \
--cloud_provider $GC_VENDOR \
--data_partition $GC_TENANT \
--acl_domain $GROUP_ID \
--legal_tag $LEGAL_TAG

# Run pytest
pytest ./functional --environment="./generated/postman_environment.json" --filter-tag=!search -p no:randomly
