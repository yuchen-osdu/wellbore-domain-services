from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
RUNNER_PATH = ROOT / ".spi" / "run_acceptance.py"
SPEC = importlib.util.spec_from_file_location("spi_run_acceptance", RUNNER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load SPI acceptance runner")
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def test_pytest_command_selects_the_proven_live_suite(tmp_path):
    command = runner._pytest_command(
        tmp_path / "environment.json",
        tmp_path / "junit.xml",
    )

    assert "functional/tests/test_about.py" in command
    assert "functional/tests/test_crud_v3.py" in command
    assert (
        "functional/tests/test_bulk_statistics.py::test_get_bulk_statistic_basic_workflow"
        in command
    )
    assert "-p" in command
    assert "no:randomly" in command


def test_postman_environment_contains_only_the_supplied_live_contract():
    environment = runner._postman_environment(
        token="token-value",
        base_url="https://example.test/api/os-wellbore-ddms",
        partition="opendes",
        acl_domain="dataservices.energy",
        legal_tag="opendes-wdms-ci",
    )
    values = {item["key"]: item["value"] for item in environment["values"]}

    assert values["token"] == "token-value"
    assert values["base_url"].endswith("/api/os-wellbore-ddms")
    assert values["data_partition"] == "opendes"
    assert values["acl_domain"] == "dataservices.energy"
    assert values["legal_tag"] == "opendes-wdms-ci"
