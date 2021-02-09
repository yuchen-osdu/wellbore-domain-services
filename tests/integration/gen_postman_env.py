# Copyright 2021 Schlumberger
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
import time
import json
import argparse
import os

def get_environment_data(env_name, token):
    return {
        "name": env_name,        
        "values": [
            {
                "enabled": True,
                "key": "token",
                "value": token,
                "type": "text"
            },          
        ],
        "date" : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": time.time(),
        "_postman_variable_scope": "environment",
    }

def add_environment_data(environment, key, value, type):
    environment['values'].append(
        {
            "enabled": True,
            "key": key,
            "value": value,
            "type": type
        }
    )

def create_env_file(file_path, env_data):
    with open(file_path, 'w') as outfile:
        json.dump(env_data, outfile)


if __name__ == "__main__":
    # execute only if run as a script

    parser = argparse.ArgumentParser(description='Generates postman environment file for test')
    parser.add_argument('--token', dest="token", help="auth token")
    parser.add_argument('--base_url', dest="base_url", help="service base url", default=None)
    parser.add_argument('--data_partition', dest="data_partition", help="data partition name", default=None)
    parser.add_argument('--cloud_provider', dest="cloud_provider", help="Name of cloud provider in which tests are run")
    parser.add_argument('--acl_domain', dest="acl_domain", help="acl_domain name", default=None)
    parser.add_argument('--legal_tag', dest="legal_tag", help="legal_tag", default=None)
    args = parser.parse_args()

    try:
        os.mkdir("./generated")
    except FileExistsError:
        pass

    env_data = get_environment_data(env_name="wellboredms_continuous_tests", token=args.token)
    if args.base_url:
        add_environment_data(env_data, "base_url", args.base_url, "string")
    if args.data_partition:
        add_environment_data(env_data, "data_partition", args.data_partition, "string")
    if args.cloud_provider:
        add_environment_data(env_data, "cloud_provider", args.cloud_provider, "string")
    if args.acl_domain:
        add_environment_data(env_data, "acl_domain", args.acl_domain, "string")
    if args.legal_tag:
        add_environment_data(env_data, "legal_tag", args.legal_tag, "string")
    create_env_file("generated/postman_environment.json", env_data)