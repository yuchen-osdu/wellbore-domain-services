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

import pytest
import os
import uuid
from unittest import mock

from app.helper.traces import create_exporter
from app.conf import Config, ConfigurationContainer, check_environment, validator_path_must_exist, \
    cloud_provider_additional_environment


@pytest.fixture
def testing_config():
    """
       WARNING: write access to a ConfigurationManager instance modifies the global config
    """

    config = ConfigurationContainer.with_load_all()

    # patching Config in app.conf module, so it is found by other modules
    with mock.patch('app.conf.Config', config):
        # returning the config for explicit use in tests.
        yield config

    # mock.patch will restore original Config after fixture use but original Config might been corrupted
    # when test write to testing_config


@pytest.fixture()
def gc_config_fixture():
    """
       DO NOT USE THIS
       BUG: global app.conf.Config corruption
    """
    original_provider_name = Config.cloud_provider.value

    provider_name = "gc"

    environment_dict = os.environ.copy()
    environment_dict[ConfigurationContainer.cloud_provider.key] = provider_name
    environment_dict['SERVICE_HOST_STORAGE'] = 'https://test-endpoint/api/storage'
    environment_dict['SERVICE_HOST_SEARCH'] = 'https://test-endpoint/api/search'
    environment_dict['SERVICE_HOST_SCHEMA'] = 'https://test-endpoint/api/schema-service'

    assert Config.cloud_provider.value == original_provider_name

    config = ConfigurationContainer.with_load_all(
        environment_dict=environment_dict,
        contextual_loader=cloud_provider_additional_environment)

    assert Config.cloud_provider.value == original_provider_name # Fails

    # patching Config in app.conf module, so it is found by other modules
    with mock.patch('app.conf.Config', config):
        # returning the config for explicit use in tests.
        yield config

    # mock.patch will restore original Config after fixture use but original Config is corrupted
    # because write access to an Config instance modifies other config instances
    assert Config.cloud_provider.value == original_provider_name # Fails





@pytest.fixture()
def azure_config_fixture():
    """
       DO NOT USE THIS
       BUG: global app.conf.Config corruption
    """
    original_provider_name = Config.cloud_provider.value

    provider_name = "az"

    environment_dict = os.environ.copy()
    environment_dict[ConfigurationContainer.cloud_provider.key] = provider_name
    environment_dict['AZ_AI_INSTRUMENTATION_KEY'] = 'ffffffff-1111-2222-aaaa-ffffffffffff'
    environment_dict['SERVICE_HOST_STORAGE'] = 'https://test-endpoint/api/storage'
    environment_dict['SERVICE_HOST_SEARCH'] = 'https://test-endpoint/api/search'
    environment_dict['SERVICE_HOST_SCHEMA'] = 'https://test-endpoint/api/schema-service'
    environment_dict['USE_PARTITION_SERVICE'] = 'disabled'

    assert Config.cloud_provider.value == original_provider_name

    config = ConfigurationContainer.with_load_all(
        environment_dict=environment_dict,
        contextual_loader=cloud_provider_additional_environment)

    assert Config.cloud_provider.value == original_provider_name # Fails

    # patching Config in app.conf module, so it is found by other modules
    with mock.patch('app.conf.Config', config):
        # returning the config for explicit use in tests.
        yield config

    assert Config.cloud_provider.value == original_provider_name # Fails


@pytest.mark.skip("global app.conf.Config corruption")
def test_gc_configuration_checker(gc_config_fixture):
    gc_config = gc_config_fixture

    assert gc_config.cloud_provider.value == "gc"
    variables_dict = gc_config.as_printable_dict()

    assert "default_data_tenant_project_id" in variables_dict.keys()
    assert "default_data_tenant_credentials" in variables_dict.keys()

    check_environment(gc_config)


@pytest.mark.skip("global app.conf.Config corruption")
def test_azure_configuration_checker(azure_config_fixture):
    azure_config = azure_config_fixture

    assert azure_config.cloud_provider.value == 'az'
    variables_dict = azure_config.as_printable_dict().keys()

    check_environment(azure_config)

    assert azure_config.az_bulk_container == 'wdms-osdu'

    # below attribute are Google Cloud only
    assert "default_data_tenant_project_id" not in variables_dict
    assert "default_data_tenant_credentials" not in variables_dict


