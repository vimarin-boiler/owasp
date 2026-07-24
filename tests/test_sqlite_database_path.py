from pathlib import Path

from config import BASE_DIR, resolve_database_url


def test_documented_relative_sqlite_path_is_resolved_from_project_root():
    uri = resolve_database_url("sqlite:///instance/samm_assessment.db")
    expected = (BASE_DIR / "instance" / "samm_assessment.db").resolve().as_posix()
    assert uri == f"sqlite:///{expected}"


def test_simple_relative_sqlite_path_is_resolved_from_instance_directory():
    uri = resolve_database_url("sqlite:///samm_assessment.db")
    expected = (BASE_DIR / "instance" / "samm_assessment.db").resolve().as_posix()
    assert uri == f"sqlite:///{expected}"


def test_non_sqlite_url_is_not_modified():
    uri = "postgresql+psycopg://user:password@db/app"
    assert resolve_database_url(uri) == uri


def test_memory_database_is_not_modified():
    assert resolve_database_url("sqlite:///:memory:") == "sqlite:///:memory:"
