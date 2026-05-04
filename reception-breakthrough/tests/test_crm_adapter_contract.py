from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from infra.external.crm_adapter import (
    CRMAdapter,
    CallResult,
    LeadAlreadyLockedError,
    LeadId,
    LeadNotFoundError,
    LeadTarget,
)


class InMemoryCRMAdapter(CRMAdapter):
    def __init__(self, leads: list[LeadTarget]) -> None:
        self._leads = {lead.id: lead for lead in leads}
        self._locks: dict[LeadId, str] = {}
        self._results: dict[str, CallResult] = {}

    def fetch_call_targets(
        self,
        limit: int,
        filters: dict[str, object] | None = None,
    ) -> list[LeadTarget]:
        filters = filters or {}
        items = list(self._leads.values())
        for key, expected in filters.items():
            items = [item for item in items if getattr(item, key) == expected]
        return items[:limit]

    def update_call_result(self, result: CallResult) -> bool:
        if result.lead_id not in self._leads:
            raise LeadNotFoundError(result.lead_id)

        if result.session_id in self._results:
            return True

        self._results[result.session_id] = result
        lead = self._leads[result.lead_id]
        self._leads[result.lead_id] = replace(
            lead,
            last_called_at=result.ended_at,
            next_call_at=result.callback_at,
            status=result.outcome_id,
        )
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


@pytest.fixture
def adapter() -> InMemoryCRMAdapter:
    now = datetime(2026, 5, 4, 12, 0, 0)
    leads = [
        LeadTarget(
            id="lead-1",
            company_name="Acme KK",
            phone="03-0000-0001",
            industry="manufacturing",
            last_called_at=None,
            next_call_at=None,
            status="new",
        ),
        LeadTarget(
            id="lead-2",
            company_name="Bravo KK",
            phone="03-0000-0002",
            industry="it",
            last_called_at=now - timedelta(days=1),
            next_call_at=None,
            status="queued",
        ),
    ]
    return InMemoryCRMAdapter(leads)


def test_fetch_call_targets_filters_and_limit(adapter: InMemoryCRMAdapter) -> None:
    manufacturing = adapter.fetch_call_targets(limit=10, filters={"industry": "manufacturing"})
    limited = adapter.fetch_call_targets(limit=1, filters={})

    assert [lead.id for lead in manufacturing] == ["lead-1"]
    assert len(limited) == 1


def test_update_call_result_round_trip_and_idempotency(adapter: InMemoryCRMAdapter) -> None:
    started_at = datetime(2026, 5, 4, 12, 0, 0)
    ended_at = started_at + timedelta(minutes=3)
    callback_at = ended_at + timedelta(days=1)
    result = CallResult(
        session_id="session-1",
        lead_id="lead-1",
        outcome_id="OUT_ABSENT",
        final_state_id="S10",
        rejection_reason=None,
        callback_at=callback_at,
        started_at=started_at,
        ended_at=ended_at,
        mode="HUMAN",
    )

    assert adapter.update_call_result(result) is True
    assert adapter.update_call_result(result) is True

    updated = adapter.fetch_call_targets(limit=1, filters={"id": "lead-1"})[0]
    assert updated.last_called_at == ended_at
    assert updated.next_call_at == callback_at
    assert updated.status == "OUT_ABSENT"
    assert len(adapter._results) == 1


def test_lock_and_release_lead(adapter: InMemoryCRMAdapter) -> None:
    assert adapter.mark_lead_locked("lead-1", locked_by="worker-a") is True

    with pytest.raises(LeadAlreadyLockedError):
        adapter.mark_lead_locked("lead-1", locked_by="worker-b")

    adapter.release_lead_lock("lead-1", locked_by="worker-a")
    assert adapter.mark_lead_locked("lead-1", locked_by="worker-b") is True


def test_update_call_result_raises_for_unknown_lead(adapter: InMemoryCRMAdapter) -> None:
    result = CallResult(
        session_id="session-missing",
        lead_id="missing",
        outcome_id="OUT_NOISE",
        final_state_id="S11",
        rejection_reason=None,
        callback_at=None,
        started_at=datetime(2026, 5, 4, 9, 0, 0),
        ended_at=datetime(2026, 5, 4, 9, 1, 0),
        mode="AI",
    )

    with pytest.raises(LeadNotFoundError):
        adapter.update_call_result(result)
