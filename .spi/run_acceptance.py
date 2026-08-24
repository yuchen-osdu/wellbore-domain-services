#!/usr/bin/env python3
"""Run the SPI live WDMS acceptance subset against the deployed service."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import requests

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = REPOSITORY_ROOT / "tests" / "integration"
FUNCTIONAL_TESTS = (
    "functional/tests/test_about.py",
    "functional/tests/test_crud_v3.py",
    "functional/tests/test_bulk_statistics.py::test_get_bulk_statistic_basic_workflow",
)


def _required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable is not set: {name}")
    return value


def _access_token() -> str:
    return os.environ.get("ROOT_USER_TOKEN") or _required_environment(
        "INTEGRATION_TESTER_ACCESS_TOKEN"
    )


def _ensure_legal_tag(
    gateway_url: str,
    partition: str,
    token: str,
    *,
    session: Any = requests,
) -> str:
    legal_tag = os.environ.get("LEGAL_TAG", f"{partition}-wdms-ci")
    legal_api = f"{gateway_url.rstrip('/')}/api/legal/v1/legaltags"
    headers = {
        "Authorization": f"Bearer {token}",
        "data-partition-id": partition,
        "accept": "application/json",
    }

    response = session.get(f"{legal_api}/{legal_tag}", headers=headers, timeout=30)
    if response.status_code == 200:
        return legal_tag
    if response.status_code != 404:
        raise RuntimeError(
            f"LegalTag lookup failed with HTTP {response.status_code}: {response.text[:500]}"
        )

    prefix = f"{partition}-"
    short_name = legal_tag.removeprefix(prefix)
    payload = {
        "name": short_name,
        "description": "Legal tag for SPI Wellbore live acceptance tests",
        "properties": {
            "countryOfOrigin": ["US"],
            "contractId": "SPI-WDMS-CI",
            "expirationDate": "2099-12-31",
            "dataType": "Public Domain Data",
            "originator": "OSDU",
            "securityClassification": "Public",
            "exportClassification": "EAR99",
            "personalData": "No Personal Data",
        },
    }
    response = session.post(
        legal_api,
        headers={**headers, "content-type": "application/json"},
        json=payload,
        timeout=30,
    )
    if response.status_code not in {200, 201, 409}:
        raise RuntimeError(
            f"LegalTag creation failed with HTTP {response.status_code}: {response.text[:500]}"
        )
    return legal_tag


def _postman_environment(
    *,
    token: str,
    base_url: str,
    partition: str,
    acl_domain: str,
    legal_tag: str,
) -> dict[str, Any]:
    schemas = json.loads(
        (
            REPOSITORY_ROOT
            / "tests"
            / "dependencies"
            / "default_schemas_versions_list.json"
        ).read_text(encoding="utf-8")
    )
    values = {
        "token": token,
        "base_url": base_url,
        "data_partition": partition,
        "cloud_provider": os.environ.get("CLOUD_PROVIDER", "az"),
        "acl_domain": acl_domain,
        "legal_tag": legal_tag,
        "authorityKind": os.environ.get("AUTHORITY_KIND", "osdu"),
        "schemas_versions_list_json": json.dumps(schemas),
    }
    return {
        "name": "spi_wellbore_acceptance",
        "values": [
            {"enabled": True, "key": key, "value": value, "type": "text"}
            for key, value in values.items()
        ],
    }


def _pytest_command(environment_file: Path, junit_xml: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "pytest",
        *FUNCTIONAL_TESTS,
        f"--environment={environment_file}",
        "--timeout-request=15000",
        "--retry-on-error=500|502|503|504",
        "-p",
        "no:randomly",
        f"--junitxml={junit_xml}",
    ]


def run(junit_xml: Path) -> int:
    gateway_url = _required_environment("GATEWAY_URL").rstrip("/")
    partition = _required_environment("DATA_PARTITION")
    acl_domain = _required_environment("ACL_DOMAIN")
    token = _access_token()
    legal_tag = _ensure_legal_tag(gateway_url, partition, token)
    base_url = os.environ.get(
        "WELLBORE_BASE_URL",
        f"{gateway_url}/api/os-wellbore-ddms",
    ).rstrip("/")

    junit_xml.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="spi-wdms-acceptance-") as directory:
        environment_file = Path(directory) / "postman_environment.json"
        environment_file.write_text(
            json.dumps(
                _postman_environment(
                    token=token,
                    base_url=base_url,
                    partition=partition,
                    acl_domain=acl_domain,
                    legal_tag=legal_tag,
                )
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            _pytest_command(environment_file, junit_xml),
            cwd=INTEGRATION_DIR,
            check=False,
        )
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit-xml", required=True, type=Path)
    args = parser.parse_args()
    try:
        return run(args.junit_xml.resolve())
    except (OSError, RuntimeError, ValueError, requests.RequestException) as error:
        print(f"SPI WDMS acceptance runner failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
