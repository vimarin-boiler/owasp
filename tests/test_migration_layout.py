"""Regression tests for the Flask-Migrate directory layout."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_alembic_ini_is_inside_migrations_directory():
    config_path = PROJECT_ROOT / "migrations" / "alembic.ini"
    assert config_path.is_file()
    assert not (PROJECT_ROOT / "alembic.ini").exists()


def test_alembic_script_location_resolves_to_migrations_directory():
    config_path = PROJECT_ROOT / "migrations" / "alembic.ini"
    config = Config(str(config_path))
    script = ScriptDirectory.from_config(config)

    assert Path(script.dir).resolve() == (PROJECT_ROOT / "migrations").resolve()
    assert script.get_current_head() == "0004_scoring_recommendations"
