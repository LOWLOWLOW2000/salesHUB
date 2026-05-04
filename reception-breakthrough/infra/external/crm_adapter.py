"""CRM adapter contract for the reception-breakthrough module."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, TypeAlias

LeadId: TypeAlias = str
PhoneNumber: TypeAlias = str
LeadFilters: TypeAlias = Mapping[str, object]


class CRMAdapterError(Exception):
    """Base error for CRM adapter failures."""


class CRMConnectionError(CRMAdapterError):
    """Raised when the adapter cannot reach the backing CRM."""


class LeadNotFoundError(CRMAdapterError):
    """Raised when a lead id is not known to the adapter."""


class LeadAlreadyLockedError(CRMAdapterError):
    """Raised when another worker already owns the lead lock."""


@dataclass(frozen=True, slots=True)
class LeadTarget:
    id: LeadId
    company_name: str
    phone: PhoneNumber
    industry: str | None
    last_called_at: datetime | None
    next_call_at: datetime | None
    status: str


@dataclass(frozen=True, slots=True)
class CallResult:
    session_id: str
    lead_id: LeadId
    outcome_id: str
    final_state_id: str
    rejection_reason: str | None
    callback_at: datetime | None
    started_at: datetime
    ended_at: datetime
    mode: str


class CRMAdapter(ABC):
    """Synchronous contract for reading targets and writing call results."""

    @abstractmethod
    def fetch_call_targets(
        self,
        limit: int,
        filters: LeadFilters | None = None,
    ) -> list[LeadTarget]:
        """Return at most ``limit`` leads that match ``filters``."""

    @abstractmethod
    def update_call_result(self, result: CallResult) -> bool:
        """Persist a call result. Must be idempotent on ``session_id``."""

    @abstractmethod
    def mark_lead_locked(self, lead_id: LeadId, locked_by: str) -> bool:
        """Lock a lead for exclusive handling."""

    @abstractmethod
    def release_lead_lock(self, lead_id: LeadId, locked_by: str) -> None:
        """Release a lead lock held by ``locked_by``."""
