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
    args = parser.parse_args()

    try:
        os.mkdir("./generated")
    except FileExistsError:
        pass

    env_data = get_environment_data(env_name="wellboredms_continuous_tests", token=args.token)
    if args.base_url is not None:
        add_environment_data(env_data, "base_url", args.base_url, "string")
    create_env_file("generated/postman_environment.json", env_data)