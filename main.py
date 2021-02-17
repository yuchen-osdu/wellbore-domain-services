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

import uvicorn
import click
from app.wdms_app import base_app
from app.conf import Config
import os


@click.command()
@click.option('-p', '--port', default=8080, help='port')
@click.option('-h', '--host', default='127.0.0.1',
              help='host, set to "0.0.0.0" to make the service available on network')
@click.option('--dev_mode', default=-1,
              help='(0|1) set dev mode, if not set will be true if localhost', type=int)
@click.option('-e', '--env', multiple=True, type=(str, str),
              help='set/override the env var within the service process')
def run_wdms_app(port: int, host: str, dev_mode, env):
    dev_mode = dev_mode if dev_mode >= 0 else int(host == '127.0.0.1' or host.lower() == 'localhost')

    if len(env) > 0:
        # work on a copy of environ
        environment_dict = os.environ.copy()
        for env_key, env_value in env:
            print(f'set {env_key} to {env_value}')
            environment_dict[env_key] = env_value

        # reload config with the updated environment -> will update declared var
        Config.reload(environment_dict)

        # push not explicitly declared var from the command args
        for env_key, env_value in env:
            if env_key not in Config:
                Config.add_from_env(env_key)
            Config.get_env_or_attribute(env_key).value = env_value

    # update
    Config.dev_mode.value = bool(dev_mode)
    Config.add('port', port)
    Config.add('host', host)

    uvicorn.run(base_app, port=port, host=host)


if __name__ == "__main__":
    run_wdms_app()

