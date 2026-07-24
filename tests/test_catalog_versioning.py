from pathlib import Path

from sqlalchemy import func, select

from app.extensions import db
from app.models import QuestionRevision
from app.repositories.catalog import catalog_repository
from app.services.catalog_service import catalog_service
from app.services.samm_import_service import catalog_import_service

SOURCE = Path(__file__).parents[1] / "data" / "SAMM_spreadsheet.xlsx"


def test_editing_question_creates_revision_without_overwrite(app, admin_user):
    record = catalog_import_service.create_preview_from_path(SOURCE, actor_id=admin_user.id)
    catalog_import_service.confirm(
        record,
        version_name="Draft",
        version_number="draft-versioning",
        description=None,
        publish=False,
        actor_id=admin_user.id,
    )
    question = catalog_repository.questions()[0]
    original = question.current_revision
    catalog_service.revise_question(
        question,
        canonical_name=question.canonical_name,
        business_function_id=original.business_function_id,
        security_practice_id=original.security_practice_id,
        practice_stream_id=original.practice_stream_id,
        maturity_level_id=original.maturity_level_id,
        answer_set_id=original.answer_set_id,
        question_text=original.question_text + " Updated",
        guidance_text=original.guidance_text,
        criteria=[criterion.criterion_text for criterion in original.criteria],
        change_reason="Ajuste controlado para prueba",
        is_active=True,
        actor_id=admin_user.id,
    )
    db.session.refresh(question)
    assert question.current_revision_number == 2
    revisions = list(db.session.scalars(select(QuestionRevision).where(QuestionRevision.question_id == question.id).order_by(QuestionRevision.revision_number)))
    assert len(revisions) == 2
    assert revisions[0].question_text == original.question_text
    assert revisions[1].question_text.endswith("Updated")
