from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.enums import CatalogImportStatus, QuestionnaireStatus
from app.extensions import db
from app.models import (
    AnswerSet,
    BusinessFunction,
    PracticeStream,
    Question,
    QuestionnaireVersion,
    QuestionRevision,
    SecurityPractice,
)
from app.services.samm_import_service import catalog_import_service

SOURCE = Path(__file__).parents[1] / "data" / "SAMM_spreadsheet.xlsx"


def _count(model):
    return db.session.scalar(select(func.count(model.id)))


def test_import_creates_complete_catalog_transactionally(app, admin_user):
    record = catalog_import_service.create_preview_from_path(SOURCE, actor_id=admin_user.id)
    assert record.status == CatalogImportStatus.PREVIEWED
    version = catalog_import_service.confirm(
        record,
        version_name="OWASP SAMM 2.2.0",
        version_number="2.2.0-test",
        description="Prueba integral",
        publish=True,
        actor_id=admin_user.id,
    )
    assert version.status == QuestionnaireStatus.PUBLISHED
    assert len(version.question_links) == 90
    assert _count(BusinessFunction) == 5
    assert _count(SecurityPractice) == 15
    assert _count(PracticeStream) == 30
    assert _count(Question) == 90
    assert _count(QuestionRevision) == 90
    assert _count(AnswerSet) == 24
    assert record.status == CatalogImportStatus.IMPORTED


def test_reimport_reuses_unchanged_revisions_and_answer_sets(app, admin_user):
    first = catalog_import_service.create_preview_from_path(SOURCE, actor_id=admin_user.id)
    catalog_import_service.confirm(
        first,
        version_name="Baseline",
        version_number="baseline-1",
        description=None,
        publish=False,
        actor_id=admin_user.id,
    )
    second = catalog_import_service.create_preview_from_path(SOURCE, actor_id=admin_user.id)
    second_version = catalog_import_service.confirm(
        second,
        version_name="Baseline copy",
        version_number="baseline-2",
        description=None,
        publish=False,
        actor_id=admin_user.id,
    )
    assert len(second_version.question_links) == 90
    assert _count(QuestionRevision) == 90
    assert _count(AnswerSet) == 24
    assert _count(QuestionnaireVersion) == 2


def test_duplicate_version_rolls_back_catalog_changes(app, admin_user):
    first = catalog_import_service.create_preview_from_path(SOURCE, actor_id=admin_user.id)
    catalog_import_service.confirm(
        first,
        version_name="Baseline",
        version_number="same-version",
        description=None,
        publish=False,
        actor_id=admin_user.id,
    )
    second = catalog_import_service.create_preview_from_path(SOURCE, actor_id=admin_user.id)
    before_revisions = _count(QuestionRevision)
    with pytest.raises(ValueError, match="same-version"):
        catalog_import_service.confirm(
            second,
            version_name="Duplicate",
            version_number="same-version",
            description=None,
            publish=False,
            actor_id=admin_user.id,
        )
    assert _count(QuestionRevision) == before_revisions
