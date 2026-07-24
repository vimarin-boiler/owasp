"""Regression tests for Alembic/Flask-Migrate configure arguments."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_online_context_configure_does_not_duplicate_migrate_arguments():
    source = (PROJECT_ROOT / "migrations" / "env.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    online_function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_migrations_online"
    )
    configure_call = next(
        node
        for node in ast.walk(online_function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "configure"
    )

    explicit_keywords = {keyword.arg for keyword in configure_call.keywords if keyword.arg}
    assert "compare_type" not in explicit_keywords
    assert "render_as_batch" not in explicit_keywords
    assert any(keyword.arg is None for keyword in configure_call.keywords)
