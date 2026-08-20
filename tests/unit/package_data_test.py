from pathlib import Path
import tomllib


ROOT = Path(__file__).parents[2]


def test_known_schemas_are_declared_as_package_data():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    patterns = config["tool"]["setuptools"]["package-data"]["app.schemas"]
    schemas = list((ROOT / "app" / "schemas" / "known_schemas").glob("*.json"))

    assert patterns == ["known_schemas/*.json"]
    assert schemas
