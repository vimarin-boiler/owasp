from __future__ import annotations

from app.common.errors import ConflictError, ValidationError
from app.common.validators import slugify
from app.extensions import db
from app.models import Organization
from app.repositories.organizations import organization_repository
from app.services.audit_service import audit_service


class OrganizationService:
    def _unique_slug(self, name: str, current_id: int | None = None) -> str:
        base = slugify(name)
        candidate = base
        counter = 2
        while True:
            existing = organization_repository.get_by_slug(candidate)
            if existing is None or existing.id == current_id:
                return candidate
            candidate = f"{base}-{counter}"
            counter += 1

    def create(
        self,
        *,
        name: str,
        legal_name: str | None,
        tax_identifier: str | None,
        description: str | None,
        actor_id: int,
        is_active: bool = True,
    ) -> Organization:
        if not name.strip():
            raise ValidationError("El nombre de la organización es obligatorio.")
        organization = Organization(
            name=name.strip(),
            slug=self._unique_slug(name),
            legal_name=legal_name.strip() if legal_name else None,
            tax_identifier=tax_identifier.strip() if tax_identifier else None,
            description=description.strip() if description else None,
            created_by_id=actor_id,
            updated_by_id=actor_id,
            is_active=is_active,
            status="active" if is_active else "inactive",
        )
        db.session.add(organization)
        audit_service.record(
            action="organization.created",
            entity_type="organization",
            entity_public_id=organization.public_id,
            actor_user_id=actor_id,
            after={
                "name": organization.name,
                "slug": organization.slug,
                "is_active": organization.is_active,
            },
        )
        db.session.commit()
        return organization

    def update(
        self,
        organization: Organization,
        *,
        name: str,
        legal_name: str | None,
        tax_identifier: str | None,
        description: str | None,
        is_active: bool,
        actor_id: int,
    ) -> Organization:
        if not name.strip():
            raise ValidationError("El nombre de la organización es obligatorio.")
        before = {
            "name": organization.name,
            "legal_name": organization.legal_name,
            "tax_identifier": organization.tax_identifier,
            "is_active": organization.is_active,
        }
        organization.name = name.strip()
        organization.slug = self._unique_slug(name, organization.id)
        organization.legal_name = legal_name.strip() if legal_name else None
        organization.tax_identifier = tax_identifier.strip() if tax_identifier else None
        organization.description = description.strip() if description else None
        organization.is_active = is_active
        organization.status = "active" if is_active else "inactive"
        organization.updated_by_id = actor_id
        audit_service.record(
            action="organization.updated",
            entity_type="organization",
            entity_public_id=organization.public_id,
            actor_user_id=actor_id,
            organization_id=organization.id,
            before=before,
            after={
                "name": organization.name,
                "legal_name": organization.legal_name,
                "tax_identifier": organization.tax_identifier,
                "is_active": organization.is_active,
            },
        )
        db.session.commit()
        return organization


organization_service = OrganizationService()
