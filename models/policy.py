"""Data models for insurance policies and policyholders."""
from dataclasses import dataclass
from enum import Enum


class PatientRole(Enum):
    """Role of patient on an insurance plan."""
    PRIMARY_HOLDER = "primary_holder"
    DEPENDENT = "dependent"


class PlanPriority(Enum):
    """Priority designation in COB."""
    PRIMARY = "primary"
    SECONDARY = "secondary"


@dataclass
class PatientInfo:
    """Patient information for claim processing."""
    name: str
    dob: str
    plan_a_role: PatientRole  # Role on Plan A
    plan_b_role: PatientRole  # Role on Plan B


# Pre-defined patients
AARAV = PatientInfo(
    name="Aarav Sen",
    dob="1986-07-22",
    plan_a_role=PatientRole.DEPENDENT,
    plan_b_role=PatientRole.PRIMARY_HOLDER
)

PRIYA = PatientInfo(
    name="Priya Sen",
    dob="1988-03-15",
    plan_a_role=PatientRole.PRIMARY_HOLDER,
    plan_b_role=PatientRole.DEPENDENT
)
