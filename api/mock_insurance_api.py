"""Mock Insurance API built with FastAPI.

Provides endpoints to simulate insurance company APIs for:
- Coverage verification
- Pre-authorization requirement checks
- Claim submission and processing
- COB determination
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from api.plan_data import PLANS, get_plan


app = FastAPI(
    title="DuCO-Agent Mock Insurance API",
    description="Simulated insurance company API for COB processing",
    version="1.0.0"
)


# ─── Request/Response Models ───

class CoverageVerifyRequest(BaseModel):
    patient_name: str
    cpt_codes: list[str]
    estimated_cost: float


class CoverageVerifyResponse(BaseModel):
    plan_id: str
    patient_name: str
    is_covered: bool
    patient_role: str  # "primary_holder" or "dependent"
    in_network: bool
    deductible_remaining: float
    coinsurance_rate: float
    oop_remaining: float
    covered_codes: list[str]
    uncovered_codes: list[str]


class PreAuthCheckRequest(BaseModel):
    patient_name: str
    cpt_codes: list[str]
    estimated_cost: float
    procedure_type: str  # "surgery" or "therapy"


class PreAuthCheckResponse(BaseModel):
    plan_id: str
    requires_preauth: bool
    reason: str
    preauth_codes: list[str]  # Which codes need pre-auth


class ClaimSubmitRequest(BaseModel):
    patient_name: str
    cpt_codes: list[str]
    icd_codes: list[str]
    total_charge: float
    is_primary: bool
    prior_payments: float = 0.0  # Amount already paid by another plan (for COB)


class ClaimSubmitResponse(BaseModel):
    plan_id: str
    claim_id: str
    patient_name: str
    total_charge: float
    deductible_applied: float
    coinsurance_plan_pays: float
    coinsurance_patient_pays: float
    plan_total_payment: float
    patient_responsibility: float
    remaining_for_secondary: float
    eob_summary: str


class COBDeterminationRequest(BaseModel):
    patient_name: str
    plan_a_id: str
    plan_b_id: str


class COBDeterminationResponse(BaseModel):
    patient_name: str
    primary_plan_id: str
    secondary_plan_id: str
    determination_rule: str
    explanation: str


# ─── Endpoints ───

@app.get("/api/v1/plans/{plan_id}/details")
def get_plan_details(plan_id: str):
    """Get full plan details including coverage parameters."""
    try:
        plan = get_plan(plan_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "plan_id": plan.plan_id,
        "insurer_name": plan.insurer_name,
        "plan_name": plan.plan_name,
        "primary_holder": plan.primary_holder.name,
        "dependents": [d.name for d in plan.dependents],
        "coverage": {
            "annual_deductible": plan.coverage.annual_deductible,
            "coinsurance_rate": plan.coverage.coinsurance_rate,
            "oop_maximum": plan.coverage.oop_maximum,
            "preauth_all_surgery": plan.coverage.preauth_all_surgery,
            "preauth_surgery_threshold": plan.coverage.preauth_surgery_threshold,
            "covered_cpt_codes": plan.coverage.covered_cpt_codes,
        }
    }


@app.post("/api/v1/plans/{plan_id}/verify-coverage", response_model=CoverageVerifyResponse)
def verify_coverage(plan_id: str, request: CoverageVerifyRequest):
    """Verify if a patient's procedures are covered under a plan."""
    try:
        plan = get_plan(plan_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Determine patient's role on this plan
    patient_role = "unknown"
    if plan.primary_holder.name == request.patient_name:
        patient_role = "primary_holder"
    else:
        for dep in plan.dependents:
            if dep.name == request.patient_name:
                patient_role = "dependent"
                break

    if patient_role == "unknown":
        raise HTTPException(
            status_code=404,
            detail=f"{request.patient_name} not found on plan {plan_id}"
        )

    # Check which codes are covered
    covered = [c for c in request.cpt_codes if c in plan.coverage.covered_cpt_codes]
    uncovered = [c for c in request.cpt_codes if c not in plan.coverage.covered_cpt_codes]

    deductible_remaining = max(0, plan.coverage.annual_deductible - plan.deductible_used)

    return CoverageVerifyResponse(
        plan_id=plan_id,
        patient_name=request.patient_name,
        is_covered=len(covered) > 0,
        patient_role=patient_role,
        in_network=True,  # Assume in-network for this demo
        deductible_remaining=deductible_remaining,
        coinsurance_rate=plan.coverage.coinsurance_rate,
        oop_remaining=plan.coverage.oop_maximum,
        covered_codes=covered,
        uncovered_codes=uncovered
    )


@app.post("/api/v1/plans/{plan_id}/check-preauth-requirement", response_model=PreAuthCheckResponse)
def check_preauth_requirement(plan_id: str, request: PreAuthCheckRequest):
    """Check if pre-authorization is required for the procedures."""
    try:
        plan = get_plan(plan_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    requires_preauth = False
    preauth_codes = []
    reason = "No pre-authorization required."

    if request.procedure_type == "surgery":
        # Plan B requires pre-auth for ALL surgeries
        if plan.coverage.preauth_all_surgery:
            requires_preauth = True
            preauth_codes = request.cpt_codes
            reason = f"Plan {plan_id} requires pre-authorization for all surgical procedures."
        # Plan A requires pre-auth if cost exceeds threshold
        elif request.estimated_cost > plan.coverage.preauth_surgery_threshold:
            requires_preauth = True
            preauth_codes = request.cpt_codes
            reason = (
                f"Estimated cost ₹{request.estimated_cost:,.0f} exceeds "
                f"pre-authorization threshold of ₹{plan.coverage.preauth_surgery_threshold:,.0f}."
            )

    return PreAuthCheckResponse(
        plan_id=plan_id,
        requires_preauth=requires_preauth,
        reason=reason,
        preauth_codes=preauth_codes
    )


@app.post("/api/v1/plans/{plan_id}/submit-claim", response_model=ClaimSubmitResponse)
def submit_claim(plan_id: str, request: ClaimSubmitRequest):
    """Process a claim submission and return EOB (Explanation of Benefits)."""
    try:
        plan = get_plan(plan_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    total_charge = request.total_charge
    deductible_remaining = max(0, plan.coverage.annual_deductible - plan.deductible_used)

    if request.is_primary:
        # Primary claim processing
        deductible_applied = min(deductible_remaining, total_charge)
        after_deductible = total_charge - deductible_applied
        plan_pays = round(after_deductible * plan.coverage.coinsurance_rate, 2)
        patient_pays_coinsurance = round(after_deductible - plan_pays, 2)
        patient_responsibility = deductible_applied + patient_pays_coinsurance
        remaining_for_secondary = total_charge - plan_pays
    else:
        # Secondary claim processing (COB)
        # Secondary pays on what's remaining after primary
        remaining_amount = total_charge - request.prior_payments
        deductible_applied = min(deductible_remaining, remaining_amount)
        after_deductible = max(0, remaining_amount - deductible_applied)
        plan_pays = round(after_deductible * plan.coverage.coinsurance_rate, 2)
        patient_pays_coinsurance = round(after_deductible - plan_pays, 2)
        patient_responsibility = deductible_applied + patient_pays_coinsurance
        remaining_for_secondary = 0.0  # No further plans

    import uuid
    claim_id = f"CLM-{plan_id}-{uuid.uuid4().hex[:8].upper()}"

    eob_summary = (
        f"EOB for {request.patient_name} | Plan: {plan_id}\n"
        f"Total Charge: ₹{total_charge:,.2f}\n"
        f"Deductible Applied: ₹{deductible_applied:,.2f}\n"
        f"Plan Pays ({plan.coverage.coinsurance_rate*100:.0f}%): ₹{plan_pays:,.2f}\n"
        f"Patient Coinsurance: ₹{patient_pays_coinsurance:,.2f}\n"
        f"Patient Total Responsibility: ₹{patient_responsibility:,.2f}"
    )

    return ClaimSubmitResponse(
        plan_id=plan_id,
        claim_id=claim_id,
        patient_name=request.patient_name,
        total_charge=total_charge,
        deductible_applied=deductible_applied,
        coinsurance_plan_pays=plan_pays,
        coinsurance_patient_pays=patient_pays_coinsurance,
        plan_total_payment=plan_pays,
        patient_responsibility=patient_responsibility,
        remaining_for_secondary=remaining_for_secondary,
        eob_summary=eob_summary
    )


@app.post("/api/v1/plans/{plan_id}/cob-determination", response_model=COBDeterminationResponse)
def determine_cob(plan_id: str, request: COBDeterminationRequest):
    """Determine primary vs. secondary plan for a patient using Employee-First Rule."""
    try:
        plan_a = get_plan(request.plan_a_id)
        plan_b = get_plan(request.plan_b_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    patient = request.patient_name

    # Employee-First Rule: The plan where patient is the primary holder is primary
    if plan_a.primary_holder.name == patient:
        primary_plan = request.plan_a_id
        secondary_plan = request.plan_b_id
        rule = "Employee-First Rule"
        explanation = (
            f"{patient} is the primary policyholder (employee) on {request.plan_a_id}. "
            f"Therefore {request.plan_a_id} is PRIMARY and {request.plan_b_id} is SECONDARY."
        )
    elif plan_b.primary_holder.name == patient:
        primary_plan = request.plan_b_id
        secondary_plan = request.plan_a_id
        rule = "Employee-First Rule"
        explanation = (
            f"{patient} is the primary policyholder (employee) on {request.plan_b_id}. "
            f"Therefore {request.plan_b_id} is PRIMARY and {request.plan_a_id} is SECONDARY."
        )
    else:
        # Patient is a dependent on both — use Birthday Rule
        primary_plan = request.plan_a_id
        secondary_plan = request.plan_b_id
        rule = "Birthday Rule (fallback)"
        explanation = f"{patient} is a dependent on both plans. Using Birthday Rule."

    return COBDeterminationResponse(
        patient_name=patient,
        primary_plan_id=primary_plan,
        secondary_plan_id=secondary_plan,
        determination_rule=rule,
        explanation=explanation
    )
