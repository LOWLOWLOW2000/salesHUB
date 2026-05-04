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


# ---------------------------------------------------------------------------
# インメモリ実装 — 開発・テスト・デモ用
# ---------------------------------------------------------------------------


class InMemoryCRMAdapter(CRMAdapter):
    """スレッドセーフではないシンプルなインメモリ CRM アダプター。

    開発・デモ・単体テスト用。本番では外部 CRM と繋ぐ実装に差し替える。

    API サーバーでの利用では :meth:`register_lead` でリードをキューに積み、
    :meth:`pop_next_lead` で 1 件ずつ取り出す形で使う。
    """

    def __init__(self) -> None:
        self._leads: dict[LeadId, dict] = {}
        self._queue: list[LeadId] = []
        self._locks: dict[LeadId, str] = {}
        self._results: dict[str, CallResult] = {}

    # ── 追加 API（架電キュー管理） ───────────────────────────────────────────

    def register_lead(self, lead_id: LeadId, **meta: object) -> None:
        """リードをキューに追加する。

        Args:
            lead_id: リードの一意 ID。
            **meta: ``company``, ``contact_name``, ``phone`` 等の任意属性。
        """
        self._leads[lead_id] = {"lead_id": lead_id, **meta}
        if lead_id not in self._queue:
            self._queue.append(lead_id)

    def pop_next_lead(self) -> dict | None:
        """キューの先頭からリードを 1 件取り出す。空の場合は ``None``。"""
        if not self._queue:
            return None
        lead_id = self._queue.pop(0)
        return self._leads.get(lead_id)

    # ── CRMAdapter 実装 ───────────────────────────────────────────────────

    def fetch_call_targets(
        self,
        limit: int,
        filters: LeadFilters | None = None,
    ) -> list[LeadTarget]:
        filters = filters or {}
        items: list[dict] = list(self._leads.values())
        for key, expected in filters.items():
            items = [item for item in items if item.get(key) == expected]

        targets: list[LeadTarget] = []
        for item in items[:limit]:
            targets.append(
                LeadTarget(
                    id=item["lead_id"],
                    company_name=item.get("company", ""),
                    phone=item.get("phone", ""),
                    industry=item.get("industry"),
                    last_called_at=None,
                    next_call_at=None,
                    status=item.get("status", "new"),
                )
            )
        return targets

    def update_call_result(self, result: CallResult) -> bool:
        if result.lead_id not in self._leads:
            raise LeadNotFoundError(result.lead_id)
        if result.session_id in self._results:
            return True
        self._results[result.session_id] = result
        self._leads[result.lead_id]["status"] = result.outcome_id
        return True

    def mark_lead_locked(self, lead_id: LeadId, locked_by: str) -> bool:
        if lead_id not in self._leads:
            raise LeadNotFoundError(lead_id)
        if lead_id in self._locks and self._locks[lead_id] != locked_by:
            raise LeadAlreadyLockedError(lead_id)
        self._locks[lead_id] = locked_by
        return True

    def release_lead_lock(self, lead_id: LeadId, locked_by: str) -> None:
        if lead_id not in self._leads:
            raise LeadNotFoundError(lead_id)
        if self._locks.get(lead_id) == locked_by:
            del self._locks[lead_id]
