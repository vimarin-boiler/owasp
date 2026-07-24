from __future__ import annotations

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect


def _load_initial_migration():
    path = Path(__file__).parents[1] / "migrations" / "versions" / "0001_initial.py"
    spec = importlib.util.spec_from_file_location("initial_migration", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_initial_migration_up_and_down():
    migration = _load_initial_migration()
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        context = MigrationContext.configure(connection, opts={"render_as_batch": True})
        with Operations.context(context):
            migration.upgrade()
        assert len(inspect(connection).get_table_names()) == 29
        with Operations.context(context):
            migration.downgrade()
        assert inspect(connection).get_table_names() == []


def _load_catalog_migration():
    path = Path(__file__).parents[1] / "migrations" / "versions" / "0002_catalog_imports.py"
    spec = importlib.util.spec_from_file_location("catalog_migration", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_catalog_migration_up_and_down():
    initial = _load_initial_migration()
    catalog = _load_catalog_migration()
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        context = MigrationContext.configure(connection, opts={"render_as_batch": True})
        with Operations.context(context):
            initial.upgrade()
            catalog.upgrade()
        assert len(inspect(connection).get_table_names()) == 30
        assert "catalog_imports" in inspect(connection).get_table_names()
        with Operations.context(context):
            catalog.downgrade()
            initial.downgrade()
        assert inspect(connection).get_table_names() == []


def _load_workflow_migration():
    path = Path(__file__).parents[1] / "migrations" / "versions" / "0003_assessment_workflow.py"
    spec = importlib.util.spec_from_file_location("workflow_migration", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_workflow_migration_up_and_down():
    initial = _load_initial_migration()
    catalog = _load_catalog_migration()
    workflow = _load_workflow_migration()
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        context = MigrationContext.configure(connection, opts={"render_as_batch": True})
        with Operations.context(context):
            initial.upgrade()
            catalog.upgrade()
            workflow.upgrade()
        inspector = inspect(connection)
        assert len(inspector.get_table_names()) == 31
        assert "assessment_review_notes" in inspector.get_table_names()
        assert "review_comment" in {column["name"] for column in inspector.get_columns("evidences")}
        with Operations.context(context):
            workflow.downgrade()
            catalog.downgrade()
            initial.downgrade()
        assert inspect(connection).get_table_names() == []
