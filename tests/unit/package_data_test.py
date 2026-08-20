from pathlib import Path
import tomllib


ROOT = Path(__file__).parents[2]


def test_runtime_json_assets_are_declared_as_package_data():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_data = config["tool"]["setuptools"]["package-data"]
    examples = list((ROOT / "app" / "model_examples").glob("*.json"))
    schemas = list((ROOT / "app" / "schemas" / "known_schemas").glob("*.json"))

    assert package_data["app"] == ["model_examples/*.json"]
    assert package_data["app.schemas"] == ["known_schemas/*.json"]
    assert examples
    assert schemas
