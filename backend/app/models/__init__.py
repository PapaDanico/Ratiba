"""SQLAlchemy ORM models.

Importing this package registers every model with the declarative ``Base``
metadata, which Alembic's autogenerate relies on.
"""

from app.models.audit import AuditEvent
from app.models.base import TimestampMixin, UUIDMixin
from app.models.crew import ContractType, Crew, CrewRole
from app.models.ftl import FdpType, FlightDutyPeriod, FtlRule, LegalityState, RuleSource
from app.models.leave import LeaveRequest, LeaveStatus, LeaveType
from app.models.operator import Operator, OperatorTier
from app.models.pairing import PairingToken
from app.models.roster import Sector, SectorAssignment, SectorStatus
from app.models.swap import SwapRequest, SwapStatus
from app.models.training import CrewCurrency, CrewTypeRating, CurrencyType
from app.models.user import User, UserRole

__all__ = [
    "AuditEvent",
    "ContractType",
    "Crew",
    "CrewCurrency",
    "CrewRole",
    "CrewTypeRating",
    "CurrencyType",
    "FdpType",
    "FlightDutyPeriod",
    "FtlRule",
    "LeaveRequest",
    "LeaveStatus",
    "LeaveType",
    "LegalityState",
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
