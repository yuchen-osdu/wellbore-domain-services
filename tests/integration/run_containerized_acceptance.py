#!/usr/bin/env python3
"""Delegated runner for the Wellbore DDMS acceptance suite.

This is the ADME containerized runner contract adapted to work from either a
checked-out repository or `/app/testing`. SPI supplies `TEST_REPO_ROOT`,
`TEST_RESULTS_DIR`, and the WDMS runtime environment.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.stderr.write(f"ERROR: required environment variable {name} is not set\n")
        raise SystemExit(2)
    return value


def main() -> None:
    repo_root = Path(os.environ.get("TEST_REPO_ROOT", DEFAULT_REPO_ROOT)).resolve()
    os.chdir(repo_root)

    token = _require("INTEGRATION_TESTER_ACCESS_TOKEN")
    base_url = _require("WDMS_BASE_URL")
    acl_domain = _require("WDMS_ACL_DOMAIN")
    legal_tag = _require("WDMS_LEGAL_TAG")
    data_partition = _require("WDMS_DATA_PARTITION")

    results_dir = Path(
        os.environ.get("TEST_RESULTS_DIR", repo_root / "test-reports")
    ).resolve()
    results_dir.mkdir(parents=True, exist_ok=True)

    python = sys.executable
    subprocess.run(
        [
            python,
            "tests/integration/gen_postman_env.py",
            f"--token={token}",
            f"--base_url={base_url}",
            "--cloud_provider",
            "az",
            f"--acl_domain={acl_domain}",
            f"--legal_tag={legal_tag}",
            f"--data_partition={data_partition}",
        ],
        check=True,
    )

    completed = subprocess.run(
        [
            python,
            "-m",
            "pytest",
            "tests/integration/functional",
            "--environment=./generated/postman_environment.json",
            f"--junit-xml={results_dir / 'int_tests_report.xml'}",
            "-o",
            "junit_suite_name=wdms_integration",
            "--insecure",
            "--timeout-request=60000",
            "--filter-tag=!search",
            "-p",
            "no:randomly",
        ],
        check=False,
    )
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
