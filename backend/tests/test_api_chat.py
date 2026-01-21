from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.schemas import Message
from app.schemas import TriageState

client = TestClient(app)

def test_chat_endpoint_returns_ticket_created():
    fake_state = TriageState(messages=[Message(role="assistant", content="Ticket created")])
    fake_state.ticket_created = True
    fake_state.ticket_id = 123

    with patch("app.main.run_triage_turn", new=AsyncMock(return_value=fake_state)):
        r = client.post("/chat", json={"message":"Fire sprinkler burst"})
    assert r.status_code == 200
    data = r.json()
    assert data["ticket_created"] is True
    assert data["ticket_id"] == 123
    assert "Ticket" in data["reply"]
