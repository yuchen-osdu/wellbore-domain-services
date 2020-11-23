from app.conf import *
import pytest
import os
import uuid
from app.utils import Context, NopeLogger


@pytest.fixture
def testing_context():
    """ This is a basic Context initialized with empty logger to ensure tested methods can contains logging calls """
    return Context.set_current(Context(logger=NopeLogger(), request_id='this is a test'))


@pytest.fixture
def testing_config():
    return ConfigurationContainer.with_load_all()


def test_config_get_by_name(testing_config):
    assert testing_config.dev_mode.value == testing_config['dev_mode']


def test_add(testing_config):
    assert testing_config.get('custom', 42) == 42
    assert 'custom' not in testing_config
    testing_config.add('custom', 1337)
    assert testing_config['custom'] == 1337
    assert testing_config.custom == 1337
    assert testing_config.get('custom', 42) == 1337

    with pytest.raises(Exception):
        testing_config.add('custom', 42)
    assert testing_config.custom == 1337

    # with override
    testing_config.add('custom', 42, override=True)
    assert testing_config.custom == 42


def test_contains(testing_config):
    assert not 'CUSTOM_ENVVAR' in testing_config
    testing_config.add_from_env(env_var_key='CUSTOM_ENVVAR', attribute_name='custom_var', default='Dummy')

    assert 'CUSTOM_ENVVAR' in testing_config
    assert 'custom_var' in testing_config


def test_get_as_env(testing_config):
    assert not 'CUSTOM_ENVVAR' in testing_config
    testing_config.add_from_env(env_var_key='CUSTOM_ENVVAR', attribute_name='custom_var', default='Dummy')
    testing_config.add('Not_an_env', 'value')

    assert testing_config.get_env('CUSTOM_ENVVAR').value == 'Dummy'
    assert testing_config.get_env('custom_var').value == 'Dummy'
    assert 'Not_an_env' in testing_config
    assert testing_config.get_env('Not_an_env') is None


def test_add_from_env(testing_config):
    expected_path = os.getenv('PATH')
    testing_config.add_from_env(env_var_key='PATH', attribute_name='env_var_path')
    assert expected_path == testing_config.env_var_path.value
    assert expected_path == testing_config['env_var_path']
    assert expected_path == testing_config['PATH']

    with pytest.raises(Exception):
        testing_config.add_from_env(env_var_key='NO_EXISTING_VAR', attribute_name='env_var_path', default='Dummy')
    assert expected_path == testing_config.env_var_path.value

    testing_config.add_from_env(env_var_key='NO_EXISTING_VAR', attribute_name='env_var_path', default='Dummy', override=True)
    assert 'Dummy' == testing_config.env_var_path.value

    with pytest.raises(Exception):
        str(testing_config['PATH'])  # no longer exist


def test_secret_value_must_not_be_printed(testing_config):
    testing_config.add_from_env(env_var_key='DUMMY_VAR', default='ThisIsSecret', secret=True)

    assert 'ThisIsSecret' not in testing_config.DUMMY_VAR.printable_value
    assert 'ThisIsSecret' not in str(testing_config)


@pytest.mark.parametrize("config_attribute_name", ['default_data_tenant_project_id'])
def test_check_environment_must_throw_for_undefined_envvar(config_attribute_name, testing_config):
    # given undefined (overriding it to ensure undefined)
    env_var_key = str(uuid.uuid4())  # substitute of the real one
    testing_config.add_from_env(env_var_key=env_var_key, attribute_name=config_attribute_name, override=True)
    assert not testing_config[config_attribute_name], f'=config.{config_attribute_name} must be undefined'
    testing_config.dev_mode.value = False

    # then
    with pytest.raises(RuntimeError) as e:
        # when
        check_environment(testing_config)

    # and then expect something meaningful in the error description
    assert env_var_key in str(e)


@pytest.mark.parametrize("config_attribute_name", ['default_data_tenant_credentials'])
def test_check_environment_must_throw_for_invalid_path(config_attribute_name, testing_config):
    # given defined with invalid path (overriding it to ensure undefined)
    env_var_key = str(uuid.uuid4())  # substitute of the real one
    testing_config.add_from_env(env_var_key=env_var_key, attribute_name=config_attribute_name, override=True,
                                default=env_var_key + '.not_exist.txt')
    assert testing_config[config_attribute_name], f'=config.{config_attribute_name} must be defined'
    assert not os.path.exists(testing_config[config_attribute_name])
    testing_config.dev_mode.value = False

    # then
    with pytest.raises(RuntimeError) as e:
        # when
        check_environment(testing_config)

    # and then expect something meaningful in the error description
    assert env_var_key in str(e)
    assert testing_config[config_attribute_name] in str(e)
    assert 'not found' in str(e)


@pytest.mark.parametrize('input_value,expected_value', [
    ('false', False),
    ('0', False),
    ('dummy_value', False),
    ('TrUe', True),
    ('1', True)])
def test_config_dev_mode(input_value: str, expected_value: bool, testing_config):
    # update dev_mode input value without effecting env
    testing_config.dev_mode.default = input_value
    testing_config.dev_mode.key = str(uuid.uuid4())
    testing_config.dev_mode.load()

    # then
    assert type(testing_config.dev_mode.value) == bool
    assert testing_config.dev_mode.value == expected_value

