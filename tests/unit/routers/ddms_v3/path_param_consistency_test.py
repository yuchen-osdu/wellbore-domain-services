"""
Regression tests guarding the consistent ``record_id`` path parameter name
across every DDMS v3 entity resource.

Historically each resource declared its own record identifier path parameter
(``wellboretrajectoryid``, ``welllogid``, ``osdu_record_id``,
``welllogacquisitionid``, ...). This made the public API inconsistent and the
generated OpenAPI/clients awkward. The fix renamed all of them to a single
``record_id``. These tests fail if a resource-specific identifier name is ever
reintroduced.
"""

import re

import pytest

from app.wdms_app import wdms_app, DDMS_V3_PATH

# Path parameters that are legitimately not the record identifier.
NON_RECORD_PATH_PARAMS = {"version", "session_id"}

# The single canonical record identifier path parameter name.
CANONICAL_RECORD_ID_PARAM = "record_id"

# Legacy, resource-specific identifier names that must never come back.
FORBIDDEN_LEGACY_ID_PARAMS = {
    "osdu_record_id",
    "wellid",
    "wellboreid",
    "wellboretrajectoryid",
    "welllogid",
    "welllogacquisitionid",
    "markersetid",
    "wellboreintervalsetid",
}


def _ddms_v3_routes_with_params():
    """Yield (path, [param names]) for DDMS v3 routes that carry path parameters.

    Introspection is done through the generated OpenAPI schema rather than
    ``wdms_app.routes``. Recent FastAPI versions no longer flatten included
    routers into ``app.routes`` (they are wrapped in internal ``_IncludedRouter``
    objects with an empty ``path``), whereas the OpenAPI paths remain the stable,
    public representation of the routing table.
    """
    for path in wdms_app.openapi()["paths"]:
        if not path.startswith(DDMS_V3_PATH):
            continue
        params = re.findall(r"{([^}]+)}", path)
        if params:
            yield path, params


def test_there_are_ddms_v3_routes_with_record_id():
    """Sanity check: the introspection actually finds parameterised v3 routes."""
    record_id_routes = [
        path
        for path, params in _ddms_v3_routes_with_params()
        if CANONICAL_RECORD_ID_PARAM in params
    ]
    assert record_id_routes, "Expected DDMS v3 routes with a {record_id} path parameter"


def test_all_ddms_v3_record_path_params_are_record_id():
    """Every record identifier path parameter under DDMS v3 must be ``record_id``."""
    offending = {}
    for path, params in _ddms_v3_routes_with_params():
        non_canonical = [
            p
            for p in params
            if p != CANONICAL_RECORD_ID_PARAM and p not in NON_RECORD_PATH_PARAMS
        ]
        if non_canonical:
            offending[path] = non_canonical

    assert not offending, (
        "DDMS v3 routes must use the consistent '{record_id}' path parameter. "
        f"Found non-canonical path parameters: {offending}"
    )


def test_no_legacy_resource_specific_id_params():
    """None of the previously-used resource-specific id names may reappear."""
    found = {}
    for path, params in _ddms_v3_routes_with_params():
        legacy = [p for p in params if p in FORBIDDEN_LEGACY_ID_PARAMS]
        if legacy:
            found[path] = legacy

    assert not found, (
        "Legacy resource-specific record id path parameters were reintroduced: "
        f"{found}. Use '{{record_id}}' instead."
    )
