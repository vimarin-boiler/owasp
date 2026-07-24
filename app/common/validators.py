from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class PasswordValidation:
    valid: bool
    errors: tuple[str, ...]


def normalize_email(value: str) -> str:
    return value.strip().casefold()


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match(normalize_email(value)))


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = SLUG_RE.sub("-", ascii_value).strip("-")
    return slug or "organization"


def validate_password(password: str, min_length: int = 12) -> PasswordValidation:
    errors: list[str] = []
    if len(password) < min_length:
        errors.append(f"Debe contener al menos {min_length} caracteres.")
    if not any(char.islower() for char in password):
        errors.append("Debe incluir al menos una letra minúscula.")
    if not any(char.isupper() for char in password):
        errors.append("Debe incluir al menos una letra mayúscula.")
    if not any(char.isdigit() for char in password):
        errors.append("Debe incluir al menos un número.")
    if not any(not char.isalnum() for char in password):
        errors.append("Debe incluir al menos un carácter especial.")
    return PasswordValidation(valid=not errors, errors=tuple(errors))
