"""Text Parser for user query intent and entity extraction."""
import re
from dataclasses import dataclass, field


@dataclass
class QueryIntent:
    """Parsed intent from user's voice-to-text query."""
    raw_text: str
    patients_mentioned: list[str] = field(default_factory=list)
    plans_mentioned: list[str] = field(default_factory=list)
    claims_identified: list[str] = field(default_factory=list)
    actions_requested: list[str] = field(default_factory=list)


class TextParser:
    """Parser for extracting intents and entities from user queries."""

    PATIENT_PATTERNS = {
        "aarav": "Aarav Sen",
        "priya": "Priya Sen",
    }

    PLAN_PATTERNS = {
        "plan a": "Plan A (Insurer1)",
        "plan b": "Plan B (Insurer2)",
        "insurer1": "Plan A (Insurer1)",
        "insurer2": "Plan B (Insurer2)",
    }

    CLAIM_PATTERNS = {
        "surgery": "ACL Reconstruction Surgery",
        "knee": "ACL Reconstruction Surgery",
        "operated": "ACL Reconstruction Surgery",
        "operation": "ACL Reconstruction Surgery",
        "physical therapy": "Physical Therapy Sessions",
        "pt": "Physical Therapy Sessions",
        "therapy bills": "Physical Therapy Sessions",
    }

    ACTION_PATTERNS = {
        "which plan pays first": "determine_primary_secondary",
        "pays first": "determine_primary_secondary",
        "out of.*pocket": "calculate_oop",
        "how much.*pay": "calculate_oop",
        "pre-auth": "generate_preauth",
        "pre-authorization": "generate_preauth",
        "preauth": "generate_preauth",
        "claim rejection": "generate_preauth",
    }

    def parse_query(self, text: str) -> QueryIntent:
        """Extract intents and entities from user query text."""
        lower_text = text.lower()
        intent = QueryIntent(raw_text=text)

        # Extract patients
        for pattern, name in self.PATIENT_PATTERNS.items():
            if pattern in lower_text and name not in intent.patients_mentioned:
                intent.patients_mentioned.append(name)

        # Extract plans
        for pattern, plan in self.PLAN_PATTERNS.items():
            if pattern in lower_text and plan not in intent.plans_mentioned:
                intent.plans_mentioned.append(plan)

        # Extract claims
        for pattern, claim in self.CLAIM_PATTERNS.items():
            if pattern in lower_text and claim not in intent.claims_identified:
                intent.claims_identified.append(claim)

        # Extract requested actions
        for pattern, action in self.ACTION_PATTERNS.items():
            if re.search(pattern, lower_text) and action not in intent.actions_requested:
                intent.actions_requested.append(action)

        return intent
