from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from flask import current_app

from app.extensions import db
from app.version import __version__


BACKUP_FORMAT_VERSION = "1.0"
MAX_ARCHIVE_ENTRIES = 100000
MAX_UNCOMPRESSED_BYTES = 20 * 1024 * 1024 * 1024


class BackupError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_member(info: zipfile.ZipInfo) -> bool:
    pure = PurePosixPath(info.filename)
    if pure.is_absolute() or ".." in pure.parts:
        return False
    unix_mode = info.external_attr >> 16
    return not (unix_mode and stat.S_ISLNK(unix_mode))


class BackupService:
    def _database_path(self) -> Path:
        url = db.engine.url
        if url.get_backend_name() != "sqlite":
            raise BackupError("Los comandos integrados de backup/restore están disponibles únicamente para SQLite.")
        database = url.database
        if not database or database == ":memory:":
            raise BackupError("No es posible respaldar una base SQLite en memoria.")
        path = Path(database)
        if not path.is_absolute():
            path = (Path(current_app.root_path).parent / path).resolve()
        if not path.exists():
            raise BackupError(f"No se encontró la base de datos SQLite: {path}")
        return path

    @staticmethod
    def _upload_root() -> Path:
        return Path(current_app.config["UPLOAD_FOLDER"]).resolve()

    @staticmethod
    def _backup_root() -> Path:
        root = Path(current_app.config.get("BACKUP_FOLDER", "backups"))
        if not root.is_absolute():
            root = Path(current_app.root_path).parent / root
        root = root.resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def create(self, output_file: str | Path | None = None) -> Path:
        source_db = self._database_path()
        upload_root = self._upload_root()
        now = datetime.now(timezone.utc)
        if output_file:
            target = Path(output_file)
            if not target.is_absolute():
                target = self._backup_root() / target
            target = target.resolve()
        else:
            target = self._backup_root() / f"samm-backup-{now.strftime('%Y%m%dT%H%M%S%fZ')}.zip"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise BackupError(f"El archivo de respaldo ya existe: {target}")

        with tempfile.TemporaryDirectory(prefix="samm-backup-") as temp_dir:
            stage = Path(temp_dir) / "backup"
            db_dir = stage / "database"
            evidence_dir = stage / "evidences"
            db_dir.mkdir(parents=True)
            evidence_dir.mkdir(parents=True)
            backup_db = db_dir / "samm_assessment.db"

            with sqlite3.connect(source_db) as source, sqlite3.connect(backup_db) as destination:
                source.execute("PRAGMA busy_timeout=30000")
                source.backup(destination)
                integrity = destination.execute("PRAGMA integrity_check").fetchone()
                if not integrity or integrity[0] != "ok":
                    raise BackupError("La copia SQLite no superó la validación de integridad.")

            evidence_count = 0
            evidence_bytes = 0
            if upload_root.exists():
                for source in sorted(upload_root.rglob("*")):
                    if not source.is_file() or source.is_symlink():
                        continue
                    relative = source.relative_to(upload_root)
                    if ".quarantine" in relative.parts or "quarantine" in relative.parts:
                        continue
                    destination = evidence_dir / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
                    evidence_count += 1
                    evidence_bytes += source.stat().st_size

            files = {}
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    relative = path.relative_to(stage).as_posix()
                    files[relative] = {"sha256": _sha256(path), "size_bytes": path.stat().st_size}

            metadata = {
                "backup_format_version": BACKUP_FORMAT_VERSION,
                "application_version": __version__,
                "created_at": now.isoformat(),
                "database": "database/samm_assessment.db",
                "database_sha256": files["database/samm_assessment.db"]["sha256"],
                "evidence_file_count": evidence_count,
                "evidence_total_bytes": evidence_bytes,
                "source_database_name": source_db.name,
            }
            (stage / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            files["metadata.json"] = {"sha256": _sha256(stage / "metadata.json"), "size_bytes": (stage / "metadata.json").stat().st_size}
            manifest = {"algorithm": "SHA-256", "files": files}
            (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            temporary_zip = target.with_suffix(target.suffix + ".tmp")
            temporary_zip.unlink(missing_ok=True)
            with zipfile.ZipFile(temporary_zip, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for path in sorted(stage.rglob("*")):
                    if path.is_file():
                        archive.write(path, arcname=path.relative_to(stage).as_posix())
            os.replace(temporary_zip, target)
        return target

    def inspect(self, archive_file: str | Path) -> dict:
        archive_path = Path(archive_file).resolve()
        if not archive_path.is_file():
            raise BackupError(f"No se encontró el archivo de respaldo: {archive_path}")
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_ENTRIES:
                raise BackupError("El respaldo contiene demasiados elementos.")
            total = 0
            for info in infos:
                if not _safe_member(info):
                    raise BackupError(f"El respaldo contiene una ruta insegura: {info.filename}")
                total += info.file_size
                if total > MAX_UNCOMPRESSED_BYTES:
                    raise BackupError("El tamaño descomprimido del respaldo excede el límite permitido.")
                if info.compress_size and info.file_size / info.compress_size > 200:
                    raise BackupError(f"Relación de compresión anómala en {info.filename}.")
            names = {info.filename for info in infos}
            required = {"metadata.json", "manifest.json", "database/samm_assessment.db"}
            if not required.issubset(names):
                raise BackupError("El archivo no contiene todos los componentes obligatorios del respaldo.")
            metadata = json.loads(archive.read("metadata.json").decode("utf-8"))
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            if metadata.get("backup_format_version") != BACKUP_FORMAT_VERSION:
                raise BackupError("La versión del formato de respaldo no es compatible.")
            declared_files = manifest.get("files")
            if not isinstance(declared_files, dict) or not declared_files:
                raise BackupError("El manifiesto del respaldo no contiene archivos declarados.")
            archive_files = {name for name in names if not name.endswith("/") and name != "manifest.json"}
            undeclared = archive_files.difference(declared_files)
            if undeclared:
                raise BackupError(
                    "El respaldo contiene archivos no declarados en el manifiesto: "
                    + ", ".join(sorted(undeclared)[:5])
                )
            for name, expected in declared_files.items():
                if name not in names:
                    raise BackupError(f"Falta el archivo declarado en el manifiesto: {name}")
                if not isinstance(expected, dict):
                    raise BackupError(f"Entrada inválida en el manifiesto para {name}.")
                content = archive.read(name)
                digest = hashlib.sha256(content).hexdigest()
                if digest != expected.get("sha256") or len(content) != expected.get("size_bytes"):
                    raise BackupError(f"Falló la validación de integridad para {name}.")
            database_entry = declared_files.get("database/samm_assessment.db", {})
            if metadata.get("database_sha256") != database_entry.get("sha256"):
                raise BackupError("El hash de la base de datos no coincide entre metadatos y manifiesto.")
            return {"path": str(archive_path), "metadata": metadata, "manifest": manifest}

    def restore(self, archive_file: str | Path, *, create_safety_backup: bool = True) -> dict:
        inspection = self.inspect(archive_file)
        archive_path = Path(inspection["path"])
        destination_db = self._database_path()
        upload_root = self._upload_root()
        safety_backup = None
        if create_safety_backup:
            safety_backup = self.create()

        with tempfile.TemporaryDirectory(prefix="samm-restore-") as temp_dir:
            extracted = Path(temp_dir) / "extracted"
            extracted.mkdir()
            with zipfile.ZipFile(archive_path) as archive:
                for info in archive.infolist():
                    if not _safe_member(info):
                        raise BackupError(f"Ruta insegura durante restauración: {info.filename}")
                    archive.extract(info, extracted)

            candidate_db = extracted / "database" / "samm_assessment.db"
            with sqlite3.connect(candidate_db) as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()
                if not integrity or integrity[0] != "ok":
                    raise BackupError("La base de datos del respaldo no superó PRAGMA integrity_check.")

            restored_uploads = extracted / "evidences"
            staged_db = destination_db.with_suffix(destination_db.suffix + ".restore")
            staged_uploads = upload_root.with_name(upload_root.name + ".restore")
            staged_db.unlink(missing_ok=True)
            if staged_uploads.exists():
                shutil.rmtree(staged_uploads)
            shutil.copy2(candidate_db, staged_db)
            if restored_uploads.exists():
                shutil.copytree(restored_uploads, staged_uploads)
            else:
                staged_uploads.mkdir(parents=True)

            db.engine.dispose()
            destination_db.parent.mkdir(parents=True, exist_ok=True)
            for suffix in ("-wal", "-shm"):
                Path(str(destination_db) + suffix).unlink(missing_ok=True)
            os.replace(staged_db, destination_db)
            previous_uploads = upload_root.with_name(upload_root.name + ".previous")
            if previous_uploads.exists():
                shutil.rmtree(previous_uploads)
            if upload_root.exists():
                os.replace(upload_root, previous_uploads)
            os.replace(staged_uploads, upload_root)
            if previous_uploads.exists():
                shutil.rmtree(previous_uploads)

        return {
            "restored_from": str(archive_path),
            "metadata": inspection["metadata"],
            "safety_backup": str(safety_backup) if safety_backup else None,
        }


backup_service = BackupService()
