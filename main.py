import uvicorn
import click
from app.wdms_app import wdms_app
from app.conf import Config


@click.command()
@click.option('-p', '--port', default=8097, help='port')
@click.option('-h', '--host', default='127.0.0.1',
              help='host, set to "0.0.0.0" to make the service available on network')
@click.option('--dev_mode', default=-1,
              help='(0|1) set dev mode, if not set will be true if localhost', type=int)
@click.option('-e', '--env', multiple=True, type=(str, str),
              help='set/override the env var within the service process')
def run_wdms_app(port: int, host: str, dev_mode, env):
    dev_mode = dev_mode if dev_mode >= 0 else int(host == '127.0.0.1' or host.lower() == 'localhost')
    Config.dev_mode.value = bool(dev_mode)
    Config.add('port', port)
    Config.add('host', host)

    for env_key, env_value in env:
        print(f'set {env_key} to {env_value}')
        if env_key not in Config:
            Config.add_from_env(env_key)
        Config.get_env(env_key).value = env_value

    uvicorn.run(wdms_app, port=port, host=host)


if __name__ == "__main__":
    run_wdms_app()

