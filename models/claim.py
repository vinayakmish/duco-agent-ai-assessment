"""Data models for insurance claims and Explanation of Benefits."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ClaimLine:
    """A single line item on a claim."""
    cpt_code: str
    description: str
    charge_amount: float
    icd_codes: list[str] = field(default_factory=list)


@dataclass
class Claim:
    """An insurance claim for processing."""
    claim_id: str
    patient_name: str
    claim_type: str  # "surgery" or "therapy"
    line_items: list[ClaimLine] = field(default_factory=list)
    total_charge: float = 0.0
    icd_codes: list[str] = field(default_factory=list)
    requires_preauth: bool = False

    def __post_init__(self):
        if self.total_charge == 0 and self.line_items:
            self.total_charge = sum(item.charge_amount for item in self.line_items)


@dataclass
class EOB:
    """Explanation of Benefits — what an insurer pays."""
    plan_id: str
    claim_id: str
    is_primary: bool
    total_charge: float
    deductible_applied: float
    amount_after_deductible: float
    plan_pays: float  # What the plan pays
    patient_coinsurance: float  # Patient's coinsurance share
    patient_responsibility: float  # Total patient owes
    remaining_for_secondary: float  # What goes to secondary plan


@dataclass
class COBResult:
    """Final result of Coordination of Benefits processing."""
    patient_name: str
    claim_type: str
    total_charge: float
    primary_plan_id: str
    secondary_plan_id: str
    primary_eob: Optional[EOB] = None
    secondary_eob: Optional[EOB] = None
    total_plan_payments: float = 0.0
    final_patient_oop: float = 0.0
    savings_vs_single: float = 0.0  # How much saved via COB
    single_plan_oop: float = 0.0  # What patient would pay without COB
    determination_rule: str = ""
    validation_passed: bool = False
    validation_message: str = ""
