# app/policy.py
from typing import List, Tuple
from .schemas import Message

def should_escalate(msgs: List[Message]) -> Tuple[bool, str, str]:
    """
    Returns: (needs_ticket, urgency, reason)
    """
    text = " ".join(m.content.lower() for m in msgs)

    emergency = [
        "fire", "smoke", "burning smell", "sparking",
        "gas smell", "smell gas", "gas leak",
        "major flooding", "flooding", "uncontrolled water",
        "water dripping through light", "dripping through light", "light fixture",
        "electrocution", "outlet", "electrical panel", "breaker box",
        "ceiling bulging", "ceiling sagging", "structural",
    ]
    if any(k in text for k in emergency):
        return True, "Emergency", "Immediate danger (fire/gas/electrical/flood/structural)."

    # rain intrusion (window/roof/wall)
    if any(k in text for k in ["rain", "storm"]) and any(k in text for k in ["window", "roof", "wall"]) and any(k in text for k in ["leak", "leaking", "water inside", "water coming in"]):
        return True, "Medium", "Rain/water intrusion from outside."

    # persistent leak
    if any(k in text for k in ["leak", "leaking", "drip", "dripping"]) and any(k in text for k in ["comes back", "when the water is on", "still leaking", "won't stop", "cannot stop", "can't stop"]):
        return True, "High", "Leak persists or returns."

    # habitability
    habitability = ["no heat", "no hot water", "no power", "power out", "electricity out"]
    if any(k in text for k in habitability) and any(k in text for k in ["still", "not working", "checked", "breaker", "switch", "thermostat"]):
        return True, "High", "Habitability impacted and unresolved after basic checks."

    return False, "Medium", ""
