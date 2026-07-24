from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import User
from app.services.backup_service import BackupError, backup_service


def test_backup_contains_database_evidence_and_hashes(app, admin_user):
    upload_root = Path(app.config["UPLOAD_FOLDER"])
    evidence = upload_root / "assessment" / "question" / "evidence.txt"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text("evidencia", encoding="utf-8")

    archive = backup_service.create()
    assert archive.is_file()
    inspection = backup_service.inspect(archive)
    metadata = inspection["metadata"]
    assert metadata["evidence_file_count"] == 1
    assert metadata["database_sha256"]
    with zipfile.ZipFile(archive) as content:
        assert "database/samm_assessment.db" in content.namelist()
        assert "evidences/assessment/question/evidence.txt" in content.namelist()
        assert json.loads(content.read("manifest.json"))["algorithm"] == "SHA-256"


def test_restore_replaces_database_and_creates_safety_backup(app, admin_user):
    original_name = admin_user.display_name
    admin_email = admin_user.email_normalized
    archive = backup_service.create("baseline.zip")
    admin_user.display_name = "Nombre modificado"
    db.session.commit()

    result = backup_service.restore(archive)
    assert result["safety_backup"]
    db.session.remove()
    restored = db.session.scalar(select(User).where(User.email_normalized == admin_email))
    assert restored.display_name == original_name


def test_backup_inspection_rejects_path_traversal(app, tmp_path):
    malicious = tmp_path / "malicious.zip"
    with zipfile.ZipFile(malicious, "w") as archive:
        archive.writestr("../outside", "bad")
        archive.writestr("metadata.json", "{}")
        archive.writestr("manifest.json", "{}")
        archive.writestr("database/samm_assessment.db", "bad")
    with pytest.raises(BackupError):
        backup_service.inspect(malicious)


def test_backup_inspection_rejects_unmanifested_file(app, admin_user, tmp_path):
    source = backup_service.create("signed-baseline.zip")
    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(tampered, "w", zipfile.ZIP_DEFLATED) as output:
        for info in original.infolist():
            output.writestr(info, original.read(info.filename))
        output.writestr("evidences/injected.txt", "contenido no declarado")
    with pytest.raises(BackupError):
        backup_service.inspect(tampered)
