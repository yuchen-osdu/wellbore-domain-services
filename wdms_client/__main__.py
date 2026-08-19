import click
import os
import json
from .request_builders import request_path_dict
from .request_builders.wdms_variables import variables_dict
from .variables import Variables
from .request_runner import RequestRunner


def get_env_file(environment) -> str:
    if environment:
        if not os.path.exists(environment):
            raise ValueError(f"{environment} does not exist")
        print("using environment file", environment)
        return environment

    # try get local
    try:
        return get_env_file(os.path.join(os.getcwd(), "local_environment.json"))
    except Exception:
        pass
    if not environment:
        print("WARNING no valid environment file provided")
    return environment


def get_env(environment) -> Variables:
    env = Variables.from_dict(variables_dict)
    environment = get_env_file(environment)
    if environment:
        local_env = Variables.load_env(environment, ignore_empty=True)
        env.update_env(local_env)
    return env


def get_runner(api) -> RequestRunner:
    if api not in request_path_dict:
        raise ValueError(f"ERROR:: api {api} is unknown")
    return request_path_dict[api]()


@click.group()
def cli():
    pass


@click.command(help='call an endpoint')
@click.option('--environment', default='', type=str, help='Specify a environment as a JSON file path (postman format)')
@click.argument('api', type=str)  # help='api to call, use "list" command to list them'
def call(api, environment):
    r = get_runner(api)
    r.call(get_env(environment))
    print(r)


@click.command(help='list available "api"')
def list():
    print("available apis:")
    for api in request_path_dict.keys():
        print('  -', api)


@click.command(help='describe the given "api"')
@click.option('--environment', default='', type=str, help='Specify a environment as a JSON file path (postman format)')
@click.argument('api', type=str)
def describe(api, environment):
    env = get_env(environment)
    r = get_runner(api)
    r.call(env, dry_run=True)
    print(r.runs[0].request)


@click.command(help='show env')
@click.option('--environment', default='', type=str, help='Specify a environment as a JSON file path (postman format)')
def show_env(environment):
    env = get_env(environment)

    print(f"environments variables given environment {environment if environment else '[none]'}")
    for k, v in env.enumerate():
        print(f"  - {k} = {v}")


@click.command(help='generate a basic environment file (targeting local server). Meant to be manually updated afterward')
@click.argument('output_file', type=str)
@click.option('--no-edit', '-n', default=False, is_flag=True, help="Do not edit file after creation.")
@click.option('--overwrite', '-o', default=False, is_flag=True, help="Allow overwrite if file exists.")
def gen_env(output_file: str, no_edit=False, overwrite=False):
    base_env_dict = {
        "description": "This is just a basic environment file target a local server.",
        "name": "wdms integration environment file",
        "values": [
            {
                "enabled": True,
                "key": "token",
                "value": "",
                "description": "JWT content"
            },
            {
                "enabled": True,
                "key": "data_partition",
                "value": ""
            },
            {
                "enabled": True,
                "key": "cloud_provider",
                "value": "local",
                "description": "any of ['local', 'az', 'gc', 'aws', 'ibm']"
            },
            {
                "enabled": True,
                "key": "base_url",
                "value": "http://127.0.0.1:8080/api/os-wellbore-ddms"
            },
            {
                "enabled": True,
                "key": "acl_domain",
                "value": ""
            },
            {
                "enabled": True,
                "key": "legal_tag",
                "value": ""
            }
        ]
    }

    if not output_file.lower().endswith('.json'):
        output_file = output_file + '.json'

    if not overwrite and os.path.exists(output_file):
        raise ValueError(f'"{output_file}" file already exists')

    with open(output_file, 'w') as f:
        json.dump(base_env_dict, f, indent=4)

    if no_edit:
        return

    abs_output_file = os.path.abspath(output_file)
    print("basic environment file generated in", os.path.abspath(abs_output_file))
    click.edit(filename=abs_output_file)


cli.add_command(call)
cli.add_command(list)
cli.add_command(describe)
cli.add_command(show_env)
cli.add_command(gen_env)


if __name__ == "__main__":
    cli()
