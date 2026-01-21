import pytest
from unittest.mock import AsyncMock, patch

from app.schemas import Message
from app.schemas import TriageState  # or wherever your TriageState is
from app.orchestrator import run_triage_turn
from tests.fake_supabase import FakeSupabase
from tests.fakes import FakeLLMResponse

@pytest.mark.asyncio
async def test_orchestrator_emergency_creates_ticket_without_calling_llm():
    supabase = FakeSupabase()
    llm_client = object()  # unused if we pre-escalate

    state = TriageState(messages=[Message(role="user", content="Fire sprinkler burst")])

    # Patch chat_turn to ensure it is NOT called
    with patch("app.orchestrator.chat_turn", new=AsyncMock()) as mock_chat:
        state2 = await run_triage_turn(llm_client, supabase, state)

    assert state2.ticket_created is True
    assert state2.ticket_id == 1
    assert len(supabase.rows) == 1
    assert "sprinkler" in supabase.rows[0]["summary"].lower()
    mock_chat.assert_not_called()

@pytest.mark.asyncio
async def test_orchestrator_non_escalation_calls_llm_and_returns_reply():
    supabase = FakeSupabase()
    llm_client = object()

    state = TriageState(messages=[Message(role="user", content="My faucet drips a little")])

    with patch("app.orchestrator.chat_turn", new=AsyncMock(return_value=FakeLLMResponse(output_text="Can you confirm if it's from the base or handle?"))) as mock_chat:
        state2 = await run_triage_turn(llm_client, supabase, state)

    assert state2.ticket_created is False
    assert state2.messages[-1].role == "assistant"
    assert "confirm" in state2.messages[-1].content.lower()
    mock_chat.assert_awaited_once()
