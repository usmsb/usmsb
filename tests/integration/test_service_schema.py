"""The service database must work on a fresh host without a prebuilt data dir."""

from usmsb_sdk.services.schema import create_db


def test_sqlite_service_schema_creates_missing_parent_directory(tmp_path):
    path = tmp_path / "new" / "nested" / "platform.db"
    engine = create_db(f"sqlite:///{path}")
    try:
        assert path.is_file()
    finally:
        engine.dispose()
