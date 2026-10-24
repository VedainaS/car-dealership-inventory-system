"""Each test must use its own on-disk SQLite file (no shared global pytest path)."""

from pathlib import Path

_seen_db_paths: set[str] = set()


def _sqlite_file_path(db_engine) -> str:
    database = db_engine.url.database
    assert database is not None
    return str(Path(database).resolve())


def test_database_path_isolated_first(db_engine):
    path = _sqlite_file_path(db_engine)
    assert path not in _seen_db_paths
    _seen_db_paths.add(path)


def test_database_path_isolated_second(db_engine):
    path = _sqlite_file_path(db_engine)
    assert path not in _seen_db_paths
    _seen_db_paths.add(path)
