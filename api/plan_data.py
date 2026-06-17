"""Insurance plan data and configuration.

Mock data for Plan A (Insurer1) and Plan B (Insurer2).
These values are configurable — actual policy values were not provided
in the assessment. See README for assumptions.
"""
from dataclasses import dataclass, field


@dataclass
class CoverageDetails:
    """Coverage parameters for an insurance plan."""
    annual_deductible: float
    coinsurance_rate: float  # What the plan pays (e.g., 0.80 = 80%)
    coinsurance_rate_oon: float  # Out-of-network rate
    oop_maximum: float
    preauth_surgery_threshold: float  # Pre-auth required if cost exceeds this
    preauth_all_surgery: bool  # If True, all surgeries need pre-auth
    pt_sessions_per_year: int
    pt_copay_per_session: float
    covered_cpt_codes: list[str] = field(default_factory=list)
    network_hospitals: list[str] = field(default_factory=list)


@dataclass
class PolicyMember:
    """A member on an insurance policy."""
    name: str
    relationship: str  # "self" or "spouse"
    dob: str
    employee_id: str
    policy_number: str


@dataclass
class InsurancePlan:
    """Complete insurance plan with members and coverage."""
    plan_id: str
    insurer_name: str
    plan_name: str
    primary_holder: PolicyMember
    dependents: list[PolicyMember]
    coverage: CoverageDetails
    deductible_used: float = 0.0  # Amount of deductible already used this year


# ─── Plan A (Insurer1 — Priya is primary holder) ───
PLAN_A = InsurancePlan(
    plan_id="PLAN_A",
    insurer_name="Insurer1",
    plan_name="Corporate Health Shield - Plan A",
    primary_holder=PolicyMember(
        name="Priya Sen",
        relationship="self",
        dob="1988-03-15",
        employee_id="EMP-A-10234",
        policy_number="INS1-2024-HLT-78432"
    ),
    dependents=[
        PolicyMember(
            name="Aarav Sen",
            relationship="spouse",
            dob="1986-07-22",
            employee_id="",
            policy_number="INS1-2024-HLT-78432-D1"
        )
    ],
    coverage=CoverageDetails(
        annual_deductible=10000.0,
        coinsurance_rate=0.80,
        coinsurance_rate_oon=0.60,
        oop_maximum=100000.0,
        preauth_surgery_threshold=100000.0,
        preauth_all_surgery=False,
        pt_sessions_per_year=20,
        pt_copay_per_session=2000.0,
        covered_cpt_codes=["29888", "29881", "97161", "97110"],
        network_hospitals=["Mumbai Ortho Center", "City Surgical Hospital"]
    )
)

# ─── Plan B (Insurer2 — Aarav is primary holder) ───
PLAN_B = InsurancePlan(
    plan_id="PLAN_B",
    insurer_name="Insurer2",
    plan_name="Premium Health Plus - Plan B",
    primary_holder=PolicyMember(
        name="Aarav Sen",
        relationship="self",
        dob="1986-07-22",
        employee_id="EMP-B-55891",
        policy_number="INS2-2024-HLT-91205"
    ),
    dependents=[
        PolicyMember(
            name="Priya Sen",
            relationship="spouse",
            dob="1988-03-15",
            employee_id="",
            policy_number="INS2-2024-HLT-91205-D1"
        )
    ],
    coverage=CoverageDetails(
        annual_deductible=15000.0,
        coinsurance_rate=0.70,
        coinsurance_rate_oon=0.50,
        oop_maximum=150000.0,
        preauth_surgery_threshold=0.0,
        preauth_all_surgery=True,
        pt_sessions_per_year=30,
        pt_copay_per_session=1500.0,
        covered_cpt_codes=["29888", "29881", "97161", "97110"],
        network_hospitals=["Mumbai Ortho Center", "National Knee Institute"]
    )
)

PLANS = {"PLAN_A": PLAN_A, "PLAN_B": PLAN_B}


def get_plan(plan_id: str) -> InsurancePlan:
    """Retrieve a plan by ID."""
    if plan_id not in PLANS:
        raise ValueError(f"Unknown plan: {plan_id}. Available: {list(PLANS.keys())}")
    return PLANS[plan_id]


def get_member_plan(patient_name: str, as_role: str = "self") -> InsurancePlan | None:
    """Find the plan where a patient has a specific role."""
    for plan in PLANS.values():
        if as_role == "self" and plan.primary_holder.name == patient_name:
            return plan
        if as_role == "dependent":
            for dep in plan.dependents:
                if dep.name == patient_name:
                    return plan
    return None
