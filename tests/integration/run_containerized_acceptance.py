#!/usr/bin/env python3
"""Delegated runner for the Wellbore DDMS acceptance suite.

This is the ADME containerized runner contract adapted to work from either a
checked-out repository or `/app/testing`. SPI supplies `TEST_REPO_ROOT`,
`TEST_RESULTS_DIR`, and the WDMS runtime environment.
"""

from __future__ import annotations

import os
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.stderr.write(f"ERROR: required environment variable {name} is not set\n")
        raise SystemExit(2)
    return value


def _legal_request(
    method: str,
    url: str,
    *,
    token: str,
    partition: str,
    payload: dict[str, object] | None = None,
) -> tuple[int, str]:
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "data-partition-id": partition,
            "accept": "application/json",
            "content-type": "application/json",
        },
    )
    try:
        response = urllib.request.urlopen(request, timeout=60)
        return response.getcode(), response.read().decode(errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode(errors="replace")


def _ensure_legal_tag(token: str, legal_url: str, legal_tag: str, partition: str) -> None:
    base = legal_url.rstrip("/")
    encoded_tag = urllib.parse.quote(legal_tag, safe="")
    status, _ = _legal_request(
        "GET",
        f"{base}/legaltags/{encoded_tag}",
        token=token,
        partition=partition,
    )
    if status == 200:
        print(f"LegalTag {legal_tag} already exists")
        return

    prefix = f"{partition}-"
    short_name = legal_tag[len(prefix) :] if legal_tag.startswith(prefix) else legal_tag
    payload = {
        "name": short_name,
        "description": "Legal tag for Wellbore DDMS integration tests",
        "properties": {
            "countryOfOrigin": ["US"],
            "contractId": "A1234",
            "expirationDate": "2099-12-31",
            "dataType": "Public Domain Data",
            "originator": "OSDU",
            "securityClassification": "Public",
            "exportClassification": "EAR99",
            "personalData": "No Personal Data",
        },
    }
    status, response = _legal_request(
        "POST",
        f"{base}/legaltags",
        token=token,
        partition=partition,
        payload=payload,
    )
    if status not in {200, 201, 409}:
        raise RuntimeError(
            f"Unable to create LegalTag {legal_tag}: HTTP {status} {response[:200]}"
        )
    print(f"LegalTag {legal_tag} created or already present")


def main() -> None:
    repo_root = Path(os.environ.get("TEST_REPO_ROOT", DEFAULT_REPO_ROOT)).resolve()
    os.chdir(repo_root)

    token = _require("INTEGRATION_TESTER_ACCESS_TOKEN")
    base_url = _require("WDMS_BASE_URL")
    legal_url = _require("WDMS_LEGAL_URL")
    acl_domain = _require("WDMS_ACL_DOMAIN")
    legal_tag = _require("WDMS_LEGAL_TAG")
    data_partition = _require("WDMS_DATA_PARTITION")

    results_dir = Path(
        os.environ.get("TEST_RESULTS_DIR", repo_root / "test-reports")
    ).resolve()
    results_dir.mkdir(parents=True, exist_ok=True)

    _ensure_legal_tag(token, legal_url, legal_tag, data_partition)

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