@pytest.mark.skip("global app.conf.Config corruption")
def test_azure_trace_exporter_created(azure_config_fixture):
    exporter_name = 'AzureExporter'

    mock_exporter = mock.MagicMock(exporter_name=exporter_name)

    with mock.patch('app.helper.traces._create_azure_exporter', return_value=mock_exporter):
        exporter = create_exporter(service_name='test-service', config=azure_config_fixture)
        assert len(exporter.exporters) == 1
        # ensure called method is azure exporter
        azure_exporter = exporter.exporters[0]
        assert azure_exporter.exporter_name == exporter_name


@pytest.mark.skip("global app.conf.Config corruption")
def test_gc_trace_exporter_created(gc_config_fixture):
    exporter_name = 'StackdriverExporter'

    mock_exporter = mock.MagicMock(exporter_name=exporter_name)

    with mock.patch('app.helper.traces._create_gc_exporter', return_value=mock_exporter):
        exporter = create_exporter(service_name='test-service', config=gc_config_fixture)
        assert len(exporter.exporters) == 1
        # ensure called method is Google Cloud exporter
        gc_exporter = exporter.exporters[0]
        assert gc_exporter.exporter_name == exporter_name


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
    env_var_key = str(uuid.uuid4())
    assert env_var_key not in testing_config
    testing_config.add_from_env(env_var_key=env_var_key, attribute_name='custom_var'+env_var_key, default='Dummy')

    assert env_var_key in testing_config
    assert 'custom_var'+env_var_key in testing_config


def test_get_as_env(testing_config):
    env_var_key = str(uuid.uuid4())
    assert env_var_key not in testing_config
    testing_config.add_from_env(env_var_key=env_var_key, attribute_name='custom_var'+env_var_key, default='Dummy')
    testing_config.add('Not_an_env'+env_var_key, 'value')

    assert 'Not_an_env'+env_var_key in testing_config


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


def test_get_fall_back_to_env_if_not_declared(testing_config):
    expected_path = os.getenv('PATH')
    assert expected_path == testing_config['PATH']
    assert expected_path == testing_config.get('PATH')


def test_secret_value_must_not_be_printed(testing_config):
    testing_config.add_from_env(env_var_key='DUMMY_VAR', default='ThisIsSecret', secret=True)

    assert 'ThisIsSecret' not in testing_config.DUMMY_VAR.printable_value
    assert 'ThisIsSecret' not in str(testing_config)


def test_check_environment_must_throw_for_undefined_envvar(testing_config):
    # given undefined (overriding it to ensure undefined)
    env_var_key = str(uuid.uuid4())  # substitute of the real one
    testing_config.add_from_env(env_var_key=env_var_key,
                                attribute_name=env_var_key,
                                override=True,
                                is_mandatory=True)

    testing_config.dev_mode.value = False

    # then
    with pytest.raises(RuntimeError) as e:
        # when
        check_environment(testing_config)

    # and then expect something meaningful in the error description
    assert env_var_key in str(e)


def test_check_environment_must_throw_for_invalid_path(testing_config):
    # given defined with invalid path (overriding it to ensure undefined)
    env_var_key = str(uuid.uuid4())  # substitute of the real one
    testing_config.add_from_env(env_var_key=env_var_key,
                                attribute_name=env_var_key,
                                override=True,
                                default=env_var_key + '.not_exist.txt',
                                is_mandatory=True,
                                validator=validator_path_must_exist)

    testing_config.dev_mode.value = False

    # then
    with pytest.raises(RuntimeError) as e:
        # when
        check_environment(testing_config)

    # and then expect something meaningful in the error description
    assert env_var_key in str(e)


@pytest.mark.skip("global app.conf.Config corruption")
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
    testing_config.dev_mode.load(os.environ)

    # then
    assert type(testing_config.dev_mode.value) == bool
    assert testing_config.dev_mode.value == expected_value
