"""SQLAlchemy ORM models.

Importing this package registers every model with the declarative ``Base``
metadata, which Alembic's autogenerate relies on.
"""

from app.models.aircraft import Aircraft
from app.models.audit import AuditEvent
from app.models.audit_pack import AuditPack
from app.models.base import TimestampMixin, UUIDMixin
from app.models.constraint import (
    ConstraintReviewComment,
    ConstraintReviewStatus,
    ConstraintRule,
    ConstraintSet,
    ConstraintSetStatus,
)
from app.models.crew import ContractType, Crew, CrewRole
from app.models.document import CrewDocument, DocumentType
from app.models.ftl import FdpType, FlightDutyPeriod, FtlRule, LegalityState, RuleSource
from app.models.leave import LeaveRequest, LeaveStatus, LeaveType
from app.models.llm_usage import LlmUsageEvent
from app.models.notice import (
    Notice,
    NoticeAcknowledgement,
    NoticeCategory,
    NoticeSeverity,
)
from app.models.operator import Operator, OperatorTier
from app.models.pairing import PairingToken
from app.models.roster import Sector, SectorAssignment, SectorStatus
from app.models.swap import SwapRequest, SwapStatus
from app.models.training import CrewCurrency, CrewTypeRating, CurrencyType
from app.models.user import User, UserRole

__all__ = [
    "Aircraft",
    "AuditEvent",
    "AuditPack",
    "ConstraintReviewComment",
    "ConstraintReviewStatus",
    "ConstraintRule",
    "ConstraintSet",
    "ConstraintSetStatus",
    "ContractType",
    "Crew",
    "CrewCurrency",
    "CrewDocument",
    "CrewRole",
    "CrewTypeRating",
    "CurrencyType",
    "DocumentType",
    "FdpType",
    "FlightDutyPeriod",
    "FtlRule",
    "LeaveRequest",
    "LeaveStatus",
    "LeaveType",
    "LegalityState",
    "LlmUsageEvent",
    "Notice",
    "NoticeAcknowledgement",
    "NoticeCategory",
    "NoticeSeverity",
    "Operator",
    "OperatorTier",
    "PairingToken",
    "RuleSource",
    "Sector",
    "SectorAssignment",
    "SectorStatus",
    "SwapRequest",
    "SwapStatus",
    "TimestampMixin",
    "UUIDMixin",
    "User",
    "UserRole",
]
