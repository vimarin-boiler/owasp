from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import current_app
from sqlalchemy import func, select
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.common.errors import DomainError
from app.enums import CatalogImportStatus, QuestionRevisionStatus, QuestionnaireStatus
from app.extensions import db
from app.models import (
    AnswerOption, AnswerSet, BusinessFunction, CatalogImport, MaturityLevel,
    PracticeStream, Question, QuestionnaireVersion, QuestionnaireVersionQuestion,
    QuestionQualityCriterion, QuestionRevision, SecurityPractice,
)
from app.models.base import utc_now
from app.services.audit_service import audit_service
from app.services.samm_workbook_parser import SammWorkbookParser, samm_workbook_parser

class CatalogImportService:
    def __init__(self, parser: SammWorkbookParser | None = None) -> None:
        self.parser = parser or SammWorkbookParser()

    def create_preview_from_upload(self, upload: FileStorage, actor_id: int) -> CatalogImport:
        filename = secure_filename(upload.filename or "")
        if not filename or Path(filename).suffix.lower() != ".xlsx":
            raise ValueError("Debes seleccionar un archivo Excel con extensión .xlsx.")
        folder = Path(current_app.config["CATALOG_IMPORT_FOLDER"])
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / f"{uuid4().hex}.xlsx"
        upload.save(destination)
        if destination.stat().st_size > current_app.config["MAX_CATALOG_IMPORT_MB"] * 1024 * 1024:
            destination.unlink(missing_ok=True)
            raise ValueError("El archivo excede el tamaño máximo permitido para importaciones.")
        try:
            return self.create_preview_from_path(
                destination, actor_id=actor_id, source_name=filename, temporary=True
            )
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    def create_preview_from_path(
        self,
        file_path: str | Path,
        *,
        actor_id: int | None,
        source_name: str | None = None,
        temporary: bool = False,
    ) -> CatalogImport:
        path = Path(file_path)
        if not path.is_file():
            raise ValueError(f"El archivo no existe: {path}")
        preview = self.parser.parse(path)
        if source_name:
            preview.source_name = source_name
        status = CatalogImportStatus.INVALID if preview.errors else CatalogImportStatus.PREVIEWED
        record = CatalogImport(
            source_name=preview.source_name,
            source_file_hash=preview.source_file_hash,
            source_version=preview.source_version,
            status=status,
            summary_json=preview.summary,
            errors_json=[issue.as_dict() for issue in preview.issues],
            preview_json=preview.as_dict(),
            temporary_file_path=str(path.resolve()) if temporary else None,
            created_by_id=actor_id,
        )
        db.session.add(record)
        db.session.flush()
        audit_service.record(
            action="catalog.import.preview",
            entity_type="CatalogImport",
            entity_public_id=record.public_id,
            actor_user_id=actor_id,
            after={"source_name": record.source_name, "status": status, "summary": record.summary_json},
            result="validation_failed" if preview.errors else "success",
        )
        db.session.commit()
        return record

    def confirm(
        self,
        import_record: CatalogImport,
        *,
        version_name: str,
        version_number: str,
        description: str | None,
        publish: bool,
        actor_id: int | None,
    ) -> QuestionnaireVersion:
        if import_record.status != CatalogImportStatus.PREVIEWED:
            raise ValueError("La importación no está disponible para confirmación.")
        if import_record.errors_json and any(item.get("severity") == "error" for item in import_record.errors_json):
            raise ValueError("La importación contiene errores de validación.")
        if db.session.scalar(select(QuestionnaireVersion).where(QuestionnaireVersion.version_number == version_number.strip())):
            raise ValueError("Ya existe una versión con ese número.")

        import_id = import_record.id
        try:
            version = self._apply_preview(
                import_record.preview_json,
                version_name=version_name.strip(),
                version_number=version_number.strip(),
                description=(description or "").strip() or None,
                publish=publish,
                actor_id=actor_id,
            )
            import_record.requested_version_name = version.name
            import_record.requested_version_number = version.version_number
            import_record.questionnaire_version_id = version.id
            import_record.status = CatalogImportStatus.IMPORTED
            import_record.confirmed_at = utc_now()
            audit_service.record(
                action="catalog.import.confirm",
                entity_type="CatalogImport",
                entity_public_id=import_record.public_id,
                actor_user_id=actor_id,
                after={"version": version.version_number, "publish": publish, "summary": import_record.summary_json},
            )
            db.session.commit()
            self._remove_temporary_file(import_record)
            return version
        except Exception as exc:
            db.session.rollback()
            current_app.logger.exception("Catalog import confirmation failed", exc_info=exc)
            safe_message = (
                str(exc)
                if isinstance(exc, (DomainError, ValueError))
                else "Error interno durante la importación. Consulta la bitácora de la aplicación."
            )
            failed = db.session.get(CatalogImport, import_id)
            if failed is not None:
                failed.status = CatalogImportStatus.FAILED
                failed.errors_json = [*failed.errors_json, {"sheet": "database", "row": None, "field": None, "message": safe_message, "severity": "error"}]
                audit_service.record(
                    action="catalog.import.confirm",
                    entity_type="CatalogImport",
                    entity_public_id=failed.public_id,
                    actor_user_id=actor_id,
                    result="failure",
                    error_code=type(exc).__name__,
                )
                db.session.commit()
            raise

    def _apply_preview(
        self,
        preview: dict[str, Any],
        *,
        version_name: str,
        version_number: str,
        description: str | None,
        publish: bool,
        actor_id: int | None,
    ) -> QuestionnaireVersion:
        status = QuestionnaireStatus.PUBLISHED if publish else QuestionnaireStatus.DRAFT
        version = QuestionnaireVersion(
            name=version_name,
            version_number=version_number,
            description=description,
            status=status,
            source_name=preview["source_name"],
            source_file_hash=preview["source_file_hash"],
            published_at=utc_now() if publish else None,
            published_by_id=actor_id if publish else None,
            created_by_id=actor_id,
            updated_by_id=actor_id,
        )
        db.session.add(version)
        db.session.flush()

        answer_sets = self._upsert_answer_sets(preview["answer_sets"], actor_id)
        functions: dict[str, BusinessFunction] = {}
        practices: dict[str, SecurityPractice] = {}
        streams: dict[str, PracticeStream] = {}
        levels: dict[int, MaturityLevel] = {}

        for item in preview["questions"]:
            function = functions.get(item["business_function_code"])
            if function is None:
                function = db.session.scalar(select(BusinessFunction).where(BusinessFunction.code == item["business_function_code"]))
                if function is None:
                    function = BusinessFunction(
                        code=item["business_function_code"],
                        name=item["business_function_name"],
                        sort_order=item["business_function_sort_order"],
                        created_by_id=actor_id,
                        updated_by_id=actor_id,
                    )
                    db.session.add(function)
                    db.session.flush()
                else:
                    function.name = item["business_function_name"]
                    function.sort_order = item["business_function_sort_order"]
                    function.is_active = True
                    function.updated_by_id = actor_id
                functions[item["business_function_code"]] = function

            practice = practices.get(item["security_practice_code"])
            if practice is None:
                practice = db.session.scalar(
                    select(SecurityPractice).where(
                        SecurityPractice.business_function_id == function.id,
                        SecurityPractice.code == item["security_practice_code"],
                    )
                )
                if practice is None:
                    practice = SecurityPractice(
                        business_function_id=function.id,
                        code=item["security_practice_code"],
                        name=item["security_practice_name"],
                        sort_order=item["security_practice_sort_order"],
                        created_by_id=actor_id,
                        updated_by_id=actor_id,
                    )
                    db.session.add(practice)
                    db.session.flush()
                else:
                    practice.name = item["security_practice_name"]
                    practice.sort_order = item["security_practice_sort_order"]
                    practice.is_active = True
                    practice.updated_by_id = actor_id
                practices[item["security_practice_code"]] = practice

            stream = streams.get(item["practice_stream_code"])
            if stream is None:
                stream = db.session.scalar(
                    select(PracticeStream).where(
                        PracticeStream.security_practice_id == practice.id,
                        PracticeStream.code == item["practice_stream_code"],
                    )
                )
                if stream is None:
                    stream = PracticeStream(
                        security_practice_id=practice.id,
                        code=item["practice_stream_code"],
                        name=item["practice_stream_name"],
                        sort_order=item["practice_stream_sort_order"],
                        created_by_id=actor_id,
                        updated_by_id=actor_id,
                    )
                    db.session.add(stream)
                    db.session.flush()
                else:
                    stream.name = item["practice_stream_name"]
                    stream.sort_order = item["practice_stream_sort_order"]
                    stream.is_active = True
                    stream.updated_by_id = actor_id
                streams[item["practice_stream_code"]] = stream

            level = levels.get(item["maturity_level"])
            if level is None:
                level = db.session.scalar(select(MaturityLevel).where(MaturityLevel.level_number == item["maturity_level"]))
                if level is None:
                    level = MaturityLevel(
                        level_number=item["maturity_level"],
                        name=item["maturity_name"],
                        max_score=Decimal("1"),
                        sort_order=item["maturity_level"],
                        created_by_id=actor_id,
                        updated_by_id=actor_id,
                    )
                    db.session.add(level)
                    db.session.flush()
                levels[item["maturity_level"]] = level

            question = db.session.scalar(select(Question).where(Question.external_code == item["external_code"]))
            current_revision = None
            if question is None:
                question = Question(
                    external_code=item["external_code"],
                    canonical_name=item["canonical_name"],
                    created_by_id=actor_id,
                    updated_by_id=actor_id,
                )
                db.session.add(question)
                db.session.flush()
            else:
                question.canonical_name = item["canonical_name"]
                question.is_active = True
                question.updated_by_id = actor_id
                if question.current_revision_number is not None:
                    current_revision = db.session.scalar(
                        select(QuestionRevision).where(
                            QuestionRevision.question_id == question.id,
                            QuestionRevision.revision_number == question.current_revision_number,
                        )
                    )

            if current_revision is not None and current_revision.content_hash == item["content_hash"]:
                revision = current_revision
                if publish and revision.status == QuestionRevisionStatus.DRAFT:
                    revision.status = QuestionRevisionStatus.PUBLISHED
            else:
                next_revision = (db.session.scalar(select(func.max(QuestionRevision.revision_number)).where(QuestionRevision.question_id == question.id)) or 0) + 1
                revision = QuestionRevision(
                    question_id=question.id,
                    revision_number=next_revision,
                    business_function_id=function.id,
                    security_practice_id=practice.id,
                    practice_stream_id=stream.id,
                    maturity_level_id=level.id,
                    answer_set_id=answer_sets[item["answer_set_external_code"]].id,
                    question_text=item["question_text"],
                    guidance_text=item["guidance_text"],
                    content_hash=item["content_hash"],
                    supersedes_revision_id=current_revision.id if current_revision else None,
                    change_reason="Importación desde Excel" if current_revision else "Creación inicial desde Excel",
                    status=QuestionRevisionStatus.PUBLISHED if publish else QuestionRevisionStatus.DRAFT,
                    created_by_id=actor_id,
                    updated_by_id=actor_id,
                )
                db.session.add(revision)
                db.session.flush()
                for index, criterion in enumerate(item["criteria"], start=1):
                    db.session.add(
                        QuestionQualityCriterion(
                            question_revision_id=revision.id,
                            criterion_text=criterion,
                            sort_order=index,
                            created_by_id=actor_id,
                            updated_by_id=actor_id,
                        )
                    )
                question.current_revision_number = next_revision

            db.session.add(
                QuestionnaireVersionQuestion(
                    questionnaire_version_id=version.id,
                    question_revision_id=revision.id,
                    sort_order=item["sort_order"],
                    is_required=True,
                )
            )

        if publish:
            previous_versions = db.session.scalars(
                select(QuestionnaireVersion).where(
                    QuestionnaireVersion.id != version.id,
                    QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED,
                )
            )
            for previous in previous_versions:
                previous.status = QuestionnaireStatus.ARCHIVED
                previous.updated_by_id = actor_id
        db.session.flush()
        return version

    def _upsert_answer_sets(self, items: list[dict[str, Any]], actor_id: int | None) -> dict[str, AnswerSet]:
        result: dict[str, AnswerSet] = {}
        for item in items:
            answer_set = db.session.scalar(select(AnswerSet).where(AnswerSet.content_hash == item["content_hash"]))
            if answer_set is None:
                external_code = f"SAMM-{item['external_code']}-{item['content_hash'][:10]}"
                answer_set = AnswerSet(
                    external_code=external_code,
                    name=item["name"],
                    description=item["description"],
                    content_hash=item["content_hash"],
                    created_by_id=actor_id,
                    updated_by_id=actor_id,
                )
                db.session.add(answer_set)
                db.session.flush()
                for option in item["options"]:
                    db.session.add(
                        AnswerOption(
                            answer_set_id=answer_set.id,
                            option_code=option["option_code"],
                            text=option["text"],
                            weight=Decimal(option["weight"]),
                            sort_order=option["sort_order"],
                            created_by_id=actor_id,
                            updated_by_id=actor_id,
                        )
                    )
            result[item["external_code"]] = answer_set
        return result

    @staticmethod
    def _remove_temporary_file(record: CatalogImport) -> None:
        if not record.temporary_file_path:
            return
        try:
            Path(record.temporary_file_path).unlink(missing_ok=True)
        except OSError:
            return
        record.temporary_file_path = None
        db.session.commit()



catalog_import_service = CatalogImportService(samm_workbook_parser)
