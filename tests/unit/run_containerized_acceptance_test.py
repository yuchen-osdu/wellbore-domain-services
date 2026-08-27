from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

RUNNER_PATH = (
    Path(__file__).parents[1] / "integration" / "run_containerized_acceptance.py"
)
REQUIRED_ENVIRONMENT = {
    "INTEGRATION_TESTER_ACCESS_TOKEN": "token",
    "WDMS_ACL_DOMAIN": "dataservices.energy",
    "WDMS_BASE_URL": "https://example.test/api/os-wellbore-ddms",
    "WDMS_LEGAL_URL": "https://example.test/api/legal/v1",
    "WDMS_DATA_PARTITION": "opendes",
    "WDMS_LEGAL_TAG": "opendes-test-legal-tag",
}


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_containerized_acceptance", RUNNER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the acceptance runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunContainerizedAcceptanceTest(unittest.TestCase):
    def test_main_runs_acceptance_suite_without_runtime_install(self):
        runner = load_runner()
        environment = {
            **REQUIRED_ENVIRONMENT,
            "TEST_REPO_ROOT": "/tmp/repository",
            "TEST_RESULTS_DIR": "/tmp/test-reports",
        }
        pytest_result = SimpleNamespace(returncode=17)

        with (
            mock.patch.dict(os.environ, environment, clear=True),
            mock.patch.object(runner.os, "chdir") as chdir,
            mock.patch.object(runner.Path, "mkdir") as mkdir,
            mock.patch.object(runner, "_ensure_legal_tag") as ensure_legal_tag,
            mock.patch.object(
                runner.subprocess,
                "run",
                side_effect=[SimpleNamespace(returncode=0), pytest_result],
            ) as run,
            self.assertRaises(SystemExit) as exit_error,
        ):
            runner.main()

        self.assertEqual(exit_error.exception.code, 17)
        chdir.assert_called_once_with(Path("/tmp/repository").resolve())
        mkdir.assert_called_once_with(parents=True, exist_ok=True)
        ensure_legal_tag.assert_called_once_with(
            "token",
            "https://example.test/api/legal/v1",
            "opendes-test-legal-tag",
            "opendes",
        )
        self.assertEqual(run.call_count, 2)
        self.assertIn(
            "tests/integration/gen_postman_env.py",
            run.call_args_list[0].args[0],
        )
        pytest_command = run.call_args_list[1].args[0]
        self.assertIn("tests/integration/functional", pytest_command)
        self.assertIn("--filter-tag=!search", pytest_command)
        self.assertNotIn("--reruns", pytest_command)
        self.assertNotIn(
            "pip",
            " ".join(
                argument for call in run.call_args_list for argument in call.args[0]
            ),
        )

    def test_main_rejects_each_missing_required_variable(self):
        runner = load_runner()

        for missing_name in REQUIRED_ENVIRONMENT:
            with self.subTest(missing_name=missing_name):
                environment = {
                    name: value
                    for name, value in REQUIRED_ENVIRONMENT.items()
                    if name != missing_name
                }
                environment["TEST_REPO_ROOT"] = "/tmp/repository"
                with (
                    mock.patch.dict(os.environ, environment, clear=True),
                    mock.patch.object(runner.os, "chdir"),
                    mock.patch.object(runner.subprocess, "run") as run,
                    mock.patch.object(runner.sys.stderr, "write") as write,
                    self.assertRaises(SystemExit) as exit_error,
                ):
                    runner.main()

                self.assertEqual(exit_error.exception.code, 2)
                run.assert_not_called()
                write.assert_called_once_with(
                    f"ERROR: required environment variable {missing_name} is not set\n"
                )

    def test_legal_tag_creation_is_idempotent(self):
        runner = load_runner()
        with mock.patch.object(
            runner,
            "_legal_request",
            side_effect=[(404, ""), (201, "{}")],
        ) as request:
            runner._ensure_legal_tag(
                "token",
                "https://example.test/api/legal/v1/",
                "opendes-wdms-ci",
                "opendes",
            )

        self.assertEqual(request.call_count, 2)
        self.assertEqual("GET", request.call_args_list[0].args[0])
        self.assertEqual("POST", request.call_args_list[1].args[0])
        self.assertEqual(
            "wdms-ci",
            request.call_args_list[1].kwargs["payload"]["name"],
        )

    def test_existing_legal_tag_is_not_recreated(self):
        runner = load_runner()
        with mock.patch.object(
            runner,
            "_legal_request",
            return_value=(200, "{}"),
        ) as request:
            runner._ensure_legal_tag(
                "token",
                "https://example.test/api/legal/v1",
                "opendes-wdms-ci",
                "opendes",
            )

        request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
