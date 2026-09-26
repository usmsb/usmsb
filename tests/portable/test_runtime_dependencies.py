"""Validate eager-import requirements without importing the full SDK."""

import tomllib
from pathlib import Path

from packaging.requirements import Requirement


def test_async_storage_runtime_declares_sqlalchemy_asyncio_extra():
    config = tomllib.loads(
        (Path(__file__).parents[2] / "pyproject.toml").read_text(encoding="utf-8")
    )
    requirements = [Requirement(value) for value in config["project"]["dependencies"]]
    sqlalchemy = next(item for item in requirements if item.name.lower() == "sqlalchemy")
    assert "asyncio" in sqlalchemy.extras, "Eager async storage imports require greenlet at runtime"
