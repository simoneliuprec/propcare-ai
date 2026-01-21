from app.schemas import Message
from app.policy import should_escalate

def test_emergency_sprinkler_burst_escalates():
    msgs = [Message(role="user", content="Fire sprinkler burst and water is spraying everywhere")]
    needs, urgency, reason = should_escalate(msgs)
    assert needs is True
    assert urgency == "Emergency"
    assert "danger" in reason.lower() or "emergency" in reason.lower()

def test_minor_issue_no_escalation():
    msgs = [Message(role="user", content="My cabinet door is loose.")]
    needs, urgency, reason = should_escalate(msgs)
    assert needs is False
