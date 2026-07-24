from __future__ import annotations

import hashlib
import os
import shutil
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from uuid import uuid4

from flask import current_app
from sqlalchemy import func, select
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.common.errors import ConflictError, ValidationError
from app.enums import EvidenceValidationStatus, ResponseStatus
from app.extensions import db
from app.models import AssessmentQuestion, Evidence
from app.models.base import utc_now
from app.services.audit_service import audit_service


BLOCKED_ARCHIVE_EXTENSIONS = {
    ".exe", ".dll", ".com", ".msi", ".scr", ".bat", ".cmd", ".ps1", ".psm1",
    ".sh", ".bash", ".js", ".vbs", ".jar", ".py", ".pl", ".php", ".asp", ".aspx",
}

MIME_BY_EXTENSION = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "txt": "text/plain",
    "csv": "text/csv",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "zip": "application/zip",
}


@dataclass(frozen=True)
class ScanResult:
    clean: bool
    details: str = ""


class AntivirusScanner:
    def scan(self, path: Path) -> ScanResult:  # pragma: no cover - contrato de integración
        raise NotImplementedError


class NullAntivirusScanner(AntivirusScanner):
    def scan(self, path: Path) -> ScanResult:
        return ScanResult(clean=True, details="Scanner antivirus no configurado")


