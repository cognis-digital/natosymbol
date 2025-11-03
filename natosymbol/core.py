"""Core SIDC engine for APP-6 / MIL-STD-2525C.

The Symbol Identification Code (SIDC) is a 15-character string. Positions are
1-indexed in the standard; here we use 0-indexed Python slices internally.

  Pos 1     Coding Scheme        (S, G, W, I, O, E ...)
  Pos 2     Affiliation          (P,U,A,F,N,S,H,G,W,M,D,L,J,K)
  Pos 3     Battle Dimension     (P,A,G,S,U,F,X,Z)
  Pos 4     Status / Planning    (A,P,...)
  Pos 5-10  Function ID          (6 chars, scheme-specific; '-' = unused)
  Pos 11    Symbol Modifier 1    (HQ / TF / Feint-Dummy)
  Pos 12    Symbol Modifier 2    (echelon / mobility)
  Pos 13-14 Country code         (2 char ISO-ish or '--')
  Pos 15    Order of Battle

Unused positions are filled with '-' (hyphen) per the standard.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Optional

SIDC_LENGTH = 15
PAD = "-"


class SIDCError(ValueError):
    """Raised when a SIDC is structurally or semantically invalid."""


# --- Code tables (1=position character -> human label) ----------------------

CODING_SCHEMES = {
    "S": "Warfighting",
    "G": "Tactical Graphics",
    "W": "Meteorological / Oceanographic",
    "I": "Signals Intelligence",
    "O": "Stability Operations",
    "E": "Emergency Management",
}

AFFILIATIONS = {
    "P": "Pending",
    "U": "Unknown",
    "A": "Assumed Friend",
    "F": "Friend",
    "N": "Neutral",
    "S": "Suspect",
    "H": "Hostile",
    "G": "Exercise Pending",
    "W": "Exercise Unknown",
    "M": "Exercise Friend",
    "D": "Exercise Neutral",
    "L": "Exercise Assumed Friend",
    "J": "Joker",
    "K": "Faker",
}

BATTLE_DIMENSIONS = {
    "P": "Space",
    "A": "Air",
    "G": "Ground",
    "S": "Sea Surface",
    "U": "Sea Subsurface",
    "F": "SOF",
    "X": "Other / Unknown",
    "Z": "Unknown Dimension",
}

STATUS = {
    "A": "Anticipated / Planned",
    "P": "Present",
    "C": "Present / Fully Capable",
    "D": "Present / Damaged",
    "X": "Present / Destroyed",
    "F": "Present / Full to Capacity",
}

ORDER_OF_BATTLE = {
    "A": "Air OB",
    "E": "Electronic OB",
    "C": "Civilian OB",
    "G": "Ground OB",
    "N": "Maritime OB",
    "S": "SOF OB",
}

# Symbol modifier position 11 (HQ / Task Force / Feint-Dummy indicator).
MODIFIER_1 = {
    "-": "None",
    "A": "Feint / Dummy",
    "B": "Headquarters",
    "C": "Feint/Dummy Headquarters",
    "D": "Task Force",
    "E": "Feint/Dummy Task Force",
    "F": "Task Force Headquarters",
    "G": "Feint/Dummy Task Force Headquarters",
}

# Symbol modifier position 12 (echelon / mobility / towed).
MODIFIER_2 = {
    "-": "None",
    "A": "Team / Crew",
    "B": "Squad",
    "C": "Section",
    "D": "Platoon / Detachment",
    "E": "Company / Battery / Troop",
    "F": "Battalion / Squadron",
    "G": "Regiment / Group",
    "H": "Brigade",
    "I": "Division",
    "J": "Corps / MEF",
    "K": "Army",
    "L": "Army Group / Front",
    "M": "Region / Theater",
    "N": "Command",
}

# A small, real Function-ID dictionary for the Warfighting scheme so that
# describe_sidc produces meaningful output for the most common units. Keyed by
# (battle_dimension, function_id_6chars). Not exhaustive (the full 2525C list is
# thousands of entries) but covers canonical examples and is data-driven.
FUNCTION_IDS = {
    ("G", "UCI---"): "Infantry",
    ("G", "UCR---"): "Armor / Armored",
    ("G", "UCF---"): "Field Artillery",
    ("G", "UCA---"): "Anti-Armor",
    ("G", "UCE---"): "Engineer",
    ("G", "UCAA--"): "Air Defense",
    ("G", "UUS---"): "Signal",
    ("G", "UUM---"): "Medical",
    ("G", "UCAW--"): "Anti-Tank/Anti-Armor (Wheeled)",
    ("A", "MF----"): "Military Fixed Wing",
    ("A", "MFF---"): "Fighter",
    ("A", "MFB---"): "Bomber",
    ("A", "MH----"): "Military Rotary Wing",
    ("A", "MFKB--"): "Tanker / Refuel",
    ("S", "CLCV--"): "Surface Combatant (Carrier)",
    ("S", "CLDD--"): "Destroyer",
    ("S", "CLFF--"): "Frigate",
    ("U", "SNN---"): "Submarine (Nuclear)",
    ("U", "SNF---"): "Submarine (Diesel/Fast Attack)",
}

_ALPHANUM = re.compile(r"^[A-Z0-9\-]$")


@dataclass
class SIDC:
    """Parsed, structured representation of a 15-char SIDC."""

    code: str
    coding_scheme: str
    affiliation: str
    battle_dimension: str
    status: str
    function_id: str
    modifier_1: str
    modifier_2: str
    country: str
    order_of_battle: str

    def to_dict(self) -> dict:
        return asdict(self)

    def describe(self) -> dict:
        return describe_sidc(self)


def _norm(value: Optional[str], width: int) -> str:
    """Uppercase, pad with '-' to width, validate charset."""
    v = (value or "").upper()
    if len(v) > width:
        raise SIDCError(f"field too long: {value!r} (max {width})")
    v = v.ljust(width, PAD)
    for ch in v:
        if not _ALPHANUM.match(ch):
            raise SIDCError(f"illegal character {ch!r} in field {value!r}")
    return v


def build_sidc(
    coding_scheme: str = "S",
    affiliation: str = "U",
    battle_dimension: str = "G",
    status: str = "P",
    function_id: str = "",
    modifier_1: str = "-",
    modifier_2: str = "-",
    country: str = "--",
    order_of_battle: str = "-",
) -> str:
    """Assemble a 15-char SIDC from its component fields.

    Raises SIDCError on out-of-range field values.
    """
    cs = _norm(coding_scheme, 1)
    af = _norm(affiliation, 1)
    bd = _norm(battle_dimension, 1)
    st = _norm(status, 1)
    fn = _norm(function_id, 6)
    m1 = _norm(modifier_1, 1)
    m2 = _norm(modifier_2, 1)
    cc = _norm(country, 2)
    ob = _norm(order_of_battle, 1)

    code = cs + af + bd + st + fn + m1 + m2 + cc + ob
    if len(code) != SIDC_LENGTH:
        raise SIDCError(f"assembled length {len(code)} != {SIDC_LENGTH}")
    # Validate the produced code semantically before returning.
    validate_sidc(code)
    return code


def parse_sidc(code: str) -> SIDC:
    """Parse a 15-char SIDC string into a structured SIDC object."""
    if not isinstance(code, str):
        raise SIDCError("SIDC must be a string")
    code = code.strip().upper()
    if len(code) != SIDC_LENGTH:
        raise SIDCError(f"SIDC must be {SIDC_LENGTH} chars, got {len(code)}: {code!r}")
    for ch in code:
        if not _ALPHANUM.match(ch):
            raise SIDCError(f"illegal character {ch!r} in SIDC {code!r}")
    return SIDC(
        code=code,
        coding_scheme=code[0],
        affiliation=code[1],
        battle_dimension=code[2],
        status=code[3],
        function_id=code[4:10],
        modifier_1=code[10],
        modifier_2=code[11],
        country=code[12:14],
        order_of_battle=code[14],
    )


def validate_sidc(code: str) -> SIDC:
    """Validate a SIDC and return its parsed form.

    Raises SIDCError describing the first semantic problem found.
    """
    s = parse_sidc(code)
    errors = []
    if s.coding_scheme not in CODING_SCHEMES:
        errors.append(f"unknown coding scheme {s.coding_scheme!r}")
    if s.affiliation not in AFFILIATIONS:
        errors.append(f"unknown affiliation {s.affiliation!r}")
    if s.battle_dimension not in BATTLE_DIMENSIONS:
        errors.append(f"unknown battle dimension {s.battle_dimension!r}")
    if s.status not in STATUS:
        errors.append(f"unknown status {s.status!r}")
    if s.modifier_1 not in MODIFIER_1:
        errors.append(f"unknown symbol modifier-1 {s.modifier_1!r}")
    if s.modifier_2 not in MODIFIER_2:
        errors.append(f"unknown symbol modifier-2 {s.modifier_2!r}")
    if s.order_of_battle != PAD and s.order_of_battle not in ORDER_OF_BATTLE:
        errors.append(f"unknown order of battle {s.order_of_battle!r}")
    if errors:
        raise SIDCError("; ".join(errors))
    return s


def describe_sidc(code_or_obj) -> dict:
    """Return a fully human-readable description of every field."""
    s = code_or_obj if isinstance(code_or_obj, SIDC) else parse_sidc(code_or_obj)
    fn_label = FUNCTION_IDS.get(
        (s.battle_dimension, s.function_id),
        "Unspecified / Unknown function" if s.function_id == "------" else "Unmapped function ID",
    )
    return {
        "code": s.code,
        "coding_scheme": {"code": s.coding_scheme, "label": CODING_SCHEMES.get(s.coding_scheme, "UNKNOWN")},
        "affiliation": {"code": s.affiliation, "label": AFFILIATIONS.get(s.affiliation, "UNKNOWN")},
        "battle_dimension": {"code": s.battle_dimension, "label": BATTLE_DIMENSIONS.get(s.battle_dimension, "UNKNOWN")},
        "status": {"code": s.status, "label": STATUS.get(s.status, "UNKNOWN")},
        "function_id": {"code": s.function_id, "label": fn_label},
        "modifier_1": {"code": s.modifier_1, "label": MODIFIER_1.get(s.modifier_1, "UNKNOWN")},
        "modifier_2": {"code": s.modifier_2, "label": MODIFIER_2.get(s.modifier_2, "UNKNOWN")},
        "country": {"code": s.country, "label": "Unspecified" if s.country == "--" else s.country},
        "order_of_battle": {
            "code": s.order_of_battle,
            "label": "None" if s.order_of_battle == PAD else ORDER_OF_BATTLE.get(s.order_of_battle, "UNKNOWN"),
        },
    }
