from app.repositories.assessments import assessment_repository
from app.repositories.audit import audit_repository
from app.repositories.catalog import catalog_repository
from app.repositories.evidences import evidence_repository
from app.repositories.organizations import organization_repository
from app.repositories.recommendations import recommendation_repository
from app.repositories.responses import response_repository
from app.repositories.users import user_repository

__all__ = [
    "assessment_repository",
    "audit_repository",
    "catalog_repository",
    "evidence_repository",
    "organization_repository",
    "recommendation_repository",
    "response_repository",
    "user_repository",
]
