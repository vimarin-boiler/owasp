from enum import StrEnum


class RoleCode(StrEnum):
    ADMIN = "admin"
    RESPONDENT = "respondent"
    REVIEWER = "reviewer"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class QuestionnaireStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class QuestionRevisionStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AssessmentStatus(StrEnum):
    DRAFT = "draft"
    CONFIGURED = "configured"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    OBSERVED = "observed"
    COMPLETED = "completed"
    PUBLISHED = "published"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class AssignmentRole(StrEnum):
    RESPONDENT = "respondent"
    REVIEWER = "reviewer"


class ResponseStatus(StrEnum):
    UNANSWERED = "unanswered"
    DRAFT = "draft"
    ANSWERED = "answered"
    SUBMITTED = "submitted"
    OBSERVED = "observed"
    REJECTED = "rejected"
    APPROVED = "approved"


class ReviewDecision(StrEnum):
    APPROVED = "approved"
    OBSERVED = "observed"
    REJECTED = "rejected"
    REOPENED = "reopened"


class EvidenceValidationStatus(StrEnum):
    PENDING = "pending"
    VALID = "valid"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


class RecommendationPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationStatus(StrEnum):
    OPEN = "open"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


class ScoringSource(StrEnum):
    DECLARED = "declared"
    REVIEWED = "reviewed"
    APPROVED = "approved"


class NotificationStatus(StrEnum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"