class EvidenceService:
    def __init__(self, scanner: AntivirusScanner | None = None) -> None:
        self.scanner = scanner or NullAntivirusScanner()

    @staticmethod
    def _upload_root() -> Path:
        root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def resolve_storage_path(self, storage_key: str) -> Path:
        root = self._upload_root()
        path = (root / storage_key).resolve()
        if path == root or root not in path.parents:
            raise ValidationError("La ruta de evidencia almacenada no es válida.")
        return path

    @staticmethod
    def _validate_archive(path: Path, extension: str) -> str:
        try:
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                if len(names) > 5000:
                    raise ValidationError("El archivo comprimido contiene demasiados elementos.")
                total_uncompressed = 0
                for item in archive.infolist():
                    pure = PurePosixPath(item.filename)
                    if pure.is_absolute() or ".." in pure.parts:
                        raise ValidationError("El archivo comprimido contiene rutas inseguras.")
                    unix_mode = item.external_attr >> 16
                    if unix_mode and stat.S_ISLNK(unix_mode):
                        raise ValidationError("El archivo comprimido contiene enlaces simbólicos no permitidos.")
                    if item.file_size > 0 and item.compress_size == 0:
                        raise ValidationError("El archivo comprimido presenta una relación de compresión insegura.")
                    if item.compress_size and item.file_size / item.compress_size > 100:
                        raise ValidationError("El archivo comprimido presenta una relación de compresión insegura.")
                    total_uncompressed += item.file_size
                    if total_uncompressed > 500 * 1024 * 1024:
                        raise ValidationError("El contenido descomprimido excede el límite de seguridad.")
                    if Path(item.filename).suffix.casefold() in BLOCKED_ARCHIVE_EXTENSIONS:
                        raise ValidationError("El archivo comprimido contiene ejecutables o scripts no permitidos.")
                markers = set(names)
                if extension == "docx" and not any(name.startswith("word/") for name in markers):
                    raise ValidationError("El contenido no corresponde a un documento DOCX válido.")
                if extension == "xlsx" and not any(name.startswith("xl/") for name in markers):
                    raise ValidationError("El contenido no corresponde a un libro XLSX válido.")
                if extension == "pptx" and not any(name.startswith("ppt/") for name in markers):
                    raise ValidationError("El contenido no corresponde a una presentación PPTX válida.")
        except zipfile.BadZipFile as exc:
            raise ValidationError("El archivo comprimido u Office no es válido.") from exc
        return MIME_BY_EXTENSION[extension]

    @classmethod
    def _detect_type(cls, path: Path, extension: str) -> str:
        with path.open("rb") as stream:
            header = stream.read(8192)
        if header.startswith(b"MZ") or header.startswith(b"\x7fELF"):
            raise ValidationError("Se rechazó un archivo ejecutable.")
        if extension == "pdf":
            if not header.startswith(b"%PDF-"):
                raise ValidationError("El contenido no corresponde a un PDF válido.")
            return MIME_BY_EXTENSION[extension]
        if extension == "png":
            if not header.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValidationError("El contenido no corresponde a una imagen PNG válida.")
            return MIME_BY_EXTENSION[extension]
        if extension in {"jpg", "jpeg"}:
            if not header.startswith(b"\xff\xd8\xff"):
                raise ValidationError("El contenido no corresponde a una imagen JPEG válida.")
            return MIME_BY_EXTENSION[extension]
        if extension in {"docx", "xlsx", "pptx", "zip"}:
            if not header.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
                raise ValidationError("El contenido no corresponde a un archivo ZIP u Office válido.")
            return cls._validate_archive(path, extension)
        if extension in {"txt", "csv"}:
            if b"\x00" in header:
                raise ValidationError("El archivo de texto contiene datos binarios no permitidos.")
            try:
                header.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise ValidationError("Los archivos TXT y CSV deben usar codificación UTF-8.") from exc
            return MIME_BY_EXTENSION[extension]
        raise ValidationError("La extensión del archivo no está permitida.")

    def upload(
        self,
        question: AssessmentQuestion,
        file: FileStorage,
        *,
        description: str | None,
        actor_id: int,
    ) -> Evidence:
        active_count = int(
            db.session.scalar(
                select(func.count(Evidence.id)).where(
                    Evidence.assessment_question_id == question.id,
                    Evidence.is_active.is_(True),
                )
            )
            or 0
        )
        if active_count >= current_app.config["MAX_EVIDENCE_FILES_PER_QUESTION"]:
            raise ConflictError("Se alcanzó el máximo de evidencias permitido para esta pregunta.")

        original_name = secure_filename(file.filename or "")
        if not original_name or "." not in original_name:
            raise ValidationError("El archivo debe tener un nombre y una extensión válida.")
        extension = original_name.rsplit(".", 1)[1].casefold()
        if extension not in current_app.config["ALLOWED_EXTENSIONS"]:
            raise ValidationError(f"La extensión .{extension} no está permitida.")

        root = self._upload_root()
        quarantine = root / ".quarantine"
        quarantine.mkdir(parents=True, exist_ok=True)
        temporary = quarantine / f"{uuid4().hex}.upload"
        digest = hashlib.sha256()
        size = 0
        maximum = current_app.config["MAX_CONTENT_LENGTH_MB"] * 1024 * 1024
        try:
            file.stream.seek(0)
            with temporary.open("xb") as target:
                while True:
                    chunk = file.stream.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > maximum:
                        raise ValidationError(
                            f"El archivo supera el límite de {current_app.config['MAX_CONTENT_LENGTH_MB']} MB."
                        )
                    digest.update(chunk)
                    target.write(chunk)
            if size == 0:
                raise ValidationError("El archivo está vacío.")
            detected_mime = self._detect_type(temporary, extension)
            scan = self.scanner.scan(temporary)
            if not scan.clean:
                raise ValidationError("La evidencia fue rechazada por el análisis antivirus.")
            sha256 = digest.hexdigest()
            duplicate = db.session.scalar(
                select(Evidence).where(
                    Evidence.assessment_question_id == question.id,
                    Evidence.sha256 == sha256,
                    Evidence.is_active.is_(True),
                )
            )
            if duplicate:
                raise ConflictError("Esta misma evidencia ya fue adjuntada a la pregunta.")

            internal_name = f"{uuid4().hex}.{extension}"
            storage_key = f"{question.assessment.public_id}/{question.public_id}/{internal_name}"
            destination = self.resolve_storage_path(storage_key)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise ConflictError("No fue posible generar un nombre de archivo único.")
            os.replace(temporary, destination)
            response = question.response
            evidence = Evidence(
                assessment_question=question,
                assessment_response_id=response.id if response else None,
                response_version=response.response_version if response else None,
                original_filename=original_name,
                internal_filename=internal_name,
                storage_key=storage_key,
                reported_mime_type=(file.mimetype or "")[:160] or None,
                detected_mime_type=detected_mime,
                extension=extension,
                size_bytes=size,
                sha256=sha256,
                description=description.strip() if description else None,
                uploaded_by_id=actor_id,
                validation_status=EvidenceValidationStatus.PENDING,
            )
            db.session.add(evidence)
            db.session.flush()
            assessment = question.assessment
            audit_service.record(
                action="evidence.uploaded",
                entity_type="evidence",
                entity_public_id=evidence.public_id,
                actor_user_id=actor_id,
                organization_id=assessment.organization_id,
                assessment_id=assessment.id,
                after={
                    "filename": original_name,
                    "extension": extension,
                    "size_bytes": size,
                    "sha256": sha256,
                    "detected_mime_type": detected_mime,
                    "scanner": scan.details,
                },
            )
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                destination.unlink(missing_ok=True)
                raise
            return evidence
        finally:
            temporary.unlink(missing_ok=True)

    def delete(self, evidence: Evidence, *, actor_id: int) -> None:
        if not evidence.is_active:
            return
        question = evidence.assessment_question
        response = question.response
        if response and response.status in {ResponseStatus.SUBMITTED, ResponseStatus.APPROVED}:
            raise ConflictError("No se puede eliminar evidencia de una respuesta enviada o aprobada.")
        path = self.resolve_storage_path(evidence.storage_key)
        before = {
            "filename": evidence.original_filename,
            "sha256": evidence.sha256,
            "size_bytes": evidence.size_bytes,
        }
        evidence.deactivate()
        evidence.updated_at = utc_now()
        audit_service.record(
            action="evidence.deleted",
            entity_type="evidence",
            entity_public_id=evidence.public_id,
            actor_user_id=actor_id,
            organization_id=question.assessment.organization_id,
            assessment_id=question.assessment_id,
            before=before,
            after={"is_active": False},
        )
        db.session.commit()
        path.unlink(missing_ok=True)
        parent = path.parent
        if parent.exists() and not any(parent.iterdir()):
            shutil.rmtree(parent, ignore_errors=True)

    def record_download(self, evidence: Evidence, *, actor_id: int) -> Path:
        path = self.resolve_storage_path(evidence.storage_key)
        if not path.is_file():
            raise ValidationError("El archivo de evidencia no está disponible en el almacenamiento.")
        question = evidence.assessment_question
        audit_service.record(
            action="evidence.downloaded",
            entity_type="evidence",
            entity_public_id=evidence.public_id,
            actor_user_id=actor_id,
            organization_id=question.assessment.organization_id,
            assessment_id=question.assessment_id,
            after={"filename": evidence.original_filename, "sha256": evidence.sha256},
        )
        db.session.commit()
        return path


evidence_service = EvidenceService()
