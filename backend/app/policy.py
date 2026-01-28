# app/policy.py
from typing import Optional, List, Tuple
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
        return True, "P0_EMERGENCY", "Immediate danger (fire/gas/electrical/flood/structural)."

    # rain intrusion (window/roof/wall)
    if any(k in text for k in ["rain", "storm"]) and any(k in text for k in ["window", "roof", "wall"]) and any(k in text for k in ["leak", "leaking", "water inside", "water coming in"]):
        return True, "P2_SOON", "Rain/water intrusion from outside."

    # persistent leak
    if any(k in text for k in ["leak", "leaking", "drip", "dripping"]) and any(k in text for k in ["comes back", "when the water is on", "still leaking", "won't stop", "cannot stop", "can't stop"]):
        return True, "P1_URGENT", "Leak persists or returns."

    # habitability
    habitability = ["no heat", "no hot water", "no power", "power out", "electricity out"]
    if any(k in text for k in habitability) and any(k in text for k in ["still", "not working", "checked", "breaker", "switch", "thermostat"]):
        return True, "P1_URGENT", "Habitability impacted and unresolved after basic checks."

    return False, "P2_SOON", ""

def detect_emergency(latest_text: str) -> Tuple[bool, Optional[str], str]:
    """
    Returns (is_emergency, emergency_type, reason)
    emergency_type: "gas"|"fire"|"electrical"|"flooding"|"structural"|None
    """
    t = (latest_text or "").lower()

    # GAS
    if any(k in t for k in ["gas smell", "smell gas", "gas leak", "rotten eggs"]):
        return True, "gas", "Possible gas leak."

    # FIRE / SMOKE
    if any(k in t for k in ["fire", "smoke"]):
        return True, "fire", "Fire/smoke reported."

    # ELECTRICAL HAZARD (high-signal only)
    if any(k in t for k in ["sparking", "sparks", "arcing", "electric shock", "shocked me", "burning smell"]) and any(
        k in t for k in ["outlet", "switch", "panel", "breaker", "light", "fixture", "wire"]
    ):
        return True, "electrical", "Electrical hazard reported."

    # WATER + ELECTRICAL (very dangerous)
    if any(k in t for k in ["water dripping through light", "dripping through light", "water in light", "light fixture"]) and any(
        k in t for k in ["water", "drip", "leak", "leaking"]
    ):
        return True, "electrical", "Water near electrical fixture."

    # MAJOR FLOODING / UNCONTROLLED WATER
    if any(k in t for k in ["major flooding", "flooding", "uncontrolled water", "water pouring", "pouring water", "won't stop", "can't stop"]):
        return True, "flooding", "Uncontrolled flooding."

    # STRUCTURAL IMMEDIATE DANGER
    if any(k in t for k in ["ceiling bulging", "ceiling sagging", "structural collapse", "about to fall"]):
        return True, "structural", "Possible structural hazard."

    return False, None, ""